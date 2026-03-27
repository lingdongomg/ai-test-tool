"""
实时日志流 API
提供 WebSocket 日志接入通道和日志源 CRUD
"""

import json
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query, Depends
from pydantic import BaseModel, Field

from ...database.models.log_source import LogSource
from ...database.repositories.log_source import LogSourceRepository
from ...services.log_stream import LogStreamService
from ...utils.logger import get_logger
from ..dependencies import get_log_stream_service, get_log_source_repository

router = APIRouter()
logger = get_logger()


# ==================== 请求/响应模型 ====================

class CreateLogSourceRequest(BaseModel):
    """创建日志源请求"""
    name: str = Field(..., description="日志源名称")
    description: str = Field(default="", description="描述")
    tags: list[str] = Field(default_factory=list, description="标签")
    buffer_size: int = Field(default=100, ge=10, le=1000, description="缓冲区行数阈值")
    buffer_timeout_sec: int = Field(default=30, ge=5, le=300, description="缓冲超时秒数")
    auto_learn: bool = Field(default=True, description="是否自动学习")
    auto_approve_threshold: float = Field(default=0.8, ge=0, le=1, description="自动审核阈值")


class UpdateLogSourceRequest(BaseModel):
    """更新日志源请求"""
    name: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    buffer_size: int | None = Field(default=None, ge=10, le=1000)
    buffer_timeout_sec: int | None = Field(default=None, ge=5, le=300)
    auto_learn: bool | None = None
    auto_approve_threshold: float | None = Field(default=None, ge=0, le=1)
    is_enabled: bool | None = None


# ==================== 日志源 CRUD ====================

@router.get("/sources")
async def list_log_sources(
    is_enabled: bool | None = Query(None),
    status: str | None = Query(None),
    source_repo: LogSourceRepository = Depends(get_log_source_repository),
) -> dict[str, Any]:
    """获取日志源列表"""
    sources = source_repo.list_all(is_enabled=is_enabled, status=status)
    return {
        "total": len(sources),
        "items": [s.to_dict() for s in sources],
    }


@router.post("/sources", status_code=201)
async def create_log_source(
    request: CreateLogSourceRequest,
    source_repo: LogSourceRepository = Depends(get_log_source_repository),
) -> dict[str, Any]:
    """创建日志源"""
    source = LogSource(
        source_id=str(uuid.uuid4())[:8],
        name=request.name,
        description=request.description,
        tags=request.tags,
        buffer_size=request.buffer_size,
        buffer_timeout_sec=request.buffer_timeout_sec,
        auto_learn=request.auto_learn,
        auto_approve_threshold=request.auto_approve_threshold,
    )
    source_repo.create(source)

    return {
        "success": True,
        "source_id": source.source_id,
        "message": "日志源创建成功",
        "ws_url": f"/ws/logs?source_id={source.source_id}",
    }


@router.put("/sources/{source_id}")
async def update_log_source(
    source_id: str,
    request: UpdateLogSourceRequest,
    source_repo: LogSourceRepository = Depends(get_log_source_repository),
) -> dict[str, Any]:
    """更新日志源配置"""
    existing = source_repo.get_by_id(source_id)
    if not existing:
        raise HTTPException(status_code=404, detail="日志源不存在")

    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if updates:
        source_repo.update(source_id, updates)

    return {"success": True, "message": "日志源更新成功"}


@router.delete("/sources/{source_id}", status_code=204)
async def delete_log_source(
    source_id: str,
    source_repo: LogSourceRepository = Depends(get_log_source_repository),
    service: LogStreamService = Depends(get_log_stream_service),
) -> None:
    """删除日志源（同时断开活跃连接）"""
    existing = source_repo.get_by_id(source_id)
    if not existing:
        raise HTTPException(status_code=404, detail="日志源不存在")

    # 断开活跃连接
    service.unregister_connection(source_id)
    source_repo.delete(source_id)


@router.get("/sources/{source_id}/stats")
async def get_log_source_stats(
    source_id: str,
    service: LogStreamService = Depends(get_log_stream_service),
) -> dict[str, Any]:
    """获取日志源详细统计"""
    try:
        return service.get_source_stats(source_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ==================== WebSocket 端点 ====================

@router.websocket("/ws")
async def websocket_log_endpoint(
    websocket: WebSocket,
    source_id: str = Query(...),
    token: str | None = Query(None),
):
    """
    实时日志推送 WebSocket 端点

    客户端发送消息格式：
    - {"type": "log", "line": "日志行"}
    - {"type": "batch", "lines": ["行1", "行2"]}
    - {"type": "ping"}
    """
    # 延迟获取服务（避免循环依赖）
    service = get_log_stream_service()

    # 检查连接数限制
    if not service.can_accept_connection():
        await websocket.close(code=4003, reason="超出最大连接数限制")
        return

    # 验证 source_id
    try:
        service.register_connection(source_id, websocket)
    except ValueError as e:
        await websocket.accept()
        await websocket.close(code=4002, reason=str(e))
        return

    await websocket.accept()
    logger.info(f"WebSocket 连接已建立: source_id={source_id}")

    try:
        while True:
            data = await websocket.receive_text()

            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                # 非 JSON 消息当作单行日志处理
                message = {"type": "log", "line": data}

            response = await service.on_message(source_id, message)

            if response:
                await websocket.send_text(json.dumps(response, ensure_ascii=False))

    except WebSocketDisconnect:
        logger.info(f"WebSocket 连接断开: source_id={source_id}")
    except Exception as e:
        logger.error(f"WebSocket 错误 (source_id={source_id}): {e}")
    finally:
        service.unregister_connection(source_id)


# ==================== 告警 API ====================

@router.get("/alerts")
async def list_alerts(
    source_id: str | None = None,
    hours: int = 24,
    limit: int = 50,
):
    """获取最近告警列表"""
    from ...services.alert_manager import AlertManager
    manager = AlertManager()
    alerts = manager.get_recent_alerts(
        source_id=source_id or "",
        hours=hours,
        limit=limit,
    )
    return {"success": True, "total": len(alerts), "alerts": alerts}


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str):
    """确认告警"""
    from ...services.alert_manager import AlertManager
    manager = AlertManager()
    success = manager.acknowledge_alert(alert_id)
    if success:
        return {"success": True, "message": "告警已确认"}
    return {"success": False, "message": "确认失败"}
