"""
健康检查器

提供各类健康检查功能
"""

import time
import uuid
from datetime import datetime
from typing import Any, Callable

from .models import (
    HealthCheckResult,
    HealthStatus,
    ComponentHealth,
    HealthMetric,
    MetricType,
)


class HealthChecker:
    """
    健康检查器

    提供组件健康检查功能
    """

    def __init__(self):
        """初始化检查器"""
        # 检查函数注册表
        self._checks: dict[str, dict[str, Any]] = {}

    def register(
        self,
        check_id: str,
        component_id: str,
        check_func: Callable[[], tuple[bool, str, dict[str, Any]]],
        check_type: str = "basic",
        timeout_ms: int = 5000,
    ) -> None:
        """
        注册健康检查

        Args:
            check_id: 检查ID
            component_id: 组件ID
            check_func: 检查函数，返回 (success, message, details)
            check_type: 检查类型
            timeout_ms: 超时时间
        """
        self._checks[check_id] = {
            "component_id": component_id,
            "func": check_func,
            "type": check_type,
            "timeout_ms": timeout_ms,
        }

    def unregister(self, check_id: str) -> bool:
        """注销检查"""
        if check_id in self._checks:
            del self._checks[check_id]
            return True
        return False

    def run(self, check_id: str) -> HealthCheckResult | None:
        """
        执行单个检查

        Args:
            check_id: 检查ID

        Returns:
            检查结果
        """
        check_info = self._checks.get(check_id)
        if not check_info:
            return None

        start_time = time.time()

        try:
            success, message, details = check_info["func"]()
            duration = (time.time() - start_time) * 1000

            # 根据结果确定状态
            if success:
                status = HealthStatus.HEALTHY
            else:
                status = HealthStatus.UNHEALTHY

            return HealthCheckResult(
                check_id=check_id,
                component_id=check_info["component_id"],
                check_type=check_info["type"],
                success=success,
                status=status,
                message=message,
                details=details,
                duration_ms=duration,
            )

        except TimeoutError:
            return HealthCheckResult(
                check_id=check_id,
                component_id=check_info["component_id"],
                check_type=check_info["type"],
                success=False,
                status=HealthStatus.UNHEALTHY,
                message="检查超时",
                duration_ms=check_info["timeout_ms"],
            )

        except Exception as e:
            duration = (time.time() - start_time) * 1000
            return HealthCheckResult(
                check_id=check_id,
                component_id=check_info["component_id"],
                check_type=check_info["type"],
                success=False,
                status=HealthStatus.CRITICAL,
                message=f"检查异常: {str(e)}",
                duration_ms=duration,
            )

    def run_all(self) -> list[HealthCheckResult]:
        """执行所有检查"""
        results = []
        for check_id in self._checks:
            result = self.run(check_id)
            if result:
                results.append(result)
        return results

    def run_for_component(self, component_id: str) -> list[HealthCheckResult]:
        """执行组件的所有检查"""
        results = []
        for check_id, check_info in self._checks.items():
            if check_info["component_id"] == component_id:
                result = self.run(check_id)
                if result:
                    results.append(result)
        return results

    def list_checks(self) -> list[dict[str, str]]:
        """列出所有检查"""
        return [
            {
                "check_id": check_id,
                "component_id": info["component_id"],
                "type": info["type"],
            }
            for check_id, info in self._checks.items()
        ]


# 预定义检查函数

def create_http_check(
    url: str,
    expected_status: int = 200,
    timeout_seconds: float = 5.0,
) -> Callable[[], tuple[bool, str, dict[str, Any]]]:
    """
    创建HTTP健康检查函数

    Args:
        url: 检查URL
        expected_status: 期望状态码
        timeout_seconds: 超时时间

    Returns:
        检查函数
    """
    import urllib.request
    import urllib.error

    def check() -> tuple[bool, str, dict[str, Any]]:
        start = time.time()
        try:
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
                status_code = response.status
                duration = (time.time() - start) * 1000

                success = status_code == expected_status
                message = f"HTTP {status_code}" if success else f"期望 {expected_status}，实际 {status_code}"

                return success, message, {
                    "status_code": status_code,
                    "latency_ms": round(duration, 2),
                    "url": url,
                }
        except urllib.error.URLError as e:
            return False, f"连接失败: {e.reason}", {"url": url, "error": str(e)}
        except Exception as e:
            return False, f"检查失败: {str(e)}", {"url": url, "error": str(e)}

    return check


def create_tcp_check(
    host: str,
    port: int,
    timeout_seconds: float = 5.0,
) -> Callable[[], tuple[bool, str, dict[str, Any]]]:
    """
    创建TCP端口检查函数

    Args:
        host: 主机地址
        port: 端口号
        timeout_seconds: 超时时间

    Returns:
        检查函数
    """
    import socket

    def check() -> tuple[bool, str, dict[str, Any]]:
        start = time.time()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout_seconds)
            result = sock.connect_ex((host, port))
            duration = (time.time() - start) * 1000
            sock.close()

            success = result == 0
            message = "端口可达" if success else f"端口不可达 (错误码: {result})"

            return success, message, {
                "host": host,
                "port": port,
                "latency_ms": round(duration, 2),
            }
        except socket.timeout:
            return False, "连接超时", {"host": host, "port": port}
        except Exception as e:
            return False, f"检查失败: {str(e)}", {"host": host, "port": port}

    return check


def create_threshold_check(
    metric_getter: Callable[[], float],
    metric_name: str,
    warning_threshold: float,
    critical_threshold: float,
    higher_is_worse: bool = True,
) -> Callable[[], tuple[bool, str, dict[str, Any]]]:
    """
    创建阈值检查函数

    Args:
        metric_getter: 获取指标值的函数
        metric_name: 指标名称
        warning_threshold: 警告阈值
        critical_threshold: 严重阈值
        higher_is_worse: 值越高越差

    Returns:
        检查函数
    """
    def check() -> tuple[bool, str, dict[str, Any]]:
        try:
            value = metric_getter()

            if higher_is_worse:
                if value >= critical_threshold:
                    return False, f"{metric_name} 严重: {value}", {
                        "value": value,
                        "threshold": critical_threshold,
                    }
                elif value >= warning_threshold:
                    return True, f"{metric_name} 警告: {value}", {
                        "value": value,
                        "threshold": warning_threshold,
                    }
                else:
                    return True, f"{metric_name} 正常: {value}", {"value": value}
            else:
                if value <= critical_threshold:
                    return False, f"{metric_name} 严重: {value}", {
                        "value": value,
                        "threshold": critical_threshold,
                    }
                elif value <= warning_threshold:
                    return True, f"{metric_name} 警告: {value}", {
                        "value": value,
                        "threshold": warning_threshold,
                    }
                else:
                    return True, f"{metric_name} 正常: {value}", {"value": value}

        except Exception as e:
            return False, f"获取指标失败: {str(e)}", {"error": str(e)}

    return check


def create_custom_check(
    name: str,
    check_logic: Callable[[], bool],
    success_message: str = "检查通过",
    failure_message: str = "检查失败",
) -> Callable[[], tuple[bool, str, dict[str, Any]]]:
    """
    创建自定义检查函数

    Args:
        name: 检查名称
        check_logic: 检查逻辑函数
        success_message: 成功消息
        failure_message: 失败消息

    Returns:
        检查函数
    """
    def check() -> tuple[bool, str, dict[str, Any]]:
        try:
            result = check_logic()
            message = success_message if result else failure_message
            return result, message, {"check_name": name}
        except Exception as e:
            return False, f"检查异常: {str(e)}", {"check_name": name, "error": str(e)}

    return check


class ComponentHealthBuilder:
    """
    组件健康度构建器

    便捷地构建ComponentHealth对象
    """

    def __init__(self, component_id: str, name: str):
        """
        初始化构建器

        Args:
            component_id: 组件ID
            name: 组件名称
        """
        self._component = ComponentHealth(
            component_id=component_id,
            name=name,
        )

    def set_type(self, component_type: str) -> "ComponentHealthBuilder":
        """设置组件类型"""
        self._component.component_type = component_type
        return self

    def add_dependency(self, dep_id: str) -> "ComponentHealthBuilder":
        """添加依赖"""
        self._component.dependencies.append(dep_id)
        return self

    def add_tag(self, key: str, value: str) -> "ComponentHealthBuilder":
        """添加标签"""
        self._component.tags[key] = value
        return self

    def add_availability_metric(
        self,
        value: float = 100.0,
        warning: float = 99.0,
        critical: float = 95.0,
    ) -> "ComponentHealthBuilder":
        """添加可用性指标"""
        self._component.add_metric(HealthMetric(
            name="availability",
            value=value,
            metric_type=MetricType.AVAILABILITY,
            threshold_warning=warning,
            threshold_critical=critical,
            weight=2.0,
            unit="%",
        ))
        return self

    def add_latency_metric(
        self,
        value: float = 100.0,
        warning: float = 500.0,
        critical: float = 1000.0,
    ) -> "ComponentHealthBuilder":
        """添加延迟指标"""
        self._component.add_metric(HealthMetric(
            name="latency_p99",
            value=value,
            metric_type=MetricType.LATENCY,
            threshold_warning=warning,
            threshold_critical=critical,
            weight=1.5,
            unit="ms",
        ))
        return self

    def add_error_rate_metric(
        self,
        value: float = 0.0,
        warning: float = 1.0,
        critical: float = 5.0,
    ) -> "ComponentHealthBuilder":
        """添加错误率指标"""
        self._component.add_metric(HealthMetric(
            name="error_rate",
            value=value,
            metric_type=MetricType.ERROR_RATE,
            threshold_warning=warning,
            threshold_critical=critical,
            weight=2.0,
            unit="%",
        ))
        return self

    def add_custom_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.CUSTOM,
        warning: float | None = None,
        critical: float | None = None,
        weight: float = 1.0,
        unit: str = "",
    ) -> "ComponentHealthBuilder":
        """添加自定义指标"""
        self._component.add_metric(HealthMetric(
            name=name,
            value=value,
            metric_type=metric_type,
            threshold_warning=warning,
            threshold_critical=critical,
            weight=weight,
            unit=unit,
        ))
        return self

    def build(self) -> ComponentHealth:
        """构建组件健康度对象"""
        return self._component
