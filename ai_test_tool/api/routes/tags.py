"""
标签管理 API
"""

from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ...database import get_db_manager
from ...database.models import ApiTag

router = APIRouter()


class TagCreate(BaseModel):
    """创建标签请求"""
    name: str = Field(..., min_length=1, max_length=50, description="标签名称")
    description: str = Field(default="", max_length=255, description="标签描述")
    color: str = Field(default="#1890ff", description="显示颜色")
    parent_id: int | None = Field(default=None, description="父标签ID")
    sort_order: int = Field(default=0, description="排序")


class TagUpdate(BaseModel):
    """更新标签请求"""
    name: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = Field(default=None, max_length=255)
    color: str | None = None
    parent_id: int | None = None
    sort_order: int | None = None


class TagResponse(BaseModel):
    """标签响应"""
    id: int
    name: str
    description: str
    color: str
    parent_id: int | None
    sort_order: int
    is_system: bool
    children: list["TagResponse"] = []
    
    class Config:
        from_attributes = True


@router.get("", response_model=list[TagResponse])
async def list_tags(
    parent_id: int | None = None,
    include_children: bool = False
):
    """获取标签列表"""
    db = get_db_manager()
    
    if parent_id is not None:
        sql = "SELECT * FROM api_tags WHERE parent_id = %s ORDER BY sort_order, name"
        rows = db.fetch_all(sql, (parent_id,))
    else:
        sql = "SELECT * FROM api_tags WHERE parent_id IS NULL ORDER BY sort_order, name"
        rows = db.fetch_all(sql)
    
    tags = [_row_to_tag_response(row) for row in rows]
    
    if include_children:
        for tag in tags:
            tag.children = await _get_children(db, tag.id)
    
    return tags


@router.get("/{tag_id}", response_model=TagResponse)
async def get_tag(tag_id: int):
    """获取单个标签"""
    db = get_db_manager()
    sql = "SELECT * FROM api_tags WHERE id = %s"
    row = db.fetch_one(sql, (tag_id,))
    
    if not row:
        raise HTTPException(status_code=404, detail="标签不存在")
    
    return _row_to_tag_response(row)


@router.post("", response_model=TagResponse)
async def create_tag(tag: TagCreate):
    """创建标签"""
    db = get_db_manager()
    
    # 检查名称是否已存在
    check_sql = "SELECT id FROM api_tags WHERE name = %s"
    existing = db.fetch_one(check_sql, (tag.name,))
    if existing:
        raise HTTPException(status_code=400, detail="标签名称已存在")
    
    # 检查父标签是否存在
    if tag.parent_id:
        parent_sql = "SELECT id FROM api_tags WHERE id = %s"
        parent = db.fetch_one(parent_sql, (tag.parent_id,))
        if not parent:
            raise HTTPException(status_code=400, detail="父标签不存在")
    
    sql = """
        INSERT INTO api_tags (name, description, color, parent_id, sort_order)
        VALUES (%s, %s, %s, %s, %s)
    """
    db.execute(sql, (tag.name, tag.description, tag.color, tag.parent_id, tag.sort_order))
    
    # 获取创建的标签
    new_tag = db.fetch_one("SELECT * FROM api_tags WHERE name = %s", (tag.name,))
    return _row_to_tag_response(new_tag)


@router.put("/{tag_id}", response_model=TagResponse)
async def update_tag(tag_id: int, tag: TagUpdate):
    """更新标签"""
    db = get_db_manager()
    
    # 检查标签是否存在
    existing = db.fetch_one("SELECT * FROM api_tags WHERE id = %s", (tag_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="标签不存在")
    
    # 检查是否是系统标签
    if existing.get('is_system'):
        raise HTTPException(status_code=400, detail="系统标签不可修改")
    
    # 构建更新语句
    updates = []
    params: list[Any] = []
    
    if tag.name is not None:
        # 检查名称是否已被其他标签使用
        check_sql = "SELECT id FROM api_tags WHERE name = %s AND id != %s"
        if db.fetch_one(check_sql, (tag.name, tag_id)):
            raise HTTPException(status_code=400, detail="标签名称已存在")
        updates.append("name = %s")
        params.append(tag.name)
    
    if tag.description is not None:
        updates.append("description = %s")
        params.append(tag.description)
    
    if tag.color is not None:
        updates.append("color = %s")
        params.append(tag.color)
    
    if tag.parent_id is not None:
        # 防止循环引用
        if tag.parent_id == tag_id:
            raise HTTPException(status_code=400, detail="不能将自己设为父标签")
        updates.append("parent_id = %s")
        params.append(tag.parent_id if tag.parent_id != 0 else None)
    
    if tag.sort_order is not None:
        updates.append("sort_order = %s")
        params.append(tag.sort_order)
    
    if updates:
        sql = f"UPDATE api_tags SET {', '.join(updates)} WHERE id = %s"
        params.append(tag_id)
        db.execute(sql, tuple(params))
    
    # 返回更新后的标签
    updated = db.fetch_one("SELECT * FROM api_tags WHERE id = %s", (tag_id,))
    return _row_to_tag_response(updated)


@router.delete("/{tag_id}")
async def delete_tag(tag_id: int):
    """删除标签"""
    db = get_db_manager()
    
    # 检查标签是否存在
    existing = db.fetch_one("SELECT * FROM api_tags WHERE id = %s", (tag_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="标签不存在")
    
    # 检查是否是系统标签
    if existing.get('is_system'):
        raise HTTPException(status_code=400, detail="系统标签不可删除")
    
    # 删除标签（子标签的 parent_id 会自动设为 NULL）
    sql = "DELETE FROM api_tags WHERE id = %s"
    db.execute(sql, (tag_id,))
    
    return {"message": "删除成功"}


@router.get("/tree/all", response_model=list[TagResponse])
async def get_tag_tree():
    """获取标签树"""
    db = get_db_manager()
    
    # 获取所有根标签
    sql = "SELECT * FROM api_tags WHERE parent_id IS NULL ORDER BY sort_order, name"
    rows = db.fetch_all(sql)
    
    tags = []
    for row in rows:
        tag = _row_to_tag_response(row)
        tag.children = await _get_children(db, tag.id)
        tags.append(tag)
    
    return tags


async def _get_children(db: Any, parent_id: int) -> list[TagResponse]:
    """递归获取子标签"""
    sql = "SELECT * FROM api_tags WHERE parent_id = %s ORDER BY sort_order, name"
    rows = db.fetch_all(sql, (parent_id,))
    
    children = []
    for row in rows:
        tag = _row_to_tag_response(row)
        tag.children = await _get_children(db, tag.id)
        children.append(tag)
    
    return children


def _row_to_tag_response(row: dict[str, Any]) -> TagResponse:
    """转换数据库行为响应对象"""
    return TagResponse(
        id=row['id'],
        name=row['name'],
        description=row.get('description', ''),
        color=row.get('color', '#1890ff'),
        parent_id=row.get('parent_id'),
        sort_order=row.get('sort_order', 0),
        is_system=bool(row.get('is_system', False)),
        children=[]
    )
