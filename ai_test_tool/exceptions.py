"""
自定义异常层次结构

提供统一的异常处理机制，支持：
- 错误码标识
- 生产环境错误信息脱敏
- 结构化错误响应
"""

from typing import Any


class AITestToolError(Exception):
    """
    基础异常类

    所有自定义异常都应继承此类，提供统一的错误处理接口。
    """

    def __init__(
        self,
        message: str,
        code: str = "UNKNOWN_ERROR",
        details: dict[str, Any] | None = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)

    def to_dict(self, include_details: bool = True) -> dict[str, Any]:
        """转换为字典格式"""
        result = {
            "code": self.code,
            "message": self.message
        }
        if include_details and self.details:
            result["details"] = self.details
        return result


# =====================================================
# 客户端错误 (4xx)
# =====================================================

class ValidationError(AITestToolError):
    """
    输入验证错误 - 400

    用于请求参数验证失败的场景。
    """

    def __init__(self, message: str, field: str | None = None):
        details = {"field": field} if field else {}
        super().__init__(message, "VALIDATION_ERROR", details)
        self.field = field


class NotFoundError(AITestToolError):
    """
    资源不存在 - 404

    用于请求的资源不存在的场景。
    """

    def __init__(self, resource: str, identifier: str):
        message = f"{resource} '{identifier}' 不存在"
        details = {"resource": resource, "identifier": identifier}
        super().__init__(message, "NOT_FOUND", details)
        self.resource = resource
        self.identifier = identifier


class ConflictError(AITestToolError):
    """
    资源冲突 - 409

    用于资源已存在或状态冲突的场景。
    """

    def __init__(self, message: str, resource: str | None = None):
        details = {"resource": resource} if resource else {}
        super().__init__(message, "CONFLICT", details)


class UnauthorizedError(AITestToolError):
    """
    未授权 - 401

    用于需要认证但未提供凭证的场景。
    """

    def __init__(self, message: str = "需要登录认证"):
        super().__init__(message, "UNAUTHORIZED")


class ForbiddenError(AITestToolError):
    """
    禁止访问 - 403

    用于已认证但无权限访问的场景。
    """

    def __init__(self, message: str = "无权限访问"):
        super().__init__(message, "FORBIDDEN")


class FileUploadError(AITestToolError):
    """
    文件上传错误 - 400

    用于文件上传验证失败的场景。
    """

    def __init__(self, message: str, filename: str | None = None):
        details = {"filename": filename} if filename else {}
        super().__init__(message, "FILE_UPLOAD_ERROR", details)
        self.filename = filename


# =====================================================
# 服务端错误 (5xx)
# =====================================================

class DatabaseError(AITestToolError):
    """
    数据库操作错误 - 500

    用于数据库操作失败的场景。
    生产环境不应暴露具体的数据库错误信息。
    """

    def __init__(self, message: str = "数据库操作失败", original_error: Exception | None = None):
        details = {}
        if original_error:
            details["original_error"] = str(original_error)
        super().__init__(message, "DATABASE_ERROR", details)
        self.original_error = original_error


class LLMError(AITestToolError):
    """
    LLM 调用错误 - 503

    用于大语言模型调用失败的场景。
    """

    def __init__(self, message: str = "AI 服务暂时不可用", provider: str | None = None):
        details = {"provider": provider} if provider else {}
        super().__init__(message, "LLM_ERROR", details)
        self.provider = provider


class ExternalServiceError(AITestToolError):
    """
    外部服务错误 - 502

    用于调用外部API失败的场景。
    """

    def __init__(self, message: str, service: str | None = None, status_code: int | None = None):
        details = {}
        if service:
            details["service"] = service
        if status_code:
            details["status_code"] = status_code
        super().__init__(message, "EXTERNAL_SERVICE_ERROR", details)
        self.service = service
        self.status_code = status_code


class TaskError(AITestToolError):
    """
    后台任务错误 - 500

    用于后台任务执行失败的场景。
    """

    def __init__(self, message: str, task_id: str | None = None):
        details = {"task_id": task_id} if task_id else {}
        super().__init__(message, "TASK_ERROR", details)
        self.task_id = task_id


class ConfigurationError(AITestToolError):
    """
    配置错误 - 500

    用于配置缺失或无效的场景。
    """

    def __init__(self, message: str, config_key: str | None = None):
        details = {"config_key": config_key} if config_key else {}
        super().__init__(message, "CONFIGURATION_ERROR", details)
        self.config_key = config_key


# =====================================================
# 异常映射
# =====================================================

# HTTP状态码到异常类的映射
HTTP_STATUS_MAP: dict[type[AITestToolError], int] = {
    ValidationError: 400,
    FileUploadError: 400,
    UnauthorizedError: 401,
    ForbiddenError: 403,
    NotFoundError: 404,
    ConflictError: 409,
    DatabaseError: 500,
    TaskError: 500,
    ConfigurationError: 500,
    ExternalServiceError: 502,
    LLMError: 503,
}


def get_http_status(exc: AITestToolError) -> int:
    """获取异常对应的HTTP状态码"""
    return HTTP_STATUS_MAP.get(type(exc), 500)
