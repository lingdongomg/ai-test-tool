# 该文件内容使用AI生成，注意识别准确性
"""
通知服务

提供统一的通知发送接口，当前实现 webhook 通道。
预留 NotificationChannel 抽象接口，未来可接入企微/钉钉/邮件。
"""

import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class NotificationService:
    """统一通知服务"""

    def send_webhook(
        self,
        url: str,
        payload: dict[str, Any],
        max_retries: int = 3,
    ) -> bool:
        """
        发送 webhook 通知

        Args:
            url: webhook URL
            payload: 请求体 JSON
            max_retries: 最大重试次数

        Returns:
            是否发送成功
        """
        import httpx

        retry_delays = [5, 15, 30]  # 重试间隔（秒）

        for attempt in range(max_retries):
            try:
                with httpx.Client(timeout=10) as client:
                    response = client.post(
                        url,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                    )
                    if 200 <= response.status_code < 300:
                        logger.info(f"Webhook 发送成功: {url} (HTTP {response.status_code})")
                        return True
                    else:
                        logger.warning(
                            f"Webhook 返回非 2xx: {url} (HTTP {response.status_code}), "
                            f"重试 {attempt + 1}/{max_retries}"
                        )
            except Exception as e:
                logger.warning(f"Webhook 发送异常: {url}, 重试 {attempt + 1}/{max_retries}: {e}")

            if attempt < max_retries - 1:
                time.sleep(retry_delays[attempt])

        logger.error(f"Webhook 发送最终失败: {url} (已重试 {max_retries} 次)")
        return False
