from __future__ import annotations

import json
import os
import queue
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import SessionLocal
from .models import ApiCredential, GenerationJob, ProviderConfig
from .provider_registry import (
    ProviderSpec,
    get_provider_specs,
    is_valid_slug,
    merge_provider_specs,
    normalize_slug,
    normalize_wire_api,
)
from .security import decrypt_api_key
from .settings import BASE_DIR, RUNS_DIR, settings


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _cancel_flag_path(run_id: str) -> Path:
    return RUNS_DIR / run_id / "cancel.flag"


def _is_cancel_requested(run_id: str) -> bool:
    try:
        return _cancel_flag_path(run_id).exists()
    except Exception:
        return False


def _stdout_reader(pipe, out_queue: "queue.Queue[Optional[str]]") -> None:
    try:
        if pipe is None:
            return
        for line in iter(pipe.readline, ""):
            out_queue.put(line)
    finally:
        out_queue.put(None)


def _job_status_is_running(db: Session, job_id: int) -> bool:
    # Use a fresh DB session to avoid stale transaction snapshots.
    _ = db  # keep signature stable for existing callers
    with SessionLocal() as s:
        fresh = s.get(GenerationJob, job_id)
        return bool(fresh and fresh.status == "running")


def _custom_provider_specs_for_user(db: Session, user_id: int) -> dict[str, ProviderSpec]:
    rows = (
        db.execute(
            select(ProviderConfig).where(ProviderConfig.user_id == user_id)
        )
        .scalars()
        .all()
    )
    specs: dict[str, ProviderSpec] = {}
    for row in rows:
        slug = normalize_slug(row.slug)
        if not is_valid_slug(slug):
            continue
        base_url = (row.base_url or "").strip()
        model = (row.model or "").strip()
        if not base_url or not model:
            continue
        specs[slug] = ProviderSpec(
            slug=slug,
            label=(row.label or "").strip() or slug.upper(),
            base_url=base_url,
            model=model,
            wire_api=normalize_wire_api(row.wire_api),
        )
    return specs


def _provider_env(
    provider: str,
    api_key: str,
    provider_specs: Optional[dict[str, ProviderSpec]] = None,
) -> dict[str, str]:
    provider = provider.lower().strip()
    provider_specs = provider_specs or get_provider_specs(settings)
    spec = provider_specs.get(provider)
    if not spec:
        raise ValueError(f"Unsupported provider: {provider}")

    env = {
        "LLM_PROVIDER": provider,
        "LLM_API_KEY": api_key,
        "LLM_BASE_URL": spec.base_url,
        "MODEL_NAME": spec.model,
        "WIRE_API": spec.wire_api,
        "RUNS_DIR": str(RUNS_DIR),
        "MAX_ITERATIONS": str(settings.max_iterations),
        "MAX_TOTAL_ITERATIONS": str(settings.max_total_iterations),
        "FAST_MODE": "1" if settings.fast_mode else "0",
        "FULL_CYCLE_INTERVAL": str(settings.full_cycle_interval),
        "CHAPTERS_PER_ITER": str(settings.chapters_per_iter),
        "MAX_CHAPTER_SUBROUNDS": str(settings.max_chapter_subrounds),
        "EVAL_INTERVAL": str(settings.eval_interval),
        "LLM_TIMEOUT_SECONDS": os.getenv("LLM_TIMEOUT_SECONDS", "0"),
        "LLM_MAX_RETRIES": os.getenv("LLM_MAX_RETRIES", "1"),
        "EMBEDDING_MODEL": "none",
        # Keep default behavior close to original pipeline (full-rag).
        "MEMORY_ONLY_MODE": os.getenv("WEB_MEMORY_ONLY_MODE", "0"),
        "ENABLE_RAG": os.getenv("WEB_ENABLE_RAG", "1"),
        "ENABLE_STATIC_KB": os.getenv("WEB_ENABLE_STATIC_KB", "1"),
        "ENABLE_EVALUATOR": os.getenv("WEB_ENABLE_EVALUATOR", "1"),
        # Force UTF-8 output from worker process on Windows to avoid mojibake.
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        # Force unbuffered stdout/stderr so web tail logs update in near real-time.
        "PYTHONUNBUFFERED": "1",
    }

    # Backward-compat env aliases used by legacy config paths.
    env["OPENAI_API_KEY"] = api_key
    env["OPENAI_BASE_URL"] = spec.base_url

    if provider == "deepseek":
        env["DEEPSEEK_API_KEY"] = api_key
        env["DEEPSEEK_BASE_URL"] = spec.base_url
    elif provider == "openai":
        env["OPENAI_API_KEY"] = api_key
        env["OPENAI_BASE_URL"] = spec.base_url
    elif provider == "codex":
        env["CODEX_API_KEY"] = api_key
        env["CODEX_BASE_URL"] = spec.base_url

    return env


def _save_job_artifacts(run_id: str, result: dict) -> tuple[str, str]:
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    output_path = run_dir / "output.txt"
    result_json_path = run_dir / "result.json"
    round_results_path = run_dir / "round_results.json"
    metadata_path = run_dir / "metadata.json"
    final_text = result.get("final_text", "")

    header_lines = [
        f"主题: {result.get('topic', '')}",
        f"文本类型: {result.get('text_type', '')}",
        f"文本长度: {result.get('length', 0)} 字",
        f"迭代次数: {result.get('iterations', 0)}",
        f"最佳奖励分数: {result.get('best_reward', 0):.3f}",
        "",
        "=" * 60,
        "生成的文本：",
        "=" * 60,
        "",
        final_text,
    ]
    output_path.write_text("\n".join(header_lines), encoding="utf-8")

    metadata = {
        "run_id": run_id,
        "topic": result.get("topic", ""),
        "text_type": result.get("text_type", ""),
        "genre": result.get("genre", ""),
        "style_tags": result.get("style_tags", []),
        "length": result.get("length", 0),
        "iterations": result.get("iterations", 0),
        "chapters_written": result.get("chapters_written", 0),
        "best_reward": result.get("best_reward", 0),
        "consistency": result.get("consistency", {}),
        "created_at": datetime.now().isoformat(),
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    result_json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    round_results_path.write_text(
        json.dumps(result.get("round_results", []), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return str(output_path), final_text[:600].strip()


def _tail_text(path: Path, max_chars: int = 4000) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")[-max_chars:]
    except Exception:
        return ""


def _run_worker_subprocess(
    idea: str,
    provider: str,
    api_key: str,
    run_id: str,
    provider_specs: Optional[dict[str, ProviderSpec]] = None,
    is_running_check: Optional[Callable[[], bool]] = None,
) -> dict:
    worker_out = RUNS_DIR / run_id / "worker_result.json"
    worker_out.parent.mkdir(parents=True, exist_ok=True)
    worker_log = RUNS_DIR / run_id / "worker.log"
    cancel_flag = _cancel_flag_path(run_id)
    try:
        if cancel_flag.exists():
            cancel_flag.unlink()
    except Exception:
        pass

    cmd = [
        sys.executable,
        "-u",
        "-m",
        "local_web_portal.worker_process",
        "--idea",
        idea,
        "--output-json",
        str(worker_out),
    ]

    env = os.environ.copy()
    env.update(_provider_env(provider, api_key, provider_specs=provider_specs))
    env["RUN_ID"] = run_id

    process = subprocess.Popen(
        cmd,
        cwd=str(BASE_DIR.parent),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    started = time.monotonic()
    last_output_at = started
    line_queue: "queue.Queue[Optional[str]]" = queue.Queue()
    reader = threading.Thread(target=_stdout_reader, args=(process.stdout, line_queue), daemon=True)
    reader.start()
    stdout_closed = False

    with worker_log.open("a", encoding="utf-8", buffering=1) as log_fp:
        log_fp.write(f"[system] worker started pid={process.pid} run_id={run_id}\n")
        log_fp.flush()
        while True:
            line: Optional[str]
            try:
                line = line_queue.get(timeout=0.2)
            except queue.Empty:
                line = ""
            if line is None:
                stdout_closed = True
            elif line:
                clean = line.rstrip("\n")
                if clean:
                    last_output_at = time.monotonic()
                    log_fp.write(clean + "\n")
                    log_fp.flush()
                    print(f"[worker][job:{run_id}] {clean}")

            if is_running_check and not is_running_check():
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                log_fp.write("[system] worker terminated because job is no longer running.\n")
                log_fp.flush()
                raise RuntimeError("Job canceled while worker was running.")
            if _is_cancel_requested(run_id):
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                log_fp.write("[system] worker terminated by cancel flag.\n")
                log_fp.flush()
                raise RuntimeError("Job canceled while worker was running.")

            now = time.monotonic()
            if settings.job_timeout_seconds > 0 and now - started > settings.job_timeout_seconds:
                process.kill()
                log_fp.write("[system] worker killed due to timeout.\n")
                log_fp.flush()
                raise TimeoutError(f"Worker exceeded timeout: {settings.job_timeout_seconds}s")

            if settings.job_idle_timeout_seconds > 0 and now - last_output_at > settings.job_idle_timeout_seconds:
                process.kill()
                log_fp.write("[system] worker killed due to idle timeout.\n")
                log_fp.flush()
                raise TimeoutError(f"Worker exceeded idle timeout: {settings.job_idle_timeout_seconds}s")

            if process.poll() is not None and (stdout_closed or line_queue.empty()):
                break

    return_code = process.wait()

    if not worker_out.exists():
        raise RuntimeError(
            "Worker did not produce output file.\n"
            f"log_tail:\n{_tail_text(worker_log, max_chars=2500)}"
        )

    payload = json.loads(worker_out.read_text(encoding="utf-8"))
    payload["_stdout"] = _tail_text(worker_log, max_chars=4000)
    payload["_stderr"] = ""
    payload["_returncode"] = return_code
    payload["_worker_log_path"] = str(worker_log)
    return payload


def run_generation_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.get(GenerationJob, job_id)
        if not job:
            return

        job.status = "running"
        job.updated_at = _utcnow()
        db.commit()

        cred_stmt = select(ApiCredential).where(
            ApiCredential.user_id == job.user_id,
            ApiCredential.provider == job.provider,
        )
        credential = db.execute(cred_stmt).scalar_one_or_none()
        if not credential:
            raise RuntimeError("No API key saved for this provider.")

        run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_u{job.user_id}_j{job.id}"
        job.run_id = run_id
        job.updated_at = _utcnow()
        db.commit()

        raw_api_key = decrypt_api_key(credential.encrypted_key)
        provider_specs = merge_provider_specs(
            get_provider_specs(settings),
            _custom_provider_specs_for_user(db, job.user_id).values(),
            allow_override=False,
        )
        worker_payload = _run_worker_subprocess(
            job.idea,
            job.provider,
            raw_api_key,
            run_id,
            provider_specs=provider_specs,
            is_running_check=lambda: _job_status_is_running(db, job_id),
        )

        if not _job_status_is_running(db, job_id):
            return

        if not worker_payload.get("ok"):
            worker_error = worker_payload.get("error", "Unknown worker error.")
            worker_tb = worker_payload.get("traceback", "")
            worker_stderr = worker_payload.get("_stderr", "")
            raise RuntimeError(
                f"{worker_error}\n\n{worker_tb}\n\nworker_stderr:\n{worker_stderr}"
            )

        result = worker_payload.get("result", {})
        output_path, excerpt = _save_job_artifacts(run_id, result)

        job.status = "succeeded"
        job.run_id = run_id
        job.output_path = output_path
        job.result_excerpt = excerpt
        job.error_message = ""
        job.finished_at = _utcnow()
        job.updated_at = _utcnow()
        db.commit()
    except Exception as exc:
        job = db.get(GenerationJob, job_id, populate_existing=True)
        if job and job.status == "running":
            if job.run_id:
                run_dir = RUNS_DIR / job.run_id
                run_dir.mkdir(parents=True, exist_ok=True)
                (run_dir / "error.txt").write_text(str(exc), encoding="utf-8")
            job.status = "failed"
            job.error_message = str(exc)[:4000]
            job.finished_at = _utcnow()
            job.updated_at = _utcnow()
            db.commit()
    finally:
        db.close()
