"""
强化学习奖励系统
"""
from typing import Dict, List, Optional
import re


class RewardSystem:
    """奖励系统：评估生成文本的质量并给出奖励分数"""
    
    def __init__(self, config):
        self.config = config
    
    def calculate_reward(
        self,
        generated_text: str,
        evaluation_result: Dict,
        consistency_result: Optional[Dict] = None,
        context: Optional[Dict] = None,
        target_length: Optional[int] = None
    ) -> Dict:
        """
        计算奖励分数
        
        Args:
            generated_text: 生成的文本
            evaluation_result: 评估结果
            context: 上下文信息
            consistency_result: 一致性检查结果
        
        Returns:
            奖励分数和详细信息
        """
        # 从评估结果中获取分数（新颖性置零，不影响总分）
        novelty_score = 0.0
        coherence_score = evaluation_result.get("coherence_score", 0.5)
        emotional_score = evaluation_result.get("emotional_score", 0.5)
        overall_score = evaluation_result.get("overall_score", 0.5)
        # 一致性（来自一致性检查）
        consistency_conf = 0.5
        consistency_issues = 0
        if consistency_result:
            consistency_conf = consistency_result.get("overall_confidence", 0.5)
            consistency_issues = len(consistency_result.get("all_issues", []))
        
        # 计算文本长度奖励（鼓励达到目标长度，允许小幅超长）
        text_length = len(generated_text)
        target = max(target_length or 1000, 1)
        length_score = min(1.2, text_length / target)
        
        # 计算结构完整性奖励
        structure_score = self._calculate_structure_score(generated_text)

        # 一致性得分：置信度减去问题数量轻微惩罚
        consistency_score = max(0.0, min(1.0, consistency_conf - 0.03 * consistency_issues))
        
        # 综合奖励（去掉新颖性，强调连贯/整体/一致性/长度/结构）
        reward = (
            coherence_score * 0.30 +
            overall_score * 0.35 +
            consistency_score * 0.20 +
            length_score * 0.10 +
            structure_score * 0.05
        )
        
        return {
            "total_reward": reward,
            "novelty_score": novelty_score,
            "coherence_score": coherence_score,
            "emotional_score": emotional_score,
            "overall_score": overall_score,
            "length_score": length_score,
            "structure_score": structure_score,
            "consistency_score": consistency_score,
            "consistency_issues": consistency_issues,
            "breakdown": {
                "coherence": coherence_score * 0.30,
                "overall": overall_score * 0.35,
                "consistency": consistency_score * 0.20,
                "length": length_score * 0.10,
                "structure": structure_score * 0.05
            }
        }
    
    def _calculate_structure_score(self, text: str) -> float:
        """
        计算结构完整性分数
        
        Args:
            text: 文本内容
        
        Returns:
            结构分数（0-1）
        """
        score = 0.5  # 基础分
        
        # 检查是否有段落分隔
        if "\n\n" in text or "\n" in text:
            score += 0.2
        
        # 检查是否有标题或章节标记
        if re.search(r'[第].{1,3}[章节部分]', text) or re.search(r'^#{1,3}\s', text, re.MULTILINE):
            score += 0.2
        
        # 检查文本长度是否合理
        if 500 <= len(text) <= 10000:
            score += 0.1
        
        return min(1.0, score)
    
    def should_continue(
        self,
        reward: Dict,
        iteration: int,
        target_length: Optional[int] = None,
        current_length: Optional[int] = None
    ) -> bool:
        """
        判断是否应该继续迭代
        
        Args:
            reward: 奖励分数
            iteration: 当前迭代次数
        
        Returns:
            是否继续
        """
        total_reward = reward.get("total_reward", 0)
        
        # 如果奖励分数足够高且长度基本达标，可以停止
        if total_reward >= self.config.min_quality_score:
            if target_length and current_length:
                if current_length >= target_length * 0.8:
                    return False
            else:
                if current_length is None or current_length >= 800:
                    return False
        
        # 若长度已达成目标，可提前结束
        if target_length and current_length and current_length >= target_length:
            return False
        
        # 如果迭代次数过多，停止
        max_iters = min(self.config.max_iterations, getattr(self.config, 'max_total_iterations', self.config.max_iterations))
        if iteration >= max_iters:
            return False
        
        return True



