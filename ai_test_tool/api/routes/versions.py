"""
测试用例版本管理 API
"""

import uuid
from typing import Any, Literal
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ...database import get_db_manager
from ...database.repository import (
    TestCaseRepository,
    TestCaseVersionRepository,
    TestCaseChangeLogRepository
)
from ...database.models import (
    TestCaseRecord,
    TestCaseVersion,
    TestCaseChangeLog,
    ChangeType,
    TestCaseCategory,
    TestCasePriority
)

router = APIRouter()


class VersionResponse(BaseModel):
    """版本响应"""
    version_id: str
    task_id: str
    case_id: str
    version_number: int
    name: str
    method: str
    url: str
    change_type: str
    change_summary: str
    changed_fields: list[str]
    changed_by: str
    created_at: str | None


class VersionListResponse(BaseModel):
    """版本列表响应"""
    total: int
    versions: list[VersionResponse]


class VersionDetailResponse(BaseModel):
    """版本详情响应"""
    version_id: str
    task_id: str
    case_id: str
    version_number: int
    name: str
    description: str
    category: str
    priority: str
    method: str
    url: str
    headers: dict[str, str]
    body: dict[str, Any] | None
    query_params: dict[str, str]
    expected_status_code: int
    expected_response: dict[str, Any]
    max_response_time_ms: int
    tags: list[str]
    group_name: str
    dependencies: list[str]
    change_type: str
    change_summary: str
    changed_fields: list[str]
    changed_by: str
    created_at: str | None


class CompareResponse(BaseModel):
    """版本比较响应"""
    version1: int
    version2: int
    has_changes: bool
    differences: list[dict[str, Any]]


class RestoreRequest(BaseModel):
    """回滚请求"""
    version_number: int = Field(..., description="要回滚到的版本号")
    reason: str = Field(default="", description="回滚原因")


class ChangeLogResponse(BaseModel):
    """变更日志响应"""
    task_id: str
    case_id: str
    version_id: str
    change_type: str
    change_summary: str
    old_value: dict[str, Any]
    new_value: dict[str, Any]
    changed_by: str
    created_at: str | None


@router.get("/{task_id}/cases/{case_id}/versions", response_model=VersionListResponse)
async def list_versions(
    task_id: str,
    case_id: str,
    limit: int = Query(default=50, ge=1, le=200)
):
    """获取测试用例的版本历史"""
    version_repo = TestCaseVersionRepository()
    
    versions = version_repo.get_by_case(task_id, case_id, limit)
    
    return VersionListResponse(
        total=len(versions),
        versions=[
            VersionResponse(
                version_id=v.version_id,
                task_id=v.task_id,
                case_id=v.case_id,
                version_number=v.version_number,
                name=v.name,
                method=v.method,
                url=v.url,
                change_type=v.change_type.value if isinstance(v.change_type, ChangeType) else v.change_type,
                change_summary=v.change_summary,
                changed_fields=v.changed_fields,
                changed_by=v.changed_by,
                created_at=v.created_at.isoformat() if v.created_at else None
            )
            for v in versions
        ]
    )


@router.get("/{task_id}/cases/{case_id}/versions/{version_number}", response_model=VersionDetailResponse)
async def get_version(task_id: str, case_id: str, version_number: int):
    """获取指定版本的详情"""
    version_repo = TestCaseVersionRepository()
    
    version = version_repo.get_version(task_id, case_id, version_number)
    if not version:
        raise HTTPException(status_code=404, detail="版本不存在")
    
    return VersionDetailResponse(
        version_id=version.version_id,
        task_id=version.task_id,
        case_id=version.case_id,
        version_number=version.version_number,
        name=version.name,
        description=version.description,
        category=version.category.value if isinstance(version.category, TestCaseCategory) else version.category,
        priority=version.priority.value if isinstance(version.priority, TestCasePriority) else version.priority,
        method=version.method,
        url=version.url,
        headers=version.headers,
        body=version.body,
        query_params=version.query_params,
        expected_status_code=version.expected_status_code,
        expected_response=version.expected_response,
        max_response_time_ms=version.max_response_time_ms,
        tags=version.tags,
        group_name=version.group_name,
        dependencies=version.dependencies,
        change_type=version.change_type.value if isinstance(version.change_type, ChangeType) else version.change_type,
        change_summary=version.change_summary,
        changed_fields=version.changed_fields,
        changed_by=version.changed_by,
        created_at=version.created_at.isoformat() if version.created_at else None
    )


@router.get("/{task_id}/cases/{case_id}/versions/compare", response_model=CompareResponse)
async def compare_versions(
    task_id: str,
    case_id: str,
    v1: int = Query(..., description="版本1"),
    v2: int = Query(..., description="版本2")
):
    """比较两个版本的差异"""
    version_repo = TestCaseVersionRepository()
    
    result = version_repo.compare_versions(task_id, case_id, v1, v2)
    
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    
    return CompareResponse(**result)


@router.post("/{task_id}/cases/{case_id}/restore")
async def restore_version(
    task_id: str,
    case_id: str,
    request: RestoreRequest,
    req: Request
):
    """回滚到指定版本"""
    version_repo = TestCaseVersionRepository()
    case_repo = TestCaseRepository()
    log_repo = TestCaseChangeLogRepository()
    
    # 获取要回滚到的版本
    target_version = version_repo.get_version(task_id, case_id, request.version_number)
    if not target_version:
        raise HTTPException(status_code=404, detail="目标版本不存在")
    
    # 获取当前用例
    current_case = case_repo.get_by_id(task_id, case_id)
    if not current_case:
        raise HTTPException(status_code=404, detail="测试用例不存在")
    
    # 获取请求信息
    changed_by = req.headers.get("X-User", "system")
    ip_address = req.client.host if req.client else ""
    user_agent = req.headers.get("User-Agent", "")
    
    # 创建新版本（回滚版本）
    new_version_number = version_repo.get_latest_version_number(task_id, case_id) + 1
    new_version_id = f"v_{uuid.uuid4().hex[:16]}"
    
    # 从目标版本恢复数据
    restored_case = TestCaseRecord(
        task_id=task_id,
        case_id=case_id,
        name=target_version.name,
        description=target_version.description,
        category=target_version.category,
        priority=target_version.priority,
        method=target_version.method,
        url=target_version.url,
        headers=target_version.headers,
        body=target_version.body,
        query_params=target_version.query_params,
        expected_status_code=target_version.expected_status_code,
        expected_response=target_version.expected_response,
        max_response_time_ms=target_version.max_response_time_ms,
        tags=target_version.tags,
        group_name=target_version.group_name,
        dependencies=target_version.dependencies,
        is_enabled=current_case.is_enabled
    )
    
    # 更新数据库中的用例
    import json
    updates = {
        "name": restored_case.name,
        "description": restored_case.description,
        "category": restored_case.category.value if isinstance(restored_case.category, TestCaseCategory) else restored_case.category,
        "priority": restored_case.priority.value if isinstance(restored_case.priority, TestCasePriority) else restored_case.priority,
        "method": restored_case.method,
        "url": restored_case.url,
        "headers": json.dumps(restored_case.headers, ensure_ascii=False),
        "body": json.dumps(restored_case.body, ensure_ascii=False) if restored_case.body else None,
        "query_params": json.dumps(restored_case.query_params, ensure_ascii=False),
        "expected_status_code": restored_case.expected_status_code,
        "expected_response": json.dumps(restored_case.expected_response, ensure_ascii=False),
        "max_response_time_ms": restored_case.max_response_time_ms,
        "tags": json.dumps(restored_case.tags, ensure_ascii=False),
        "group_name": restored_case.group_name,
        "dependencies": json.dumps(restored_case.dependencies, ensure_ascii=False)
    }
    case_repo.update(task_id, case_id, updates)
    
    # 创建回滚版本记录
    restore_version = TestCaseVersion.from_test_case(
        restored_case,
        version_id=new_version_id,
        version_number=new_version_number,
        change_type=ChangeType.RESTORE,
        change_summary=f"回滚到版本 {request.version_number}" + (f": {request.reason}" if request.reason else ""),
        changed_fields=["all"],
        changed_by=changed_by
    )
    version_repo.create(restore_version)
    
    # 创建变更日志
    change_log = TestCaseChangeLog(
        task_id=task_id,
        case_id=case_id,
        version_id=new_version_id,
        change_type=ChangeType.RESTORE,
        change_summary=f"回滚到版本 {request.version_number}" + (f": {request.reason}" if request.reason else ""),
        old_value={"version": version_repo.get_latest_version_number(task_id, case_id) - 1},
        new_value={"restored_from_version": request.version_number},
        changed_by=changed_by,
        ip_address=ip_address,
        user_agent=user_agent
    )
    log_repo.create(change_log)
    
    return {
        "success": True,
        "message": f"已回滚到版本 {request.version_number}",
        "new_version_number": new_version_number,
        "version_id": new_version_id
    }


@router.get("/{task_id}/cases/{case_id}/changelog", response_model=list[ChangeLogResponse])
async def get_change_logs(
    task_id: str,
    case_id: str,
    limit: int = Query(default=100, ge=1, le=500)
):
    """获取测试用例的变更日志"""
    log_repo = TestCaseChangeLogRepository()
    
    logs = log_repo.get_by_case(task_id, case_id, limit)
    
    return [
        ChangeLogResponse(
            task_id=log.task_id,
            case_id=log.case_id,
            version_id=log.version_id,
            change_type=log.change_type.value if isinstance(log.change_type, ChangeType) else log.change_type,
            change_summary=log.change_summary,
            old_value=log.old_value,
            new_value=log.new_value,
            changed_by=log.changed_by,
            created_at=log.created_at.isoformat() if log.created_at else None
        )
        for log in logs
    ]


@router.get("/{task_id}/changelog", response_model=list[ChangeLogResponse])
async def get_task_change_logs(
    task_id: str,
    limit: int = Query(default=500, ge=1, le=1000),
    offset: int = Query(default=0, ge=0)
):
    """获取任务下所有用例的变更日志"""
    log_repo = TestCaseChangeLogRepository()
    
    logs = log_repo.get_by_task(task_id, limit, offset)
    
    return [
        ChangeLogResponse(
            task_id=log.task_id,
            case_id=log.case_id,
            version_id=log.version_id,
            change_type=log.change_type.value if isinstance(log.change_type, ChangeType) else log.change_type,
            change_summary=log.change_summary,
            old_value=log.old_value,
            new_value=log.new_value,
            changed_by=log.changed_by,
            created_at=log.created_at.isoformat() if log.created_at else None
        )
        for log in logs
    ]


# =====================================================
# 版本管理服务函数（供其他模块调用）
# =====================================================

def create_version_on_update(
    test_case: TestCaseRecord,
    old_case: TestCaseRecord | None,
    change_type: ChangeType,
    changed_by: str = "system",
    ip_address: str = "",
    user_agent: str = ""
) -> str:
    """
    在测试用例更新时创建版本记录
    
    Args:
        test_case: 更新后的测试用例
        old_case: 更新前的测试用例（如果是创建则为None）
        change_type: 变更类型
        changed_by: 变更人
        ip_address: IP地址
        user_agent: User-Agent
        
    Returns:
        新版本ID
    """
    version_repo = TestCaseVersionRepository()
    log_repo = TestCaseChangeLogRepository()
    
    # 生成版本ID和版本号
    version_id = f"v_{uuid.uuid4().hex[:16]}"
    version_number = version_repo.get_latest_version_number(test_case.task_id, test_case.case_id) + 1
    
    # 计算变更字段
    changed_fields: list[str] = []
    old_value: dict[str, Any] = {}
    new_value: dict[str, Any] = {}
    
    if old_case and change_type == ChangeType.UPDATE:
        fields_to_compare = [
            'name', 'description', 'category', 'priority', 'method', 'url',
            'headers', 'body', 'query_params', 'expected_status_code',
            'expected_response', 'max_response_time_ms', 'tags', 'group_name', 'dependencies'
        ]
        
        for field in fields_to_compare:
            old_val = getattr(old_case, field)
            new_val = getattr(test_case, field)
            
            # 枚举类型转换
            if hasattr(old_val, 'value'):
                old_val = old_val.value
            if hasattr(new_val, 'value'):
                new_val = new_val.value
            
            if old_val != new_val:
                changed_fields.append(field)
                old_value[field] = old_val
                new_value[field] = new_val
    
    # 生成变更摘要
    if change_type == ChangeType.CREATE:
        change_summary = f"创建测试用例: {test_case.name}"
    elif change_type == ChangeType.UPDATE:
        if changed_fields:
            change_summary = f"更新字段: {', '.join(changed_fields[:5])}" + ("..." if len(changed_fields) > 5 else "")
        else:
            change_summary = "无实质变更"
    elif change_type == ChangeType.DELETE:
        change_summary = f"删除测试用例: {test_case.name}"
    else:
        change_summary = f"变更类型: {change_type.value}"
    
    # 创建版本记录
    version = TestCaseVersion.from_test_case(
        test_case,
        version_id=version_id,
        version_number=version_number,
        change_type=change_type,
        change_summary=change_summary,
        changed_fields=changed_fields,
        changed_by=changed_by
    )
    version_repo.create(version)
    
    # 创建变更日志
    change_log = TestCaseChangeLog(
        task_id=test_case.task_id,
        case_id=test_case.case_id,
        version_id=version_id,
        change_type=change_type,
        change_summary=change_summary,
        old_value=old_value,
        new_value=new_value,
        changed_by=changed_by,
        ip_address=ip_address,
        user_agent=user_agent
    )
    log_repo.create(change_log)
    
    return version_id
