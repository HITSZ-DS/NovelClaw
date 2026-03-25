"""
人物塑造 Agent
"""
from typing import Dict, Optional, List
from agents.base_agent import BaseAgent
from utils.llm_client import LLMClient
from rag.retriever import Retriever
from rag.memory_system import MemorySystem
from rag.static_knowledge_base import StaticKnowledgeBase
from config import Config


class CharacterAgent(BaseAgent):
    """人物塑造Agent：设计主要及次要人物特征"""

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
            system_prompt = """You are a professional character designer.
Responsibilities:
1. Create dimensional characters with depth.
2. Shape personality, backstory, motivation, and growth arcs.
3. Ensure behavior matches the established personality.
4. Build complex relationships between characters.
Respond in English with detailed, vivid character designs."""
            name = "Character Agent"
        else:
            system_prompt = """你是一个专业的人物塑造专家。你的职责是：
1. 设计立体、有深度的人物角色
2. 塑造人物的性格、背景、动机和成长弧线
3. 确保人物行为符合其性格设定
4. 创造人物之间的复杂关系
请用中文回答，提供详细、生动的人物设计。"""
            name = "人物塑造Agent"

        super().__init__(
            name=name,
            role="character",
            system_prompt=system_prompt,
            config=config,
            llm_client=llm_client,
            retriever=retriever,
            memory_system=memory_system,
            static_kb=static_kb,
        )

    def generate(
        self,
        prompt: str,
        context: Optional[str] = None,
        topic: Optional[str] = None,
        genre: Optional[str] = None,
        style_tags: Optional[List[str]] = None,
    ) -> Dict:
        """生成人物设计"""
        messages = self._build_messages(
            prompt,
            context,
            use_rag=True,
            topic=topic,
            use_memory=True,
            use_static_kb=True,
            genre=genre,
            style_tags=style_tags,
        )

        response = self.llm_client.chat(
            messages=messages,
            temperature=self.config.temperature,
        )

        self.add_to_history("user", prompt)
        self.add_to_history("assistant", response)

        return {
            "agent": self.name,
            "role": self.role,
            "content": response,
            "type": "character",
        }
