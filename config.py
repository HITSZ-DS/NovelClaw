"""
配置管理模块
"""
import os
from dotenv import load_dotenv, dotenv_values
from typing import Optional
import os.path


def _env_flag(name: str, default: str = "0") -> bool:
    val = os.getenv(name, default)
    return str(val).strip() in {"1", "true", "True", "yes", "YES", "y", "Y", "on", "ON"}

# 始终从当前文件所在目录加载 .env，若缺失则回退到项目根目录或当前工作目录
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_DOTENV_CANDIDATES = [
    os.path.join(_BASE_DIR, ".env"),
    os.path.join(os.path.dirname(_BASE_DIR), ".env"),
    os.path.join(os.getcwd(), ".env"),
]
loaded = False
for _p in _DOTENV_CANDIDATES:
    if os.path.exists(_p):
        load_dotenv(dotenv_path=_p, encoding="utf-8-sig", override=False)
        loaded = True
        break
# 兜底：若仍未加载到 key，则手动读取候选路径并写入环境变量
if not os.getenv("DEEPSEEK_API_KEY"):
    for _p in _DOTENV_CANDIDATES:
        if os.path.exists(_p):
            vals = dotenv_values(_p, encoding="utf-8-sig")
            for k, v in vals.items():
                if k and v and k not in os.environ:
                    os.environ[k] = v
            break
# 处理可能存在的 BOM 前缀的 key
for k in list(os.environ.keys()):
    if k.startswith("\ufeff"):
        clean_k = k.lstrip("\ufeff")
        if clean_k and clean_k not in os.environ:
            os.environ[clean_k] = os.environ[k]


class Config:
    """系统配置类"""
    
    def __init__(self, require_api_key: bool = True):
        # 基础语言/提供商配置
        # 默认 auto：根据用户输入动态识别 zh/en
        self.language: str = os.getenv("LANGUAGE", "auto").lower()  # zh / en / auto
        # 工作流模式：chaptered（分章）/ unfixed（整篇自由体，推荐英文）
        self.workflow_mode: str = os.getenv("WORKFLOW_MODE", "chaptered").lower()
        # 英文子模式：novel（长篇分段写）、premise_story（根据 premise 单篇），可扩展
        self.en_mode: str = os.getenv("EN_MODE", "novel").lower()
        # 是否完全跳过大纲（英文自由生成时可用）
        self.outline_free: bool = os.getenv("OUTLINE_FREE", "0") in {"1", "true", "True", "yes", "YES"}
        # 英文分段控制（unfixed/novel分段提示长度）
        self.en_segment_words: int = int(os.getenv("EN_SEGMENT_WORDS", "1200"))
        self.en_segments: int = int(os.getenv("EN_SEGMENTS", "3"))
        self.llm_provider: str = os.getenv("LLM_PROVIDER", "deepseek").lower()

        # API Key 与 Base URL（优先使用通用变量，兼容任意 provider）
        generic_api_key = os.getenv("LLM_API_KEY", "").strip()
        generic_base_url = os.getenv("LLM_BASE_URL", "").strip()
        if self.llm_provider == "deepseek":
            fallback_key = (
                os.getenv("DEEPSEEK_API_KEY")
                or os.getenv("CODEX_API_KEY")
                or os.getenv("OPENAI_API_KEY")
                or ""
            )
            fallback_base = (
                os.getenv("DEEPSEEK_BASE_URL")
                or "https://api.deepseek.com/v1"
            )
        elif self.llm_provider in {"codex", "packycode"}:
            fallback_key = (
                os.getenv("CODEX_API_KEY")
                or os.getenv("OPENAI_API_KEY")
                or os.getenv("DEEPSEEK_API_KEY", "")
            )
            fallback_base = (
                os.getenv("CODEX_BASE_URL")
                or os.getenv("OPENAI_BASE_URL")
                or "https://codex-api.packycode.com/v1"
            )
        else:
            fallback_key = (
                os.getenv("OPENAI_API_KEY")
                or os.getenv("CODEX_API_KEY")
                or os.getenv("DEEPSEEK_API_KEY", "")
            )
            fallback_base = (
                os.getenv("OPENAI_BASE_URL")
                or os.getenv("CODEX_BASE_URL")
                or os.getenv("DEEPSEEK_BASE_URL")
                or "https://api.openai.com/v1"
            )

        self.api_key: str = generic_api_key or fallback_key
        self.api_base_url: str = generic_base_url or fallback_base
        # 保持向后兼容的字段
        self.deepseek_api_key: str = self.api_key if self.llm_provider == "deepseek" else os.getenv("DEEPSEEK_API_KEY", "")
        self.deepseek_base_url: str = self.api_base_url or "https://api.deepseek.com/v1"
        
        # RAG 配置
        # 作为“基目录”使用；具体 collection 建议分开存储在子目录，避免单库损坏影响全局
        self.vector_db_path: str = os.getenv("VECTOR_DB_PATH", "./vector_db")

        # 各向量库子路径（隔离，降低 Chroma 索引损坏时的连带影响）
        self.memory_vector_db_path: str = os.getenv(
            "MEMORY_VECTOR_DB_PATH",
            os.path.join(self.vector_db_path, "memory")
        )
        self.knowledge_vector_db_path: str = os.getenv(
            "KNOWLEDGE_VECTOR_DB_PATH",
            os.path.join(self.vector_db_path, "knowledge")
        )
        # 静态知识库使用独立的向量库路径，避免与其它 collection 共用时索引损坏影响全局
        self.static_vector_db_path: str = os.getenv(
            "STATIC_VECTOR_DB_PATH",
            os.path.join(self.vector_db_path, "static_kb")
        )
        self.embedding_model: str = os.getenv(
            "EMBEDDING_MODEL",
            "none"
        )
        self.chunk_size: int = int(os.getenv("CHUNK_SIZE", "500"))
        self.chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "100"))
        self.top_k: int = int(os.getenv("TOP_K", "5"))  # 检索返回的文档数量
        # Dynamic memory weighting controls
        self.memory_score_semantic_weight: float = float(os.getenv("MEMORY_SCORE_SEMANTIC_WEIGHT", "0.5"))
        self.memory_score_importance_weight: float = float(os.getenv("MEMORY_SCORE_IMPORTANCE_WEIGHT", "0.25"))
        self.memory_score_recency_weight: float = float(os.getenv("MEMORY_SCORE_RECENCY_WEIGHT", "0.15"))
        self.memory_score_reinforcement_weight: float = float(os.getenv("MEMORY_SCORE_REINFORCEMENT_WEIGHT", "0.10"))
        self.memory_recency_half_life_days: float = float(os.getenv("MEMORY_RECENCY_HALF_LIFE_DAYS", "14"))
        self.memory_reinforcement_cap: float = float(os.getenv("MEMORY_REINFORCEMENT_CAP", "12"))
        self.memory_retrieval_oversample_factor: int = int(os.getenv("MEMORY_RETRIEVAL_OVERSAMPLE_FACTOR", "4"))
        self.memory_recent_chapter_window: int = int(os.getenv("MEMORY_RECENT_CHAPTER_WINDOW", "1"))
        self.memory_fact_chapter_window: int = int(os.getenv("MEMORY_FACT_CHAPTER_WINDOW", "2"))
        self.memory_keep_writer_rounds: bool = _env_flag("MEMORY_KEEP_WRITER_ROUNDS", "0")
        self.memory_anchor_bonus: float = float(os.getenv("MEMORY_ANCHOR_BONUS", "0.18"))
        self.memory_anchor_decay_factor: float = float(os.getenv("MEMORY_ANCHOR_DECAY_FACTOR", "0.35"))
        self.memory_context_char_budget: int = int(os.getenv("MEMORY_CONTEXT_CHAR_BUDGET", "5000"))
        # 静态知识库：每条原始文本最多写入多少个 chunk（降低磁盘占用与索引损坏概率）
        self.static_max_chunks_per_doc: int = int(os.getenv("STATIC_MAX_CHUNKS_PER_DOC", "12"))
        
        # Agent 配置
        self.max_iterations: int = int(os.getenv("MAX_ITERATIONS", "60"))
        self.temperature: float = float(os.getenv("TEMPERATURE", "0.7"))
        # 最大输出token，默认 8000（可通过环境变量覆盖，但高于接口上限会在客户端再截断）
        self.max_tokens: int = int(os.getenv("MAX_TOKENS", "8000"))
        # LLM call timeout/retry controls. Set LLM_TIMEOUT_SECONDS=0 to disable request timeout.
        self.llm_timeout_seconds: int = int(os.getenv("LLM_TIMEOUT_SECONDS", "0"))
        self.llm_max_retries: int = int(os.getenv("LLM_MAX_RETRIES", "1"))
        default_model = "deepseek-chat" if self.llm_provider == "deepseek" else "gpt-5.2"
        self.model_name: str = os.getenv("MODEL_NAME", default_model)
        self.wire_api: str = os.getenv("WIRE_API", "chat").lower()
        
        # Workflow 配置
        self.min_quality_score: float = 0.7  # 最低质量分数
        self.max_retry_rounds: int = 3  # 最大重试轮数
        
        # 上下文控制（避免超长生成时提示爆炸）
        # 默认适度放宽，便于提示携带更多大纲/摘要信息
        self.context_max_chars: int = int(os.getenv("CONTEXT_MAX_CHARS", "12000"))
        self.recent_context_items: int = int(os.getenv("RECENT_CONTEXT_ITEMS", "4"))
        # per-run memory isolation
        self.memory_reset_each_run: bool = os.getenv("MEMORY_RESET_EACH_RUN", "1") in {"1", "true", "True", "yes", "YES"}
        # store full chapter text in vector memory
        self.store_full_text_in_memory: bool = os.getenv("STORE_FULL_TEXT_IN_MEMORY", "0") in {"1", "true", "True", "yes", "YES"}
        # force total length to reach target（默认不强制，目标为软约束）
        self.force_target_length: bool = os.getenv("FORCE_TARGET_LENGTH", "0") in {"1", "true", "True", "yes", "YES"}
        # minimum chapter length
        # 默认单章不少于 3000 字（可用环境变量覆盖）
        self.min_chapter_chars: int = int(os.getenv("MIN_CHAPTER_CHARS", "3000"))
        # 单章硬上限（0 表示不启用硬上限）
        self.max_chapter_chars: int = int(os.getenv("MAX_CHAPTER_CHARS", "0"))
        # 当未设置硬上限时，按目标章节长度的该比例作为上限
        self.chapter_max_ratio: float = float(os.getenv("CHAPTER_MAX_RATIO", "1.15"))
        # chapter target ratio
        self.chapter_target_ratio: float = float(os.getenv("CHAPTER_TARGET_RATIO", "1.0"))
        # max subrounds per chapter
        self.max_chapter_subrounds: int = int(os.getenv("MAX_CHAPTER_SUBROUNDS", "3"))
        # max total iterations
        self.max_total_iterations: int = int(os.getenv("MAX_TOTAL_ITERATIONS", "120"))
        # analysis interval (chapters)
        self.analysis_interval: int = int(os.getenv("ANALYSIS_INTERVAL", "5"))
        # run output
        self.runs_dir: str = os.getenv("RUNS_DIR", "runs")
        self.run_id: str = os.getenv("RUN_ID", "")
        # 每个外层迭代内写多少章（可按需提升效率，默认 1 章/轮）
        self.chapters_per_iter: int = int(os.getenv("CHAPTERS_PER_ITER", "1"))

        # 快速生成模式：仅走核心写作 Agent，降低回合数
        self.fast_mode: bool = os.getenv("FAST_MODE", "0") in {"1", "true", "True", "yes", "YES"}
        # 章节周期：每隔多少章/轮走一次完整多Agent，其余仅写作（加速长篇生成）
        self.full_cycle_interval: int = int(os.getenv("FULL_CYCLE_INTERVAL", "0"))  # 0 表示每次都走完整
        # 静态库是否仅首轮使用（减少后续检索开销）
        self.static_kb_first_only: bool = os.getenv("STATIC_KB_FIRST_ONLY", "1") in {"1", "true", "True", "yes", "YES"}
        # RAG controls (for local memory-only mode and server deployment flexibility)
        # 默认仅动态 memory：关闭静态 RAG 与静态知识库
        self.memory_only_mode: bool = _env_flag("MEMORY_ONLY_MODE", "1")
        self.enable_rag: bool = _env_flag("ENABLE_RAG", "0") and not _env_flag("DISABLE_RAG", "0")
        self.enable_static_kb: bool = _env_flag("ENABLE_STATIC_KB", "0") and not _env_flag("DISABLE_STATIC_KB", "0")
        if self.memory_only_mode:
            self.enable_rag = False
            self.enable_static_kb = False
        # Static KB is part of RAG; if RAG is off, static KB must be off as well.
        if not self.enable_rag:
            self.enable_static_kb = False
        # 评估/打分间隔（迭代轮为粒度），减少每轮评分的开销
        self.eval_interval: int = int(os.getenv("EVAL_INTERVAL", "4"))
        # 是否启用评估Agent（默认关闭，避免影响主写作工作流时延）
        self.enable_evaluator: bool = _env_flag("ENABLE_EVALUATOR", "0") and not _env_flag("DISABLE_EVALUATOR", "0")
        # 是否打印每次 LLM 调用耗时日志（用于终端进度感知）
        self.llm_call_log: bool = _env_flag("LLM_CALL_LOG", "1")
        # 是否开启转折点检测（默认开启，如需关闭可设置 TURNING_POINT_ENABLED=0）
        self.turning_point_enabled: bool = os.getenv("TURNING_POINT_ENABLED", "1") in {"1", "true", "True", "yes", "YES"}
        # 章节规划控制（已改为自动估算，这里保留默认值但不会依赖 env）
        self.target_chapters_min: int = 5
        self.target_chapters_max: int = 30
        self.per_chapter_target_hint: int = 3300
        
        # 验证配置
        if require_api_key and not self.api_key:
            raise ValueError("请设置 LLM_API_KEY，或设置 CODEX_API_KEY/OPENAI_API_KEY/DEEPSEEK_API_KEY")
    
    def __repr__(self):
        return f"Config(model={self.model_name}, db_path={self.vector_db_path})"
