"""
接口文档导入 API
支持增量更新：更新已有接口、新增缺失接口
"""

import json
from typing import Any, Literal
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field

from ...database import get_db_manager
from ...importer import DocImporter, ImportResult, UpdateStrategy, EndpointDiff

router = APIRouter()


class ImportRequest(BaseModel):
    """导入请求（JSON数据）"""
    data: dict[str, Any] = Field(..., description="接口文档JSON数据")
    doc_type: Literal["swagger", "postman", "auto"] = Field(
        default="auto",
        description="文档类型"
    )
    source_name: str = Field(default="import.json", description="来源名称")
    save_to_db: bool = Field(default=True, description="是否保存到数据库")
    update_strategy: Literal["merge", "replace", "skip"] = Field(
        default="merge",
        description="更新策略: merge=合并更新, replace=完全替换, skip=跳过已有"
    )


class ImportResponse(BaseModel):
    """导入响应"""
    success: bool
    message: str
    endpoint_count: int
    tag_count: int
    endpoints: list[dict[str, Any]] = []
    tags: list[str] = []
    errors: list[str] = []
    # 增量更新统计
    created_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    deleted_count: int = 0


class PreviewResponse(BaseModel):
    """预览响应"""
    doc_type: str
    endpoint_count: int
    tag_count: int
    endpoints: list[dict[str, Any]]
    tags: list[str]


class DiffItem(BaseModel):
    """差异项"""
    endpoint_id: str
    method: str
    path: str
    name: str
    status: Literal["new", "updated", "unchanged", "deleted"]
    changes: list[str] = []


class DiffResponse(BaseModel):
    """差异对比响应"""
    total_new: int
    total_updated: int
    total_unchanged: int
    total_deleted: int
    diffs: list[DiffItem]


@router.post("/file", response_model=ImportResponse)
async def import_file(
    file: UploadFile = File(..., description="接口文档文件"),
    doc_type: Literal["swagger", "postman", "auto"] = Form(default="auto"),
    save_to_db: bool = Form(default=True),
    update_strategy: Literal["merge", "replace", "skip"] = Form(default="merge")
):
    """
    上传并导入接口文档文件
    
    支持 Swagger/OpenAPI 和 Postman Collection 格式
    支持增量更新：
    - merge: 合并更新（更新已有接口，新增缺失接口）
    - replace: 完全替换（删除旧数据，导入新数据）
    - skip: 跳过已有（仅新增缺失接口）
    """
    # 检查文件类型
    if not file.filename or not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="只支持 JSON 文件")
    
    # 读取文件内容
    try:
        content = await file.read()
        data = json.loads(content.decode('utf-8'))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"JSON 解析失败: {e}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件读取失败: {e}")
    
    # 导入
    importer = DocImporter()
    result = importer.import_json(data, doc_type, file.filename)
    
    if not result.success:
        return ImportResponse(
            success=False,
            message=result.message,
            endpoint_count=0,
            tag_count=0,
            errors=result.errors
        )
    
    # 保存到数据库（支持增量更新）
    created_count = 0
    updated_count = 0
    skipped_count = 0
    deleted_count = 0
    
    if save_to_db:
        strategy = UpdateStrategy(update_strategy)
        counts = _save_import_result_with_strategy(result, file.filename, strategy)
        created_count, updated_count, skipped_count, deleted_count = counts
    
    return ImportResponse(
        success=True,
        message=f"成功导入 {result.endpoint_count} 个接口，新增 {created_count}，更新 {updated_count}，跳过 {skipped_count}，删除 {deleted_count}",
        endpoint_count=result.endpoint_count,
        tag_count=result.tag_count,
        endpoints=[_endpoint_to_dict(e) for e in result.endpoints],
        tags=result.tags,
        created_count=created_count,
        updated_count=updated_count,
        skipped_count=skipped_count,
        deleted_count=deleted_count
    )


@router.post("/json", response_model=ImportResponse)
async def import_json(request: ImportRequest):
    """
    导入 JSON 数据
    
    支持 Swagger/OpenAPI 和 Postman Collection 格式
    支持增量更新
    """
    importer = DocImporter()
    result = importer.import_json(request.data, request.doc_type, request.source_name)
    
    if not result.success:
        return ImportResponse(
            success=False,
            message=result.message,
            endpoint_count=0,
            tag_count=0,
            errors=result.errors
        )
    
    # 保存到数据库（支持增量更新）
    created_count = 0
    updated_count = 0
    skipped_count = 0
    deleted_count = 0
    
    if request.save_to_db:
        strategy = UpdateStrategy(request.update_strategy)
        counts = _save_import_result_with_strategy(result, request.source_name, strategy)
        created_count, updated_count, skipped_count, deleted_count = counts
    
    return ImportResponse(
        success=True,
        message=f"成功导入 {result.endpoint_count} 个接口，新增 {created_count}，更新 {updated_count}，跳过 {skipped_count}，删除 {deleted_count}",
        endpoint_count=result.endpoint_count,
        tag_count=result.tag_count,
        endpoints=[_endpoint_to_dict(e) for e in result.endpoints],
        tags=result.tags,
        created_count=created_count,
        updated_count=updated_count,
        skipped_count=skipped_count,
        deleted_count=deleted_count
    )


@router.post("/preview", response_model=PreviewResponse)
async def preview_import(
    file: UploadFile = File(..., description="接口文档文件"),
    doc_type: Literal["swagger", "postman", "auto"] = Form(default="auto")
):
    """
    预览导入结果（不保存到数据库）
    """
    # 检查文件类型
    if not file.filename or not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="只支持 JSON 文件")
    
    # 读取文件内容
    try:
        content = await file.read()
        data = json.loads(content.decode('utf-8'))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"JSON 解析失败: {e}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件读取失败: {e}")
    
    # 检测文档类型
    importer = DocImporter()
    detected_type = importer._detect_doc_type(data)
    
    if detected_type == "auto":
        raise HTTPException(status_code=400, detail="无法识别文档类型")
    
    # 解析
    result = importer.import_json(data, doc_type, file.filename or "preview.json")
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    
    return PreviewResponse(
        doc_type=detected_type,
        endpoint_count=result.endpoint_count,
        tag_count=result.tag_count,
        endpoints=[_endpoint_to_dict(e) for e in result.endpoints[:50]],  # 限制预览数量
        tags=result.tags
    )


@router.post("/diff", response_model=DiffResponse)
async def diff_import(
    file: UploadFile = File(..., description="接口文档文件"),
    doc_type: Literal["swagger", "postman", "auto"] = Form(default="auto")
):
    """
    对比导入文件与现有数据的差异
    
    返回新增、更新、未变更、已删除的接口列表
    """
    # 检查文件类型
    if not file.filename or not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="只支持 JSON 文件")
    
    # 读取文件内容
    try:
        content = await file.read()
        data = json.loads(content.decode('utf-8'))
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"JSON 解析失败: {e}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件读取失败: {e}")
    
    # 解析新文档
    importer = DocImporter()
    result = importer.import_json(data, doc_type, file.filename or "diff.json")
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    
    # 获取现有接口
    existing_endpoints = _get_existing_endpoints()
    
    # 对比差异
    diffs = importer.compare_endpoints(result.endpoints, existing_endpoints)
    
    # 统计
    total_new = sum(1 for d in diffs if d.status == "new")
    total_updated = sum(1 for d in diffs if d.status == "updated")
    total_unchanged = sum(1 for d in diffs if d.status == "unchanged")
    total_deleted = sum(1 for d in diffs if d.status == "deleted")
    
    return DiffResponse(
        total_new=total_new,
        total_updated=total_updated,
        total_unchanged=total_unchanged,
        total_deleted=total_deleted,
        diffs=[
            DiffItem(
                endpoint_id=d.endpoint_id,
                method=d.method,
                path=d.path,
                name=d.name,
                status=d.status,
                changes=d.changes
            )
            for d in diffs
        ]
    )


@router.get("/supported-formats")
async def get_supported_formats():
    """获取支持的文档格式"""
    return {
        "formats": [
            {
                "name": "Swagger/OpenAPI",
                "type": "swagger",
                "versions": ["2.0", "3.0", "3.1"],
                "description": "OpenAPI 规范（原 Swagger）"
            },
            {
                "name": "Postman Collection",
                "type": "postman",
                "versions": ["2.0", "2.1"],
                "description": "Postman 导出的 Collection 文件"
            }
        ],
        "update_strategies": [
            {
                "name": "merge",
                "description": "合并更新：更新已有接口，新增缺失接口，保留其他接口"
            },
            {
                "name": "replace",
                "description": "完全替换：删除不在新文档中的接口"
            },
            {
                "name": "skip",
                "description": "跳过已有：仅新增缺失接口，不更新已有接口"
            }
        ]
    }


def _get_existing_endpoints() -> list:
    """获取数据库中的现有接口"""
    from ...database.models import ApiEndpoint, EndpointSourceType
    
    db = get_db_manager()
    rows = db.fetch_all("SELECT * FROM api_endpoints")
    
    endpoints = []
    for row in rows:
        ep = ApiEndpoint(
            endpoint_id=row['endpoint_id'],
            name=row['name'],
            method=row['method'],
            path=row['path'],
            description=row.get('description'),
            summary=row.get('summary'),
            parameters=json.loads(row['parameters']) if row.get('parameters') else None,
            request_body=json.loads(row['request_body']) if row.get('request_body') else None,
            responses=json.loads(row['responses']) if row.get('responses') else None,
            tags=[],  # 标签单独查询
            source_type=EndpointSourceType(row.get('source_type', 'manual')),
            is_deprecated=row.get('is_deprecated', False)
        )
        ep.id = row.get('id')
        endpoints.append(ep)
    
    return endpoints


def _save_import_result_with_strategy(
    result: ImportResult,
    source_file: str,
    strategy: UpdateStrategy
) -> tuple[int, int, int, int]:
    """
    使用指定策略保存导入结果
    
    Returns:
        (created_count, updated_count, skipped_count, deleted_count)
    """
    db = get_db_manager()
    importer = DocImporter()
    
    created_count = 0
    updated_count = 0
    skipped_count = 0
    deleted_count = 0
    
    # 保存标签
    for tag_name in result.tags:
        # 截断标签名，api_tags.name 是 VARCHAR(50)
        tag_name_truncated = (tag_name or "")[:50]
        existing = db.fetch_one("SELECT id FROM api_tags WHERE name = %s", (tag_name_truncated,))
        if not existing:
            db.execute(
                "INSERT INTO api_tags (name, description) VALUES (%s, %s)",
                (tag_name_truncated, f"从 {source_file} 导入"[:255])
            )
    
    # 获取现有接口
    existing_endpoints = _get_existing_endpoints()
    
    # 应用导入策略
    to_create, to_update, to_delete_ids = importer.apply_import(
        result.endpoints, existing_endpoints, strategy
    )
    
    # 创建新接口
    for endpoint in to_create:
        _create_endpoint(db, endpoint, source_file)
        created_count += 1
    
    # 更新已有接口
    for endpoint in to_update:
        _update_endpoint(db, endpoint, source_file)
        updated_count += 1
    
    # 删除接口（仅 replace 策略）
    for endpoint_id in to_delete_ids:
        db.execute("DELETE FROM api_endpoint_tags WHERE endpoint_id = %s", (endpoint_id,))
        db.execute("DELETE FROM api_endpoints WHERE endpoint_id = %s", (endpoint_id,))
        deleted_count += 1
    
    # 计算跳过数量
    total_existing_keys = {f"{e.method.upper()}:{e.path}" for e in existing_endpoints}
    for endpoint in result.endpoints:
        key = f"{endpoint.method.upper()}:{endpoint.path}"
        if key in total_existing_keys:
            if strategy == UpdateStrategy.SKIP:
                skipped_count += 1
            elif endpoint not in to_update:
                skipped_count += 1  # 未变更的接口
    
    return created_count, updated_count, skipped_count, deleted_count


def _create_endpoint(db, endpoint, source_file: str) -> None:
    """创建新接口"""
    sql = """
        INSERT INTO api_endpoints 
        (endpoint_id, name, description, method, path, summary,
         parameters, request_body, responses, source_type, source_file, is_deprecated)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    # 截断过长字段，防止数据库报错
    # TEXT 类型在 utf8mb4 下最大约 16000 字符安全值
    name = (endpoint.name or "")[:255]
    summary = (endpoint.summary or "")[:500]
    description = (endpoint.description or "")[:16000]
    
    db.execute(sql, (
        endpoint.endpoint_id,
        name,
        description,
        endpoint.method,
        endpoint.path,
        summary,
        json.dumps(endpoint.parameters, ensure_ascii=False) if endpoint.parameters else None,
        json.dumps(endpoint.request_body, ensure_ascii=False) if endpoint.request_body else None,
        json.dumps(endpoint.responses, ensure_ascii=False) if endpoint.responses else None,
        endpoint.source_type.value,
        source_file,
        endpoint.is_deprecated
    ))
    
    # 保存标签关联
    _save_endpoint_tags(db, endpoint.endpoint_id, endpoint.tags)


def _update_endpoint(db, endpoint, source_file: str) -> None:
    """更新已有接口"""
    sql = """
        UPDATE api_endpoints SET
            name = %s, description = %s, summary = %s,
            parameters = %s, request_body = %s, responses = %s,
            source_type = %s, source_file = %s, is_deprecated = %s,
            updated_at = datetime('now')
        WHERE endpoint_id = %s
    """
    # 截断过长字段
    name = (endpoint.name or "")[:255]
    summary = (endpoint.summary or "")[:500]
    description = (endpoint.description or "")[:16000]
    
    db.execute(sql, (
        name,
        description,
        summary,
        json.dumps(endpoint.parameters, ensure_ascii=False) if endpoint.parameters else None,
        json.dumps(endpoint.request_body, ensure_ascii=False) if endpoint.request_body else None,
        json.dumps(endpoint.responses, ensure_ascii=False) if endpoint.responses else None,
        endpoint.source_type.value,
        source_file,
        endpoint.is_deprecated,
        endpoint.endpoint_id
    ))
    
    # 更新标签关联
    db.execute("DELETE FROM api_endpoint_tags WHERE endpoint_id = %s", (endpoint.endpoint_id,))
    _save_endpoint_tags(db, endpoint.endpoint_id, endpoint.tags)


def _save_endpoint_tags(db, endpoint_id: str, tags: list[str]) -> None:
    """保存接口标签关联"""
    for tag_name in tags:
        tag = db.fetch_one("SELECT id FROM api_tags WHERE name = %s", (tag_name,))
        if tag:
            db.execute(
                "INSERT OR IGNORE INTO api_endpoint_tags (endpoint_id, tag_id) VALUES (%s, %s)",
                (endpoint_id, tag['id'])
            )


def _endpoint_to_dict(endpoint: Any) -> dict[str, Any]:
    """转换端点为字典"""
    return {
        "endpoint_id": endpoint.endpoint_id,
        "name": endpoint.name,
        "method": endpoint.method,
        "path": endpoint.path,
        "summary": endpoint.summary,
        "description": endpoint.description,
        "tags": endpoint.tags,
        "source_type": endpoint.source_type.value,
        "is_deprecated": endpoint.is_deprecated
    }
