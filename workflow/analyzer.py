"""
任务理解模块 (Analyzer) - bilingual zh/en
"""
from typing import Dict, List
from utils.llm_client import LLMClient
from config import Config
import json
import re


class Analyzer:
    """任务理解模块：分析任务需求和复杂度"""

    def __init__(self, config: Config, llm_client: LLMClient):
        self.config = config
        self.llm_client = llm_client

    def analyze_task(
        self,
        topic: str,
        text_type: str = "creative",
        target_length: int = 5000
    ) -> Dict:
        """
        分析任务需求
        """
        lang = str(getattr(self.config, "language", "zh")).lower()
        if lang.startswith("en"):
            prompt = f"""Analyze the following text-generation task and assess complexity.

Topic: {topic}
Text type: {text_type}
Target length: {target_length} words

Provide:
1. Plot depth requirement (1-10)
2. Character diversity requirement (1-10)
3. Background info requirement (1-10)
4. Creativity requirement (1-10)
5. Logic rigor requirement (1-10)
6. Task complexity (simple/medium/complex)

Output JSON:
{{
    "plot_depth": 5,
    "character_diversity": 5,
    "background_info": 5,
    "creativity": 5,
    "logic_rigor": 5,
    "complexity": "medium",
    "recommended_agents": ["plot", "character", "world"],
    "rag_required": true,
    "estimated_iterations": 5
}}"""
            system_prompt = "You are a task analysis expert for long-form text generation."
        else:
            prompt = f"""请分析以下文本生成任务的需求和复杂度：

主题：{topic}
文本类型：{text_type}
目标长度：{target_length}字

请从以下维度进行分析：
1. 情节深度要求（1-10分）
2. 角色多样性要求（1-10分）
3. 背景信息要求（1-10分）
4. 创意新颖性要求（1-10分）
5. 逻辑严谨性要求（1-10分）
6. 任务复杂度（simple/medium/complex）

请以JSON格式输出分析结果：
{{
    "plot_depth": 5,
    "character_diversity": 5,
    "background_info": 5,
    "creativity": 5,
    "logic_rigor": 5,
    "complexity": "medium",
    "recommended_agents": ["plot", "character", "world"],
    "rag_required": true,
    "estimated_iterations": 5
}}"""
            system_prompt = "你是一个专业的任务分析专家，擅长分析文本生成任务的复杂度和需求。"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        response = self.llm_client.chat(messages, temperature=0.3)
        analysis_result = self._parse_analysis(response)

        if not analysis_result:
            analysis_result = {
                "plot_depth": 7,
                "character_diversity": 6,
                "background_info": 7,
                "creativity": 8,
                "logic_rigor": 6,
                "complexity": "medium",
                "recommended_agents": ["plot", "character", "world", "writer", "retrieval"],
                "rag_required": True,
                "estimated_iterations": 5
            }

        rec = analysis_result.get("recommended_agents", [])
        if "writer" not in rec:
            rec.append("writer")
        if "evaluator" not in rec:
            rec.append("evaluator")
        analysis_result["recommended_agents"] = rec

        return analysis_result

    def _parse_analysis(self, response: str) -> Dict:
        """解析分析结果中的JSON"""
        json_match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except:
                pass

        return {}
