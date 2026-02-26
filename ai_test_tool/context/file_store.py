"""
文件系统上下文存储

将任务上下文持久化到文件系统，支持跨会话恢复
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class FileContextStore:
    """
    文件系统上下文存储

    以 JSON 文件方式将任务上下文持久化到工作目录
    """

    def __init__(self, base_dir: str = ".context_store"):
        """
        Args:
            base_dir: 存储根目录
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, task_id: str, data: dict[str, Any]) -> Path:
        """
        保存上下文

        Args:
            task_id: 任务标识
            data: 上下文数据

        Returns:
            保存的文件路径
        """
        file_path = self._get_path(task_id)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "task_id": task_id,
            "saved_at": datetime.now().isoformat(),
            "data": data,
        }

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        logger.debug(f"上下文已保存: {file_path}")
        return file_path

    def load(self, task_id: str) -> dict[str, Any] | None:
        """
        加载上下文

        Args:
            task_id: 任务标识

        Returns:
            上下文数据，不存在返回 None
        """
        file_path = self._get_path(task_id)
        if not file_path.exists():
            return None

        with open(file_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        return payload.get("data")

    def delete(self, task_id: str) -> bool:
        """
        删除上下文

        Args:
            task_id: 任务标识

        Returns:
            是否删除成功
        """
        file_path = self._get_path(task_id)
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def list_tasks(self) -> list[str]:
        """列出所有存储的任务 ID"""
        return [
            p.stem
            for p in self.base_dir.glob("*.json")
        ]

    def _get_path(self, task_id: str) -> Path:
        """获取存储文件路径"""
        # 清理 task_id 中的不安全字符
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in task_id)
        return self.base_dir / f"{safe_id}.json"
