"""
评分裁判 Agent：对两篇文本在六个维度打分
维度：Relevance, Coherence, Empathy, Surprise, Creativity, Complexity（0-10）
返回 JSON：
{
  "candidate": {...scores... , "overall": x},
  "reference": {...scores... , "overall": y},
  "winner": "candidate"|"reference"|"tie",
  "notes": ["..."]
}
"""
from typing import Dict, Optional
from agents.base_agent import BaseAgent
from utils.llm_client import LLMClient
from config import Config


class JudgeAgent(BaseAgent):
    def __init__(
        self,
        config: Config,
        llm_client: LLMClient,
    ):
        system_prompt = """You are a fair literary judge. Score two stories on six dimensions: Relevance, Coherence, Empathy, Surprise, Creativity, Complexity. Each score 0-10. Output JSON:
{
  "candidate": {"Relevance": x, "Coherence": x, "Empathy": x, "Surprise": x, "Creativity": x, "Complexity": x, "overall": x},
  "reference": {"Relevance": x, "Coherence": x, "Empathy": x, "Surprise": x, "Creativity": x, "Complexity": x, "overall": x},
  "winner": "candidate"|"reference"|"tie",
  "notes": ["short rationale bullet(s)"]
}
Be concise and consistent."""
        super().__init__(
            name="JudgeAgent",
            role="judge",
            system_prompt=system_prompt,
            config=config,
            llm_client=llm_client,
            retriever=None,
            memory_system=None,
            static_kb=None,
        )

    def generate(
        self,
        prompt: str,
        context: Optional[str] = None,
        topic: Optional[str] = None,
        genre: Optional[str] = None,
        style_tags: Optional[list] = None,
    ) -> Dict:
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.append({"role": "user", "content": prompt})
        response = self.llm_client.chat(
            messages=messages,
            temperature=max(0.1, self.config.temperature - 0.2),
            max_tokens=1200,
        )
        self.add_to_history("user", prompt)
        self.add_to_history("assistant", response)
        return {
            "agent": self.name,
            "role": self.role,
            "content": response,
            "type": "judgment",
        }
