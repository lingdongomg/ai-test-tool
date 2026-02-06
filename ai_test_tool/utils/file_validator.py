"""
文件上传验证工具

提供统一的文件上传验证功能，包括：
- 文件扩展名验证
- MIME 类型验证
- 文件大小验证
- 文件名净化
"""

import os
import re
import mimetypes
from pathlib import Path
from typing import BinaryIO

from fastapi import UploadFile

from ..config.settings import get_config
from ..exceptions import FileUploadError


def validate_upload_file(
    file: UploadFile,
    allowed_extensions: set[str] | None = None,
    allowed_mimetypes: set[str] | None = None,
    max_size: int | None = None
) -> None:
    """
    验证上传文件

    Args:
        file: FastAPI UploadFile 对象
        allowed_extensions: 允许的文件扩展名（如 {".json", ".txt"}），为 None 时使用配置默认值
        allowed_mimetypes: 允许的 MIME 类型，为 None 时使用配置默认值
        max_size: 最大文件大小（字节），为 None 时使用配置默认值

    Raises:
        FileUploadError: 文件验证失败
    """
    config = get_config().security

    # 使用默认配置
    if allowed_extensions is None:
        allowed_extensions = config.upload_allowed_extensions
    if allowed_mimetypes is None:
        allowed_mimetypes = config.upload_allowed_mimetypes
    if max_size is None:
        max_size = config.upload_max_size

    filename = file.filename or "unknown"

    # 1. 验证文件名
    if not filename or filename.strip() == "":
        raise FileUploadError("文件名不能为空", filename)

    # 2. 验证文件扩展名
    ext = Path(filename).suffix.lower()
    if allowed_extensions and ext not in allowed_extensions:
        raise FileUploadError(
            f"不支持的文件类型 '{ext}'，允许的类型: {', '.join(sorted(allowed_extensions))}",
            filename
        )

    # 3. 验证 MIME 类型
    content_type = file.content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
    if allowed_mimetypes and content_type not in allowed_mimetypes:
        # 对于某些扩展名，允许通用的 octet-stream
        if content_type != "application/octet-stream":
            raise FileUploadError(
                f"不支持的文件 MIME 类型 '{content_type}'",
                filename
            )

    # 4. 验证文件大小（如果可以获取）
    if file.size is not None and file.size > max_size:
        max_size_mb = max_size / (1024 * 1024)
        file_size_mb = file.size / (1024 * 1024)
        raise FileUploadError(
            f"文件大小 ({file_size_mb:.2f}MB) 超过限制 ({max_size_mb:.2f}MB)",
            filename
        )


async def validate_upload_file_content(
    file: UploadFile,
    max_size: int | None = None
) -> bytes:
    """
    读取并验证文件内容大小

    Args:
        file: FastAPI UploadFile 对象
        max_size: 最大文件大小（字节）

    Returns:
        文件内容

    Raises:
        FileUploadError: 文件内容验证失败
    """
    config = get_config().security
    if max_size is None:
        max_size = config.upload_max_size

    filename = file.filename or "unknown"

    try:
        content = await file.read()
    except Exception as e:
        raise FileUploadError(f"读取文件内容失败: {e}", filename)

    if len(content) > max_size:
        max_size_mb = max_size / (1024 * 1024)
        file_size_mb = len(content) / (1024 * 1024)
        raise FileUploadError(
            f"文件大小 ({file_size_mb:.2f}MB) 超过限制 ({max_size_mb:.2f}MB)",
            filename
        )

    return content


def sanitize_filename(filename: str) -> str:
    """
    净化文件名，移除潜在危险字符

    Args:
        filename: 原始文件名

    Returns:
        净化后的文件名
    """
    if not filename:
        return "unnamed_file"

    # 获取文件名和扩展名
    name = Path(filename).stem
    ext = Path(filename).suffix.lower()

    # 移除路径分隔符和危险字符
    # 只保留字母、数字、中文、下划线、横线、点
    name = re.sub(r'[^\w\u4e00-\u9fff\-.]', '_', name)

    # 移除连续的下划线
    name = re.sub(r'_+', '_', name)

    # 移除首尾的下划线和点
    name = name.strip('_.')

    # 确保文件名不为空
    if not name:
        name = "unnamed_file"

    # 限制文件名长度（保留扩展名空间）
    max_name_length = 200
    if len(name) > max_name_length:
        name = name[:max_name_length]

    return f"{name}{ext}"


def get_safe_upload_path(base_dir: str | Path, filename: str) -> Path:
    """
    获取安全的上传文件路径，防止路径遍历攻击

    Args:
        base_dir: 基础目录
        filename: 文件名

    Returns:
        安全的文件完整路径

    Raises:
        FileUploadError: 路径验证失败
    """
    base_dir = Path(base_dir).resolve()
    safe_filename = sanitize_filename(filename)
    target_path = (base_dir / safe_filename).resolve()

    # 确保目标路径在基础目录内
    if not str(target_path).startswith(str(base_dir)):
        raise FileUploadError("非法的文件路径", filename)

    return target_path
