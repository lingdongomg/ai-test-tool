# 该文件内容使用AI生成，注意识别准确性
"""
数据查询类 Skill

零 LLM 成本的确定性操作：数据库查询、正则匹配、统计聚合。
"""

import re
import logging
from typing import Any
from collections import Counter

from .registry import SkillRegistry, skill

logger = logging.getLogger(__name__)


@skill(
    name="search_logs",
    description="使用正则模式搜索日志内容，返回匹配的行",
    category="data_query",
    parameters={"pattern": "正则表达式", "log_content": "日志内容文本", "max_results": "最大返回数(默认20)"},
    returns="匹配的日志行列表",
)
def search_logs(pattern: str, log_content: str, max_results: int = 20) -> dict[str, Any]:
    """正则搜索日志"""
    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return {"error": f"正则表达式无效: {e}", "matches": []}

    matches = []
    for i, line in enumerate(log_content.split('\n')):
        if regex.search(line):
            matches.append({"line_number": i + 1, "content": line.strip()[:500]})
            if len(matches) >= max_results:
                break

    return {"total_matches": len(matches), "matches": matches}


@skill(
    name="get_error_stats",
    description="从数据库统计指定任务或时间范围内的错误数量和分布",
    category="data_query",
    parameters={"task_id": "任务ID(可选)", "hours": "统计时间范围-小时(默认24)"},
    returns="错误统计：总数、按状态码分布、按端点分布",
)
def get_error_stats(task_id: str = "", hours: int = 24) -> dict[str, Any]:
    """统计错误数量和分布"""
    try:
        from ..database.repository import RequestRepository
        repo = RequestRepository()

        if task_id:
            rows = repo.db.fetch_all(
                "SELECT http_status, url, method FROM parsed_requests WHERE task_id = ? AND http_status >= 400",
                (task_id,)
            )
        else:
            rows = repo.db.fetch_all(
                "SELECT http_status, url, method FROM parsed_requests "
                "WHERE http_status >= 400 AND created_at >= datetime('now', ?)",
                (f"-{hours} hours",)
            )

        if not rows:
            return {"total_errors": 0, "by_status": {}, "by_endpoint": {}, "message": "无错误记录"}

        status_counter: Counter = Counter()
        endpoint_counter: Counter = Counter()
        for r in rows:
            status_counter[r['http_status']] += 1
            endpoint_counter[f"{r['method']} {r['url']}"] += 1

        return {
            "total_errors": len(rows),
            "by_status": dict(status_counter.most_common(10)),
            "by_endpoint": dict(endpoint_counter.most_common(10)),
        }
    except Exception as e:
        return {"error": str(e), "total_errors": 0}


@skill(
    name="get_endpoint_performance",
    description="查询接口性能数据：平均响应时间、P50/P90/P99",
    category="data_query",
    parameters={"endpoint": "接口路径(可选，为空则查全部)", "hours": "时间范围-小时(默认24)"},
    returns="性能统计：平均响应时间、分位数、慢请求数",
)
def get_endpoint_performance(endpoint: str = "", hours: int = 24) -> dict[str, Any]:
    """查询接口性能数据"""
    try:
        from ..database.repository import RequestRepository
        repo = RequestRepository()

        if endpoint:
            rows = repo.db.fetch_all(
                "SELECT response_time_ms FROM parsed_requests "
                "WHERE url LIKE ? AND response_time_ms > 0 AND created_at >= datetime('now', ?)",
                (f"%{endpoint}%", f"-{hours} hours")
            )
        else:
            rows = repo.db.fetch_all(
                "SELECT response_time_ms FROM parsed_requests "
                "WHERE response_time_ms > 0 AND created_at >= datetime('now', ?)",
                (f"-{hours} hours",)
            )

        if not rows:
            return {"message": "无性能数据", "count": 0}

        times = sorted(r['response_time_ms'] for r in rows)
        n = len(times)

        return {
            "count": n,
            "avg_ms": round(sum(times) / n, 1),
            "p50_ms": round(times[n // 2], 1),
            "p90_ms": round(times[int(n * 0.9)], 1),
            "p99_ms": round(times[int(n * 0.99)], 1) if n >= 100 else round(times[-1], 1),
            "max_ms": round(times[-1], 1),
            "slow_count": sum(1 for t in times if t > 3000),
        }
    except Exception as e:
        return {"error": str(e)}


@skill(
    name="get_recent_alerts",
    description="获取最近的告警列表",
    category="data_query",
    parameters={"source_id": "日志源ID(可选)", "hours": "时间范围-小时(默认24)", "limit": "最大数量(默认20)"},
    returns="告警列表",
)
def get_recent_alerts(source_id: str = "", hours: int = 24, limit: int = 20) -> dict[str, Any]:
    """获取最近告警"""
    try:
        from ..database import get_db_manager
        db = get_db_manager()

        if source_id:
            rows = db.fetch_all(
                "SELECT * FROM log_alerts WHERE source_id = ? "
                "AND created_at >= datetime('now', ?) ORDER BY created_at DESC LIMIT ?",
                (source_id, f"-{hours} hours", limit)
            )
        else:
            rows = db.fetch_all(
                "SELECT * FROM log_alerts "
                "WHERE created_at >= datetime('now', ?) ORDER BY created_at DESC LIMIT ?",
                (f"-{hours} hours", limit)
            )

        return {
            "total": len(rows),
            "alerts": [dict(r) for r in rows] if rows else [],
        }
    except Exception as e:
        # log_alerts 表可能还不存在
        return {"total": 0, "alerts": [], "message": str(e)}


@skill(
    name="classify_request",
    description="根据 URL 路径前缀规则分类 HTTP 请求（不调用 LLM）",
    category="data_query",
    parameters={"url": "请求URL路径"},
    returns="分类结果",
)
def classify_request(url: str) -> dict[str, Any]:
    """URL 规则分类"""
    url_lower = url.lower()

    # URL 前缀 → 分类映射表
    CATEGORY_RULES = [
        (("/user", "/auth", "/login", "/register", "/oauth", "/sso"), "用户认证"),
        (("/product", "/goods", "/item", "/sku", "/catalog"), "商品管理"),
        (("/order", "/trade", "/purchase"), "订单管理"),
        (("/pay", "/payment", "/charge", "/refund"), "支付系统"),
        (("/upload", "/file", "/cos", "/oss", "/image"), "文件管理"),
        (("/config", "/setting", "/system"), "系统配置"),
        (("/stat", "/analytics", "/report", "/dashboard"), "数据统计"),
        (("/message", "/notification", "/push", "/sms", "/email"), "消息通知"),
        (("/search", "/query", "/filter"), "搜索查询"),
        (("/health", "/ping", "/status", "/monitor"), "健康检查"),
    ]

    for prefixes, category in CATEGORY_RULES:
        for prefix in prefixes:
            if prefix in url_lower:
                return {"url": url, "category": category, "source": "rule", "confidence": 0.9}

    return {"url": url, "category": "其他", "source": "default", "confidence": 0.3}


def register_data_skills(registry: SkillRegistry) -> None:
    """注册数据查询类 Skill（通过 @skill 装饰器已自动注册，此函数仅确保模块被导入）"""
    logger.info(f"数据查询类 Skill 已注册: search_logs, get_error_stats, get_endpoint_performance, get_recent_alerts, classify_request")
