"""
配置管理模块
支持多种配置方式：环境变量、配置文件、代码配置
使用 python-dotenv 自动加载 .env 文件
"""

import os
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, Field

# 自动加载 .env 文件
from dotenv import load_dotenv

# 查找项目根目录的 .env 文件
_project_root = Path(__file__).parent.parent.parent
_env_file = _project_root / ".env"
if _env_file.exists():
    load_dotenv(_env_file)
else:
    # 尝试当前工作目录
    load_dotenv()


class LLMConfig(BaseModel):
    """LLM配置"""
    provider: Literal["ollama", "openai", "azure", "anthropic"] = Field(
        default="ollama",
        description="LLM提供商"
    )
    model: str = Field(
        default="qwen3:8b",
        description="模型名称"
    )
    api_key: str | None = Field(
        default=None,
        description="API密钥（对于需要认证的服务）"
    )
    api_base: str | None = Field(
        default=None,
        description="API基础URL"
    )
    temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="生成温度"
    )
    max_tokens: int = Field(
        default=8192,
        description="最大生成token数（建议8192以上，避免输出截断）"
    )
    debug: bool = Field(
        default=False,
        description="是否开启LangChain调试模式"
    )

    @classmethod
    def from_env(cls) -> Self:
        """从环境变量加载配置"""
        return cls(
            provider=os.getenv("LLM_PROVIDER", "ollama"),  # type: ignore
            model=os.getenv("LLM_MODEL", "qwen3:8b"),
            api_key=os.getenv("LLM_API_KEY"),
            api_base=os.getenv("LLM_API_BASE"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.3")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "8192")),
            debug=os.getenv("LLM_DEBUG", "false").lower() in ("true", "1", "yes")
        )


class LogParserConfig(BaseModel):
    """日志解析配置"""
    chunk_size: int = Field(
        default=500,
        description="每次处理的日志行数"
    )
    max_lines: int | None = Field(
        default=None,
        description="最大处理行数"
    )
    supported_formats: list[str] = Field(
        default=["json", "jsonl", "text"],
        description="支持的日志格式"
    )


class TestConfig(BaseModel):
    """测试执行配置"""
    base_url: str = Field(
        default="http://localhost:8080",
        description="测试目标基础URL"
    )
    timeout: int = Field(
        default=30,
        description="请求超时时间（秒）"
    )
    retry_count: int = Field(
        default=3,
        description="失败重试次数"
    )
    concurrent_requests: int = Field(
        default=5,
        description="并发请求数"
    )
    headers: dict[str, str] = Field(
        default_factory=dict,
        description="默认请求头"
    )


class OutputConfig(BaseModel):
    """输出配置"""
    output_dir: str = Field(
        default="./output",
        description="输出目录"
    )
    report_format: Literal["html", "json", "markdown"] = Field(
        default="markdown",
        description="报告格式"
    )
    export_csv: bool = Field(
        default=True,
        description="是否导出CSV"
    )


class SecurityConfig(BaseModel):
    """安全配置"""
    # 环境标识
    environment: Literal["development", "staging", "production"] = Field(
        default="development",
        description="运行环境"
    )
    debug: bool = Field(
        default=False,
        description="调试模式（生产环境应关闭）"
    )

    # CORS 配置
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="允许的跨域来源（生产环境使用）"
    )
    cors_allow_credentials: bool = Field(
        default=True,
        description="是否允许携带凭证"
    )

    # 文件上传配置
    upload_max_size: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        description="最大上传文件大小（字节）"
    )
    upload_allowed_extensions: set[str] = Field(
        default={".log", ".txt", ".json", ".jsonl", ".csv"},
        description="允许的文件扩展名"
    )
    upload_allowed_mimetypes: set[str] = Field(
        default={
            "text/plain",
            "application/json",
            "text/csv",
            "application/octet-stream"  # 用于 .log 文件
        },
        description="允许的MIME类型"
    )

    @property
    def is_production(self) -> bool:
        """是否为生产环境"""
        return self.environment == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        """获取CORS允许的来源列表"""
        if self.is_production:
            return self.cors_origins
        return ["*"]  # 开发环境允许所有来源

    @classmethod
    def from_env(cls) -> Self:
        """从环境变量加载配置"""
        cors_origins_str = os.getenv("CORS_ORIGINS", "")
        cors_origins = [o.strip() for o in cors_origins_str.split(",") if o.strip()] \
            if cors_origins_str else ["http://localhost:3000", "http://localhost:5173"]

        return cls(
            environment=os.getenv("ENVIRONMENT", "development"),  # type: ignore
            debug=os.getenv("DEBUG", "false").lower() in ("true", "1", "yes"),
            cors_origins=cors_origins,
            cors_allow_credentials=os.getenv("CORS_CREDENTIALS", "true").lower() in ("true", "1", "yes"),
            upload_max_size=int(os.getenv("UPLOAD_MAX_SIZE", str(10 * 1024 * 1024))),
        )


class TaskConfig(BaseModel):
    """后台任务配置"""
    max_workers: int = Field(
        default=4,
        description="后台任务最大工作线程数"
    )

    @classmethod
    def from_env(cls) -> Self:
        """从环境变量加载配置"""
        return cls(
            max_workers=int(os.getenv("TASK_MAX_WORKERS", "4"))
        )


class AppConfig(BaseModel):
    """应用总配置"""
    llm: LLMConfig = Field(default_factory=LLMConfig)
    parser: LogParserConfig = Field(default_factory=LogParserConfig)
    test: TestConfig = Field(default_factory=TestConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    task: TaskConfig = Field(default_factory=TaskConfig)

    @classmethod
    def load(cls, config_path: str | None = None) -> Self:
        """加载配置"""
        if config_path and os.path.exists(config_path):
            import yaml
            with open(config_path, encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return cls(**data)

        # 从环境变量加载
        return cls(
            llm=LLMConfig.from_env(),
            parser=LogParserConfig(),
            test=TestConfig(),
            output=OutputConfig(),
            security=SecurityConfig.from_env(),
            task=TaskConfig.from_env()
        )


# 全局配置实例
_config: AppConfig | None = None


def get_config() -> AppConfig:
    """获取全局配置"""
    global _config
    if _config is None:
        _config = AppConfig.load()
    return _config


def set_config(config: AppConfig) -> None:
    """设置全局配置"""
    global _config
    _config = config
