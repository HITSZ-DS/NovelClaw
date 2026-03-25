"""
执行计划调度模块 (Adaptive Organizer)
"""
from typing import Dict, List, Optional
from utils.llm_client import LLMClient
from config import Config


class AdaptiveOrganizer:
    """执行计划调度模块：根据任务需求制定执行方案"""
    
    def __init__(self, config: Config, llm_client: LLMClient):
        self.config = config
        self.llm_client = llm_client
    
    def create_execution_plan(
        self,
        task_analysis: Dict,
        available_agents: List[str]
    ) -> Dict:
        """
        创建执行计划
        
        Args:
            task_analysis: 任务分析结果
            available_agents: 可用的Agent列表
        
        Returns:
            执行计划
        """
        complexity = task_analysis.get("complexity", "medium")
        recommended_agents = task_analysis.get("recommended_agents", [])
        rag_required = task_analysis.get("rag_required", True)
        estimated_iterations = task_analysis.get("estimated_iterations", 5)
        
        # 过滤掉评估类Agent，只保留可执行生成/检索的Agent
        agent_sequence = [
            agent for agent in recommended_agents
            if agent in available_agents and agent != "evaluator"
        ]
        
        # 根据复杂度决定执行策略
        if complexity == "simple":
            strategy = "direct_generation"
            use_rag = rag_required
        elif complexity == "complex":
            strategy = "collaborative_generation"
            use_rag = True
        else:  # medium
            strategy = "hybrid_generation"
            use_rag = rag_required
        
        # 确保需要RAG时有检索步骤
        if use_rag and "retrieval" not in agent_sequence and "retrieval" in available_agents:
            agent_sequence.insert(0, "retrieval")
        
        # 优先保证写作Agent在末尾收束生成
        if "writer" in available_agents and "writer" not in agent_sequence:
            agent_sequence.append("writer")

        # 自动构建章节计划（总章节数与每章目标长度）
        chapter_plan = self._build_chapter_plan(task_analysis)
        # 用章节数量指导迭代轮数（若比分析结果更合理）
        if chapter_plan.get("total_chapters"):
            estimated_iterations = max(estimated_iterations, chapter_plan["total_chapters"])
        
        execution_plan = {
            "strategy": strategy,
            "agent_sequence": agent_sequence,
            "use_rag": use_rag,
            "estimated_iterations": estimated_iterations,
            "chapter_plan": chapter_plan,
            "workflow_steps": self._generate_workflow_steps(
                strategy, agent_sequence, use_rag
            )
        }
        
        return execution_plan
    
    def _generate_workflow_steps(
        self,
        strategy: str,
        agent_sequence: List[str],
        use_rag: bool
    ) -> List[Dict]:
        """
        生成工作流步骤
        
        Args:
            strategy: 执行策略
            agent_sequence: Agent序列
            use_rag: 是否使用RAG
        
        Returns:
            工作流步骤列表
        """
        steps = []
        
        # 初始检索步骤（如果需要）
        if use_rag:
            steps.append({
                "step": 1,
                "action": "retrieval",
                "agent": "retrieval",
                "description": "检索相关背景信息"
            })
        
        # Agent执行步骤
        step_num = len(steps) + 1
        for agent in agent_sequence:
            steps.append({
                "step": step_num,
                "action": "generate",
                "agent": agent,
                "description": f"{agent}生成内容"
            })
            step_num += 1
        
        # 评估步骤（默认关闭；如需启用可打开 config.enable_evaluator）
        if getattr(self.config, "enable_evaluator", False):
            steps.append({
                "step": step_num,
                "action": "evaluate",
                "agent": "evaluator",
                "description": "评估生成内容质量"
            })

        return steps
    
    def adjust_plan(
        self,
        current_plan: Dict,
        feedback: Dict,
        iteration: int
    ) -> Dict:
        """
        根据反馈调整执行计划
        
        Args:
            current_plan: 当前执行计划
            feedback: 反馈信息（包含评估结果等）
            iteration: 当前迭代次数
        
        Returns:
            调整后的执行计划
        """
        adjusted_plan = current_plan.copy()
        
        # 如果质量分数低，增加迭代或调整策略
        evaluation = feedback.get("evaluation", {})
        overall_score = evaluation.get("overall_score", 0.5)
        
        if overall_score < self.config.min_quality_score:
            # 增加迭代次数
            adjusted_plan["estimated_iterations"] = min(
                adjusted_plan["estimated_iterations"] + 1,
                self.config.max_iterations
            )
            
            # 如果分数很低，切换到协作模式
            if overall_score < 0.5 and adjusted_plan["strategy"] != "collaborative_generation":
                adjusted_plan["strategy"] = "collaborative_generation"
                adjusted_plan["use_rag"] = True
        
        # 根据建议调整Agent序列
        suggestions = evaluation.get("suggestions", [])
        if suggestions:
            # 如果建议涉及特定方面，确保相关Agent在序列中
            if any("情节" in s or "plot" in s.lower() for s in suggestions):
                if "plot" not in adjusted_plan["agent_sequence"]:
                    adjusted_plan["agent_sequence"].insert(0, "plot")
            if any("人物" in s or "character" in s.lower() for s in suggestions):
                if "character" not in adjusted_plan["agent_sequence"]:
                    adjusted_plan["agent_sequence"].insert(1, "character")
        
        return adjusted_plan

    def _build_chapter_plan(self, task_analysis: Dict) -> Dict:
        """
        根据目标长度/复杂度推断章节数与每章目标长度（自适应，无需用户配置）
        """
        target_length = task_analysis.get("target_length", 20000) or 20000
        complexity = task_analysis.get("complexity", "medium")

        # 自动估算：单章软目标 3200-3800，按总长反推章节数
        base_per_chapter = 3500
        if complexity == "simple":
            base_per_chapter = 3700
        elif complexity == "complex":
            base_per_chapter = 3300

        base_per_chapter = max(self.config.min_chapter_chars, min(3800, base_per_chapter))
        total_chapters = max(4, min(80, round(target_length / base_per_chapter)))
        per_chapter_target = max(self.config.min_chapter_chars, min(4000, round(target_length / max(total_chapters, 1))))

        return {
            "total_chapters": total_chapters,
            "per_chapter_target": per_chapter_target
        }
