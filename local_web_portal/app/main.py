from __future__ import annotations

import json
import re
import shutil
import threading
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from agents.idea_copilot_agent import (
    IdeaCopilotAgent,
    append_assistant_turn,
    append_user_reply,
    build_generation_idea,
    dump_state,
    latest_assistant_turn,
    load_state,
)
from .db import SessionLocal, engine, get_db
from .job_runner import run_generation_job
from .models import ApiCredential, Base, GenerationJob, IdeaCopilotSession, ProviderConfig, User
from .provider_registry import (
    ProviderSpec,
    get_provider_specs,
    is_valid_slug,
    merge_provider_specs,
    normalize_slug,
    normalize_wire_api,
)
from .security import SESSION_SECRET, decrypt_api_key, encrypt_api_key, hash_password, verify_password
from .settings import BASE_DIR, RUNS_DIR, settings

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")

EVENT_LABELS = {
    "global_outline": "Global outline",
    "chapter_outline_ready": "Chapter outlines ready",
    "chapter_plan": "Chapter plan",
    "chapter_outline": "Chapter outline",
    "chapter_length_plan": "Chapter length plan",
    "chapter_length_warning": "Chapter length warning",
    "character_setting": "Character setting",
    "world_setting": "World setting",
    "memory_snapshot": "Memory snapshot",
}

MEMORY_COUNT_KEYS = (
    "texts",
    "outlines",
    "characters",
    "world_settings",
    "plot_points",
    "fact_cards",
)

app = FastAPI(title=settings.app_name)
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="lax",
    https_only=settings.https_only,
)

app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    # Recover jobs left in non-terminal state after a server/process restart.
    # Note: web jobs run in daemon threads; after restart those threads are gone.
    with SessionLocal() as db:
        now = datetime.now(timezone.utc)
        running_cutoff = now - timedelta(seconds=max(60, settings.startup_recovery_seconds))
        queued_cutoff = now - timedelta(seconds=max(60, settings.stale_queued_seconds))

        stale_running_jobs = db.execute(
            select(GenerationJob).where(
                GenerationJob.status == "running",
                GenerationJob.updated_at < running_cutoff,
            )
        ).scalars().all()
        stale_queued_jobs = db.execute(
            select(GenerationJob).where(
                GenerationJob.status == "queued",
                GenerationJob.created_at < queued_cutoff,
            )
        ).scalars().all()

        for job in stale_running_jobs:
            job.status = "failed"
            prefix = (job.error_message + "\n") if job.error_message else ""
            job.error_message = prefix + "[system] marked as failed after app restart (worker thread was lost)."
            job.finished_at = now
            job.updated_at = now

        for job in stale_queued_jobs:
            job.status = "failed"
            prefix = (job.error_message + "\n") if job.error_message else ""
            job.error_message = prefix + "[system] queued too long without active worker; marked failed on startup."
            job.finished_at = now
            job.updated_at = now

        if stale_running_jobs or stale_queued_jobs:
            db.commit()


def _current_user(request: Request, db: Session) -> Optional[User]:
    uid = request.session.get("uid")
    if not uid:
        return None
    return db.get(User, uid)


def _require_user(request: Request, db: Session) -> User:
    user = _current_user(request, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return user


def _redirect(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=status.HTTP_303_SEE_OTHER)


def _mask_hint(raw: str) -> str:
    if len(raw) < 8:
        return "********"
    return f"{raw[:4]}...{raw[-4:]}"


def _tail_text(path: Path, max_chars: int = 12000) -> str:
    if not path.exists():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")[-max_chars:]
        return ANSI_ESCAPE_RE.sub("", text)
    except Exception:
        return ""


def _resolve_run_dir(run_id: str) -> Path:
    primary = RUNS_DIR / run_id
    if primary.exists():
        return primary
    legacy = BASE_DIR / "runs" / run_id
    if legacy.exists():
        return legacy
    return primary


def _list_custom_providers(db: Session, user_id: int) -> List[ProviderConfig]:
    return (
        db.execute(
            select(ProviderConfig)
            .where(ProviderConfig.user_id == user_id)
            .order_by(ProviderConfig.slug.asc())
        )
        .scalars()
        .all()
    )


def _custom_provider_specs_for_user(db: Session, user_id: int) -> Dict[str, ProviderSpec]:
    specs: Dict[str, ProviderSpec] = {}
    for row in _list_custom_providers(db, user_id):
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


def _provider_specs_for_user(db: Session, user_id: int) -> Dict[str, ProviderSpec]:
    base_specs = get_provider_specs(settings)
    custom_specs = _custom_provider_specs_for_user(db, user_id)
    return merge_provider_specs(base_specs, custom_specs.values(), allow_override=False)


def _provider_api_key(db: Session, user_id: int, provider: str) -> str:
    row = db.execute(
        select(ApiCredential).where(
            ApiCredential.user_id == user_id,
            ApiCredential.provider == provider,
        )
    ).scalar_one_or_none()
    if not row:
        raise ValueError("Save your API key for that provider first")
    try:
        return decrypt_api_key(row.encrypted_key)
    except Exception as exc:
        raise ValueError(f"Failed to decrypt API key: {exc}") from exc


def _create_generation_job(db: Session, user_id: int, provider: str, idea: str) -> GenerationJob:
    job = GenerationJob(
        user_id=user_id,
        provider=provider,
        idea=idea,
        status="queued",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _start_generation_worker(job_id: int) -> None:
    worker = threading.Thread(target=run_generation_job, args=(job_id,), daemon=True)
    worker.start()


def _to_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _default_progress_snapshot() -> Dict:
    return {
        "phase": "running",
        "phase_label": "运行中",
        "phase_note": "",
        "elapsed_seconds": 0,
        "current_chapter": 0,
        "planned_total": 0,
        "chapter_words": 0,
        "total_words": 0,
        "percent": 0,
        "last_log_at": "",
        "idle_seconds": -1,
        "stalled": False,
        "stall_reason": "",
        "memory_counts": {
            "texts": 0,
            "outlines": 0,
            "characters": 0,
            "world_settings": 0,
            "plot_points": 0,
            "fact_cards": 0,
        },
    }


def _parse_progress_log(progress_log_text: str) -> Dict:
    snapshot = {
        "current_chapter": 0,
        "planned_total": 0,
        "chapter_words": 0,
        "total_words": 0,
        "phase_note": "",
        "memory_counts": {k: 0 for k in MEMORY_COUNT_KEYS},
    }
    if not progress_log_text:
        return snapshot

    for raw in progress_log_text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("chapter="):
            try:
                parts = dict(
                    kv.strip().split("=", 1)
                    for kv in line.split(",")
                    if "=" in kv
                )
                snapshot["current_chapter"] = int(parts.get("chapter", snapshot["current_chapter"]))
                snapshot["planned_total"] = int(parts.get("planned_total", snapshot["planned_total"]))
                snapshot["chapter_words"] = int(parts.get("words", snapshot["chapter_words"]))
            except Exception:
                pass
        elif line.startswith("total_words="):
            try:
                snapshot["total_words"] = int(line.split("=", 1)[1].strip())
            except Exception:
                pass
        elif line.startswith("[event]"):
            try:
                parts = [seg.strip() for seg in line.split("|")]
                if len(parts) < 2:
                    continue

                event_name = parts[1]
                detail_parts: List[str] = []
                chapter_no = 0

                for seg in parts[2:]:
                    if seg.startswith("chapter "):
                        m_ch = re.search(r"chapter\s+(\d+)", seg)
                        if m_ch:
                            chapter_no = int(m_ch.group(1))
                    elif seg:
                        detail_parts.append(seg)

                detail = " | ".join(detail_parts)
                if chapter_no > 0:
                    snapshot["current_chapter"] = max(snapshot["current_chapter"], chapter_no)

                if event_name == "chapter_outline_ready" and snapshot["planned_total"] <= 0:
                    m_plan = re.search(r"count\s*=\s*(\d+)", detail)
                    if m_plan:
                        snapshot["planned_total"] = int(m_plan.group(1))

                if event_name == "memory_snapshot":
                    detail_map = {
                        k.strip(): v.strip()
                        for k, v in (
                            item.split("=", 1)
                            for item in detail.split(",")
                            if "=" in item
                        )
                    }
                    for key in MEMORY_COUNT_KEYS:
                        if key in detail_map:
                            try:
                                snapshot["memory_counts"][key] = int(detail_map[key])
                            except Exception:
                                pass

                label = EVENT_LABELS.get(event_name, event_name.replace("_", " "))
                snapshot["phase_note"] = f"{label}: {detail}" if detail else label
            except Exception:
                pass
    return snapshot


def _read_status_file(run_dir: Optional[Path]) -> Dict:
    if not run_dir:
        return {}
    path = run_dir / "status.json"
    if not path.exists():
        return {}
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _infer_phase(worker_log_text: str) -> str:
    if not worker_log_text:
        return "waiting_worker"
    lines = [ln.strip() for ln in worker_log_text.splitlines() if ln.strip()]
    if not lines:
        return "waiting_worker"
    checks = [
        ("Traceback", "error"),
        ("[system] worker started", "worker_started"),
        ("[IdeaAnalyzer]", "idea_analyzing"),
        ("[Analyzer]", "task_analyzing"),
        ("[Organizer]", "planning"),
        ("[Outline]", "outline_building"),
        ("[写作Agent]", "writing"),
        ("[Memory]", "memory_storing"),
        ("[TurningPoint]", "turning_point"),
        ("[Consistency]", "consistency_check"),
        ("[RealtimeEditor]", "editing"),
        ("[Reward]", "reward_calc"),
        ("[Executor] 已完成计划章节数", "finishing"),
    ]
    for line in reversed(lines[-80:]):
        for marker, phase in checks:
            if marker in line:
                return phase
    return "running"


def _infer_action_from_worker_log(worker_log_text: str) -> str:
    if not worker_log_text:
        return ""
    lines = [ln.strip() for ln in worker_log_text.splitlines() if ln.strip()]
    if not lines:
        return ""

    noise_prefixes = (
        "Loading weights:",
        "Key",
        "|",
        "-",
        "[system] worker started",
    )
    for line in reversed(lines[-120:]):
        if not line:
            continue
        if any(line.startswith(p) for p in noise_prefixes):
            continue
        if "BertModel LOAD REPORT" in line:
            continue
        if line.startswith("UNEXPECTED") or line.startswith("[3m"):
            continue
        return line[:180]
    return ""


def _phase_label(phase: str) -> str:
    if phase.startswith("agent_") and phase.endswith("_done"):
        return "Agent step done"
    if phase.startswith("agent_"):
        return "Agent running"
    mapping = {
        "queued": "Queued",
        "running": "Running",
        "succeeded": "Succeeded",
        "failed": "Failed",
        "canceled": "Canceled",
        "waiting_worker": "Waiting worker start",
        "worker_started": "Worker started",
        "idea_analyzing": "Analyzing idea",
        "task_analyzing": "Analyzing task",
        "planning": "Planning",
        "outline_building": "Building outline",
        "writing": "Writing chapter",
        "memory_storing": "Storing memory",
        "turning_point": "Checking turning points",
        "consistency_check": "Consistency check",
        "editing": "Realtime editing",
        "reward_calc": "Calculating reward",
        "finishing": "Finalizing",
        "init": "Initializing",
        "idea_analyzed": "Idea analyzed",
        "planning_done": "Planning done",
        "outline_global_done": "Global outline done",
        "outline_chapters_done": "Chapter outlines done",
        "chapter_start": "Chapter started",
        "chapter_done": "Chapter done",
        "realtime_edit": "Realtime edit",
        "finalizing": "Final output",
        "error": "Error",
    }
    return mapping.get(phase, "Running")


def _build_progress_snapshot(job: GenerationJob, run_dir: Optional[Path], worker_log_text: str, progress_log_text: str) -> Dict:
    now = datetime.now(timezone.utc)
    snapshot = _default_progress_snapshot()
    created_at = _to_utc(job.created_at)
    finished_at = _to_utc(job.finished_at)
    updated_at = _to_utc(job.updated_at)

    terminal = job.status in {"succeeded", "failed", "canceled"}
    end_ref = finished_at or (updated_at if terminal else now)

    elapsed_seconds = 0
    if created_at:
        try:
            elapsed_seconds = max(0, int((end_ref - created_at).total_seconds()))
        except Exception:
            elapsed_seconds = 0

    parsed = _parse_progress_log(progress_log_text)
    current_chapter = parsed["current_chapter"]
    planned_total = parsed["planned_total"]
    chapter_words = parsed["chapter_words"]
    total_words = parsed["total_words"]

    status_state = _read_status_file(run_dir)
    if status_state:
        current_chapter = int(status_state.get("chapter_no") or current_chapter or 0)
        planned_total = int(status_state.get("planned_total") or planned_total or 0)
        chapter_words = int(status_state.get("chapter_words") or chapter_words or 0)
        total_words = int(status_state.get("total_words") or total_words or 0)

    percent = 0
    if planned_total > 0 and current_chapter > 0:
        percent = int(min(100, max(0, (current_chapter / planned_total) * 100)))

    last_log_at = ""
    idle_seconds: Optional[int] = None
    if run_dir:
        worker_log = run_dir / "worker.log"
        if worker_log.exists():
            try:
                mtime = datetime.fromtimestamp(worker_log.stat().st_mtime, tz=timezone.utc)
                last_log_at = mtime.isoformat()
                anchor = end_ref if terminal else now
                idle_seconds = max(0, int((anchor - mtime).total_seconds()))
            except Exception:
                pass

    phase = job.status if terminal else str(status_state.get("stage") or _infer_phase(worker_log_text))
    phase_label = _phase_label(phase)
    phase_note = str(
        status_state.get("message")
        or parsed.get("phase_note")
        or _infer_action_from_worker_log(worker_log_text)
        or ""
    )
    parsed_memory_counts = parsed.get("memory_counts") or {}
    status_memory_counts = status_state.get("memory_counts") or {}
    memory_counts: Dict[str, int] = {}
    for key in MEMORY_COUNT_KEYS:
        raw_val = status_memory_counts.get(key, parsed_memory_counts.get(key, 0))
        try:
            memory_counts[key] = int(raw_val or 0)
        except Exception:
            memory_counts[key] = 0

    stalled = False
    stall_reason = ""
    if job.status == "running":
        if not worker_log_text and elapsed_seconds > 20:
            stalled = True
            stall_reason = "No worker logs yet after 20s; worker may not have started correctly."
        elif idle_seconds is not None and idle_seconds > 90:
            stalled = True
            stall_reason = f"No new logs for {idle_seconds}s; the job may be stalled."

        if status_state and status_state.get("updated_at"):
            try:
                ts = str(status_state.get("updated_at")).replace("Z", "+00:00")
                sdt = datetime.fromisoformat(ts)
                if sdt.tzinfo is None:
                    sdt = sdt.replace(tzinfo=timezone.utc)
                idle_status = max(0, int((now - sdt.astimezone(timezone.utc)).total_seconds()))
                if idle_status > 90:
                    stalled = True
                    stall_reason = f"Status heartbeat not updated for {idle_status}s; the job may be stalled."
            except Exception:
                pass

    snapshot.update(
        {
            "phase": phase,
            "phase_label": phase_label,
            "phase_note": phase_note,
            "elapsed_seconds": elapsed_seconds,
            "current_chapter": current_chapter,
            "planned_total": planned_total,
            "chapter_words": chapter_words,
            "total_words": total_words,
            "percent": percent,
            "last_log_at": last_log_at,
            "idle_seconds": idle_seconds if idle_seconds is not None else -1,
            "stalled": stalled,
            "stall_reason": stall_reason,
            "memory_counts": memory_counts if isinstance(memory_counts, dict) else {},
        }
    )
    return snapshot


def _load_chapter_outputs(run_dir: Path) -> List[Dict]:
    """
    Load latest finalized chapter files from runs/<run_id>/chapters.
    Keep only the highest iteration per chapter.
    """
    chapter_dir = run_dir / "chapters"
    if not chapter_dir.exists():
        return []

    pattern = re.compile(r"^chapter_(\d+)_iter_(\d+)_final\.txt$")
    latest_by_chapter: Dict[int, Dict] = {}

    for path in chapter_dir.glob("chapter_*_iter_*_final.txt"):
        m = pattern.match(path.name)
        if not m:
            continue
        chapter_no = int(m.group(1))
        iteration = int(m.group(2))

        prev = latest_by_chapter.get(chapter_no)
        if prev and iteration <= prev["iteration"]:
            continue

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            content = ""

        latest_by_chapter[chapter_no] = {
            "chapter": chapter_no,
            "iteration": iteration,
            "filename": path.name,
            "content": content.strip(),
        }

    return [latest_by_chapter[k] for k in sorted(latest_by_chapter.keys())]


def _latest_chapter_file(run_dir: Path, chapter_no: int) -> Optional[Path]:
    chapter_dir = run_dir / "chapters"
    if not chapter_dir.exists():
        return None
    pattern = re.compile(rf"^chapter_{chapter_no:02d}_iter_(\d+)_final\.txt$")
    best_path: Optional[Path] = None
    best_iter = -1
    for path in chapter_dir.glob(f"chapter_{chapter_no:02d}_iter_*_final.txt"):
        m = pattern.match(path.name)
        if not m:
            continue
        iteration = int(m.group(1))
        if iteration > best_iter:
            best_iter = iteration
            best_path = path
    return best_path


def _latest_chapter_files(run_dir: Path) -> List[Path]:
    chapter_dir = run_dir / "chapters"
    if not chapter_dir.exists():
        return []
    pattern = re.compile(r"^chapter_(\d+)_iter_(\d+)_final\.txt$")
    latest: Dict[int, Dict[str, object]] = {}
    for path in chapter_dir.glob("chapter_*_iter_*_final.txt"):
        m = pattern.match(path.name)
        if not m:
            continue
        chapter_no = int(m.group(1))
        iteration = int(m.group(2))
        prev = latest.get(chapter_no)
        if prev and iteration <= int(prev["iteration"]):
            continue
        latest[chapter_no] = {"iteration": iteration, "path": path}
    return [latest[k]["path"] for k in sorted(latest.keys()) if isinstance(latest[k]["path"], Path)]


@app.get("/")
def index(request: Request, db: Session = Depends(get_db)):
    if _current_user(request, db):
        return _redirect("/dashboard")
    return _redirect("/login")


@app.get("/register")
def register_page(request: Request, db: Session = Depends(get_db)):
    if _current_user(request, db):
        return _redirect("/dashboard")
    return templates.TemplateResponse("register.html", {"request": request, "error": ""})


@app.post("/register")
def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):
    email = email.strip().lower()
    if not EMAIL_RE.match(email):
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Invalid email format."},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if len(password) < 8:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Password must be at least 8 characters."},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if password != confirm_password:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Passwords do not match."},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    existing = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if existing:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Email already registered."},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    user = User(email=email, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    request.session["uid"] = user.id
    return _redirect("/dashboard")


@app.get("/login")
def login_page(request: Request, db: Session = Depends(get_db)):
    if _current_user(request, db):
        return _redirect("/dashboard")
    return templates.TemplateResponse("login.html", {"request": request, "error": ""})


@app.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    email = email.strip().lower()
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid credentials."},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    request.session["uid"] = user.id
    return _redirect("/dashboard")


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return _redirect("/login")


@app.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = _current_user(request, db)
    if not user:
        return _redirect("/login")
    provider_specs = _provider_specs_for_user(db, user.id)
    provider_list = list(provider_specs.keys())
    custom_providers = _list_custom_providers(db, user.id)

    creds = db.execute(select(ApiCredential).where(ApiCredential.user_id == user.id)).scalars().all()
    cred_map = {c.provider: c for c in creds}

    jobs = (
        db.execute(
            select(GenerationJob)
            .where(GenerationJob.user_id == user.id)
            .order_by(GenerationJob.created_at.desc())
            .limit(20)
        )
        .scalars()
        .all()
    )
    idea_sessions = (
        db.execute(
            select(IdeaCopilotSession)
            .where(IdeaCopilotSession.user_id == user.id)
            .order_by(IdeaCopilotSession.updated_at.desc())
            .limit(20)
        )
        .scalars()
        .all()
    )

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "jobs": jobs,
            "idea_sessions": idea_sessions,
            "cred_map": cred_map,
            "providers": provider_list,
            "provider_specs": provider_specs,
            "custom_providers": custom_providers,
            "default_provider": settings.default_provider if settings.default_provider in provider_specs else (provider_list[0] if provider_list else ""),
            "message": request.query_params.get("message", ""),
            "error": request.query_params.get("error", ""),
        },
    )


@app.post("/api-keys")
def save_api_key(
    request: Request,
    provider: str = Form(...),
    api_key: str = Form(...),
    db: Session = Depends(get_db),
):
    user = _current_user(request, db)
    if not user:
        return _redirect("/login")

    provider = provider.strip().lower()
    api_key = api_key.strip()
    provider_specs = _provider_specs_for_user(db, user.id)

    if provider not in provider_specs:
        return _redirect("/dashboard?error=Unsupported+provider")
    if len(api_key) < 12:
        return _redirect("/dashboard?error=API+key+looks+too+short")

    cred = db.execute(
        select(ApiCredential).where(
            ApiCredential.user_id == user.id,
            ApiCredential.provider == provider,
        )
    ).scalar_one_or_none()

    encrypted = encrypt_api_key(api_key)
    if cred:
        cred.encrypted_key = encrypted
        cred.key_hint = _mask_hint(api_key)
    else:
        cred = ApiCredential(
            user_id=user.id,
            provider=provider,
            encrypted_key=encrypted,
            key_hint=_mask_hint(api_key),
        )
        db.add(cred)

    db.commit()
    return _redirect("/dashboard?message=API+key+saved")


@app.post("/providers")
def save_provider_config(
    request: Request,
    slug: str = Form(...),
    label: str = Form(""),
    base_url: str = Form(...),
    model: str = Form(...),
    wire_api: str = Form("chat"),
    db: Session = Depends(get_db),
):
    user = _current_user(request, db)
    if not user:
        return _redirect("/login")

    norm_slug = normalize_slug(slug)
    norm_label = (label or "").strip()
    norm_base_url = (base_url or "").strip()
    norm_model = (model or "").strip()
    norm_wire_api = normalize_wire_api(wire_api)

    if not is_valid_slug(norm_slug):
        return _redirect("/dashboard?error=Invalid+slug.+Use+2-32+chars+(a-z,0-9,_,-)")
    if not norm_base_url:
        return _redirect("/dashboard?error=Base+URL+cannot+be+empty")
    if not norm_model:
        return _redirect("/dashboard?error=Model+cannot+be+empty")
    if not (norm_base_url.startswith("http://") or norm_base_url.startswith("https://")):
        return _redirect("/dashboard?error=Base+URL+must+start+with+http://+or+https://")

    # Built-in and env-defined providers are reserved.
    base_specs = get_provider_specs(settings)
    if norm_slug in base_specs:
        return _redirect("/dashboard?error=This+provider+slug+is+reserved.+Use+another+slug")

    row = db.execute(
        select(ProviderConfig).where(
            ProviderConfig.user_id == user.id,
            ProviderConfig.slug == norm_slug,
        )
    ).scalar_one_or_none()

    if row:
        row.label = norm_label
        row.base_url = norm_base_url
        row.model = norm_model
        row.wire_api = norm_wire_api
    else:
        row = ProviderConfig(
            user_id=user.id,
            slug=norm_slug,
            label=norm_label,
            base_url=norm_base_url,
            model=norm_model,
            wire_api=norm_wire_api,
        )
        db.add(row)

    db.commit()
    return _redirect("/dashboard?message=Custom+provider+saved")


@app.post("/providers/{slug}/delete")
def delete_provider_config(slug: str, request: Request, db: Session = Depends(get_db)):
    user = _current_user(request, db)
    if not user:
        return _redirect("/login")

    norm_slug = normalize_slug(slug)
    row = db.execute(
        select(ProviderConfig).where(
            ProviderConfig.user_id == user.id,
            ProviderConfig.slug == norm_slug,
        )
    ).scalar_one_or_none()
    if not row:
        return _redirect("/dashboard?error=Custom+provider+not+found")

    # Remove key for this custom provider as well to avoid stale entries.
    cred = db.execute(
        select(ApiCredential).where(
            ApiCredential.user_id == user.id,
            ApiCredential.provider == norm_slug,
        )
    ).scalar_one_or_none()
    if cred:
        db.delete(cred)

    db.delete(row)
    db.commit()
    return _redirect("/dashboard?message=Custom+provider+deleted")


@app.post("/idea-copilot/start")
def start_idea_copilot(
    request: Request,
    idea: str = Form(...),
    provider: str = Form(...),
    db: Session = Depends(get_db),
):
    user = _current_user(request, db)
    if not user:
        return _redirect("/login")

    idea = idea.strip()
    provider = provider.strip().lower()
    if not idea:
        return _redirect("/dashboard?error=Idea+cannot+be+empty")

    provider_specs = _provider_specs_for_user(db, user.id)
    spec = provider_specs.get(provider)
    if not spec:
        return _redirect("/dashboard?error=Unsupported+provider")

    try:
        api_key = _provider_api_key(db, user.id, provider)
    except ValueError as exc:
        return _redirect(f"/dashboard?error={str(exc).replace(' ', '+')}")

    session = IdeaCopilotSession(
        user_id=user.id,
        provider=provider,
        status="active",
        original_idea=idea,
        refined_idea=idea,
        conversation_json=dump_state({"version": 1, "messages": [], "refined_idea": idea, "round": 0}),
        round_count=0,
        readiness_score=0,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    state = load_state(session.conversation_json)
    agent = IdeaCopilotAgent(spec, api_key)
    try:
        turn = agent.generate_turn(
            original_idea=idea,
            state=state,
            latest_user_reply="",
        )
    except Exception as exc:
        turn = {
            "role": "assistant",
            "analysis": f"首轮协同提问失败：{exc}",
            "refined_idea": idea,
            "questions": ["请先补充：你最想写的核心冲突是什么？"],
            "readiness": 10,
            "ready_hint": "请补充关键信息后继续提问。",
        }

    state = append_assistant_turn(state, turn)
    session.conversation_json = dump_state(state)
    session.refined_idea = str(state.get("refined_idea") or idea)
    session.round_count = int(state.get("round", 0) or 0)
    session.readiness_score = int(turn.get("readiness", 0) or 0)
    db.commit()
    return _redirect(f"/idea-copilot/{session.id}")


@app.get("/idea-copilot/{session_id}")
def idea_copilot_detail(session_id: int, request: Request, db: Session = Depends(get_db)):
    user = _current_user(request, db)
    if not user:
        return _redirect("/login")

    session = db.get(IdeaCopilotSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Idea session not found")

    state = load_state(session.conversation_json)
    latest_turn = latest_assistant_turn(state)
    messages = list(state.get("messages") or [])
    provider_specs = _provider_specs_for_user(db, user.id)

    return templates.TemplateResponse(
        "idea_copilot.html",
        {
            "request": request,
            "user": user,
            "session_data": session,
            "session_state": state,
            "messages": messages,
            "latest_turn": latest_turn,
            "provider_label": (provider_specs.get(session.provider).label if provider_specs.get(session.provider) else session.provider.upper()),
            "message": request.query_params.get("message", ""),
            "error": request.query_params.get("error", ""),
        },
    )


@app.post("/idea-copilot/{session_id}/reply")
def idea_copilot_reply(
    session_id: int,
    request: Request,
    reply: str = Form(...),
    db: Session = Depends(get_db),
):
    user = _current_user(request, db)
    if not user:
        return _redirect("/login")

    session = db.get(IdeaCopilotSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Idea session not found")
    if session.status != "active":
        return _redirect(f"/idea-copilot/{session_id}?error=Session+is+not+active")

    answer = reply.strip()
    if not answer:
        return _redirect(f"/idea-copilot/{session_id}?error=Reply+cannot+be+empty")

    provider_specs = _provider_specs_for_user(db, user.id)
    spec = provider_specs.get(session.provider)
    if not spec:
        return _redirect(f"/idea-copilot/{session_id}?error=Provider+is+no+longer+available")
    try:
        api_key = _provider_api_key(db, user.id, session.provider)
    except ValueError as exc:
        return _redirect(f"/idea-copilot/{session_id}?error={str(exc).replace(' ', '+')}")

    state = load_state(session.conversation_json)
    state = append_user_reply(state, answer)
    agent = IdeaCopilotAgent(spec, api_key)
    try:
        turn = agent.generate_turn(
            original_idea=session.original_idea,
            state=state,
            latest_user_reply=answer,
        )
    except Exception as exc:
        return _redirect(f"/idea-copilot/{session_id}?error={str(exc).replace(' ', '+')}")

    state = append_assistant_turn(state, turn)
    session.conversation_json = dump_state(state)
    session.refined_idea = str(state.get("refined_idea") or session.refined_idea or session.original_idea)
    session.round_count = int(state.get("round", 0) or 0)
    session.readiness_score = int(turn.get("readiness", 0) or 0)
    db.commit()
    return _redirect(f"/idea-copilot/{session_id}?message=Updated")


@app.post("/idea-copilot/{session_id}/confirm")
def idea_copilot_confirm(session_id: int, request: Request, db: Session = Depends(get_db)):
    user = _current_user(request, db)
    if not user:
        return _redirect("/login")

    session = db.get(IdeaCopilotSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Idea session not found")
    if session.status != "active":
        if session.final_job_id:
            return _redirect(f"/jobs/{session.final_job_id}")
        return _redirect(f"/idea-copilot/{session_id}?error=Session+is+not+active")

    state = load_state(session.conversation_json)
    final_idea = build_generation_idea(session.original_idea, state)
    if not final_idea.strip():
        return _redirect(f"/idea-copilot/{session_id}?error=Final+idea+is+empty")

    job = _create_generation_job(db, user.id, session.provider, final_idea)
    session.status = "confirmed"
    session.final_job_id = job.id
    session.refined_idea = str(state.get("refined_idea") or session.refined_idea or session.original_idea)
    session.round_count = int(state.get("round", 0) or 0)
    session.finished_at = datetime.now(timezone.utc)
    db.commit()

    _start_generation_worker(job.id)
    return _redirect(f"/jobs/{job.id}")


@app.post("/idea-copilot/{session_id}/cancel")
def idea_copilot_cancel(session_id: int, request: Request, db: Session = Depends(get_db)):
    user = _current_user(request, db)
    if not user:
        return _redirect("/login")

    session = db.get(IdeaCopilotSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Idea session not found")

    if session.status == "active":
        session.status = "canceled"
        session.finished_at = datetime.now(timezone.utc)
        db.commit()
    return _redirect("/dashboard?message=Idea+copilot+session+canceled")


@app.post("/jobs")
def create_job(
    request: Request,
    idea: str = Form(...),
    provider: str = Form(...),
    db: Session = Depends(get_db),
):
    user = _current_user(request, db)
    if not user:
        return _redirect("/login")

    idea = idea.strip()
    provider = provider.strip().lower()
    provider_specs = _provider_specs_for_user(db, user.id)

    if not idea:
        return _redirect("/dashboard?error=Idea+cannot+be+empty")
    if provider not in provider_specs:
        return _redirect("/dashboard?error=Unsupported+provider")

    try:
        _provider_api_key(db, user.id, provider)
    except ValueError:
        return _redirect("/dashboard?error=Save+your+API+key+for+that+provider+first")

    job = _create_generation_job(db, user.id, provider, idea)
    _start_generation_worker(job.id)
    return _redirect(f"/jobs/{job.id}")


@app.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: int, request: Request, db: Session = Depends(get_db)):
    user = _current_user(request, db)
    if not user:
        return _redirect("/login")

    job = db.get(GenerationJob, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job.status in {"queued", "running"}:
        run_id = (job.run_id or "").strip()
        if run_id:
            run_dir = _resolve_run_dir(run_id)
            try:
                run_dir.mkdir(parents=True, exist_ok=True)
                (run_dir / "cancel.flag").write_text("1", encoding="utf-8")
            except Exception:
                pass
        job.status = "canceled"
        prefix = (job.error_message + "\n") if job.error_message else ""
        job.error_message = prefix + "[user] canceled manually."
        now = datetime.now(timezone.utc)
        job.finished_at = now
        job.updated_at = now
        db.commit()
        return _redirect(f"/jobs/{job.id}")

    return _redirect(f"/jobs/{job.id}")


@app.post("/jobs/{job_id}/delete")
def delete_job(job_id: int, request: Request, db: Session = Depends(get_db)):
    user = _current_user(request, db)
    if not user:
        return _redirect("/login")

    job = db.get(GenerationJob, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job.status in {"queued", "running"}:
        return _redirect("/dashboard?error=Cannot+delete+a+queued/running+job.+Cancel+it+first")

    run_id = (job.run_id or "").strip()
    run_dir = _resolve_run_dir(run_id) if run_id else None

    db.delete(job)
    db.commit()

    # Best-effort cleanup of on-disk artifacts.
    if run_dir and run_dir.exists():
        try:
            shutil.rmtree(run_dir, ignore_errors=True)
        except Exception:
            pass

    return _redirect("/dashboard?message=Job+deleted+permanently")


@app.get("/jobs/{job_id}")
def job_detail(job_id: int, request: Request, db: Session = Depends(get_db)):
    user = _current_user(request, db)
    if not user:
        return _redirect("/login")

    job = db.get(GenerationJob, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    output_text = ""
    if job.output_path:
        path = Path(job.output_path)
        if path.exists():
            output_text = path.read_text(encoding="utf-8")

    worker_log_text = ""
    progress_log_text = ""
    chapter_outputs: List[Dict] = []
    run_dir: Optional[Path] = None
    if job.run_id:
        run_dir = _resolve_run_dir(job.run_id)
        worker_log_text = _tail_text(run_dir / "worker.log")
        progress_log_text = _tail_text(run_dir / "progress.log")
        chapter_outputs = _load_chapter_outputs(run_dir)
    try:
        progress_snapshot = _build_progress_snapshot(job, run_dir, worker_log_text, progress_log_text)
    except Exception:
        progress_snapshot = _default_progress_snapshot()

    return templates.TemplateResponse(
        "job_detail.html",
        {
            "request": request,
            "user": user,
            "job": job,
            "output_text": output_text,
            "worker_log_text": worker_log_text,
            "progress_log_text": progress_log_text,
            "chapter_outputs": chapter_outputs,
            "progress_snapshot": progress_snapshot,
        },
    )


@app.get("/jobs/{job_id}/logs")
def job_logs(job_id: int, request: Request, db: Session = Depends(get_db)):
    user = _current_user(request, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    job = db.get(GenerationJob, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    worker_log_text = ""
    progress_log_text = ""
    run_dir: Optional[Path] = None
    if job.run_id:
        run_dir = _resolve_run_dir(job.run_id)
        worker_log_text = _tail_text(run_dir / "worker.log")
        progress_log_text = _tail_text(run_dir / "progress.log")
    try:
        progress_snapshot = _build_progress_snapshot(job, run_dir, worker_log_text, progress_log_text)
    except Exception:
        progress_snapshot = _default_progress_snapshot()

    return JSONResponse(
        {
            "job_id": job.id,
            "status": job.status,
            "run_id": job.run_id,
            "worker_log": worker_log_text,
            "progress_log": progress_log_text,
            "updated_at": job.updated_at.isoformat() if job.updated_at else "",
            "error_message": job.error_message or "",
            "progress_snapshot": progress_snapshot,
        }
    )


@app.get("/jobs/{job_id}/chapters")
def job_chapters(job_id: int, request: Request, db: Session = Depends(get_db)):
    user = _current_user(request, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    job = db.get(GenerationJob, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    chapters: List[Dict] = []
    if job.run_id:
        run_dir = _resolve_run_dir(job.run_id)
        chapters = _load_chapter_outputs(run_dir)

    return JSONResponse(
        {
            "job_id": job.id,
            "status": job.status,
            "run_id": job.run_id,
            "chapter_count": len(chapters),
            "chapters": chapters,
        }
    )


@app.get("/jobs/{job_id}/download/output")
def download_job_output(job_id: int, request: Request, db: Session = Depends(get_db)):
    user = _current_user(request, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    job = db.get(GenerationJob, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    run_id = (job.run_id or "").strip()
    file_name = f"job_{job.id}_{run_id or 'no_run'}_output.txt"

    if job.output_path:
        out_path = Path(job.output_path)
        if out_path.exists() and out_path.is_file():
            return FileResponse(
                str(out_path),
                media_type="text/plain; charset=utf-8",
                filename=file_name,
            )

    if not run_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No output available yet")

    run_dir = _resolve_run_dir(run_id)
    chapters = _load_chapter_outputs(run_dir)
    if not chapters:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No output available yet")

    parts: List[str] = []
    for ch in chapters:
        chapter_no = ch.get("chapter", "?")
        content = (ch.get("content") or "").strip()
        parts.append(f"Chapter {chapter_no}\n\n{content}")
    merged = ("\n\n" + ("=" * 60) + "\n\n").join(parts)

    return PlainTextResponse(
        merged,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@app.get("/jobs/{job_id}/download/chapter/{chapter_no}")
def download_job_chapter(job_id: int, chapter_no: int, request: Request, db: Session = Depends(get_db)):
    user = _current_user(request, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    job = db.get(GenerationJob, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if chapter_no <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid chapter number")
    if not job.run_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No chapter output available yet")

    run_dir = _resolve_run_dir(job.run_id)
    chapter_path = _latest_chapter_file(run_dir, chapter_no)
    if not chapter_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter output not found")

    return FileResponse(
        str(chapter_path),
        media_type="text/plain; charset=utf-8",
        filename=chapter_path.name,
    )


@app.get("/jobs/{job_id}/download/chapters")
def download_job_chapters(job_id: int, request: Request, db: Session = Depends(get_db)):
    user = _current_user(request, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    job = db.get(GenerationJob, job_id)
    if not job or job.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if not job.run_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No chapter output available yet")

    run_dir = _resolve_run_dir(job.run_id)
    chapter_files = _latest_chapter_files(run_dir)
    if not chapter_files:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No chapter output available yet")

    zip_path = run_dir / f"job_{job.id}_chapters_latest.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in chapter_files:
            zf.write(path, arcname=path.name)

    return FileResponse(
        str(zip_path),
        media_type="application/zip",
        filename=zip_path.name,
    )
