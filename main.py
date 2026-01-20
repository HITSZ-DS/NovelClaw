"""
主程序入口
"""
import os
import datetime, json
from config import Config
from workflow.executor import CompositiveExecutor


def main():
    """主函数"""
    print("=" * 60)
    print("协同式 RAG-Agent 长文本生成系统")
    print("=" * 60)
    print()
    
    # 检查API Key
    if not os.getenv("DEEPSEEK_API_KEY"):
        print("错误：请设置 DEEPSEEK_API_KEY 环境变量")
        print("可以在 .env 文件中设置，或使用以下命令：")
        print("  export DEEPSEEK_API_KEY=your_api_key")
        return
    
    try:
        # 读取用户输入的 idea（留空则使用示例）
        user_idea = input("请输入你的创意想法（留空使用示例）: ").strip()
        if not user_idea:
            user_idea = "一个关于未来世界AI觉醒的科幻故事，风格细腻宏大，探讨人工智能与人类的关系"
            print(f"\n使用示例 idea: {user_idea}")
        else:
            print(f"\n收到自定义 idea: {user_idea}")

        # 初始化配置（默认每次运行使用新的动态记忆库）
        config = Config()
        if not config.run_id:
            config.run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if config.memory_reset_each_run:
            config.memory_vector_db_path = os.path.join(
                config.vector_db_path,
                "memory",
                f"run_{config.run_id}"
            )
        print(f"[配置] 动态记忆库: {config.memory_vector_db_path}")

        print(f"[配置] 模型: {config.model_name}")
        print(f"[配置] 向量数据库(基目录): {config.vector_db_path}")
        print(f"[配置] 静态知识库: {config.static_vector_db_path}")
        print()
        
        # 初始化执行器
        executor = CompositiveExecutor(config)
        
        # 可以添加初始知识库内容（可选）
        initial_knowledge = """
        科幻小说创作要点：
        1. 世界观设定要完整，包括科技水平、社会结构、时间背景
        2. 人物要有深度，动机要清晰
        3. 情节要有冲突和高潮
        4. 保持逻辑一致性
        """
        
        print("开始生成长文本...")
        print("-" * 60)
        result = executor.generate_long_text(
            idea=user_idea,
            initial_knowledge=initial_knowledge,
            auto_analyze=True  # 自动分析idea，推断genre和style
        )
        
        # 方式2：手动指定参数（如果不想自动分析）
        # result = executor.generate_long_text(
        #     idea="未来世界的AI觉醒",
        #     topic="科幻小说：未来世界的AI觉醒",
        #     text_type="creative",
        #     target_length=3000,
        #     genre="科幻",
        #     style_tags=["细腻", "宏大"],
        #     auto_analyze=False
        # )
        
        # 输出结果
        print("\n" + "=" * 60)
        print("生成完成！")
        print("=" * 60)
        print(f"\n主题: {result['topic']}")
        print(f"文本类型: {result['text_type']}")
        print(f"文本长度: {result['length']} 字")
        print(f"迭代次数: {result['iterations']}")
        print(f"已写章节: {result.get('chapters_written', 0)}")
        print(f"最佳奖励分数: {result['best_reward']:.3f}")
        if 'consistency' in result:
            print(f"一致性分数: {result['consistency'].get('overall_confidence', 0):.3f}")
        # 打印累计字数摘要
        if result.get("progress_log"):
            lines = result["progress_log"].splitlines()
            total_line = [l for l in lines if l.startswith("total_words=")]
            if total_line:
                print(total_line[-1])
        print("\n生成的文本：")
        print("-" * 60)
        print(result['final_text'])
        print("-" * 60)
        
        # 保存结果（单次 run 独立文件，便于溯源）
        run_dir = os.path.join(config.runs_dir, config.run_id)
        os.makedirs(run_dir, exist_ok=True)
        output_file = os.path.join(run_dir, "output.txt")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"主题: {result['topic']}\n")
            f.write(f"文本类型: {result['text_type']}\n")
            f.write(f"文本长度: {result['length']} 字\n")
            f.write(f"迭代次数: {result['iterations']}\n")
            f.write(f"最佳奖励分数: {result['best_reward']:.3f}\n")
            f.write("\n" + "=" * 60 + "\n")
            f.write("生成的文本：\n")
            f.write("=" * 60 + "\n\n")
            f.write(result['final_text'])
            # 追加 round 摘要，方便排查
            f.write("\n\n[轮次摘要]\n")
            f.write(json.dumps(result.get("round_results", []), ensure_ascii=False, indent=2))
        
        print(f"\n结果已保存到: {output_file}")
        
    except Exception as e:
        print(f"\n错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()



