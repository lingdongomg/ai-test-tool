"""
健康度评分引擎

执行健康检查、计算健康度评分、生成健康报告
"""

import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable

from .models import (
    HealthMetric,
    ComponentHealth,
    SystemHealth,
    HealthCheckResult,
    HealthConfig,
    HealthReport,
    HealthStatus,
    MetricType,
    TrendDirection,
)

logger = logging.getLogger(__name__)


class HealthScoreEngine:
    """
    健康度评分引擎

    功能：
    1. 管理系统和组件健康状态
    2. 执行健康检查
    3. 计算健康度评分
    4. 生成健康报告
    """

    def __init__(self, config: HealthConfig | None = None):
        """
        初始化引擎

        Args:
            config: 配置
        """
        self.config = config or HealthConfig()
        self.system = SystemHealth()

        # 健康检查函数注册表
        self._health_checks: dict[str, Callable[[], HealthCheckResult]] = {}

        # 历史记录
        self._score_history: list[tuple[datetime, float]] = []

    def register_component(
        self,
        component_id: str,
        name: str,
        component_type: str = "service",
        metrics: list[HealthMetric] | None = None,
        dependencies: list[str] | None = None,
    ) -> ComponentHealth:
        """
        注册组件

        Args:
            component_id: 组件ID
            name: 组件名称
            component_type: 组件类型
            metrics: 初始指标
            dependencies: 依赖组件

        Returns:
            ComponentHealth实例
        """
        component = ComponentHealth(
            component_id=component_id,
            name=name,
            component_type=component_type,
            dependencies=dependencies or [],
        )

        if metrics:
            for metric in metrics:
                component.add_metric(metric)

        self.system.add_component(component)
        return component

    def unregister_component(self, component_id: str) -> bool:
        """注销组件"""
        return self.system.remove_component(component_id)

    def update_metric(
        self,
        component_id: str,
        metric_name: str,
        value: float
    ) -> bool:
        """
        更新组件指标

        Args:
            component_id: 组件ID
            metric_name: 指标名称
            value: 新值

        Returns:
            是否成功
        """
        result = self.system.update_component_metric(
            component_id, metric_name, value
        )

        if result:
            # 记录系统得分历史
            self._record_score()

        return result

    def add_metric(
        self,
        component_id: str,
        metric: HealthMetric
    ) -> bool:
        """
        为组件添加新指标

        Args:
            component_id: 组件ID
            metric: 指标

        Returns:
            是否成功
        """
        component = self.system.get_component(component_id)
        if component:
            component.add_metric(metric)
            self.system._recalculate()
            return True
        return False

    def register_health_check(
        self,
        check_id: str,
        check_func: Callable[[], HealthCheckResult]
    ) -> None:
        """
        注册健康检查函数

        Args:
            check_id: 检查ID
            check_func: 检查函数
        """
        self._health_checks[check_id] = check_func

    def run_health_check(self, check_id: str) -> HealthCheckResult | None:
        """
        运行单个健康检查

        Args:
            check_id: 检查ID

        Returns:
            检查结果
        """
        check_func = self._health_checks.get(check_id)
        if not check_func:
            return None

        start_time = time.time()
        try:
            result = check_func()
            result.duration_ms = (time.time() - start_time) * 1000
            return result
        except Exception as e:
            logger.error(f"健康检查失败 {check_id}: {e}")
            return HealthCheckResult(
                check_id=check_id,
                component_id="",
                success=False,
                status=HealthStatus.UNKNOWN,
                message=str(e),
                duration_ms=(time.time() - start_time) * 1000,
            )

    def run_all_health_checks(self) -> list[HealthCheckResult]:
        """运行所有健康检查"""
        results = []
        for check_id in self._health_checks:
            result = self.run_health_check(check_id)
            if result:
                results.append(result)
        return results

    def calculate_score(
        self,
        component_id: str | None = None
    ) -> float:
        """
        计算健康度评分

        Args:
            component_id: 组件ID（None表示计算系统总分）

        Returns:
            健康度评分（0-100）
        """
        if component_id:
            component = self.system.get_component(component_id)
            return component.score if component else 0
        return self.system.score

    def get_status(
        self,
        component_id: str | None = None
    ) -> HealthStatus:
        """
        获取健康状态

        Args:
            component_id: 组件ID（None表示获取系统状态）

        Returns:
            健康状态
        """
        if component_id:
            component = self.system.get_component(component_id)
            return component.status if component else HealthStatus.UNKNOWN
        return self.system.status

    def _record_score(self) -> None:
        """记录系统得分"""
        self._score_history.append((datetime.now(), self.system.score))

        # 清理过期历史
        cutoff = datetime.now() - timedelta(hours=self.config.history_retention_hours)
        self._score_history = [
            (ts, score) for ts, score in self._score_history
            if ts > cutoff
        ]

    def get_trend(self) -> TrendDirection:
        """获取系统健康趋势"""
        if len(self._score_history) < 3:
            return TrendDirection.UNKNOWN

        recent = [score for _, score in self._score_history[-10:]]
        if len(recent) < 2:
            return TrendDirection.UNKNOWN

        # 计算平均变化
        changes = [recent[i] - recent[i-1] for i in range(1, len(recent))]
        avg_change = sum(changes) / len(changes)

        if avg_change > 2:  # 改善超过2分
            return TrendDirection.IMPROVING
        elif avg_change < -2:  # 恶化超过2分
            return TrendDirection.DEGRADING
        return TrendDirection.STABLE

    def generate_report(self) -> HealthReport:
        """
        生成健康报告

        Returns:
            健康报告
        """
        report = HealthReport(
            report_id=str(uuid.uuid4())[:8],
            system_health=self.system,
            overall_score=self.system.score,
            overall_status=self.system.status,
            trend=self.get_trend(),
            score_history=self._score_history.copy(),
        )

        # 生成摘要
        report.summary = self._generate_summary()

        # 收集问题
        for component in self.system.components.values():
            if component.status in (HealthStatus.UNHEALTHY, HealthStatus.CRITICAL):
                for issue in component.issues:
                    report.add_issue(
                        component=component.name,
                        severity=component.status.value,
                        description=issue,
                        suggestion=self._get_suggestion(component, issue)
                    )

        # 生成建议
        report.recommendations = self._generate_recommendations()

        return report

    def _generate_summary(self) -> str:
        """生成摘要"""
        status = self.system.status.value
        score = self.system.score
        total = self.system.total_components
        critical = self.system.critical_count
        unhealthy = self.system.unhealthy_count

        if status == "healthy":
            return f"系统健康，综合得分 {score:.1f}/100，共 {total} 个组件全部正常"
        elif status == "degraded":
            return f"系统轻微降级，综合得分 {score:.1f}/100，{self.system.degraded_count} 个组件性能下降"
        elif status == "unhealthy":
            return f"系统不健康，综合得分 {score:.1f}/100，{unhealthy} 个组件存在问题"
        else:
            return f"系统严重异常，综合得分 {score:.1f}/100，{critical} 个组件严重故障"

    def _get_suggestion(self, component: ComponentHealth, issue: str) -> str:
        """获取问题建议"""
        issue_lower = issue.lower()

        if "error_rate" in issue_lower or "错误率" in issue_lower:
            return f"检查 {component.name} 的错误日志，排查错误原因"
        elif "latency" in issue_lower or "延迟" in issue_lower:
            return f"检查 {component.name} 的性能瓶颈，考虑扩容或优化"
        elif "availability" in issue_lower or "可用性" in issue_lower:
            return f"检查 {component.name} 的实例健康状态，必要时重启或替换"
        elif "saturation" in issue_lower or "饱和" in issue_lower:
            return f"检查 {component.name} 的资源使用情况，考虑扩容"
        else:
            return f"检查 {component.name} 的监控指标和日志"

    def _generate_recommendations(self) -> list[str]:
        """生成建议列表"""
        recommendations = []

        # 基于系统状态
        if self.system.status == HealthStatus.CRITICAL:
            recommendations.append("立即启动应急响应流程")
            recommendations.append("检查关键服务的可用性")

        # 基于趋势
        trend = self.get_trend()
        if trend == TrendDirection.DEGRADING:
            recommendations.append("系统健康度持续下降，建议排查根因")

        # 基于组件状态
        critical_components = self.system.critical_components
        if critical_components:
            names = [c.name for c in critical_components[:3]]
            recommendations.append(f"优先处理严重问题组件: {', '.join(names)}")

        # 基于依赖关系
        if self.config.include_dependencies:
            for component in self.system.unhealthy_components:
                for dep_id in component.dependencies:
                    dep = self.system.get_component(dep_id)
                    if dep and not dep.is_healthy:
                        recommendations.append(
                            f"{component.name} 依赖的 {dep.name} 也存在问题，"
                            f"建议先解决 {dep.name} 的问题"
                        )

        return recommendations[:10]  # 最多10条建议

    def get_system_health(self) -> dict[str, Any]:
        """获取系统健康状态"""
        return self.system.to_dict()

    def get_component_health(self, component_id: str) -> dict[str, Any] | None:
        """获取组件健康状态"""
        component = self.system.get_component(component_id)
        return component.to_dict() if component else None

    def get_summary(self) -> dict[str, Any]:
        """获取健康摘要"""
        return self.system.get_summary()


# 预定义指标模板

def create_availability_metric(
    name: str = "availability",
    value: float = 100.0,
    warning: float = 99.0,
    critical: float = 95.0,
    weight: float = 2.0,
) -> HealthMetric:
    """创建可用性指标"""
    return HealthMetric(
        name=name,
        value=value,
        metric_type=MetricType.AVAILABILITY,
        threshold_warning=warning,
        threshold_critical=critical,
        weight=weight,
        unit="%",
        description="服务可用性百分比",
    )


def create_latency_metric(
    name: str = "latency_p99",
    value: float = 100.0,
    warning: float = 500.0,
    critical: float = 1000.0,
    weight: float = 1.5,
) -> HealthMetric:
    """创建延迟指标"""
    return HealthMetric(
        name=name,
        value=value,
        metric_type=MetricType.LATENCY,
        threshold_warning=warning,
        threshold_critical=critical,
        weight=weight,
        unit="ms",
        description="P99延迟",
    )


def create_error_rate_metric(
    name: str = "error_rate",
    value: float = 0.0,
    warning: float = 1.0,
    critical: float = 5.0,
    weight: float = 2.0,
) -> HealthMetric:
    """创建错误率指标"""
    return HealthMetric(
        name=name,
        value=value,
        metric_type=MetricType.ERROR_RATE,
        threshold_warning=warning,
        threshold_critical=critical,
        weight=weight,
        unit="%",
        description="请求错误率",
    )


def create_throughput_metric(
    name: str = "throughput",
    value: float = 1000.0,
    warning: float = 500.0,
    critical: float = 100.0,
    weight: float = 1.0,
) -> HealthMetric:
    """创建吞吐量指标"""
    return HealthMetric(
        name=name,
        value=value,
        metric_type=MetricType.THROUGHPUT,
        threshold_warning=warning,
        threshold_critical=critical,
        weight=weight,
        unit="req/s",
        description="请求吞吐量",
    )


def create_saturation_metric(
    name: str = "cpu_saturation",
    value: float = 50.0,
    warning: float = 70.0,
    critical: float = 90.0,
    weight: float = 1.0,
) -> HealthMetric:
    """创建饱和度指标"""
    return HealthMetric(
        name=name,
        value=value,
        metric_type=MetricType.SATURATION,
        threshold_warning=warning,
        threshold_critical=critical,
        weight=weight,
        unit="%",
        description="资源饱和度",
    )


def create_health_engine() -> HealthScoreEngine:
    """
    创建健康度引擎的便捷函数

    Returns:
        HealthScoreEngine实例
    """
    return HealthScoreEngine()
