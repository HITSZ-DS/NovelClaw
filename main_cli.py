"""
主程序入口
"""
import datetime
import json
import os
import traceback

from config import Config
from workflow.executor import CompositiveExecutor


def main():
    """主函数"""
    print("=" * 60)
    print("协同式 RAG-Agent 长文本生成系统")
    print("=" * 60)
    print()

    try:
        config = Config(require_api_key=False)

        if not config.api_key:
            print("错误：未检测到 API Key。")
            print("请在 .env 或环境变量中配置以下之一：")
            print("  DEEPSEEK_API_KEY / OPENAI_API_KEY / CODEX_API_KEY")
            return

        user_idea = input("请输入你的创意想法（留空使用示例）: ").strip()
        if not user_idea:
            user_idea = "一个关于未来世界AI觉醒的科幻故事，风格细腻宏大，探讨人工智能与人类的关系"
            print(f"\n使用示例 idea: {user_idea}")
        else:
            print(f"\n收到自定义 idea: {user_idea}")

        # 仅启用动态 memory（禁用静态 RAG / 静态知识库）
        config.memory_only_mode = True
        config.enable_rag = False
        config.enable_static_kb = False

        if not config.run_id:
            config.run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if config.memory_reset_each_run:
            config.memory_vector_db_path = os.path.join(
                config.vector_db_path,
                "memory",
                f"run_{config.run_id}",
            )

        os.makedirs(config.memory_vector_db_path, exist_ok=True)
        run_dir = os.path.join(config.runs_dir, config.run_id)
        os.makedirs(run_dir, exist_ok=True)

        print("\n[启动配置]")
        print(f"- run_id: {config.run_id}")
        print(f"- provider/model: {config.llm_provider}/{config.model_name}")
        print(f"- mode: {'memory-only' if config.memory_only_mode else 'full-rag'}")
        print(f"- dynamic_memory: {config.memory_vector_db_path}")
        print(f"- runs_dir: {run_dir}")
        print("-" * 60)

        executor = CompositiveExecutor(config)

        initial_knowledge = """
        科幻小说创作要点：
        1. 世界观设定要完整，包括科技水平、社会结构、时间背景
        2. 人物要有深度，动机要清晰
        3. 情节要有冲突和高潮
        4. 保持逻辑一致性
        """

        print("[阶段] 开始生成长文本（终端将持续输出进度）...")
        print("-" * 60)
        result = executor.generate_long_text(
            idea=user_idea,
            initial_knowledge=initial_knowledge,
            auto_analyze=True,
        )

        print("\n" + "=" * 60)
        print("生成完成")
        print("=" * 60)
        print(f"主题: {result['topic']}")
        print(f"文本类型: {result['text_type']}")
        print(f"文本长度: {result['length']} 字")
        print(f"迭代次数: {result['iterations']}")
        print(f"已写章节: {result.get('chapters_written', 0)}")
        if "consistency" in result:
            print(f"一致性分数: {result['consistency'].get('overall_confidence', 0):.3f}")
        if result.get("progress_log"):
            lines = result["progress_log"].splitlines()
            total_line = [l for l in lines if l.startswith("total_words=")]
            if total_line:
                print(total_line[-1])

        print("\n生成的文本：")
        print("-" * 60)
        print(result["final_text"])
        print("-" * 60)

        output_file = os.path.join(run_dir, "output.txt")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"主题: {result['topic']}\n")
            f.write(f"文本类型: {result['text_type']}\n")
            f.write(f"文本长度: {result['length']} 字\n")
            f.write(f"迭代次数: {result['iterations']}\n")
            f.write("\n" + "=" * 60 + "\n")
            f.write("生成的文本：\n")
            f.write("=" * 60 + "\n\n")
            f.write(result["final_text"])
            f.write("\n\n[轮次摘要]\n")
            f.write(json.dumps(result.get("round_results", []), ensure_ascii=False, indent=2))

        progress_file = os.path.join(run_dir, "progress.log")
        print(f"\n结果已保存到: {output_file}")
        print(f"进度日志: {progress_file}")
        print(f"动态记忆索引: {os.path.join(config.memory_vector_db_path, 'memory_index.json')}")
    except KeyboardInterrupt:
        print("\n已手动中断（CTRL+C）。")
    except Exception as e:
        print(f"\n错误: {str(e)}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
