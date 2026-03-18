"""
Agent 基类
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from utils.llm_client import LLMClient
from rag.retriever import Retriever
from rag.memory_system import MemorySystem
from rag.static_knowledge_base import StaticKnowledgeBase
from config import Config


class BaseAgent(ABC):
    """Agent 基类"""
    
    def __init__(
        self,
        name: str,
        role: str,
        system_prompt: str,
        config: Config,
        llm_client: LLMClient,
        retriever: Optional[Retriever] = None,
        memory_system: Optional[MemorySystem] = None,
        static_kb: Optional[StaticKnowledgeBase] = None
    ):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.config = config
        self.llm_client = llm_client
        self.retriever = retriever
        self.memory_system = memory_system
        self.static_kb = static_kb  # 外部静态知识库
        self.conversation_history: List[Dict[str, str]] = []
        self.runtime_use_rag_override: Optional[bool] = None
        self.runtime_use_static_kb_override: Optional[bool] = None
    
    def _build_messages(
        self,
        prompt: str,
        context: Optional[str] = None,
        use_rag: bool = True,
        topic: Optional[str] = None,
        use_memory: bool = True,
        use_static_kb: bool = True,
        genre: Optional[str] = None,
        style_tags: Optional[List[str]] = None
    ) -> List[Dict[str, str]]:
        """
        构建消息列表
        
        Args:
            prompt: 用户提示
            context: 额外上下文
            use_rag: 是否使用 RAG 检索
            topic: 主题（用于记忆检索）
            use_memory: 是否使用记忆系统
        
        Returns:
            消息列表
        """
        messages = [{"role": "system", "content": self.system_prompt}]
        rag_enabled = bool(use_rag and self.retriever and getattr(self.config, "enable_rag", True))
        static_kb_enabled = bool(use_static_kb and self.static_kb and getattr(self.config, "enable_static_kb", True))
        if self.runtime_use_rag_override is not None:
            rag_enabled = rag_enabled and bool(self.runtime_use_rag_override)
        if self.runtime_use_static_kb_override is not None:
            static_kb_enabled = static_kb_enabled and bool(self.runtime_use_static_kb_override)
        
        # 添加记忆系统的上下文（优先）
        memory_context = ""
        if use_memory and self.memory_system and topic:
            memory_context = self.memory_system.get_relevant_context(
                query=f"{prompt}\n\n{context or ''}",
                topic=topic,
                include_types=self._get_relevant_memory_types()
            )
            if memory_context:
                messages.append({
                    "role": "system",
                    "content": f"【重要】历史记忆信息（请确保与以下信息保持一致）：\n{memory_context}\n\n请确保生成的内容与上述历史信息保持一致，避免矛盾。"
                })
        
        # 添加外部静态知识库的风格参考（用于减少幻觉和调整风格）
        if static_kb_enabled:
            # 先给“情节参考”（仅对 plot/retrieval/writer 有帮助）
            if self.role in {"plot", "retrieval", "writer"}:
                plot_context = self.static_kb.get_plot_context(
                    query=prompt,
                    genre=genre,
                    style_tags=style_tags,
                    top_k=2
                )
                if plot_context:
                    messages.append({"role": "system", "content": plot_context})

            style_context = self.static_kb.get_style_context(
                query=prompt,
                genre=genre,
                style_tags=style_tags,
                top_k=3
            )
            if style_context:
                messages.append({
                    "role": "system",
                    "content": style_context
                })
        
        # 添加检索到的上下文（动态知识库）
        if rag_enabled:
            retrieved_context = self.retriever.retrieve_with_context(
                query=prompt,
                context=context,
                top_k=3
            )
            if retrieved_context:
                messages.append({
                    "role": "system",
                    "content": f"相关背景信息：\n{retrieved_context}"
                })
        
        # 添加对话历史
        messages.extend(self.conversation_history[-5:])  # 只保留最近5轮对话
        
        # 添加当前提示
        if context and not rag_enabled:
            messages.append({
                "role": "user",
                "content": f"{context}\n\n{prompt}"
            })
        else:
            messages.append({"role": "user", "content": prompt})
        
        return messages
    
    def _get_relevant_memory_types(self) -> List[str]:
        """获取相关的记忆类型（子类可重写）"""
        return ["character", "outline", "plot_point", "world_setting", "fact_card"]
    
    @abstractmethod
    def generate(self, prompt: str, context: Optional[str] = None) -> Dict:
        """
        生成内容（子类必须实现）
        
        Args:
            prompt: 提示
            context: 上下文
        
        Returns:
            生成结果字典
        """
        pass
    
    def reset(self):
        """重置对话历史"""
        self.conversation_history = []
    
    def add_to_history(self, role: str, content: str):
        """添加到对话历史"""
        self.conversation_history.append({"role": role, "content": content})
