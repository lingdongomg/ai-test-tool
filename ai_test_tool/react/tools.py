"""
工具注册表和内置工具

提供ReAct Agent可调用的工具集合
"""

import json
import logging
import re
import time
from collections import defaultdict
from functools import wraps
from typing import Any, Callable

from .models import Tool, ToolResult

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    工具注册表

    管理所有可用工具的注册、查询、执行
    """

    _instance: "ToolRegistry | None" = None

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    @classmethod
    def get_instance(cls) -> "ToolRegistry":
        """获取全局单例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """重置单例（测试用）"""
        cls._instance = None

    def register(self, tool: Tool) -> None:
        """注册工具"""
        if tool.name in self._tools:
            logger.warning(f"工具 {tool.name} 已存在，将被覆盖")
        self._tools[tool.name] = tool
        logger.debug(f"注册工具: {tool.name}")

    def unregister(self, name: str) -> bool:
        """注销工具"""
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get(self, name: str) -> Tool | None:
        """获取工具"""
        return self._tools.get(name)

    def get_all(self) -> list[Tool]:
        """获取所有工具"""
        return list(self._tools.values())

    def get_by_tags(self, tags: list[str]) -> list[Tool]:
        """按标签获取工具"""
        return [
            t for t in self._tools.values()
            if any(tag in t.tags for tag in tags)
        ]

    def execute(
        self,
        tool_name: str,
        **kwargs: Any
    ) -> ToolResult:
        """
        执行工具

        Args:
            tool_name: 工具名称
            **kwargs: 工具参数

        Returns:
            工具执行结果
        """
        tool = self.get(tool_name)
        if not tool:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"工具不存在: {tool_name}"
            )

        start_time = time.time()

        try:
            # 验证必需参数
            for param in tool.required_params:
                if param not in kwargs:
                    return ToolResult(
                        tool_name=tool_name,
                        success=False,
                        error=f"缺少必需参数: {param}"
                    )

            # 执行工具
            result = tool.func(**kwargs)

            return ToolResult(
                tool_name=tool_name,
                success=True,
                output=result,
                execution_time_ms=(time.time() - start_time) * 1000
            )

        except Exception as e:
            logger.error(f"工具执行失败: {tool_name}, 错误: {e}")
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000
            )

    def get_tools_prompt(self) -> str:
        """
        生成工具列表的prompt描述

        用于LLM理解可用工具
        """
        if not self._tools:
            return "当前没有可用的工具。"

        lines = ["可用工具列表：\n"]
        for tool in self._tools.values():
            lines.append(tool.to_prompt_description())
            lines.append("")

        return "\n".join(lines)

    @property
    def size(self) -> int:
        """工具数量"""
        return len(self._tools)


# 全局注册表访问函数
def get_tool_registry() -> ToolRegistry:
    """获取全局工具注册表"""
    return ToolRegistry.get_instance()


def register_tool(tool: Tool) -> None:
    """注册工具到全局注册表"""
    get_tool_registry().register(tool)


# 装饰器
def tool(
    name: str,
    description: str,
    parameters: dict[str, Any] | None = None,
    required_params: list[str] | None = None,
    return_type: str = "string",
    tags: list[str] | None = None,
    auto_register: bool = True
) -> Callable:
    """
    工具装饰器

    使用示例：
    ```python
    @tool(
        name="search_logs",
        description="在日志中搜索关键词",
        parameters={"keyword": {"type": "string", "description": "搜索关键词"}},
        required_params=["keyword"]
    )
    def search_logs(keyword: str, context: dict) -> str:
        # 实现搜索逻辑
        return results
    ```
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # 创建Tool对象
        tool_obj = Tool(
            name=name,
            description=description,
            func=wrapper,
            parameters=parameters or {},
            required_params=required_params or [],
            return_type=return_type,
            tags=tags or []
        )

        # 自动注册
        if auto_register:
            register_tool(tool_obj)

        # 附加tool对象到函数
        wrapper._tool = tool_obj
        return wrapper

    return decorator


# ============================================================
# 内置工具实现
# ============================================================

class SearchLogsTool:
    """日志搜索工具"""

    @staticmethod
    def create() -> Tool:
        return Tool(
            name="search_logs",
            description="在日志内容中搜索指定关键词或模式，返回匹配的行",
            func=SearchLogsTool.execute,
            parameters={
                "keyword": {
                    "type": "string",
                    "description": "搜索关键词（支持正则表达式）"
                },
                "context_lines": {
                    "type": "integer",
                    "description": "返回匹配行的上下文行数，默认为2"
                },
                "max_results": {
                    "type": "integer",
                    "description": "最大返回结果数，默认为20"
                }
            },
            required_params=["keyword"],
            return_type="匹配的日志行列表（JSON格式）",
            tags=["log", "search"]
        )

    @staticmethod
    def execute(
        keyword: str,
        log_content: str = "",
        context_lines: int = 2,
        max_results: int = 20,
        **kwargs: Any
    ) -> str:
        """执行日志搜索"""
        if not log_content:
            log_content = kwargs.get("_context", {}).get("log_content", "")

        if not log_content:
            return json.dumps({"error": "无日志内容可搜索", "matches": []})

        lines = log_content.split("\n")
        matches = []

        try:
            pattern = re.compile(keyword, re.IGNORECASE)
        except re.error:
            # 如果不是有效的正则，作为普通字符串搜索
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)

        for i, line in enumerate(lines):
            if pattern.search(line):
                # 获取上下文
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                context = lines[start:end]

                matches.append({
                    "line_number": i + 1,
                    "match": line.strip(),
                    "context": [l.strip() for l in context]
                })

                if len(matches) >= max_results:
                    break

        return json.dumps({
            "keyword": keyword,
            "total_matches": len(matches),
            "matches": matches
        }, ensure_ascii=False, indent=2)


class FilterRequestsTool:
    """请求过滤工具"""

    @staticmethod
    def create() -> Tool:
        return Tool(
            name="filter_requests",
            description="根据条件过滤HTTP请求，支持按状态码、URL、方法、响应时间等过滤",
            func=FilterRequestsTool.execute,
            parameters={
                "status_code": {
                    "type": "integer",
                    "description": "过滤指定HTTP状态码"
                },
                "status_range": {
                    "type": "string",
                    "description": "状态码范围，如 '4xx' 或 '5xx'"
                },
                "url_pattern": {
                    "type": "string",
                    "description": "URL匹配模式（正则表达式）"
                },
                "method": {
                    "type": "string",
                    "description": "HTTP方法，如 GET、POST"
                },
                "min_response_time": {
                    "type": "integer",
                    "description": "最小响应时间（毫秒）"
                },
                "has_error": {
                    "type": "boolean",
                    "description": "是否有错误"
                },
                "limit": {
                    "type": "integer",
                    "description": "返回结果数量限制，默认50"
                }
            },
            required_params=[],
            return_type="过滤后的请求列表（JSON格式）",
            tags=["request", "filter"]
        )

    @staticmethod
    def execute(
        requests: list[dict[str, Any]] | None = None,
        status_code: int | None = None,
        status_range: str | None = None,
        url_pattern: str | None = None,
        method: str | None = None,
        min_response_time: int | None = None,
        has_error: bool | None = None,
        limit: int = 50,
        **kwargs: Any
    ) -> str:
        """执行请求过滤"""
        if requests is None:
            requests = kwargs.get("_context", {}).get("requests", [])

        if not requests:
            return json.dumps({"error": "无请求数据", "filtered": []})

        filtered = []

        for req in requests:
            # 状态码过滤
            req_status = req.get("http_status", 0)
            if status_code is not None and req_status != status_code:
                continue
            if status_range:
                if status_range == "4xx" and not (400 <= req_status < 500):
                    continue
                elif status_range == "5xx" and not (500 <= req_status < 600):
                    continue
                elif status_range == "2xx" and not (200 <= req_status < 300):
                    continue

            # URL过滤
            if url_pattern:
                try:
                    if not re.search(url_pattern, req.get("url", ""), re.IGNORECASE):
                        continue
                except re.error:
                    pass

            # 方法过滤
            if method and req.get("method", "").upper() != method.upper():
                continue

            # 响应时间过滤
            if min_response_time is not None:
                if req.get("response_time_ms", 0) < min_response_time:
                    continue

            # 错误过滤
            if has_error is not None:
                if req.get("has_error", False) != has_error:
                    continue

            filtered.append({
                "url": req.get("url", ""),
                "method": req.get("method", ""),
                "status": req_status,
                "response_time_ms": req.get("response_time_ms", 0),
                "has_error": req.get("has_error", False),
                "error_message": req.get("error_message", "")[:200],
                "timestamp": req.get("timestamp", "")
            })

            if len(filtered) >= limit:
                break

        return json.dumps({
            "total_filtered": len(filtered),
            "filters_applied": {
                k: v for k, v in {
                    "status_code": status_code,
                    "status_range": status_range,
                    "url_pattern": url_pattern,
                    "method": method,
                    "min_response_time": min_response_time,
                    "has_error": has_error
                }.items() if v is not None
            },
            "requests": filtered
        }, ensure_ascii=False, indent=2)


class CalculateStatsTool:
    """统计计算工具"""

    @staticmethod
    def create() -> Tool:
        return Tool(
            name="calculate_stats",
            description="计算请求的统计指标，包括响应时间分布、错误率、吞吐量等",
            func=CalculateStatsTool.execute,
            parameters={
                "metric": {
                    "type": "string",
                    "description": "要计算的指标: response_time, error_rate, throughput, all"
                },
                "group_by": {
                    "type": "string",
                    "description": "分组字段: endpoint, method, status, none"
                }
            },
            required_params=[],
            return_type="统计结果（JSON格式）",
            tags=["statistics", "analysis"]
        )

    @staticmethod
    def execute(
        requests: list[dict[str, Any]] | None = None,
        metric: str = "all",
        group_by: str = "none",
        **kwargs: Any
    ) -> str:
        """计算统计指标"""
        if requests is None:
            requests = kwargs.get("_context", {}).get("requests", [])

        if not requests:
            return json.dumps({"error": "无请求数据"})

        def calc_stats(reqs: list[dict]) -> dict:
            """计算单组统计"""
            n = len(reqs)
            if n == 0:
                return {}

            response_times = [r.get("response_time_ms", 0) for r in reqs if r.get("response_time_ms", 0) > 0]
            errors = sum(1 for r in reqs if r.get("has_error") or r.get("http_status", 0) >= 400)

            stats = {"count": n}

            if metric in ("response_time", "all") and response_times:
                response_times.sort()
                rn = len(response_times)
                stats["response_time"] = {
                    "avg_ms": round(sum(response_times) / rn, 2),
                    "min_ms": round(min(response_times), 2),
                    "max_ms": round(max(response_times), 2),
                    "p50_ms": round(response_times[rn // 2], 2),
                    "p90_ms": round(response_times[int(rn * 0.9)], 2),
                    "p99_ms": round(response_times[int(rn * 0.99)], 2) if rn >= 100 else None,
                }

            if metric in ("error_rate", "all"):
                stats["error_rate"] = round(errors / n, 4)
                stats["error_count"] = errors

            return stats

        result: dict[str, Any] = {}

        if group_by == "none":
            result = calc_stats(requests)
        else:
            groups: dict[str, list] = defaultdict(list)
            for req in requests:
                if group_by == "endpoint":
                    key = req.get("url", "").split("?")[0]
                elif group_by == "method":
                    key = req.get("method", "UNKNOWN")
                elif group_by == "status":
                    key = str(req.get("http_status", 0))
                else:
                    key = "all"
                groups[key].append(req)

            result = {
                "grouped_by": group_by,
                "groups": {k: calc_stats(v) for k, v in groups.items()}
            }

        return json.dumps(result, ensure_ascii=False, indent=2)


class ExtractPatternsTool:
    """模式提取工具"""

    @staticmethod
    def create() -> Tool:
        return Tool(
            name="extract_patterns",
            description="从日志中提取特定模式的信息，如IP地址、时间戳、错误码、异常堆栈等",
            func=ExtractPatternsTool.execute,
            parameters={
                "pattern_type": {
                    "type": "string",
                    "description": "模式类型: ip, timestamp, error_code, exception, url, email, custom"
                },
                "custom_pattern": {
                    "type": "string",
                    "description": "自定义正则表达式（当pattern_type为custom时使用）"
                },
                "limit": {
                    "type": "integer",
                    "description": "返回结果数量限制，默认100"
                }
            },
            required_params=["pattern_type"],
            return_type="提取的模式列表（JSON格式）",
            tags=["pattern", "extraction"]
        )

    # 预定义模式
    PATTERNS = {
        "ip": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "timestamp": r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?",
        "error_code": r"\b(?:ERR|ERROR|FATAL|WARN)[_-]?\d{3,6}\b",
        "exception": r"(?:Exception|Error|Throwable):\s*[^\n]+",
        "url": r"https?://[^\s<>\"']+",
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    }

    @staticmethod
    def execute(
        pattern_type: str,
        log_content: str = "",
        custom_pattern: str = "",
        limit: int = 100,
        **kwargs: Any
    ) -> str:
        """提取模式"""
        if not log_content:
            log_content = kwargs.get("_context", {}).get("log_content", "")

        if not log_content:
            return json.dumps({"error": "无日志内容", "matches": []})

        # 获取正则模式
        if pattern_type == "custom":
            if not custom_pattern:
                return json.dumps({"error": "自定义模式需要提供custom_pattern参数"})
            pattern = custom_pattern
        else:
            pattern = ExtractPatternsTool.PATTERNS.get(pattern_type)
            if not pattern:
                return json.dumps({
                    "error": f"未知的模式类型: {pattern_type}",
                    "available_types": list(ExtractPatternsTool.PATTERNS.keys())
                })

        try:
            matches = re.findall(pattern, log_content, re.IGNORECASE)
        except re.error as e:
            return json.dumps({"error": f"正则表达式错误: {e}"})

        # 统计
        counter: dict[str, int] = defaultdict(int)
        for m in matches:
            counter[m] += 1

        # 排序并限制
        sorted_matches = sorted(counter.items(), key=lambda x: x[1], reverse=True)[:limit]

        return json.dumps({
            "pattern_type": pattern_type,
            "pattern": pattern,
            "unique_count": len(counter),
            "total_count": len(matches),
            "matches": [{"value": v, "count": c} for v, c in sorted_matches]
        }, ensure_ascii=False, indent=2)


class CompareTimePeriodsTool:
    """时间段对比工具"""

    @staticmethod
    def create() -> Tool:
        return Tool(
            name="compare_time_periods",
            description="对比两个时间段的请求数据，分析性能变化和异常",
            func=CompareTimePeriodsTool.execute,
            parameters={
                "period1_start": {
                    "type": "string",
                    "description": "第一个时间段开始时间（ISO格式）"
                },
                "period1_end": {
                    "type": "string",
                    "description": "第一个时间段结束时间"
                },
                "period2_start": {
                    "type": "string",
                    "description": "第二个时间段开始时间"
                },
                "period2_end": {
                    "type": "string",
                    "description": "第二个时间段结束时间"
                }
            },
            required_params=["period1_start", "period1_end", "period2_start", "period2_end"],
            return_type="时间段对比结果（JSON格式）",
            tags=["comparison", "analysis"]
        )

    @staticmethod
    def execute(
        requests: list[dict[str, Any]] | None = None,
        period1_start: str = "",
        period1_end: str = "",
        period2_start: str = "",
        period2_end: str = "",
        **kwargs: Any
    ) -> str:
        """对比时间段"""
        if requests is None:
            requests = kwargs.get("_context", {}).get("requests", [])

        if not requests:
            return json.dumps({"error": "无请求数据"})

        def filter_by_time(reqs: list, start: str, end: str) -> list:
            """按时间过滤"""
            filtered = []
            for r in reqs:
                ts = r.get("timestamp", "")
                if ts and start <= ts <= end:
                    filtered.append(r)
            return filtered

        def calc_metrics(reqs: list) -> dict:
            """计算指标"""
            if not reqs:
                return {"count": 0}

            response_times = [r.get("response_time_ms", 0) for r in reqs if r.get("response_time_ms", 0) > 0]
            errors = sum(1 for r in reqs if r.get("has_error") or r.get("http_status", 0) >= 400)

            result = {
                "count": len(reqs),
                "error_count": errors,
                "error_rate": round(errors / len(reqs), 4) if reqs else 0,
            }

            if response_times:
                response_times.sort()
                n = len(response_times)
                result["avg_response_time_ms"] = round(sum(response_times) / n, 2)
                result["p90_response_time_ms"] = round(response_times[int(n * 0.9)], 2)

            return result

        period1 = filter_by_time(requests, period1_start, period1_end)
        period2 = filter_by_time(requests, period2_start, period2_end)

        metrics1 = calc_metrics(period1)
        metrics2 = calc_metrics(period2)

        # 计算变化
        changes = {}
        for key in ["count", "error_rate", "avg_response_time_ms", "p90_response_time_ms"]:
            v1 = metrics1.get(key, 0)
            v2 = metrics2.get(key, 0)
            if v1 and v1 != 0:
                changes[key] = {
                    "absolute": round(v2 - v1, 2),
                    "percentage": round((v2 - v1) / v1 * 100, 2)
                }

        return json.dumps({
            "period1": {
                "start": period1_start,
                "end": period1_end,
                "metrics": metrics1
            },
            "period2": {
                "start": period2_start,
                "end": period2_end,
                "metrics": metrics2
            },
            "changes": changes,
            "analysis": CompareTimePeriodsTool._analyze_changes(changes)
        }, ensure_ascii=False, indent=2)

    @staticmethod
    def _analyze_changes(changes: dict) -> list[str]:
        """分析变化"""
        analysis = []

        if "error_rate" in changes:
            pct = changes["error_rate"]["percentage"]
            if pct > 50:
                analysis.append(f"错误率显著上升 {pct}%，需要关注")
            elif pct < -30:
                analysis.append(f"错误率下降 {abs(pct)}%，情况改善")

        if "avg_response_time_ms" in changes:
            pct = changes["avg_response_time_ms"]["percentage"]
            if pct > 30:
                analysis.append(f"平均响应时间上升 {pct}%，性能下降")
            elif pct < -20:
                analysis.append(f"平均响应时间下降 {abs(pct)}%，性能改善")

        if "p90_response_time_ms" in changes:
            pct = changes["p90_response_time_ms"]["percentage"]
            if pct > 50:
                analysis.append(f"P90响应时间上升 {pct}%，长尾延迟恶化")

        if not analysis:
            analysis.append("两个时间段的指标相近，无明显变化")

        return analysis


def register_builtin_tools() -> None:
    """注册所有内置工具"""
    registry = get_tool_registry()

    builtin_tools = [
        SearchLogsTool.create(),
        FilterRequestsTool.create(),
        CalculateStatsTool.create(),
        ExtractPatternsTool.create(),
        CompareTimePeriodsTool.create(),
    ]

    for tool in builtin_tools:
        registry.register(tool)

    logger.info(f"注册了 {len(builtin_tools)} 个内置工具")


# 模块加载时自动注册内置工具
register_builtin_tools()
