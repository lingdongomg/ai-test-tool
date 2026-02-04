"""
Dashboard API
首页仪表盘数据
"""

from typing import Any
from fastapi import APIRouter, Query
from pydantic import BaseModel

from ...database import get_db_manager
from ...utils.logger import get_logger

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
async def get_dashboard_stats():
    """获取仪表盘核心统计数据"""
    db = get_db_manager()
    
    # 1. 接口统计
    endpoint_stats = db.fetch_one("""
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT method) as methods
        FROM api_endpoints
    """)
    
    # 2. 测试覆盖率
    total_endpoints_result = db.fetch_one("SELECT COUNT(*) as cnt FROM api_endpoints")
    total_cases_result = db.fetch_one("SELECT COUNT(*) as cnt FROM test_cases")
    enabled_cases_result = db.fetch_one("SELECT COUNT(*) as cnt FROM test_cases WHERE is_enabled = 1")
    
    # 统计有测试用例覆盖的接口数量（通过 case_id 前缀匹配 endpoint_id）
    covered_result = db.fetch_one("""
        SELECT COUNT(*) as cnt FROM api_endpoints e
        WHERE EXISTS (SELECT 1 FROM test_cases tc WHERE tc.case_id LIKE (e.endpoint_id || '%'))
    """)
    covered_endpoints = covered_result['cnt'] if covered_result else 0
    
    coverage_stats = {
        'total_endpoints': total_endpoints_result['cnt'] if total_endpoints_result else 0,
        'covered_endpoints': covered_endpoints,
        'total_cases': total_cases_result['cnt'] if total_cases_result else 0,
        'enabled_cases': enabled_cases_result['cnt'] if enabled_cases_result else 0
    }
    
    # 3. 线上健康状态
    health_stats = db.fetch_one("""
        SELECT 
            COUNT(*) as total_monitors,
            SUM(CASE WHEN is_enabled = 1 THEN 1 ELSE 0 END) as enabled,
            SUM(CASE WHEN last_check_status = 'healthy' THEN 1 ELSE 0 END) as healthy,
            SUM(CASE WHEN last_check_status = 'unhealthy' THEN 1 ELSE 0 END) as unhealthy,
            SUM(CASE WHEN consecutive_failures >= 3 THEN 1 ELSE 0 END) as critical
        FROM production_requests
    """)
    
    # 4. 近期异常
    anomaly_stats = db.fetch_one("""
        SELECT 
            COUNT(*) as total_reports,
            SUM(JSON_EXTRACT(statistics, '$.total_anomalies')) as total_anomalies,
            SUM(JSON_EXTRACT(statistics, '$.critical_count')) as critical_count
        FROM analysis_reports
        WHERE report_type = 'anomaly' 
        AND created_at >= datetime('now', '-7 days')
    """)
    
    # 5. AI 洞察
    insight_stats = db.fetch_one("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN is_resolved = 0 THEN 1 ELSE 0 END) as unresolved,
            SUM(CASE WHEN severity = 'high' AND is_resolved = 0 THEN 1 ELSE 0 END) as `high_priority`
        FROM ai_insights
    """)
    
    total_endpoints = coverage_stats['total_endpoints'] if coverage_stats else 0
    covered_endpoints = coverage_stats['covered_endpoints'] if coverage_stats else 0
    total_monitors = health_stats['total_monitors'] if health_stats else 0
    healthy_monitors = health_stats['healthy'] if health_stats else 0
    
    return {
        "endpoints": {
            "total": endpoint_stats['total'] if endpoint_stats else 0,
            "methods": endpoint_stats['methods'] if endpoint_stats else 0
        },
        "test_coverage": {
            "total_endpoints": total_endpoints,
            "covered_endpoints": covered_endpoints,
            "coverage_rate": round(covered_endpoints / total_endpoints * 100, 1) if total_endpoints > 0 else 0,
            "total_cases": coverage_stats['total_cases'] if coverage_stats else 0,
            "enabled_cases": coverage_stats['enabled_cases'] if coverage_stats else 0
        },
        "health_status": {
            "total_monitors": total_monitors,
            "enabled": health_stats['enabled'] if health_stats else 0,
            "healthy": healthy_monitors,
            "unhealthy": health_stats['unhealthy'] if health_stats else 0,
            "critical": health_stats['critical'] if health_stats else 0,
            "health_rate": round(healthy_monitors / total_monitors * 100, 1) if total_monitors > 0 else 0
        },
        "recent_anomalies": {
            "total_reports": anomaly_stats['total_reports'] if anomaly_stats else 0,
            "total_anomalies": int(anomaly_stats['total_anomalies'] or 0) if anomaly_stats else 0,
            "critical_count": int(anomaly_stats['critical_count'] or 0) if anomaly_stats else 0
        },
        "ai_insights": {
            "total": insight_stats['total'] if insight_stats else 0,
            "unresolved": insight_stats['unresolved'] if insight_stats else 0,
            "high_priority": insight_stats['high_priority'] if insight_stats else 0
        }
    }


# ==================== 近期动态 ====================

@router.get("/activities")
async def get_recent_activities(limit: int = Query(default=10, ge=1, le=50)):
    """获取近期动态"""
    db = get_db_manager()
    
    activities = []
    
    # 1. 最近的测试执行
    executions = db.fetch_all("""
        SELECT 
            'execution' as type,
            execution_id as id,
            '执行测试场景' as title,
            status,
            created_at
        FROM scenario_executions
        ORDER BY created_at DESC
        LIMIT 5
    """)
    
    for e in executions:
        activities.append({
            "type": "execution",
            "id": e['id'],
            "title": e['title'],
            "status": e['status'],
            "time": str(e['created_at'])
        })
    
    # 2. 最近的健康检查
    health_checks = db.fetch_all("""
        SELECT 
            'health_check' as type,
            execution_id as id,
            ('健康检查 - ' || status) as title,
            status,
            healthy_count,
            unhealthy_count,
            created_at
        FROM health_check_executions
        ORDER BY created_at DESC
        LIMIT 5
    """)
    
    for h in health_checks:
        activities.append({
            "type": "health_check",
            "id": h['id'],
            "title": h['title'],
            "status": h['status'],
            "details": f"健康: {h['healthy_count']}, 异常: {h['unhealthy_count']}",
            "time": str(h['created_at'])
        })
    
    # 3. 最近的异常报告
    reports = db.fetch_all("""
        SELECT 
            'anomaly_report' as type,
            id,
            title,
            JSON_EXTRACT(statistics, '$.total_anomalies') as anomaly_count,
            created_at
        FROM analysis_reports
        WHERE report_type = 'anomaly'
        ORDER BY created_at DESC
        LIMIT 5
    """)
    
    for r in reports:
        activities.append({
            "type": "anomaly_report",
            "id": r['id'],
            "title": r['title'],
            "details": f"发现 {int(r['anomaly_count'] or 0)} 个异常",
            "time": str(r['created_at'])
        })
    
    # 4. 最近的 AI 洞察
    insights = db.fetch_all("""
        SELECT 
            'ai_insight' as type,
            insight_id as id,
            title,
            severity,
            created_at
        FROM ai_insights
        WHERE is_resolved = 0
        ORDER BY created_at DESC
        LIMIT 5
    """)
    
    for i in insights:
        activities.append({
            "type": "ai_insight",
            "id": i['id'],
            "title": i['title'],
            "severity": i['severity'],
            "time": str(i['created_at'])
        })
    
    # 按时间排序
    activities.sort(key=lambda x: x['time'], reverse=True)
    
    return {"activities": activities[:limit]}


# ==================== AI 洞察 ====================

@router.get("/insights")
async def get_dashboard_insights(limit: int = Query(default=5, ge=1, le=20)):
    """获取首页展示的 AI 洞察"""
    db = get_db_manager()
    
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
async def get_coverage_trend(days: int = Query(default=7, ge=1, le=30)):
    """获取测试覆盖率趋势"""
    db = get_db_manager()
    
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
async def get_health_trend(days: int = Query(default=7, ge=1, le=30)):
    """获取健康状态趋势"""
    db = get_db_manager()
    
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
async def get_anomaly_trend(days: int = Query(default=7, ge=1, le=30)):
    """获取异常趋势"""
    db = get_db_manager()
    
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
