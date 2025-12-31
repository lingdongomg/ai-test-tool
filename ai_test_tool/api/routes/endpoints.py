"""
接口端点管理 API
"""

from typing import Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ...database import get_db_manager
from ...database.models import ApiEndpoint, EndpointSourceType

router = APIRouter()


class EndpointCreate(BaseModel):
    """创建接口请求"""
    name: str = Field(..., min_length=1, max_length=255)
    method: str = Field(..., pattern="^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)$")
    path: str = Field(..., min_length=1, max_length=512)
    description: str = Field(default="")
    summary: str = Field(default="", max_length=500)
    parameters: list[dict[str, Any]] = Field(default_factory=list)
    request_body: dict[str, Any] = Field(default_factory=dict)
    responses: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class EndpointUpdate(BaseModel):
    """更新接口请求"""
    name: str | None = None
    description: str | None = None
    summary: str | None = None
    parameters: list[dict[str, Any]] | None = None
    request_body: dict[str, Any] | None = None
    responses: dict[str, Any] | None = None
    is_deprecated: bool | None = None
    tags: list[str] | None = None


class EndpointResponse(BaseModel):
    """接口响应"""
    id: int
    endpoint_id: str
    name: str
    description: str | None = None
    method: str
    path: str
    summary: str | None = None
    parameters: list[dict[str, Any]] | None = None
    request_body: dict[str, Any] | None = None
    responses: dict[str, Any] | None = None
    source_type: str
    source_file: str | None = None
    is_deprecated: bool
    tags: list[str] = []
    
    class Config:
        from_attributes = True


class EndpointListResponse(BaseModel):
    """接口列表响应"""
    total: int
    items: list[EndpointResponse]


@router.get("", response_model=EndpointListResponse)
async def list_endpoints(
    method: str | None = None,
    tag: str | None = None,
    search: str | None = None,
    source_type: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100)
):
    """获取接口列表"""
    db = get_db_manager()
    
    # 构建查询条件
    conditions = []
    params: list[Any] = []
    
    if method:
        conditions.append("e.method = %s")
        params.append(method.upper())
    
    if source_type:
        conditions.append("e.source_type = %s")
        params.append(source_type)
    
    if search:
        conditions.append("(e.name LIKE %s OR e.path LIKE %s OR e.description LIKE %s)")
        search_pattern = f"%{search}%"
        params.extend([search_pattern, search_pattern, search_pattern])
    
    if tag:
        conditions.append("""
            EXISTS (
                SELECT 1 FROM api_endpoint_tags et
                JOIN api_tags t ON et.tag_id = t.id
                WHERE et.endpoint_id = e.endpoint_id AND t.name = %s
            )
        """)
        params.append(tag)
    
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    
    # 获取总数
    count_sql = f"SELECT COUNT(*) as count FROM api_endpoints e {where_clause}"
    count_result = db.fetch_one(count_sql, tuple(params) if params else None)
    total = count_result['count'] if count_result else 0
    
    # 获取分页数据
    offset = (page - 1) * page_size
    sql = f"""
        SELECT e.* FROM api_endpoints e
        {where_clause}
        ORDER BY e.path, e.method
        LIMIT %s OFFSET %s
    """
    params.extend([page_size, offset])
    rows = db.fetch_all(sql, tuple(params))
    
    # 获取每个端点的标签
    items = []
    for row in rows:
        endpoint = _row_to_endpoint_response(row)
        endpoint.tags = _get_endpoint_tags(db, row['endpoint_id'])
        items.append(endpoint)
    
    return EndpointListResponse(total=total, items=items)


@router.get("/{endpoint_id}", response_model=EndpointResponse)
async def get_endpoint(endpoint_id: str):
    """获取单个接口"""
    db = get_db_manager()
    sql = "SELECT * FROM api_endpoints WHERE endpoint_id = %s"
    row = db.fetch_one(sql, (endpoint_id,))
    
    if not row:
        raise HTTPException(status_code=404, detail="接口不存在")
    
    endpoint = _row_to_endpoint_response(row)
    endpoint.tags = _get_endpoint_tags(db, endpoint_id)
    return endpoint


@router.post("", response_model=EndpointResponse)
async def create_endpoint(endpoint: EndpointCreate):
    """创建接口"""
    import hashlib
    
    db = get_db_manager()
    
    # 生成 endpoint_id
    content = f"{endpoint.method}:{endpoint.path}"
    endpoint_id = hashlib.md5(content.encode()).hexdigest()[:16]
    
    # 检查是否已存在
    existing = db.fetch_one(
        "SELECT endpoint_id FROM api_endpoints WHERE endpoint_id = %s",
        (endpoint_id,)
    )
    if existing:
        raise HTTPException(status_code=400, detail="接口已存在")
    
    # 创建接口
    import json
    sql = """
        INSERT INTO api_endpoints 
        (endpoint_id, name, description, method, path, summary, parameters, 
         request_body, responses, source_type, source_file)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    db.execute(sql, (
        endpoint_id,
        endpoint.name,
        endpoint.description,
        endpoint.method.upper(),
        endpoint.path,
        endpoint.summary,
        json.dumps(endpoint.parameters, ensure_ascii=False),
        json.dumps(endpoint.request_body, ensure_ascii=False),
        json.dumps(endpoint.responses, ensure_ascii=False),
        EndpointSourceType.MANUAL.value,
        ""
    ))
    
    # 添加标签
    if endpoint.tags:
        _update_endpoint_tags(db, endpoint_id, endpoint.tags)
    
    # 返回创建的接口
    row = db.fetch_one("SELECT * FROM api_endpoints WHERE endpoint_id = %s", (endpoint_id,))
    result = _row_to_endpoint_response(row)
    result.tags = endpoint.tags
    return result


@router.put("/{endpoint_id}", response_model=EndpointResponse)
async def update_endpoint(endpoint_id: str, endpoint: EndpointUpdate):
    """更新接口"""
    import json
    
    db = get_db_manager()
    
    # 检查是否存在
    existing = db.fetch_one(
        "SELECT * FROM api_endpoints WHERE endpoint_id = %s",
        (endpoint_id,)
    )
    if not existing:
        raise HTTPException(status_code=404, detail="接口不存在")
    
    # 构建更新语句
    updates = []
    params: list[Any] = []
    
    if endpoint.name is not None:
        updates.append("name = %s")
        params.append(endpoint.name)
    
    if endpoint.description is not None:
        updates.append("description = %s")
        params.append(endpoint.description)
    
    if endpoint.summary is not None:
        updates.append("summary = %s")
        params.append(endpoint.summary)
    
    if endpoint.parameters is not None:
        updates.append("parameters = %s")
        params.append(json.dumps(endpoint.parameters, ensure_ascii=False))
    
    if endpoint.request_body is not None:
        updates.append("request_body = %s")
        params.append(json.dumps(endpoint.request_body, ensure_ascii=False))
    
    if endpoint.responses is not None:
        updates.append("responses = %s")
        params.append(json.dumps(endpoint.responses, ensure_ascii=False))
    
    if endpoint.is_deprecated is not None:
        updates.append("is_deprecated = %s")
        params.append(endpoint.is_deprecated)
    
    if updates:
        sql = f"UPDATE api_endpoints SET {', '.join(updates)} WHERE endpoint_id = %s"
        params.append(endpoint_id)
        db.execute(sql, tuple(params))
    
    # 更新标签
    if endpoint.tags is not None:
        _update_endpoint_tags(db, endpoint_id, endpoint.tags)
    
    # 返回更新后的接口
    row = db.fetch_one("SELECT * FROM api_endpoints WHERE endpoint_id = %s", (endpoint_id,))
    result = _row_to_endpoint_response(row)
    result.tags = _get_endpoint_tags(db, endpoint_id)
    return result


@router.delete("/{endpoint_id}")
async def delete_endpoint(endpoint_id: str):
    """删除接口"""
    db = get_db_manager()
    
    # 检查是否存在
    existing = db.fetch_one(
        "SELECT endpoint_id FROM api_endpoints WHERE endpoint_id = %s",
        (endpoint_id,)
    )
    if not existing:
        raise HTTPException(status_code=404, detail="接口不存在")
    
    # 删除关联的标签
    db.execute("DELETE FROM api_endpoint_tags WHERE endpoint_id = %s", (endpoint_id,))
    
    # 删除接口
    db.execute("DELETE FROM api_endpoints WHERE endpoint_id = %s", (endpoint_id,))
    
    return {"message": "删除成功"}


@router.post("/{endpoint_id}/tags")
async def add_endpoint_tags(endpoint_id: str, tags: list[str]):
    """为接口添加标签"""
    db = get_db_manager()
    
    # 检查接口是否存在
    existing = db.fetch_one(
        "SELECT endpoint_id FROM api_endpoints WHERE endpoint_id = %s",
        (endpoint_id,)
    )
    if not existing:
        raise HTTPException(status_code=404, detail="接口不存在")
    
    # 获取现有标签
    current_tags = _get_endpoint_tags(db, endpoint_id)
    new_tags = list(set(current_tags + tags))
    
    # 更新标签
    _update_endpoint_tags(db, endpoint_id, new_tags)
    
    return {"tags": new_tags}


@router.delete("/{endpoint_id}/tags/{tag_name}")
async def remove_endpoint_tag(endpoint_id: str, tag_name: str):
    """移除接口标签"""
    db = get_db_manager()
    
    # 获取标签ID
    tag = db.fetch_one("SELECT id FROM api_tags WHERE name = %s", (tag_name,))
    if not tag:
        raise HTTPException(status_code=404, detail="标签不存在")
    
    # 删除关联
    db.execute(
        "DELETE FROM api_endpoint_tags WHERE endpoint_id = %s AND tag_id = %s",
        (endpoint_id, tag['id'])
    )
    
    return {"message": "移除成功"}


def _row_to_endpoint_response(row: dict[str, Any]) -> EndpointResponse:
    """转换数据库行为响应对象"""
    import json
    
    parameters = row.get('parameters', '[]')
    if isinstance(parameters, str):
        parameters = json.loads(parameters) if parameters else []
    
    request_body = row.get('request_body', '{}')
    if isinstance(request_body, str):
        request_body = json.loads(request_body) if request_body else {}
    
    responses = row.get('responses', '{}')
    if isinstance(responses, str):
        responses = json.loads(responses) if responses else {}
    
    return EndpointResponse(
        id=row['id'],
        endpoint_id=row['endpoint_id'],
        name=row['name'],
        description=row.get('description', ''),
        method=row['method'],
        path=row['path'],
        summary=row.get('summary', ''),
        parameters=parameters,
        request_body=request_body,
        responses=responses,
        source_type=row.get('source_type', 'manual'),
        source_file=row.get('source_file', ''),
        is_deprecated=bool(row.get('is_deprecated', False)),
        tags=[]
    )


def _get_endpoint_tags(db: Any, endpoint_id: str) -> list[str]:
    """获取接口的标签"""
    sql = """
        SELECT t.name FROM api_tags t
        JOIN api_endpoint_tags et ON t.id = et.tag_id
        WHERE et.endpoint_id = %s
        ORDER BY t.name
    """
    rows = db.fetch_all(sql, (endpoint_id,))
    return [row['name'] for row in rows]


def _update_endpoint_tags(db: Any, endpoint_id: str, tags: list[str]) -> None:
    """更新接口的标签"""
    # 删除现有关联
    db.execute("DELETE FROM api_endpoint_tags WHERE endpoint_id = %s", (endpoint_id,))
    
    # 添加新关联
    for tag_name in tags:
        # 获取或创建标签
        tag = db.fetch_one("SELECT id FROM api_tags WHERE name = %s", (tag_name,))
        if not tag:
            # 创建标签
            db.execute(
                "INSERT INTO api_tags (name, description) VALUES (%s, %s)",
                (tag_name, f"从接口导入的标签: {tag_name}")
            )
            tag = db.fetch_one("SELECT id FROM api_tags WHERE name = %s", (tag_name,))
        
        # 添加关联
        db.execute(
            "INSERT IGNORE INTO api_endpoint_tags (endpoint_id, tag_id) VALUES (%s, %s)",
            (endpoint_id, tag['id'])
        )
