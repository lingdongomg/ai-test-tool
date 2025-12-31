"""
配置管理模块
支持多种配置方式：环境变量、配置文件、代码配置
使用 python-dotenv 自动加载 .env 文件
"""

import os
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

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
        default=4096,
        description="最大生成token数"
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
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4096"))
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


class AppConfig(BaseModel):
    """应用总配置"""
    llm: LLMConfig = Field(default_factory=LLMConfig)
    parser: LogParserConfig = Field(default_factory=LogParserConfig)
    test: TestConfig = Field(default_factory=TestConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    
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
            output=OutputConfig()
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
