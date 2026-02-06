"""
Dashboard API
首页仪表盘数据
"""

from typing import Any
from fastapi import APIRouter, Query, Depends
from pydantic import BaseModel

from ...database import get_db_manager, DatabaseManager
from ...utils.logger import get_logger
from ..dependencies import get_database

router = APIRouter()
logger = get_logger()


# ==================== 响应模型 ====================

class DashboardStats(BaseModel):
    """仪表盘统计数据"""
    endpoints: dict
    test_coverage: dict
    health_status: dict
    recent_anomalies: dict


class QuickAction(BaseModel):
    """快捷操作"""
    id: str
    title: str
    description: str
    icon: str
    route: str


# ==================== 核心指标 ====================

@router.get("/stats")
async def get_dashboard_stats(db: DatabaseManager = Depends(get_database)):
    """获取仪表盘核心统计数据"""
    # 使用单次查询获取所有统计数据
    stats = db.fetch_one("""
        SELECT
            -- 接口统计
            (SELECT COUNT(*) FROM api_endpoints) as endpoint_total,
            (SELECT COUNT(DISTINCT method) FROM api_endpoints) as endpoint_methods,
            -- 测试用例统计
            (SELECT COUNT(*) FROM test_cases) as total_cases,
            (SELECT COUNT(*) FROM test_cases WHERE is_enabled = 1) as enabled_cases,
            -- 覆盖率统计
            (SELECT COUNT(*) FROM api_endpoints e
             WHERE EXISTS (SELECT 1 FROM test_cases tc WHERE tc.case_id LIKE (e.endpoint_id || '%'))) as covered_endpoints,
            -- 健康状态统计
            (SELECT COUNT(*) FROM production_requests) as total_monitors,
            (SELECT COUNT(*) FROM production_requests WHERE is_enabled = 1) as enabled_monitors,
            (SELECT COUNT(*) FROM production_requests WHERE last_check_status = 'healthy') as healthy_monitors,
            (SELECT COUNT(*) FROM production_requests WHERE last_check_status = 'unhealthy') as unhealthy_monitors,
            (SELECT COUNT(*) FROM production_requests WHERE consecutive_failures >= 3) as critical_monitors,
            -- AI 洞察统计
            (SELECT COUNT(*) FROM ai_insights) as total_insights,
            (SELECT COUNT(*) FROM ai_insights WHERE is_resolved = 0) as unresolved_insights,
            (SELECT COUNT(*) FROM ai_insights WHERE severity = 'high' AND is_resolved = 0) as high_priority_insights
    """)

    # 近期异常统计（需要单独查询因为涉及 JSON_EXTRACT 聚合）
    anomaly_stats = db.fetch_one("""
        SELECT
            COUNT(*) as total_reports,
            COALESCE(SUM(JSON_EXTRACT(statistics, '$.total_anomalies')), 0) as total_anomalies,
            COALESCE(SUM(JSON_EXTRACT(statistics, '$.critical_count')), 0) as critical_count
        FROM analysis_reports
        WHERE report_type = 'anomaly'
        AND created_at >= datetime('now', '-7 days')
    """)

    endpoint_total = stats['endpoint_total'] if stats else 0
    covered_endpoints = stats['covered_endpoints'] if stats else 0
    total_monitors = stats['total_monitors'] if stats else 0
    healthy_monitors = stats['healthy_monitors'] if stats else 0

    return {
        "endpoints": {
            "total": endpoint_total,
            "methods": stats['endpoint_methods'] if stats else 0
        },
        "test_coverage": {
            "total_endpoints": endpoint_total,
            "covered_endpoints": covered_endpoints,
            "coverage_rate": round(covered_endpoints / endpoint_total * 100, 1) if endpoint_total > 0 else 0,
            "total_cases": stats['total_cases'] if stats else 0,
            "enabled_cases": stats['enabled_cases'] if stats else 0
        },
        "health_status": {
            "total_monitors": total_monitors,
            "enabled": stats['enabled_monitors'] if stats else 0,
            "healthy": healthy_monitors,
            "unhealthy": stats['unhealthy_monitors'] if stats else 0,
            "critical": stats['critical_monitors'] if stats else 0,
            "health_rate": round(healthy_monitors / total_monitors * 100, 1) if total_monitors > 0 else 0
        },
        "recent_anomalies": {
            "total_reports": anomaly_stats['total_reports'] if anomaly_stats else 0,
            "total_anomalies": int(anomaly_stats['total_anomalies'] or 0) if anomaly_stats else 0,
            "critical_count": int(anomaly_stats['critical_count'] or 0) if anomaly_stats else 0
        },
        "ai_insights": {
            "total": stats['total_insights'] if stats else 0,
            "unresolved": stats['unresolved_insights'] if stats else 0,
            "high_priority": stats['high_priority_insights'] if stats else 0
        }
    }


# ==================== 近期动态 ====================

@router.get("/activities")
async def get_recent_activities(
    limit: int = Query(default=10, ge=1, le=50),
    db: DatabaseManager = Depends(get_database)
):
    """获取近期动态"""
    # 使用 UNION ALL 合并多个查询，一次性获取所有活动
    sql = """
        SELECT * FROM (
            -- 测试执行
            SELECT
                'execution' as type,
                execution_id as id,
                '执行测试场景' as title,
                status,
                NULL as details,
                NULL as severity,
                created_at
            FROM scenario_executions
            ORDER BY created_at DESC
            LIMIT 5
        )
        UNION ALL
        SELECT * FROM (
            -- 健康检查
            SELECT
                'health_check' as type,
                execution_id as id,
                ('健康检查 - ' || status) as title,
                status,
                ('健康: ' || healthy_count || ', 异常: ' || unhealthy_count) as details,
                NULL as severity,
                created_at
            FROM health_check_executions
            ORDER BY created_at DESC
            LIMIT 5
        )
        UNION ALL
        SELECT * FROM (
            -- 异常报告
            SELECT
                'anomaly_report' as type,
                CAST(id as TEXT) as id,
                title,
                NULL as status,
                ('发现 ' || CAST(COALESCE(JSON_EXTRACT(statistics, '$.total_anomalies'), 0) as TEXT) || ' 个异常') as details,
                NULL as severity,
                created_at
            FROM analysis_reports
            WHERE report_type = 'anomaly'
            ORDER BY created_at DESC
            LIMIT 5
        )
        UNION ALL
        SELECT * FROM (
            -- AI 洞察
            SELECT
                'ai_insight' as type,
                insight_id as id,
                title,
                NULL as status,
                NULL as details,
                severity,
                created_at
            FROM ai_insights
            WHERE is_resolved = 0
            ORDER BY created_at DESC
            LIMIT 5
        )
        ORDER BY created_at DESC
        LIMIT %s
    """
    rows = db.fetch_all(sql, (limit,))

    activities = []
    for row in rows:
        activity = {
            "type": row['type'],
            "id": row['id'],
            "title": row['title'],
            "time": str(row['created_at'])
        }
        if row['status']:
            activity['status'] = row['status']
        if row['details']:
            activity['details'] = row['details']
        if row['severity']:
            activity['severity'] = row['severity']
        activities.append(activity)

    return {"activities": activities}


# ==================== AI 洞察 ====================

@router.get("/insights")
async def get_dashboard_insights(
    limit: int = Query(default=5, ge=1, le=20),
    db: DatabaseManager = Depends(get_database)
):
    """获取首页展示的 AI 洞察"""
    # 获取未解决的高优先级洞察
    insights = db.fetch_all("""
        SELECT
            insight_id,
            insight_type,
            title,
            description,
            severity,
            confidence,
            recommendations,
            created_at
        FROM ai_insights
        WHERE is_resolved = 0
        ORDER BY
            CASE severity WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 ELSE 4 END,
            created_at DESC
        LIMIT %s
    """, (limit,))

    return {
        "insights": [
            {
                "id": i['insight_id'],
                "type": i['insight_type'],
                "title": i['title'],
                "description": i['description'],
                "severity": i['severity'],
                "confidence": float(i['confidence']) if i['confidence'] else 0.8,
                "recommendations": i['recommendations'],
                "time": str(i['created_at'])
            }
            for i in insights
        ]
    }


# ==================== 快捷操作 ====================

@router.get("/quick-actions")
async def get_quick_actions():
    """获取快捷操作列表"""
    return {
        "actions": [
            {
                "id": "import_swagger",
                "title": "导入接口文档",
                "description": "导入 Swagger/OpenAPI 文档",
                "icon": "upload",
                "route": "/import"
            },
            {
                "id": "generate_tests",
                "title": "生成测试用例",
                "description": "为接口自动生成测试",
                "icon": "code",
                "route": "/development/tests"
            },
            {
                "id": "upload_log",
                "title": "上传日志分析",
                "description": "上传日志文件进行异常检测",
                "icon": "file-text",
                "route": "/insights/upload"
            },
            {
                "id": "health_check",
                "title": "执行健康检查",
                "description": "检查线上接口健康状态",
                "icon": "activity",
                "route": "/monitoring/health-check"
            },
            {
                "id": "view_reports",
                "title": "查看分析报告",
                "description": "查看异常检测报告",
                "icon": "file-chart",
                "route": "/insights/reports"
            }
        ]
    }


# ==================== 趋势图表数据 ====================

@router.get("/trends/coverage")
async def get_coverage_trend(
    days: int = Query(default=7, ge=1, le=30),
    db: DatabaseManager = Depends(get_database)
):
    """获取测试覆盖率趋势"""
    # 按天统计新增测试用例
    sql = """
        SELECT
            DATE(created_at) as date,
            COUNT(*) as new_cases
        FROM test_cases
        WHERE created_at >= datetime('now', '-' || %s || ' days')
        GROUP BY DATE(created_at)
        ORDER BY date
    """
    rows = db.fetch_all(sql, (days,))

    return {
        "days": days,
        "data": [
            {"date": str(row['date']), "new_cases": row['new_cases']}
            for row in rows
        ]
    }


@router.get("/trends/health")
async def get_health_trend(
    days: int = Query(default=7, ge=1, le=30),
    db: DatabaseManager = Depends(get_database)
):
    """获取健康状态趋势"""
    sql = """
        SELECT
            DATE(checked_at) as date,
            COUNT(*) as total,
            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success,
            AVG(response_time_ms) as avg_time
        FROM health_check_results
        WHERE checked_at >= datetime('now', '-' || %s || ' days')
        GROUP BY DATE(checked_at)
        ORDER BY date
    """
    rows = db.fetch_all(sql, (days,))

    return {
        "days": days,
        "data": [
            {
                "date": str(row['date']),
                "total": row['total'],
                "success": row['success'],
                "success_rate": round(row['success'] / row['total'] * 100, 1) if row['total'] > 0 else 0,
                "avg_time": round(row['avg_time'] or 0, 2)
            }
            for row in rows
        ]
    }


@router.get("/trends/anomalies")
async def get_anomaly_trend(
    days: int = Query(default=7, ge=1, le=30),
    db: DatabaseManager = Depends(get_database)
):
    """获取异常趋势"""
    sql = """
        SELECT
            DATE(created_at) as date,
            SUM(JSON_EXTRACT(statistics, '$.critical_count')) as critical,
            SUM(JSON_EXTRACT(statistics, '$.error_count')) as error,
            SUM(JSON_EXTRACT(statistics, '$.warning_count')) as warning
        FROM analysis_reports
        WHERE report_type = 'anomaly'
        AND created_at >= datetime('now', '-' || %s || ' days')
        GROUP BY DATE(created_at)
        ORDER BY date
    """
    rows = db.fetch_all(sql, (days,))

    return {
        "days": days,
        "data": [
            {
                "date": str(row['date']),
                "critical": int(row['critical'] or 0),
                "error": int(row['error'] or 0),
                "warning": int(row['warning'] or 0)
            }
            for row in rows
        ]
    }
