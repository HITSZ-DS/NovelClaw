from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from config import Config
from utils.llm_client import LLMClient


@dataclass(frozen=True)
class ProviderRuntime:
    slug: str
    base_url: str
    model: str
    wire_api: str = "chat"


class IdeaCopilotAgent:
    """Collaborative idea refinement agent.

    This agent supports multi-turn ideation with user confirmation-driven termination.
    """

    def __init__(self, provider_spec: Any, api_key: str):
        self.provider = _to_provider_runtime(provider_spec)
        self.api_key = api_key

    def generate_turn(
        self,
        *,
        original_idea: str,
        state: Dict[str, Any],
        latest_user_reply: str,
    ) -> Dict[str, Any]:
        return generate_assistant_turn(
            original_idea=original_idea,
            state=state,
            latest_user_reply=latest_user_reply,
            provider_spec=self.provider,
            api_key=self.api_key,
        )

    @staticmethod
    def load_state(raw: str) -> Dict[str, Any]:
        return load_state(raw)

    @staticmethod
    def dump_state(state: Dict[str, Any]) -> str:
        return dump_state(state)

    @staticmethod
    def append_user(state: Dict[str, Any], reply: str) -> Dict[str, Any]:
        return append_user_reply(state, reply)

    @staticmethod
    def append_assistant(state: Dict[str, Any], turn: Dict[str, Any]) -> Dict[str, Any]:
        return append_assistant_turn(state, turn)

    @staticmethod
    def latest_turn(state: Dict[str, Any]) -> Dict[str, Any]:
        return latest_assistant_turn(state)

    @staticmethod
    def to_generation_idea(original_idea: str, state: Dict[str, Any]) -> str:
        return build_generation_idea(original_idea, state)


def _to_provider_runtime(spec: Any) -> ProviderRuntime:
    if isinstance(spec, ProviderRuntime):
        return spec
    if isinstance(spec, dict):
        return ProviderRuntime(
            slug=str(spec.get("slug") or ""),
            base_url=str(spec.get("base_url") or ""),
            model=str(spec.get("model") or ""),
            wire_api=str(spec.get("wire_api") or "chat"),
        )
    return ProviderRuntime(
        slug=str(getattr(spec, "slug", "") or ""),
        base_url=str(getattr(spec, "base_url", "") or ""),
        model=str(getattr(spec, "model", "") or ""),
        wire_api=str(getattr(spec, "wire_api", "chat") or "chat"),
    )


def load_state(raw: str) -> Dict[str, Any]:
    base: Dict[str, Any] = {"version": 1, "messages": [], "refined_idea": "", "round": 0}
    if not raw:
        return base
    try:
        data = json.loads(raw)
    except Exception:
        return base
    if not isinstance(data, dict):
        return base
    out = dict(base)
    msgs = data.get("messages")
    if isinstance(msgs, list):
        out["messages"] = msgs
    out["refined_idea"] = str(data.get("refined_idea") or "")
    try:
        out["round"] = max(0, int(data.get("round") or 0))
    except Exception:
        out["round"] = 0
    return out


def dump_state(state: Dict[str, Any]) -> str:
    payload = {
        "version": 1,
        "messages": state.get("messages", []),
        "refined_idea": state.get("refined_idea", ""),
        "round": int(state.get("round", 0) or 0),
    }
    return json.dumps(payload, ensure_ascii=False)


def _build_client(spec: ProviderRuntime, api_key: str) -> LLMClient:
    cfg = Config(require_api_key=False)
    cfg.language = "zh"
    cfg.llm_provider = spec.slug
    cfg.api_key = api_key
    cfg.api_base_url = spec.base_url
    cfg.model_name = spec.model
    cfg.wire_api = spec.wire_api
    cfg.temperature = 0.6
    cfg.max_tokens = min(int(getattr(cfg, "max_tokens", 1600) or 1600), 1600)
    return LLMClient(cfg)


def _extract_json_object(text: str) -> Optional[str]:
    s = (text or "").strip()
    if not s:
        return None
    start = s.find("{")
    if start < 0:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start : i + 1]
    return None


def _history_text(messages: List[Dict[str, Any]], limit: int = 12) -> str:
    if not messages:
        return "（暂无历史轮次）"
    rows: List[str] = []
    for item in messages[-limit:]:
        role = str(item.get("role") or "")
        if role == "assistant":
            analysis = str(item.get("analysis") or "").strip()
            refined = str(item.get("refined_idea") or "").strip()
            questions = item.get("questions") or []
            q_lines: List[str] = []
            if isinstance(questions, list):
                for idx, q in enumerate(questions[:3], 1):
                    q_text = str(q or "").strip()
                    if q_text:
                        q_lines.append(f"{idx}. {q_text}")
            rows.append(
                "\n".join(
                    [
                        "[assistant]",
                        f"analysis: {analysis}",
                        f"refined_idea: {refined}",
                        "questions:",
                        ("\n".join(q_lines) if q_lines else "（本轮无问题）"),
                    ]
                )
            )
        elif role == "user":
            rows.append(f"[user]\n{str(item.get('content') or '').strip()}")
    return "\n\n".join(rows) if rows else "（暂无历史轮次）"


def _normalize_turn(parsed: Dict[str, Any], fallback_refined: str, fallback_text: str) -> Dict[str, Any]:
    analysis = str(parsed.get("analysis") or "").strip()
    refined_idea = str(parsed.get("refined_idea") or "").strip()
    ready_hint = str(parsed.get("ready_hint") or "").strip()

    questions_raw = parsed.get("questions")
    questions: List[str] = []
    if isinstance(questions_raw, list):
        for q in questions_raw:
            q_text = str(q or "").strip()
            if q_text:
                questions.append(q_text)
    questions = questions[:3]

    readiness = 0
    try:
        readiness = int(parsed.get("readiness", 0))
    except Exception:
        readiness = 0
    readiness = max(0, min(100, readiness))

    if not analysis:
        analysis = (fallback_text or "本轮已更新创意草案。").strip()[:280]
    if not refined_idea:
        refined_idea = fallback_refined
    if not ready_hint:
        ready_hint = "当你觉得核心冲突、人物关系、世界规则都明确后，可手动确认并开始生成。"
    if not questions:
        questions = ["你最希望读者记住的核心情绪或主题是什么？"]

    return {
        "role": "assistant",
        "analysis": analysis[:600],
        "refined_idea": refined_idea[:6000],
        "questions": questions,
        "readiness": readiness,
        "ready_hint": ready_hint[:300],
    }


def _fallback_turn(state: Dict[str, Any], original_idea: str, raw_response: str) -> Dict[str, Any]:
    fallback_refined = str(state.get("refined_idea") or "").strip() or original_idea.strip()
    return _normalize_turn(
        parsed={},
        fallback_refined=fallback_refined,
        fallback_text=raw_response,
    )


def generate_assistant_turn(
    *,
    original_idea: str,
    state: Dict[str, Any],
    latest_user_reply: str,
    provider_spec: Any,
    api_key: str,
) -> Dict[str, Any]:
    runtime = _to_provider_runtime(provider_spec)
    client = _build_client(runtime, api_key)
    current_refined = str(state.get("refined_idea") or "").strip() or original_idea.strip()
    history = _history_text(state.get("messages") or [])

    system_prompt = """你是“小说创意协同澄清Agent”。
目标：通过连续提问帮助用户把 idea 打磨到可直接写作。
规则：
1) 每轮最多提出 3 个高价值问题，避免泛泛而谈。
2) 必须先给“本轮分析”，再给“更新后的创意草案”。
3) 问题要覆盖冲突、人物动机、世界规则、篇幅节奏中的缺口。
4) 不要替用户做最终确认，是否结束由用户决定。
5) 严格输出 JSON，不要 markdown，不要代码块。
JSON schema:
{
  "analysis": "string",
  "refined_idea": "string",
  "questions": ["q1", "q2"],
  "readiness": 0,
  "ready_hint": "string"
}
"""

    user_prompt = f"""【原始创意】
{original_idea}

【当前创意草案】
{current_refined}

【用户本轮回复】
{latest_user_reply or "（首轮，无用户回复）"}

【历史对话摘要】
{history}

请生成下一轮协同澄清结果。"""

    raw = client.chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.6,
        max_tokens=1400,
    )

    block = _extract_json_object(raw or "")
    if not block:
        return _fallback_turn(state, original_idea, raw or "")
    try:
        parsed = json.loads(block)
    except Exception:
        return _fallback_turn(state, original_idea, raw or "")

    if not isinstance(parsed, dict):
        return _fallback_turn(state, original_idea, raw or "")
    return _normalize_turn(
        parsed=parsed,
        fallback_refined=current_refined,
        fallback_text=raw or "",
    )


def append_user_reply(state: Dict[str, Any], reply: str) -> Dict[str, Any]:
    content = (reply or "").strip()
    if not content:
        return state
    out = load_state(dump_state(state))
    msgs = list(out.get("messages") or [])
    msgs.append({"role": "user", "content": content[:3000]})
    out["messages"] = msgs[-30:]
    return out


def append_assistant_turn(state: Dict[str, Any], turn: Dict[str, Any]) -> Dict[str, Any]:
    out = load_state(dump_state(state))
    msgs = list(out.get("messages") or [])
    msgs.append(turn)
    out["messages"] = msgs[-30:]
    out["refined_idea"] = str(turn.get("refined_idea") or out.get("refined_idea") or "")
    out["round"] = int(out.get("round", 0) or 0) + 1
    return out


def latest_assistant_turn(state: Dict[str, Any]) -> Dict[str, Any]:
    msgs = list(state.get("messages") or [])
    for item in reversed(msgs):
        if str(item.get("role") or "") == "assistant":
            return item
    return {
        "role": "assistant",
        "analysis": "请先开始第一轮协同澄清。",
        "refined_idea": state.get("refined_idea") or "",
        "questions": [],
        "readiness": 0,
        "ready_hint": "",
    }


def build_generation_idea(original_idea: str, state: Dict[str, Any]) -> str:
    refined = str(state.get("refined_idea") or "").strip() or original_idea.strip()
    messages = list(state.get("messages") or [])
    qa: List[str] = []
    for item in messages[-20:]:
        role = str(item.get("role") or "")
        if role == "assistant":
            qs = item.get("questions") or []
            if isinstance(qs, list):
                for q in qs[:3]:
                    q_text = str(q or "").strip()
                    if q_text:
                        qa.append(f"Q: {q_text}")
        elif role == "user":
            a = str(item.get("content") or "").strip()
            if a:
                qa.append(f"A: {a}")

    if qa:
        qa_text = "\n".join(qa[-16:])
        return (
            "【协同定稿创意】\n"
            f"{refined}\n\n"
            "【协同问答纪要（最近轮次）】\n"
            f"{qa_text}"
        ).strip()
    return refined
