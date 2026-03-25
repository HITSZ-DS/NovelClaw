"""
世界观 Agent
"""
from typing import Dict, Optional, List
from agents.base_agent import BaseAgent
from utils.llm_client import LLMClient
from rag.retriever import Retriever
from rag.memory_system import MemorySystem
from rag.static_knowledge_base import StaticKnowledgeBase
from config import Config


class WorldAgent(BaseAgent):
    """世界观设计 Agent：设定背景、规则、文化等"""

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
            system_prompt = """You are a worldbuilding expert.
Responsibilities:
1. Design coherent settings, rules, history, culture, and technology levels.
2. Ensure internal logic and constraints stay consistent.
3. Provide concrete details that writers can directly use.
Respond in English with detailed, thoughtful worldbuilding."""
            name = "World Agent"
        else:
            system_prompt = """你是一个世界观设计专家。你的职责是：
1. 设计连贯的背景、规则、历史、文化、科技水平
2. 确保内在逻辑和约束保持一致
3. 提供可直接用于写作的具体细节
请用中文回答，提供详细、有深度的世界观设计。"""
            name = "世界观Agent"

        super().__init__(
            name=name,
            role="world",
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
        """生成世界观设定"""
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
            "type": "world",
        }
