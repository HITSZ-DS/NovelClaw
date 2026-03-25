"""
情节构建 Agent
"""
from typing import Dict, Optional, List
from agents.base_agent import BaseAgent
from utils.llm_client import LLMClient
from rag.retriever import Retriever
from rag.memory_system import MemorySystem
from rag.static_knowledge_base import StaticKnowledgeBase
from config import Config


class PlotAgent(BaseAgent):
    """情节构建 Agent：负责故事主线/情节分支设计"""

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
            system_prompt = """You are a professional plot designer.
Responsibilities:
1. Design compelling main plotlines and branches.
2. Ensure logical coherence and callbacks.
3. Create dramatic conflict and climaxes.
4. Keep the plot consistent yet inventive.
Respond in English with detailed, creative plot design."""
            name = "Plot Agent"
        else:
            system_prompt = """你是一个专业的情节构建专家。你的职责是：
1. 设计引人入胜的故事主线和情节分支
2. 确保情节逻辑严密、前后呼应
3. 创造戏剧冲突和高潮
4. 保持情节的连贯性和创新性
请用中文回答，提供详细、有创意的情节设计。"""
            name = "情节构建Agent"

        super().__init__(
            name=name,
            role="plot",
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
        """生成情节内容"""
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
            temperature=self.config.temperature + 0.1,  # 情节需要更多创意
        )

        self.add_to_history("user", prompt)
        self.add_to_history("assistant", response)

        return {
            "agent": self.name,
            "role": self.role,
            "content": response,
            "type": "plot",
        }
