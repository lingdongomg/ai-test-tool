# 该文件内容使用AI生成，注意识别准确性
"""
开发自测模块 - 测试用例文件夹管理路由
"""

import re
import uuid
from typing import Any
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from ....database import DatabaseManager
from ....database.repositories.test import TestFolderRepository
from ....database.models.test import TestFolder
from ....utils.logger import get_logger
from ...dependencies import get_database, get_test_folder_repository

router = APIRouter()
logger = get_logger()

MAX_DEPTH = 6


# ==================== Request / Response Models ====================

class CreateFolderRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="文件夹名称")
    parent_id: str | None = Field(default=None, description="父文件夹ID，NULL表示顶级")
    description: str | None = Field(default=None, description="描述")


class UpdateFolderRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    parent_id: str | None = Field(default=None)
    sort_order: int | None = Field(default=None)
    description: str | None = Field(default=None)


class MoveCasesRequest(BaseModel):
    case_ids: list[str] = Field(..., min_length=1, description="用例ID列表")
    folder_id: str | None = Field(default=None, description="目标文件夹ID，NULL表示移出")


# ==================== 文件夹管理 ====================

@router.get("/folders")
async def list_folders(
    repo: TestFolderRepository = Depends(get_test_folder_repository),
):
    """获取文件夹树（含每个文件夹的用例计数）"""
    folders = repo.get_all_tree()

    # 计算未分类用例数
    db = repo.db
    uncat = db.fetch_one(
        "SELECT COUNT(*) as count FROM test_cases WHERE folder_id IS NULL"
    )
    uncategorized_count = uncat['count'] if uncat else 0

    return {
        "folders": folders,
        "uncategorized_count": uncategorized_count,
    }


@router.post("/folders")
async def create_folder(
    request: CreateFolderRequest,
    repo: TestFolderRepository = Depends(get_test_folder_repository),
):
    """创建文件夹"""
    # 层级限制检查
    if request.parent_id:
        parent = repo.get_by_id(request.parent_id)
        if not parent:
            raise HTTPException(status_code=404, detail="父文件夹不存在")
        depth = repo.get_depth(request.parent_id)
        if depth >= MAX_DEPTH:
            raise HTTPException(
                status_code=400,
                detail=f"最多支持 {MAX_DEPTH} 层嵌套，当前父文件夹已在第 {depth} 层"
            )

    folder_id = str(uuid.uuid4())[:12]
    folder = TestFolder(
        folder_id=folder_id,
        name=request.name,
        parent_id=request.parent_id,
        description=request.description or "",
    )
    repo.create(folder)

    return {"success": True, "folder_id": folder_id, "message": "文件夹创建成功"}


@router.put("/folders/{folder_id}")
async def update_folder(
    folder_id: str,
    request: UpdateFolderRequest,
    repo: TestFolderRepository = Depends(get_test_folder_repository),
):
    """更新文件夹（重命名、移动父级、排序）"""
    existing = repo.get_by_id(folder_id)
    if not existing:
        raise HTTPException(status_code=404, detail="文件夹不存在")

    updates: dict[str, Any] = {}
    if request.name is not None:
        updates['name'] = request.name
    if request.sort_order is not None:
        updates['sort_order'] = request.sort_order
    if request.description is not None:
        updates['description'] = request.description

    # 移动父级需检查层级
    if request.parent_id is not None and request.parent_id != existing.parent_id:
        if request.parent_id:
            # 不能移到自己或自己的子孙下
            descendants = repo._get_descendant_ids(folder_id)
            if request.parent_id == folder_id or request.parent_id in descendants:
                raise HTTPException(status_code=400, detail="不能将文件夹移动到自身或其子文件夹下")
            parent_depth = repo.get_depth(request.parent_id)
            if parent_depth >= MAX_DEPTH:
                raise HTTPException(status_code=400, detail=f"目标位置超过最大嵌套层级 {MAX_DEPTH}")
        updates['parent_id'] = request.parent_id if request.parent_id else None

    if updates:
        repo.update(folder_id, updates)

    return {"success": True, "message": "文件夹更新成功"}


@router.delete("/folders/{folder_id}")
async def delete_folder(
    folder_id: str,
    repo: TestFolderRepository = Depends(get_test_folder_repository),
):
    """删除文件夹（其下用例自动归入未分类）"""
    existing = repo.get_by_id(folder_id)
    if not existing:
        raise HTTPException(status_code=404, detail="文件夹不存在")

    repo.delete(folder_id)
    return {"success": True, "message": "文件夹已删除，用例已移至未分类"}


# ==================== 智能分组 ====================

def _extract_path_segments(url: str) -> list[str]:
    """从 URL 路径提取所有有意义的路径段列表，用于创建层级文件夹

    规则：
    1. 去除查询参数和尾部斜杠
    2. 过滤参数占位符 /{id} /{user_id} 等和纯数字段
    3. 保留所有路径段（包括 api、版本号等），反映真实 URL 层级
    4. 去掉最后一段（通常是资源名/操作名），其余段作为文件夹层级

    示例:
      /api/v1/dx/online_shop/product → ["api", "v1", "dx", "online_shop"]
      /api/v2/users/{id}/orders      → ["api", "v2", "users", "orders"]
      /api/v1/health                 → ["api", "v1"]
      /users                         → ["users"]
    """
    path = url.split("?")[0].rstrip("/")
    segments = [
        seg for seg in path.lstrip("/").split("/")
        if seg and not re.match(r'^\{.*\}$', seg) and not re.match(r'^\d+$', seg)
    ]
    # 去掉最后一段（资源名/操作名），其余段作为文件夹层级
    return segments[:-1] if len(segments) > 1 else segments


def _ensure_folder_chain(
    segments: list[str],
    existing_map: dict[tuple[str, str | None], str],
    repo: TestFolderRepository,
) -> str | None:
    """确保路径段对应的文件夹链存在，返回叶子文件夹 ID

    按路径段逐级创建或复用嵌套文件夹。
    existing_map 以 (name, parent_id) 为 key，folder_id 为 value，用于去重。

    返回最深层文件夹的 folder_id，如果 segments 为空返回 None。
    """
    if not segments:
        return None

    parent_id: str | None = None
    for segment in segments:
        key = (segment, parent_id)
        if key in existing_map:
            parent_id = existing_map[key]
        else:
            folder_id = str(uuid.uuid4())[:12]
            folder = TestFolder(
                folder_id=folder_id,
                name=segment,
                parent_id=parent_id,
            )
            repo.create(folder)
            existing_map[key] = folder_id
            parent_id = folder_id
    return parent_id


@router.post("/folders/auto-organize")
async def auto_organize(
    preview: bool = True,
    repo: TestFolderRepository = Depends(get_test_folder_repository),
    db: DatabaseManager = Depends(get_database),
):
    """智能分组：按 URL 路径层级自动创建嵌套文件夹并归类未分类用例

    按 URL 完整路径段逐级创建嵌套子文件夹，使文件夹结构反映真实 API 路径层级。
    例如 /api/v1/dx/online_shop/product → api > v1 > dx > online_shop

    参数:
        preview: True 仅预览不执行，False 执行分组
    """
    # 获取所有未分类用例
    rows = db.fetch_all(
        "SELECT case_id, url FROM test_cases WHERE folder_id IS NULL"
    )
    if not rows:
        return {
            "success": True,
            "preview": True,
            "total_cases": 0,
            "total_groups": 0,
            "message": "没有未分类的用例",
            "groups": [],
        }

    # 按 URL 路径层级分组
    groups: dict[str, list[str]] = defaultdict(list)
    path_segments_map: dict[str, list[str]] = {}
    for row in rows:
        segments = _extract_path_segments(row['url'])
        path_key = "/".join(segments) if segments else "other"
        groups[path_key].append(row['case_id'])
        if path_key not in path_segments_map:
            path_segments_map[path_key] = segments

    # 构建预览结果
    preview_data = [
        {
            "path": path_key,
            "folder_names": path_segments_map.get(path_key, []),
            "case_count": len(case_ids),
        }
        for path_key, case_ids in sorted(groups.items(), key=lambda x: -len(x[1]))
    ]

    if preview:
        return {
            "success": True,
            "preview": True,
            "total_cases": len(rows),
            "total_groups": len(groups),
            "groups": preview_data,
        }

    # 构建已有文件夹的 (name, parent_id) → folder_id 映射，用于复用
    existing_map: dict[tuple[str, str | None], str] = {}
    all_folders = repo.get_all_tree()
    for f in all_folders:
        key = (f['name'], f.get('parent_id'))
        existing_map[key] = f['folder_id']

    created_folders_before = len(existing_map)
    moved_cases = 0

    for path_key, case_ids in groups.items():
        segments = path_segments_map.get(path_key, [])
        target_folder_id = _ensure_folder_chain(segments, existing_map, repo)

        # 批量更新用例 folder_id
        for case_id in case_ids:
            db.execute(
                "UPDATE test_cases SET folder_id = %s WHERE case_id = %s",
                (target_folder_id, case_id)
            )
            moved_cases += 1

    created_folders = len(existing_map) - created_folders_before

    return {
        "success": True,
        "preview": False,
        "created_folders": created_folders,
        "moved_cases": moved_cases,
        "groups": preview_data,
    }


# ==================== 用例移动 ====================

@router.put("/tests/move")
async def move_cases(
    request: MoveCasesRequest,
    repo: TestFolderRepository = Depends(get_test_folder_repository),
    db: DatabaseManager = Depends(get_database),
):
    """批量移动用例到指定文件夹"""
    # 如果指定了目标文件夹，验证其存在
    if request.folder_id:
        folder = repo.get_by_id(request.folder_id)
        if not folder:
            raise HTTPException(status_code=404, detail="目标文件夹不存在")

    moved = 0
    for case_id in request.case_ids:
        result = db.execute(
            "UPDATE test_cases SET folder_id = %s WHERE case_id = %s",
            (request.folder_id, case_id)
        )
        moved += result

    return {
        "success": True,
        "moved": moved,
        "message": f"已移动 {moved} 个用例"
    }
