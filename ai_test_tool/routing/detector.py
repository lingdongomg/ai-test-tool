"""
场景识别器

基于关键词/模式匹配/LLM分类识别分析场景
"""

import re
import logging
from typing import Any
from dataclasses import dataclass, field

from .models import (
    AnalysisScenario,
    ScenarioType,
    ScenarioIndicator,
    MatchMethod,
)

logger = logging.getLogger(__name__)


@dataclass
class DetectionRule:
    """检测规则"""
    scenario_type: ScenarioType
    keywords: list[str] = field(default_factory=list)       # 关键词列表
    patterns: list[str] = field(default_factory=list)       # 正则模式列表
    threshold_conditions: dict[str, tuple[str, float]] = field(default_factory=dict)  # 阈值条件 {指标: (操作符, 值)}
    weight: float = 1.0                                     # 规则权重
    description: str = ""

    def __post_init__(self):
        # 编译正则表达式
        self._compiled_patterns = [
            re.compile(p, re.IGNORECASE | re.MULTILINE)
            for p in self.patterns
        ]


class ScenarioDetector:
    """
    场景识别器

    功能：
    1. 关键词匹配：基于预定义关键词识别场景
    2. 模式匹配：使用正则表达式匹配日志模式
    3. 阈值检测：基于统计指标判断场景
    4. LLM分类：使用LLM进行智能场景分类
    5. 组合匹配：综合多种方法得出最终结果
    """

    # 内置检测规则
    DEFAULT_RULES: list[DetectionRule] = [
        # 错误分析场景
        DetectionRule(
            scenario_type=ScenarioType.ERROR_ANALYSIS,
            keywords=[
                "error", "错误", "exception", "异常", "failed", "失败",
                "failure", "crash", "崩溃", "fatal", "严重"
            ],
            patterns=[
                r"\b(ERROR|FATAL|CRITICAL)\b",
                r"(?i)(exception|error)\s*[:：]",
                r"(?i)(failed|failure)\s+to",
                r"(?i)status[=:\s]+[45]\d{2}",
                r"Traceback \(most recent call last\)",
                r"at .+\(.+:\d+\)",  # Java stack trace
            ],
            threshold_conditions={
                "error_rate": (">=", 0.1),      # 错误率 >= 10%
                "5xx_rate": (">=", 0.05),       # 5xx >= 5%
            },
            weight=1.2,
            description="错误和异常分析"
        ),

        # 性能分析场景
        DetectionRule(
            scenario_type=ScenarioType.PERFORMANCE_ANALYSIS,
            keywords=[
                "slow", "慢", "timeout", "超时", "latency", "延迟",
                "performance", "性能", "响应时间", "response time"
            ],
            patterns=[
                r"(?i)(slow|timeout|timed?\s*out)",
                r"(?i)latency[=:\s]+\d+",
                r"(?i)response[_\s]*time[=:\s]+\d+",
                r"\d{4,}ms",  # 4位数以上的毫秒数
            ],
            threshold_conditions={
                "p99_latency_ms": (">=", 3000),    # P99 >= 3s
                "avg_latency_ms": (">=", 1000),    # 平均延迟 >= 1s
                "slow_request_rate": (">=", 0.1), # 慢请求率 >= 10%
            },
            weight=1.0,
            description="性能和延迟分析"
        ),

        # 安全分析场景
        DetectionRule(
            scenario_type=ScenarioType.SECURITY_ANALYSIS,
            keywords=[
                "security", "安全", "attack", "攻击", "injection", "注入",
                "xss", "csrf", "unauthorized", "越权", "forbidden", "禁止"
            ],
            patterns=[
                r"(?i)(sql|command|code)\s*injection",
                r"(?i)(xss|csrf|xxe|ssrf)",
                r"(?i)(unauthorized|forbidden|access\s*denied)",
                r"(?i)(brute\s*force|too\s*many\s*attempts)",
                r"(?i)(invalid|expired)\s*token",
                r"<script[^>]*>",  # XSS payload
                r"(?i)(union\s+select|or\s+1\s*=\s*1)",  # SQL injection
            ],
            threshold_conditions={
                "4xx_rate": (">=", 0.2),        # 4xx >= 20%
                "auth_failure_rate": (">=", 0.1),
            },
            weight=1.5,  # 安全场景优先级更高
            description="安全威胁分析"
        ),

        # 业务分析场景
        DetectionRule(
            scenario_type=ScenarioType.BUSINESS_ANALYSIS,
            keywords=[
                "业务", "business", "订单", "order", "支付", "payment",
                "用户", "user", "转化", "conversion"
            ],
            patterns=[
                r"(?i)/api/(v\d+/)?(order|payment|user|product)",
                r"(?i)(order|payment|transaction)_id",
            ],
            weight=0.8,
            description="业务流程分析"
        ),

        # 异常检测场景
        DetectionRule(
            scenario_type=ScenarioType.ANOMALY_DETECTION,
            keywords=[
                "anomaly", "异常", "spike", "突增", "drop", "骤降",
                "unusual", "异常波动"
            ],
            patterns=[
                r"(?i)(spike|surge|drop|plunge)",
                r"(?i)(anomal|unusual|abnormal)",
            ],
            threshold_conditions={
                "traffic_change_rate": (">=", 0.5),   # 流量变化 >= 50%
                "error_spike_rate": (">=", 2.0),     # 错误突增 >= 2倍
            },
            weight=1.0,
            description="异常模式检测"
        ),

        # API覆盖率分析
        DetectionRule(
            scenario_type=ScenarioType.API_COVERAGE,
            keywords=[
                "coverage", "覆盖", "未覆盖", "uncovered", "missing", "缺失"
            ],
            patterns=[
                r"(?i)(api|endpoint)\s*(coverage|覆盖)",
            ],
            weight=0.6,
            description="API覆盖率分析"
        ),

        # 流量分析场景
        DetectionRule(
            scenario_type=ScenarioType.TRAFFIC_ANALYSIS,
            keywords=[
                "traffic", "流量", "qps", "请求量", "并发", "concurrent"
            ],
            patterns=[
                r"(?i)(qps|tps|rps)[=:\s]+\d+",
                r"(?i)requests?[/\s]*(per\s*)?(second|sec|s)",
            ],
            threshold_conditions={
                "request_count": (">=", 1000),
            },
            weight=0.7,
            description="流量统计分析"
        ),

        # 根因分析场景
        DetectionRule(
            scenario_type=ScenarioType.ROOT_CAUSE,
            keywords=[
                "root cause", "根因", "原因", "why", "为什么", "排查", "定位"
            ],
            patterns=[
                r"(?i)(root\s*cause|根因|根本原因)",
                r"(?i)(diagnos|troubleshoot|排查|定位)",
            ],
            weight=1.1,
            description="根因定位分析"
        ),

        # 健康检查场景
        DetectionRule(
            scenario_type=ScenarioType.HEALTH_CHECK,
            keywords=[
                "health", "健康", "状态", "status", "alive", "存活"
            ],
            patterns=[
                r"(?i)/health",
                r"(?i)(health\s*check|健康检查)",
            ],
            weight=0.5,
            description="服务健康检查"
        ),
    ]

    def __init__(
        self,
        llm_provider: Any = None,
        custom_rules: list[DetectionRule] | None = None,
        enable_llm_fallback: bool = True,
        min_confidence: float = 0.3
    ):
        """
        初始化场景识别器

        Args:
            llm_provider: LLM提供者（用于智能分类）
            custom_rules: 自定义检测规则
            enable_llm_fallback: 低置信度时是否使用LLM
            min_confidence: 最低置信度阈值
        """
        self.llm_provider = llm_provider
        self.enable_llm_fallback = enable_llm_fallback
        self.min_confidence = min_confidence

        # 合并默认规则和自定义规则
        self.rules = list(self.DEFAULT_RULES)
        if custom_rules:
            self.rules.extend(custom_rules)

        # 编译所有规则的正则表达式
        for rule in self.rules:
            if not hasattr(rule, '_compiled_patterns'):
                rule._compiled_patterns = [
                    re.compile(p, re.IGNORECASE | re.MULTILINE)
                    for p in rule.patterns
                ]

    def detect(
        self,
        log_content: str = "",
        requests: list[dict[str, Any]] | None = None,
        metrics: dict[str, float] | None = None,
        user_hint: str = ""
    ) -> list[AnalysisScenario]:
        """
        检测分析场景

        Args:
            log_content: 日志内容
            requests: 解析后的请求列表
            metrics: 统计指标
            user_hint: 用户提示（如"分析错误"）

        Returns:
            检测到的场景列表（按置信度排序）
        """
        scenarios: list[AnalysisScenario] = []

        # 1. 基于用户提示的检测（最高优先级）
        if user_hint:
            hint_scenarios = self._detect_from_hint(user_hint)
            scenarios.extend(hint_scenarios)

        # 2. 基于日志内容的检测
        if log_content:
            content_scenarios = self._detect_from_content(log_content)
            scenarios.extend(content_scenarios)

        # 3. 基于请求数据的检测
        if requests:
            request_scenarios = self._detect_from_requests(requests)
            scenarios.extend(request_scenarios)

        # 4. 基于指标的检测
        if metrics:
            metric_scenarios = self._detect_from_metrics(metrics)
            scenarios.extend(metric_scenarios)

        # 5. 合并同类场景
        merged = self._merge_scenarios(scenarios)

        # 6. LLM增强（可选）
        if self.enable_llm_fallback and self.llm_provider:
            merged = self._enhance_with_llm(merged, log_content, user_hint)

        # 7. 过滤低置信度场景
        filtered = [s for s in merged if s.confidence >= self.min_confidence]

        # 8. 排序（按置信度降序）
        filtered.sort(key=lambda s: s.confidence, reverse=True)

        logger.debug(f"检测到 {len(filtered)} 个场景: {[s.scenario_type.value for s in filtered]}")

        return filtered

    def _detect_from_hint(self, hint: str) -> list[AnalysisScenario]:
        """基于用户提示检测场景"""
        scenarios: list[AnalysisScenario] = []
        hint_lower = hint.lower()

        for rule in self.rules:
            # 检查关键词
            keyword_hits = sum(
                1 for kw in rule.keywords
                if kw.lower() in hint_lower
            )

            if keyword_hits > 0:
                # 用户明确提示，给予较高置信度
                confidence = min(0.9, 0.6 + keyword_hits * 0.1)
                scenarios.append(AnalysisScenario(
                    scenario_type=rule.scenario_type,
                    confidence=confidence,
                    match_method=MatchMethod.KEYWORD,
                    description=f"用户提示匹配: {hint[:50]}",
                    indicators=[
                        ScenarioIndicator(
                            name="hint_keyword_hits",
                            value=keyword_hits / len(rule.keywords),
                            source="user_hint"
                        )
                    ]
                ))

        return scenarios

    def _detect_from_content(self, content: str) -> list[AnalysisScenario]:
        """基于日志内容检测场景"""
        scenarios: list[AnalysisScenario] = []
        content_lower = content.lower()
        content_len = len(content)

        for rule in self.rules:
            indicators: list[ScenarioIndicator] = []
            total_score = 0.0

            # 1. 关键词匹配
            keyword_hits = 0
            for kw in rule.keywords:
                count = content_lower.count(kw.lower())
                if count > 0:
                    keyword_hits += min(count, 10)  # 限制单个关键词贡献

            if keyword_hits > 0:
                keyword_score = min(1.0, keyword_hits / (len(rule.keywords) * 3))
                total_score += keyword_score * 0.4
                indicators.append(ScenarioIndicator(
                    name="keyword_match",
                    value=keyword_score,
                    weight=0.4,
                    source="content"
                ))

            # 2. 正则模式匹配
            pattern_hits = 0
            for pattern in rule._compiled_patterns:
                matches = pattern.findall(content)
                pattern_hits += len(matches)

            if pattern_hits > 0:
                pattern_score = min(1.0, pattern_hits / 10)
                total_score += pattern_score * 0.6
                indicators.append(ScenarioIndicator(
                    name="pattern_match",
                    value=pattern_score,
                    weight=0.6,
                    source="content"
                ))

            # 应用规则权重
            final_score = total_score * rule.weight

            if final_score > 0:
                scenarios.append(AnalysisScenario(
                    scenario_type=rule.scenario_type,
                    confidence=min(1.0, final_score),
                    match_method=MatchMethod.PATTERN if pattern_hits > keyword_hits else MatchMethod.KEYWORD,
                    description=rule.description,
                    indicators=indicators
                ))

        return scenarios

    def _detect_from_requests(self, requests: list[dict[str, Any]]) -> list[AnalysisScenario]:
        """基于请求数据检测场景"""
        if not requests:
            return []

        scenarios: list[AnalysisScenario] = []
        total = len(requests)

        # 计算统计指标
        error_count = sum(1 for r in requests if r.get('has_error'))
        warning_count = sum(1 for r in requests if r.get('has_warning'))
        status_codes = [r.get('http_status', 0) for r in requests]
        response_times = [r.get('response_time_ms', 0) for r in requests if r.get('response_time_ms')]

        error_rate = error_count / total if total > 0 else 0
        warning_rate = warning_count / total if total > 0 else 0
        status_5xx_count = sum(1 for s in status_codes if s >= 500)
        status_4xx_count = sum(1 for s in status_codes if 400 <= s < 500)
        rate_5xx = status_5xx_count / total if total > 0 else 0
        rate_4xx = status_4xx_count / total if total > 0 else 0

        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        slow_count = sum(1 for t in response_times if t > 3000)
        slow_rate = slow_count / len(response_times) if response_times else 0

        # 错误分析场景
        if error_rate > 0.05 or rate_5xx > 0.02:
            scenarios.append(AnalysisScenario(
                scenario_type=ScenarioType.ERROR_ANALYSIS,
                confidence=min(1.0, error_rate + rate_5xx * 2),
                match_method=MatchMethod.THRESHOLD,
                description=f"错误率 {error_rate:.1%}, 5xx率 {rate_5xx:.1%}",
                indicators=[
                    ScenarioIndicator(name="error_rate", value=error_rate, source="requests"),
                    ScenarioIndicator(name="5xx_rate", value=rate_5xx, source="requests"),
                ],
                metadata={"error_count": error_count, "5xx_count": status_5xx_count}
            ))

        # 性能分析场景
        if avg_response_time > 1000 or slow_rate > 0.1:
            scenarios.append(AnalysisScenario(
                scenario_type=ScenarioType.PERFORMANCE_ANALYSIS,
                confidence=min(1.0, slow_rate + (avg_response_time / 5000)),
                match_method=MatchMethod.THRESHOLD,
                description=f"平均响应时间 {avg_response_time:.0f}ms, 慢请求率 {slow_rate:.1%}",
                indicators=[
                    ScenarioIndicator(name="avg_latency_ms", value=avg_response_time / 5000, source="requests"),
                    ScenarioIndicator(name="slow_rate", value=slow_rate, source="requests"),
                ],
                metadata={"avg_response_time_ms": avg_response_time, "slow_count": slow_count}
            ))

        # 安全分析场景
        if rate_4xx > 0.15:
            scenarios.append(AnalysisScenario(
                scenario_type=ScenarioType.SECURITY_ANALYSIS,
                confidence=min(0.8, rate_4xx),
                match_method=MatchMethod.THRESHOLD,
                description=f"4xx错误率 {rate_4xx:.1%}",
                indicators=[
                    ScenarioIndicator(name="4xx_rate", value=rate_4xx, source="requests"),
                ],
                metadata={"4xx_count": status_4xx_count}
            ))

        # 流量分析场景
        if total >= 100:
            scenarios.append(AnalysisScenario(
                scenario_type=ScenarioType.TRAFFIC_ANALYSIS,
                confidence=min(0.6, total / 1000),
                match_method=MatchMethod.THRESHOLD,
                description=f"请求数量 {total}",
                indicators=[
                    ScenarioIndicator(name="request_count", value=min(1.0, total / 1000), source="requests"),
                ],
                metadata={"total_requests": total}
            ))

        return scenarios

    def _detect_from_metrics(self, metrics: dict[str, float]) -> list[AnalysisScenario]:
        """基于指标检测场景"""
        scenarios: list[AnalysisScenario] = []

        for rule in self.rules:
            if not rule.threshold_conditions:
                continue

            indicators: list[ScenarioIndicator] = []
            matched_conditions = 0

            for metric_name, (operator, threshold) in rule.threshold_conditions.items():
                if metric_name not in metrics:
                    continue

                value = metrics[metric_name]
                matched = False

                if operator == ">=" and value >= threshold:
                    matched = True
                elif operator == ">" and value > threshold:
                    matched = True
                elif operator == "<=" and value <= threshold:
                    matched = True
                elif operator == "<" and value < threshold:
                    matched = True
                elif operator == "==" and value == threshold:
                    matched = True

                if matched:
                    matched_conditions += 1
                    indicators.append(ScenarioIndicator(
                        name=metric_name,
                        value=value / threshold if threshold > 0 else value,
                        source="metrics"
                    ))

            if matched_conditions > 0:
                confidence = matched_conditions / len(rule.threshold_conditions) * rule.weight
                scenarios.append(AnalysisScenario(
                    scenario_type=rule.scenario_type,
                    confidence=min(1.0, confidence),
                    match_method=MatchMethod.THRESHOLD,
                    description=rule.description,
                    indicators=indicators
                ))

        return scenarios

    def _merge_scenarios(self, scenarios: list[AnalysisScenario]) -> list[AnalysisScenario]:
        """合并同类场景"""
        merged: dict[ScenarioType, AnalysisScenario] = {}

        for scenario in scenarios:
            if scenario.scenario_type not in merged:
                merged[scenario.scenario_type] = scenario
            else:
                existing = merged[scenario.scenario_type]
                # 合并置信度（取加权平均，但不超过1）
                new_confidence = min(1.0, (existing.confidence + scenario.confidence) * 0.6)
                # 合并指标
                all_indicators = existing.indicators + scenario.indicators
                # 更新
                merged[scenario.scenario_type] = AnalysisScenario(
                    scenario_type=scenario.scenario_type,
                    confidence=new_confidence,
                    match_method=MatchMethod.COMPOSITE,
                    description=existing.description or scenario.description,
                    indicators=all_indicators,
                    metadata={**existing.metadata, **scenario.metadata}
                )

        return list(merged.values())

    def _enhance_with_llm(
        self,
        scenarios: list[AnalysisScenario],
        content: str,
        hint: str
    ) -> list[AnalysisScenario]:
        """使用LLM增强场景识别"""
        if not self.llm_provider:
            return scenarios

        # 如果已有高置信度场景，不需要LLM
        if scenarios and scenarios[0].confidence >= 0.7:
            return scenarios

        try:
            # 构建 LLM 提示
            scenario_types = [st.value for st in ScenarioType]
            prompt = f"""分析以下内容，判断最可能的分析场景类型。

可选场景类型：
{', '.join(scenario_types)}

用户提示：{hint}

内容摘要（前500字符）：
{content[:500]}

请以JSON格式返回，包含：
- scenario_type: 场景类型（必须是上述类型之一）
- confidence: 置信度（0.0-1.0）
- reason: 判断理由

只返回JSON，不要其他内容。"""

            # 调用 LLM
            llm_response = self.llm_provider.generate(prompt)

            # 解析响应
            import json
            # 尝试从响应中提取 JSON
            response_text = llm_response.strip()
            if response_text.startswith('```'):
                # 移除代码块标记
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
                response_text = response_text.strip()

            result = json.loads(response_text)
            scenario_type_str = result.get('scenario_type', '')
            confidence = float(result.get('confidence', 0.5))
            reason = result.get('reason', '')

            # 验证场景类型
            try:
                scenario_type = ScenarioType(scenario_type_str)
            except ValueError:
                logger.warning(f"LLM返回了无效的场景类型: {scenario_type_str}")
                return scenarios

            # 创建 LLM 识别的场景
            llm_scenario = AnalysisScenario(
                scenario_type=scenario_type,
                confidence=confidence,
                match_method=MatchMethod.LLM,
                description=reason,
                indicators=[ScenarioIndicator(
                    name="llm_classification",
                    value=scenario_type_str,
                    weight=confidence
                )],
                metadata={"llm_reason": reason}
            )

            # 合并结果：LLM 结果与现有结果
            if scenarios:
                # 如果 LLM 结果与现有最高置信度场景类型相同，增强置信度
                if scenarios[0].scenario_type == scenario_type:
                    scenarios[0].confidence = min(0.95, scenarios[0].confidence + confidence * 0.3)
                    scenarios[0].indicators.extend(llm_scenario.indicators)
                    return scenarios
                # 否则，将 LLM 结果添加到列表并重新排序
                scenarios.append(llm_scenario)
                scenarios.sort(key=lambda s: s.confidence, reverse=True)
            else:
                scenarios = [llm_scenario]

            return scenarios

        except json.JSONDecodeError as e:
            logger.warning(f"LLM响应JSON解析失败: {e}")
            return scenarios
        except Exception as e:
            logger.warning(f"LLM场景分类失败: {e}")
            return scenarios

    def add_rule(self, rule: DetectionRule) -> None:
        """添加自定义规则"""
        rule._compiled_patterns = [
            re.compile(p, re.IGNORECASE | re.MULTILINE)
            for p in rule.patterns
        ]
        self.rules.append(rule)

    def remove_rule(self, scenario_type: ScenarioType) -> int:
        """移除指定场景类型的规则"""
        original_count = len(self.rules)
        self.rules = [r for r in self.rules if r.scenario_type != scenario_type]
        return original_count - len(self.rules)
