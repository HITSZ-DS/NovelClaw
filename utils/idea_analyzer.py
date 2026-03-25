"""
Idea分析器：根据用户的idea自动推断风格、类型等（支持中英）
"""
from typing import Dict, List, Optional
from utils.llm_client import LLMClient
from config import Config
import json
import re


class IdeaAnalyzer:
    """Idea分析器：从用户输入的idea中提取风格、类型等信息"""

    def __init__(self, config: Config, llm_client: LLMClient):
        self.config = config
        self.llm_client = llm_client

    def analyze_idea(
        self,
        idea: str,
        language: str = "auto"
    ) -> Dict:
        """
        分析用户的idea，自动推断风格、类型等（中英双语）
        """
        lang = str(language).lower()
        zh_prompt = f"""请分析以下创意想法，提取关键信息：

创意想法：
{idea}

请分析并提取：
1. 故事类型/流派（genre）：如科幻、奇幻、悬疑、历史、现代、都市等
2. 风格标签（style_tags）：如细腻、宏大、悬疑、幽默、严肃、浪漫等（最多5个）
3. 文本类型（text_type）：creative（创意写作）
4. 主题关键词（keywords）：提取3-5个关键词
5. 目标受众（target_audience）：如青少年、成人等
6. 语言风格（language_style）：如现代、古典、口语化等

请以JSON格式输出：
{{
    "genre": "科幻",
    "style_tags": ["细腻", "宏大", "悬疑"],
    "text_type": "creative",
    "keywords": ["AI", "未来", "觉醒"],
    "target_audience": "成人",
    "language_style": "现代",
    "suggested_length": 5000,
    "complexity": "medium"
}}"""
        en_prompt = f"""Analyze the creative idea below and extract key information.

Idea:
{idea}

Extract:
1. Story genre (e.g., sci-fi, fantasy, mystery, historical, contemporary).
2. Style tags (e.g., delicate, epic, suspenseful, humorous, serious, romantic; max 5).
3. Text type: creative.
4. Keywords: 3-5 keywords.
5. Target audience: e.g., teen, adult.
6. Language style: e.g., modern, classical, colloquial.

Return JSON:
{{
    "genre": "sci-fi",
    "style_tags": ["delicate", "epic", "suspenseful"],
    "text_type": "creative",
    "keywords": ["AI", "future", "awakening"],
    "target_audience": "adult",
    "language_style": "modern",
    "suggested_length": 5000,
    "complexity": "medium"
}}"""

        prompt = en_prompt if lang.startswith("en") else zh_prompt
        system_prompt = (
            "You are a creative-analysis expert who extracts genre, style, theme, and related info."
            if lang.startswith("en")
            else "你是一个专业的创意分析专家，擅长从用户的创意想法中提取关键信息，包括类型、风格、主题等。"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        try:
            response = self.llm_client.chat(messages, temperature=0.3)
            result = self._parse_analysis(response)

            if not result:
                result = self._default_result(lang)

            # Ensure required fields
            result.setdefault("genre", "general")
            result.setdefault("style_tags", ["delicate"] if lang.startswith("en") else ["细腻"])
            result.setdefault("text_type", "creative")
            result.setdefault("keywords", [])

            return result

        except Exception as e:
            print(f"分析idea失败: {e}")
            return self._default_result(lang)

    def _default_result(self, lang: str) -> Dict:
        return {
            "genre": "general",
            "style_tags": ["immersive", "tight-pacing"] if lang.startswith("en") else ["细腻"],
            "text_type": "creative",
            "keywords": [],
            "target_audience": "adult" if lang.startswith("en") else "成人",
            "language_style": "modern" if lang.startswith("en") else "现代",
            "suggested_length": 5000,
            "complexity": "medium"
        }

    def _parse_analysis(self, response: str) -> Dict:
        """解析分析结果"""
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass
        return {}

    def extract_topic_from_idea(self, idea: str) -> str:
        """
        从idea中提取主题（用于生成）
        """
        if len(idea) < 100:
            return idea

        lang = str(getattr(self.config, "language", "zh")).lower()
        if lang.startswith("en"):
            prompt = f"""Extract a concise topic (<=50 words) from the idea below.

{idea}

Output only the topic, nothing else."""
            system = "You are an extraction expert."
        else:
            prompt = f"""请从以下创意想法中提取一个简洁的主题（不超过50字）：

{idea}

请直接输出主题，不要其他说明。"""
            system = "你是一个专业的文本提取专家。"

        messages = [
            {
                "role": "system",
                "content": system
            },
            {"role": "user", "content": prompt}
        ]

        try:
            topic = self.llm_client.chat(messages, temperature=0.3)
            return topic.strip()[:100]  # 限制长度
        except:
            return idea[:100]
