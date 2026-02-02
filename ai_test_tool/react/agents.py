"""
预定义ReAct Agent

提供针对特定场景优化的Agent模板
"""

from typing import Any

from .models import ReActConfig, ReActResult, Tool
from .engine import ReActEngine
from .tools import get_tool_registry
from ..llm.provider import LLMProvider


class BaseAgent:
    """Agent基类"""

    # 子类可覆盖
    AGENT_NAME = "base_agent"
    AGENT_DESCRIPTION = "基础Agent"
    DEFAULT_MAX_ITERATIONS = 8

    # 系统提示模板
    SYSTEM_PROMPT_TEMPLATE = ""

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        config: ReActConfig | None = None
    ):
        """
        初始化Agent

        Args:
            llm_provider: LLM提供者
            config: 配置
        """
        if config is None:
            config = ReActConfig(max_iterations=self.DEFAULT_MAX_ITERATIONS)

        self.engine = ReActEngine(
            llm_provider=llm_provider,
            config=config
        )

        # 注册Agent特有工具
        self._register_tools()

    def _register_tools(self) -> None:
        """注册Agent特有的工具（子类可覆盖）"""
        pass

    def run(
        self,
        task: str,
        log_content: str = "",
        requests: list[dict[str, Any]] | None = None,
        **kwargs: Any
    ) -> ReActResult:
        """
        执行Agent任务

        Args:
            task: 任务描述
            log_content: 日志内容
            requests: 请求数据
            **kwargs: 其他参数

        Returns:
            执行结果
        """
        return self.engine.run(
            task=task,
            log_content=log_content,
            requests=requests,
            **kwargs
        )


class LogAnalysisAgent(BaseAgent):
    """
    日志分析Agent

    专门用于分析日志内容，识别错误、异常模式等

    擅长任务：
    - 错误定位和诊断
    - 异常模式识别
    - 日志关联分析
    - 根因追溯
    """

    AGENT_NAME = "log_analysis_agent"
    AGENT_DESCRIPTION = "日志分析专家，擅长从日志中提取信息、定位问题"
    DEFAULT_MAX_ITERATIONS = 10

    def _register_tools(self) -> None:
        """注册日志分析相关工具"""
        # 添加一个汇总分析工具
        self.engine.register_tool(Tool(
            name="summarize_findings",
            description="汇总当前发现的所有问题和线索，生成结构化报告",
            func=self._summarize_findings,
            parameters={
                "findings": {
                    "type": "array",
                    "description": "发现的问题列表"
                }
            },
            required_params=["findings"],
            return_type="结构化的发现汇总",
            tags=["summary", "report"]
        ))

    @staticmethod
    def _summarize_findings(findings: list[str], **kwargs: Any) -> str:
        """汇总发现"""
        import json
        return json.dumps({
            "total_findings": len(findings),
            "findings": findings,
            "summary": "已汇总所有发现"
        }, ensure_ascii=False, indent=2)


class PerformanceDebugAgent(BaseAgent):
    """
    性能调试Agent

    专门用于分析性能问题，定位瓶颈

    擅长任务：
    - 响应时间分析
    - 慢请求定位
    - 性能瓶颈识别
    - 资源使用分析
    """

    AGENT_NAME = "performance_debug_agent"
    AGENT_DESCRIPTION = "性能调试专家，擅长分析响应时间、定位性能瓶颈"
    DEFAULT_MAX_ITERATIONS = 8

    def _register_tools(self) -> None:
        """注册性能分析工具"""
        self.engine.register_tool(Tool(
            name="analyze_slow_requests",
            description="深入分析慢请求，识别共同特征",
            func=self._analyze_slow_requests,
            parameters={
                "threshold_ms": {
                    "type": "integer",
                    "description": "慢请求阈值（毫秒），默认3000"
                },
                "top_n": {
                    "type": "integer",
                    "description": "返回最慢的N个请求，默认10"
                }
            },
            required_params=[],
            return_type="慢请求分析结果",
            tags=["performance", "slow"]
        ))

        self.engine.register_tool(Tool(
            name="find_performance_anomalies",
            description="检测性能异常，如突然的响应时间飙升",
            func=self._find_anomalies,
            parameters={},
            required_params=[],
            return_type="异常检测结果",
            tags=["performance", "anomaly"]
        ))

    @staticmethod
    def _analyze_slow_requests(
        requests: list[dict[str, Any]] | None = None,
        threshold_ms: int = 3000,
        top_n: int = 10,
        **kwargs: Any
    ) -> str:
        """分析慢请求"""
        import json
        from collections import defaultdict

        if requests is None:
            requests = kwargs.get("_context", {}).get("requests", [])

        if not requests:
            return json.dumps({"error": "无请求数据"})

        # 筛选慢请求
        slow = [
            r for r in requests
            if r.get("response_time_ms", 0) >= threshold_ms
        ]

        if not slow:
            return json.dumps({
                "message": f"没有响应时间超过 {threshold_ms}ms 的请求",
                "threshold_ms": threshold_ms
            })

        # 排序并取top
        slow.sort(key=lambda x: x.get("response_time_ms", 0), reverse=True)
        top_slow = slow[:top_n]

        # 分析共同特征
        endpoint_counts: dict[str, int] = defaultdict(int)
        for r in slow:
            endpoint = r.get("url", "").split("?")[0]
            endpoint_counts[endpoint] += 1

        top_endpoints = sorted(endpoint_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        return json.dumps({
            "threshold_ms": threshold_ms,
            "total_slow_requests": len(slow),
            "top_slow_requests": [
                {
                    "url": r.get("url", ""),
                    "method": r.get("method", ""),
                    "response_time_ms": r.get("response_time_ms", 0),
                    "timestamp": r.get("timestamp", "")
                }
                for r in top_slow
            ],
            "frequently_slow_endpoints": [
                {"endpoint": ep, "slow_count": cnt}
                for ep, cnt in top_endpoints
            ],
            "analysis": f"共 {len(slow)} 个慢请求，最慢的接口是 {top_endpoints[0][0] if top_endpoints else 'N/A'}"
        }, ensure_ascii=False, indent=2)

    @staticmethod
    def _find_anomalies(
        requests: list[dict[str, Any]] | None = None,
        **kwargs: Any
    ) -> str:
        """检测性能异常"""
        import json
        from collections import defaultdict

        if requests is None:
            requests = kwargs.get("_context", {}).get("requests", [])

        if not requests:
            return json.dumps({"error": "无请求数据"})

        # 按时间窗口分组计算平均响应时间
        # 简化实现：按请求顺序分组
        window_size = max(len(requests) // 10, 5)
        windows = []

        for i in range(0, len(requests), window_size):
            window = requests[i:i + window_size]
            times = [r.get("response_time_ms", 0) for r in window if r.get("response_time_ms", 0) > 0]
            if times:
                windows.append({
                    "start_index": i,
                    "end_index": i + len(window),
                    "avg_ms": sum(times) / len(times),
                    "count": len(times)
                })

        # 检测异常窗口（与整体均值偏差大于2倍标准差）
        if not windows:
            return json.dumps({"message": "无法计算性能窗口"})

        all_avgs = [w["avg_ms"] for w in windows]
        overall_avg = sum(all_avgs) / len(all_avgs)
        variance = sum((a - overall_avg) ** 2 for a in all_avgs) / len(all_avgs)
        std_dev = variance ** 0.5

        anomalies = []
        for w in windows:
            deviation = abs(w["avg_ms"] - overall_avg)
            if deviation > 2 * std_dev:
                anomalies.append({
                    **w,
                    "deviation": round(deviation, 2),
                    "type": "spike" if w["avg_ms"] > overall_avg else "dip"
                })

        return json.dumps({
            "overall_avg_ms": round(overall_avg, 2),
            "std_dev_ms": round(std_dev, 2),
            "anomaly_count": len(anomalies),
            "anomalies": anomalies[:10],
            "analysis": f"检测到 {len(anomalies)} 个性能异常窗口" if anomalies else "未检测到明显的性能异常"
        }, ensure_ascii=False, indent=2)


class SecurityInvestigationAgent(BaseAgent):
    """
    安全调查Agent

    专门用于调查安全事件，分析潜在威胁

    擅长任务：
    - 攻击检测
    - 异常访问分析
    - 安全事件调查
    - 威胁评估
    """

    AGENT_NAME = "security_investigation_agent"
    AGENT_DESCRIPTION = "安全调查专家，擅长检测攻击、分析安全事件"
    DEFAULT_MAX_ITERATIONS = 10

    def _register_tools(self) -> None:
        """注册安全分析工具"""
        self.engine.register_tool(Tool(
            name="detect_attack_patterns",
            description="检测常见攻击模式，如SQL注入、XSS、暴力破解等",
            func=self._detect_attacks,
            parameters={},
            required_params=[],
            return_type="攻击检测结果",
            tags=["security", "attack"]
        ))

        self.engine.register_tool(Tool(
            name="analyze_suspicious_ips",
            description="分析可疑IP的行为模式",
            func=self._analyze_ips,
            parameters={
                "ip": {
                    "type": "string",
                    "description": "要分析的IP地址（可选，不指定则分析所有可疑IP）"
                }
            },
            required_params=[],
            return_type="IP行为分析结果",
            tags=["security", "ip"]
        ))

    @staticmethod
    def _detect_attacks(
        requests: list[dict[str, Any]] | None = None,
        log_content: str = "",
        **kwargs: Any
    ) -> str:
        """检测攻击模式"""
        import json
        import re

        if requests is None:
            requests = kwargs.get("_context", {}).get("requests", [])
        if not log_content:
            log_content = kwargs.get("_context", {}).get("log_content", "")

        attacks: list[dict] = []

        # 攻击模式
        patterns = [
            (r"(?i)(union\s+select|or\s+1\s*=\s*1|'\s*or\s*')", "SQL注入", "high"),
            (r"<script[^>]*>|javascript:", "XSS攻击", "high"),
            (r"(?i)(\.\.\/|\.\.\\){2,}", "路径遍历", "medium"),
            (r"(?i)(cmd=|exec=|system\()", "命令注入", "critical"),
            (r"\x00|\x0d\x0a|\r\n\r\n", "HTTP走私", "high"),
        ]

        # 检查请求
        for req in requests:
            url = req.get("url", "")
            body = str(req.get("body", ""))
            content = f"{url} {body}"

            for pattern, attack_type, severity in patterns:
                if re.search(pattern, content):
                    attacks.append({
                        "type": attack_type,
                        "severity": severity,
                        "url": url[:200],
                        "method": req.get("method", ""),
                        "evidence": re.search(pattern, content).group(0)[:50]
                    })
                    break

        # 检查日志
        for pattern, attack_type, severity in patterns:
            matches = re.findall(pattern, log_content[:10000])
            if matches:
                attacks.append({
                    "type": attack_type,
                    "severity": severity,
                    "source": "log",
                    "count": len(matches)
                })

        # 检查认证失败
        auth_failures = sum(1 for r in requests if r.get("http_status") in [401, 403])
        if auth_failures > 10:
            attacks.append({
                "type": "可能的暴力破解",
                "severity": "medium",
                "count": auth_failures
            })

        return json.dumps({
            "total_attacks": len(attacks),
            "critical": sum(1 for a in attacks if a.get("severity") == "critical"),
            "high": sum(1 for a in attacks if a.get("severity") == "high"),
            "attacks": attacks[:20],
            "recommendation": "发现严重攻击，建议立即审查" if any(a.get("severity") == "critical" for a in attacks) else "继续监控"
        }, ensure_ascii=False, indent=2)

    @staticmethod
    def _analyze_ips(
        requests: list[dict[str, Any]] | None = None,
        log_content: str = "",
        ip: str = "",
        **kwargs: Any
    ) -> str:
        """分析IP行为"""
        import json
        import re
        from collections import defaultdict

        if requests is None:
            requests = kwargs.get("_context", {}).get("requests", [])
        if not log_content:
            log_content = kwargs.get("_context", {}).get("log_content", "")

        # 从日志和请求中提取IP
        ip_pattern = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
        ips_from_log = re.findall(ip_pattern, log_content[:50000])

        # 统计IP活动
        ip_stats: dict[str, dict] = defaultdict(lambda: {
            "request_count": 0,
            "error_count": 0,
            "unique_urls": set(),
            "methods": set()
        })

        for found_ip in ips_from_log:
            ip_stats[found_ip]["request_count"] += 1

        for req in requests:
            req_ip = req.get("client_ip", "")
            if req_ip:
                ip_stats[req_ip]["request_count"] += 1
                if req.get("has_error") or req.get("http_status", 0) >= 400:
                    ip_stats[req_ip]["error_count"] += 1
                ip_stats[req_ip]["unique_urls"].add(req.get("url", "").split("?")[0])
                ip_stats[req_ip]["methods"].add(req.get("method", ""))

        # 识别可疑IP（高错误率或请求量异常高）
        suspicious = []
        for found_ip, stats in ip_stats.items():
            if ip and found_ip != ip:
                continue

            error_rate = stats["error_count"] / stats["request_count"] if stats["request_count"] > 0 else 0
            is_suspicious = (
                error_rate > 0.5 or  # 高错误率
                stats["request_count"] > 100 or  # 高请求量
                len(stats["unique_urls"]) > 50  # 访问大量不同URL
            )

            if is_suspicious or ip:
                suspicious.append({
                    "ip": found_ip,
                    "request_count": stats["request_count"],
                    "error_count": stats["error_count"],
                    "error_rate": round(error_rate, 2),
                    "unique_urls": len(stats["unique_urls"]),
                    "methods": list(stats["methods"]),
                    "risk_level": "high" if error_rate > 0.7 else "medium"
                })

        suspicious.sort(key=lambda x: x["request_count"], reverse=True)

        return json.dumps({
            "total_unique_ips": len(ip_stats),
            "suspicious_count": len(suspicious),
            "suspicious_ips": suspicious[:20],
            "analysis": f"发现 {len(suspicious)} 个可疑IP" if suspicious else "未发现明显可疑IP"
        }, ensure_ascii=False, indent=2)


class AnomalyHuntingAgent(BaseAgent):
    """
    异常猎手Agent

    主动搜索和识别各类异常，无需明确指定问题

    擅长任务：
    - 异常模式发现
    - 趋势偏离检测
    - 关联分析
    - 主动问题发现
    """

    AGENT_NAME = "anomaly_hunting_agent"
    AGENT_DESCRIPTION = "异常猎手，擅长主动发现和追踪各类异常"
    DEFAULT_MAX_ITERATIONS = 12

    def _register_tools(self) -> None:
        """注册异常检测工具"""
        self.engine.register_tool(Tool(
            name="scan_for_anomalies",
            description="全面扫描数据，检测各类异常",
            func=self._scan_anomalies,
            parameters={
                "focus_area": {
                    "type": "string",
                    "description": "重点关注领域: all, errors, performance, security, patterns"
                }
            },
            required_params=[],
            return_type="异常扫描结果",
            tags=["anomaly", "scan"]
        ))

        self.engine.register_tool(Tool(
            name="correlate_events",
            description="关联分析不同事件，找出潜在联系",
            func=self._correlate_events,
            parameters={
                "event_type": {
                    "type": "string",
                    "description": "事件类型: error, slow_request, auth_failure"
                }
            },
            required_params=["event_type"],
            return_type="事件关联分析结果",
            tags=["correlation", "analysis"]
        ))

    @staticmethod
    def _scan_anomalies(
        requests: list[dict[str, Any]] | None = None,
        log_content: str = "",
        focus_area: str = "all",
        **kwargs: Any
    ) -> str:
        """全面扫描异常"""
        import json
        import re
        from collections import defaultdict

        if requests is None:
            requests = kwargs.get("_context", {}).get("requests", [])
        if not log_content:
            log_content = kwargs.get("_context", {}).get("log_content", "")

        anomalies: list[dict] = []

        # 错误异常
        if focus_area in ("all", "errors"):
            error_count = sum(1 for r in requests if r.get("has_error") or r.get("http_status", 0) >= 400)
            if error_count > 0:
                error_rate = error_count / len(requests) if requests else 0
                if error_rate > 0.1:
                    anomalies.append({
                        "type": "high_error_rate",
                        "severity": "high" if error_rate > 0.3 else "medium",
                        "value": f"{error_rate:.1%}",
                        "description": f"错误率异常高: {error_rate:.1%}"
                    })

        # 性能异常
        if focus_area in ("all", "performance"):
            response_times = [r.get("response_time_ms", 0) for r in requests if r.get("response_time_ms", 0) > 0]
            if response_times:
                avg_rt = sum(response_times) / len(response_times)
                max_rt = max(response_times)
                if avg_rt > 2000:
                    anomalies.append({
                        "type": "high_latency",
                        "severity": "high" if avg_rt > 5000 else "medium",
                        "value": f"{avg_rt:.0f}ms",
                        "description": f"平均响应时间过高: {avg_rt:.0f}ms"
                    })
                if max_rt > 30000:
                    anomalies.append({
                        "type": "extreme_latency",
                        "severity": "high",
                        "value": f"{max_rt:.0f}ms",
                        "description": f"存在极端慢请求: {max_rt:.0f}ms"
                    })

        # 日志模式异常
        if focus_area in ("all", "patterns") and log_content:
            # 检测重复错误
            error_lines = re.findall(r"(?i)(?:error|exception|fatal)[^\n]*", log_content)
            if len(error_lines) > 50:
                anomalies.append({
                    "type": "excessive_errors_in_log",
                    "severity": "high",
                    "value": len(error_lines),
                    "description": f"日志中错误信息过多: {len(error_lines)} 条"
                })

            # 检测堆栈溢出
            if "StackOverflow" in log_content or "OutOfMemory" in log_content:
                anomalies.append({
                    "type": "resource_exhaustion",
                    "severity": "critical",
                    "description": "检测到资源耗尽错误"
                })

        # 安全异常
        if focus_area in ("all", "security"):
            auth_failures = sum(1 for r in requests if r.get("http_status") in [401, 403])
            if auth_failures > 20:
                anomalies.append({
                    "type": "auth_anomaly",
                    "severity": "medium",
                    "value": auth_failures,
                    "description": f"认证失败次数异常: {auth_failures}"
                })

        return json.dumps({
            "scan_area": focus_area,
            "total_anomalies": len(anomalies),
            "critical": sum(1 for a in anomalies if a.get("severity") == "critical"),
            "high": sum(1 for a in anomalies if a.get("severity") == "high"),
            "anomalies": anomalies,
            "recommendation": "需要立即关注" if any(a.get("severity") == "critical" for a in anomalies) else "建议进一步分析"
        }, ensure_ascii=False, indent=2)

    @staticmethod
    def _correlate_events(
        requests: list[dict[str, Any]] | None = None,
        event_type: str = "error",
        **kwargs: Any
    ) -> str:
        """关联分析事件"""
        import json
        from collections import defaultdict

        if requests is None:
            requests = kwargs.get("_context", {}).get("requests", [])

        if not requests:
            return json.dumps({"error": "无请求数据"})

        # 按事件类型筛选
        if event_type == "error":
            events = [r for r in requests if r.get("has_error") or r.get("http_status", 0) >= 400]
        elif event_type == "slow_request":
            events = [r for r in requests if r.get("response_time_ms", 0) > 3000]
        elif event_type == "auth_failure":
            events = [r for r in requests if r.get("http_status") in [401, 403]]
        else:
            events = requests

        if not events:
            return json.dumps({"message": f"未找到 {event_type} 类型事件"})

        # 分析共同特征
        endpoint_dist: dict[str, int] = defaultdict(int)
        method_dist: dict[str, int] = defaultdict(int)
        time_dist: dict[str, int] = defaultdict(int)

        for e in events:
            endpoint_dist[e.get("url", "").split("?")[0]] += 1
            method_dist[e.get("method", "")] += 1
            ts = e.get("timestamp", "")
            if ts:
                hour = ts[11:13] if len(ts) > 13 else "unknown"
                time_dist[f"{hour}:00"] += 1

        top_endpoints = sorted(endpoint_dist.items(), key=lambda x: x[1], reverse=True)[:5]
        top_times = sorted(time_dist.items(), key=lambda x: x[1], reverse=True)[:5]

        # 检测关联
        correlations = []
        if top_endpoints and top_endpoints[0][1] > len(events) * 0.5:
            correlations.append({
                "type": "endpoint_concentration",
                "description": f"事件集中在接口: {top_endpoints[0][0]}",
                "confidence": round(top_endpoints[0][1] / len(events), 2)
            })

        if top_times and top_times[0][1] > len(events) * 0.3:
            correlations.append({
                "type": "time_concentration",
                "description": f"事件集中在时间段: {top_times[0][0]}",
                "confidence": round(top_times[0][1] / len(events), 2)
            })

        return json.dumps({
            "event_type": event_type,
            "event_count": len(events),
            "correlations": correlations,
            "distribution": {
                "by_endpoint": dict(top_endpoints),
                "by_method": dict(method_dist),
                "by_time": dict(top_times)
            },
            "insight": correlations[0]["description"] if correlations else "未发现明显关联模式"
        }, ensure_ascii=False, indent=2)
