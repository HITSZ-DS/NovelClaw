"""
Writer agent for long-form story chapter generation.
"""
from typing import Dict, List, Optional

from agents.base_agent import BaseAgent
from config import Config
from rag.memory_system import MemorySystem
from rag.retriever import Retriever
from rag.static_knowledge_base import StaticKnowledgeBase
from utils.llm_client import LLMClient


class WriterAgent(BaseAgent):
    """Writer agent: generate narrative prose for the current chapter."""

    def __init__(
        self,
        config: Config,
        llm_client: LLMClient,
        retriever: Optional[Retriever] = None,
        memory_system: Optional[MemorySystem] = None,
        static_kb: Optional[StaticKnowledgeBase] = None,
    ):
        lang = getattr(config, "language", "zh").lower()
        if lang.startswith("en"):
            system_prompt = (
                "You are an expert long-form fiction writer.\n"
                "Hard rules:\n"
                "1) Follow the given premise/outline and remain consistent.\n"
                "2) Keep continuity with prior content; avoid jumps and repetition.\n"
                "3) Output narrative prose only (no outlines/bullets).\n"
                "4) If context is incomplete, extend from existing clues instead of unsupported fabrication."
            )
            name = "Writer Agent"
        else:
            system_prompt = (
                "你是一名长篇小说写作专家，擅长在既有人物、情节和世界观基础上写连贯正文。\n"
                "硬性规则：\n"
                "1) 严格遵循给定大纲与设定，不无依据扩写；\n"
                "2) 保持与上文连续，不跳章，不重复；\n"
                "3) 只输出小说正文，不输出提纲或列表；\n"
                "4) 信息不足时优先延展既有线索，而不是凭空设定。"
            )
            name = "写作Agent"

        super().__init__(
            name=name,
            role="writer",
            system_prompt=system_prompt,
            config=config,
            llm_client=llm_client,
            retriever=retriever,
            memory_system=memory_system,
            static_kb=static_kb,
        )

    def _length_hint(
        self,
        target_length: Optional[int],
        lang_en: bool,
        target_min_chars: Optional[int] = None,
        target_max_chars: Optional[int] = None,
    ) -> str:
        if target_min_chars and target_max_chars and target_max_chars > target_min_chars:
            if lang_en:
                return (
                    f" Hard constraint: output {target_min_chars}-{target_max_chars} words. "
                    "Do not exceed the upper bound. If you reach it, stop immediately."
                )
            return (
                f" 硬性约束：本次必须输出 {target_min_chars}-{target_max_chars} 字。"
                "严禁超过上限；到达上限请立即收束结尾并停止。"
            )

        if not target_length or target_length <= 0:
            return " Aim for about 1000-1800 words." if lang_en else " 本次输出控制在约 1000-1800 字。"

        low = max(800, int(target_length * 0.9))
        high = max(low + 200, int(target_length * 1.12))
        if lang_en:
            return (
                f" Hard constraint: output {low}-{high} words. "
                "Do not exceed the upper bound."
            )
        return f" 硬性约束：本次必须输出 {low}-{high} 字，且不要超过上限。"

    def _estimate_max_tokens(
        self,
        target_length: Optional[int],
        target_max_chars: Optional[int] = None,
    ) -> Optional[int]:
        hard_cap = target_max_chars if target_max_chars and target_max_chars > 0 else target_length
        if not hard_cap or hard_cap <= 0:
            return None
        # Mixed zh/en narrative usually stays under ~1.5 tokens per visible character.
        est = int(hard_cap * 1.5)
        est = max(512, est)
        return min(est, int(getattr(self.config, "max_tokens", est)))

    def generate(
        self,
        prompt: str,
        context: Optional[str] = None,
        topic: Optional[str] = None,
        genre: Optional[str] = None,
        style_tags: Optional[List[str]] = None,
        target_length: Optional[int] = None,
        target_min_chars: Optional[int] = None,
        target_max_chars: Optional[int] = None,
    ) -> Dict:
        """Generate prose for the current chapter."""
        lang_en = getattr(self.config, "language", "zh").lower().startswith("en")
        hint = self._length_hint(
            target_length,
            lang_en,
            target_min_chars=target_min_chars,
            target_max_chars=target_max_chars,
        )
        max_tokens = self._estimate_max_tokens(target_length, target_max_chars=target_max_chars)

        messages = self._build_messages(
            prompt + hint,
            context,
            use_rag=True,
            topic=topic,
            use_memory=True,
            use_static_kb=bool(getattr(self.config, "enable_static_kb", False)),
            genre=genre,
            style_tags=style_tags,
        )

        response = self.llm_client.chat(
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=max_tokens,
        )

        self.add_to_history("user", prompt)
        self.add_to_history("assistant", response)

        return {
            "agent": self.name,
            "role": self.role,
            "content": response,
            "type": "writer",
        }
