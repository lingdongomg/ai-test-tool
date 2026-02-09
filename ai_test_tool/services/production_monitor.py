"""
功能2: 线上质量自测库服务
从日志中提取真实用户请求，存储为线上自测库，定时执行检测线上健康状态
"""

import json
import hashlib
import re
from typing import Any
from dataclasses import dataclass, field
from datetime import datetime

from ..database import get_db_manager
from ..llm.chains import ResultValidatorChain
from ..llm.provider import get_llm_provider
from ..utils.logger import get_logger
from ..health.models import HealthStatus
from ..database.models.monitoring import RequestSource


@dataclass
class ProductionRequest:
    """线上请求记录"""
    request_id: str
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    body: str | None = None
    query_params: dict[str, str] = field(default_factory=dict)
    expected_status_code: int = 200
    expected_response_pattern: str | None = None  # 期望响应的正则模式
    source: RequestSource = RequestSource.LOG_PARSE
    tags: list[str] = field(default_factory=list)
    is_enabled: bool = True
    last_check_at: datetime | None = None
    last_check_status: str | None = None
    consecutive_failures: int = 0


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    request_id: str
    success: bool
    status_code: int
    response_time_ms: float
    response_body: str
    error_message: str | None = None
    ai_analysis: dict[str, Any] | None = None
    checked_at: datetime = field(default_factory=datetime.now)


class ProductionMonitorService:
    """
    线上质量监控服务
    
    功能：
    1. 从日志解析真实用户请求，存入自测库
    2. 定时执行这些请求，验证线上接口健康
    3. 使用 AI 判断返回结果是否正常
    4. 异常告警通知
    """
    
    def __init__(self, verbose: bool = False):
        self.logger = get_logger(verbose)
        self.verbose = verbose
        self.db = get_db_manager()
        self._validator_chain: ResultValidatorChain | None = None
    
    @property
    def validator_chain(self) -> ResultValidatorChain:
        """懒加载验证 Chain"""
        if self._validator_chain is None:
            provider = get_llm_provider()
            self._validator_chain = ResultValidatorChain(provider, self.verbose)
        return self._validator_chain
    
    def extract_requests_from_log(
        self,
        task_id: str,
        min_success_rate: float = 0.9,
        max_requests_per_endpoint: int = 5,
        tags: list[str] | None = None
    ) -> dict[str, Any]:
        """
        从日志分析任务中提取请求，存入线上自测库
        
        Args:
            task_id: 分析任务ID
            min_success_rate: 最小成功率过滤（只保留高成功率的请求）
            max_requests_per_endpoint: 每个接口最多保留的请求数
            
        Returns:
            提取统计结果
        """
        self.logger.start_step("提取线上请求到自测库")
        
        # 获取任务中的成功请求
        sql = """
            SELECT * FROM parsed_requests 
            WHERE task_id = %s 
            AND http_status >= 200 AND http_status < 300
            AND has_error = 0
            ORDER BY timestamp DESC
        """
        rows = self.db.fetch_all(sql, (task_id,))
        
        if not rows:
            self.logger.warn("没有找到成功的请求")
            return {"total": 0, "saved": 0, "skipped": 0}
        
        # 按接口分组
        endpoint_groups: dict[str, list[dict]] = {}
        for row in rows:
            key = f"{row['method']}:{self._normalize_url(row['url'])}"
            if key not in endpoint_groups:
                endpoint_groups[key] = []
            endpoint_groups[key].append(row)
        
        saved_count = 0
        skipped_count = 0
        
        for endpoint_key, requests in endpoint_groups.items():
            # 每个接口只保留部分请求
            for req in requests[:max_requests_per_endpoint]:
                try:
                    if self._save_production_request(req, task_id, tags):
                        saved_count += 1
                    else:
                        skipped_count += 1
                except Exception as e:
                    self.logger.error(f"保存请求失败: {e}")
                    skipped_count += 1
        
        self.logger.end_step(f"保存 {saved_count} 个请求，跳过 {skipped_count} 个")
        
        return {
            "total": len(rows),
            "endpoints": len(endpoint_groups),
            "saved": saved_count,
            "skipped": skipped_count
        }
    
    def run_health_check(
        self,
        base_url: str,
        tag_filter: str | None = None,
        use_ai_validation: bool = True,
        timeout_seconds: int = 30
    ) -> dict[str, Any]:
        """
        执行线上健康检查
        
        Args:
            base_url: 目标服务器基础URL
            tag_filter: 按标签筛选
            use_ai_validation: 是否使用AI验证返回结果
            timeout_seconds: 请求超时时间
            
        Returns:
            检查结果统计
        """
        import httpx
        
        self.logger.start_step("执行线上健康检查")
        
        # 获取要检查的请求
        requests = self._get_enabled_requests(tag_filter)
        
        if not requests:
            self.logger.warn("没有启用的监控请求")
            return {"total": 0, "healthy": 0, "unhealthy": 0}
        
        total = len(requests)
        healthy_count = 0
        unhealthy_count = 0
        results: list[HealthCheckResult] = []
        
        # 创建执行记录
        execution_id = self._create_execution_record(base_url, total)
        
        with httpx.Client(timeout=timeout_seconds) as client:
            for i, req in enumerate(requests):
                self.logger.debug(f"检查 {i+1}/{total}: {req['method']} {req['url']}")
                
                try:
                    result = self._check_single_request(
                        client, req, base_url, use_ai_validation
                    )
                    results.append(result)
                    
                    if result.success:
                        healthy_count += 1
                        self._update_request_status(req['request_id'], True)
                    else:
                        unhealthy_count += 1
                        self._update_request_status(req['request_id'], False)
                        self._record_failure(req, result)
                    
                    # 保存检查结果
                    self._save_check_result(execution_id, result)
                    
                except Exception as e:
                    unhealthy_count += 1
                    self.logger.error(f"检查失败: {e}")
                    error_result = HealthCheckResult(
                        request_id=req['request_id'],
                        success=False,
                        status_code=0,
                        response_time_ms=0,
                        response_body="",
                        error_message=str(e)
                    )
                    results.append(error_result)
                    self._update_request_status(req['request_id'], False)
        
        # 更新执行记录
        self._complete_execution_record(execution_id, healthy_count, unhealthy_count)
        
        # 计算健康状态
        health_rate = healthy_count / total if total > 0 else 0
        if health_rate >= 0.95:
            status = HealthStatus.HEALTHY
        elif health_rate >= 0.8:
            status = HealthStatus.DEGRADED
        else:
            status = HealthStatus.UNHEALTHY
        
        self.logger.end_step(f"健康率: {health_rate:.1%} ({status.value})")
        
        return {
            "execution_id": execution_id,
            "total": total,
            "healthy": healthy_count,
            "unhealthy": unhealthy_count,
            "health_rate": health_rate,
            "status": status.value,
            "results": [self._result_to_dict(r) for r in results[:50]]  # 限制返回数量
        }
    
    def _check_single_request(
        self,
        client: Any,
        req: dict[str, Any],
        base_url: str,
        use_ai_validation: bool
    ) -> HealthCheckResult:
        """检查单个请求"""
        import time
        
        method = req['method']
        url = req['url']
        headers = req.get('headers', {})
        body = req.get('body')
        
        # 解析 JSON 字段
        if isinstance(headers, str):
            headers = json.loads(headers) if headers else {}
        
        # 构建完整 URL
        if not url.startswith('http'):
            full_url = f"{base_url.rstrip('/')}{url}"
        else:
            full_url = url
        
        # 发送请求
        start_time = time.time()
        
        request_kwargs: dict[str, Any] = {
            "method": method,
            "url": full_url,
            "headers": headers
        }
        
        if body and method.upper() in ['POST', 'PUT', 'PATCH']:
            if isinstance(body, str):
                try:
                    request_kwargs["json"] = json.loads(body)
                except json.JSONDecodeError:
                    request_kwargs["content"] = body
            else:
                request_kwargs["json"] = body
        
        response = client.request(**request_kwargs)
        response_time_ms = (time.time() - start_time) * 1000
        
        # 获取响应内容
        try:
            response_body = response.text
        except Exception:
            response_body = ""
        
        # 基础验证
        expected_status = req.get('expected_status_code', 200)
        status_ok = response.status_code == expected_status
        
        # 响应模式验证
        pattern_ok = True
        expected_pattern = req.get('expected_response_pattern')
        if expected_pattern and response_body:
            pattern_ok = bool(re.search(expected_pattern, response_body))
        
        # AI 验证
        ai_analysis = None
        if use_ai_validation and response_body:
            try:
                ai_analysis = self._ai_validate_response(req, response.status_code, response_body)
                ai_ok = ai_analysis.get('is_valid', True)
            except Exception as e:
                self.logger.warn(f"AI 验证失败: {e}")
                ai_ok = True
        else:
            ai_ok = True
        
        success = status_ok and pattern_ok and ai_ok
        error_message = None
        
        if not status_ok:
            error_message = f"状态码不匹配: 期望 {expected_status}, 实际 {response.status_code}"
        elif not pattern_ok:
            error_message = f"响应不匹配期望模式: {expected_pattern}"
        elif not ai_ok:
            error_message = ai_analysis.get('reason', 'AI 判断响应异常') if ai_analysis else 'AI 判断响应异常'
        
        return HealthCheckResult(
            request_id=req['request_id'],
            success=success,
            status_code=response.status_code,
            response_time_ms=response_time_ms,
            response_body=response_body[:5000],  # 限制长度
            error_message=error_message,
            ai_analysis=ai_analysis
        )
    
    def _ai_validate_response(
        self,
        req: dict[str, Any],
        status_code: int,
        response_body: str
    ) -> dict[str, Any]:
        """使用 AI 验证响应是否正常"""
        self.logger.ai_start("AI响应验证", f"{req['method']} {req['url']}")
        
        test_case = {
            "method": req['method'],
            "url": req['url'],
            "expected_status_code": req.get('expected_status_code', 200)
        }
        
        actual_response = {
            "status_code": status_code,
            "body": response_body[:2000]  # 限制长度
        }
        
        result = self.validator_chain.validate_response(
            test_case=test_case,
            actual_response=actual_response
        )
        
        self.logger.ai_end(f"验证结果: {'正常' if result.get('is_valid', True) else '异常'}")
        
        return result
    
    def add_manual_request(
        self,
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        body: str | None = None,
        expected_status_code: int = 200,
        expected_response_pattern: str | None = None,
        tags: list[str] | None = None
    ) -> str:
        """
        手动添加监控请求
        
        Returns:
            请求ID
        """
        request_id = hashlib.md5(
            f"{method}:{url}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        sql = """
            INSERT INTO production_requests 
            (request_id, method, url, headers, body, expected_status_code,
             expected_response_pattern, source, tags, is_enabled)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        self.db.execute(sql, (
            request_id,
            method.upper(),
            url,
            json.dumps(headers or {}, ensure_ascii=False),
            body,
            expected_status_code,
            expected_response_pattern,
            RequestSource.MANUAL.value,
            json.dumps(tags or [], ensure_ascii=False),
            True
        ))
        
        return request_id
    
    def get_health_summary(self, days: int = 7) -> dict[str, Any]:
        """
        获取健康状态摘要
        
        Args:
            days: 统计天数
        """
        # 获取最近的执行记录
        sql = """
            SELECT * FROM health_check_executions
            WHERE created_at >= datetime('now', '-' || %s || ' days')
            ORDER BY created_at DESC
            LIMIT 100
        """
        executions = self.db.fetch_all(sql, (days,))
        
        if not executions:
            return {
                "status": HealthStatus.UNKNOWN.value,
                "total_checks": 0,
                "avg_health_rate": 0,
                "trend": "unknown"
            }
        
        # 计算平均健康率
        total_healthy = sum(e['healthy_count'] for e in executions)
        total_requests = sum(e['total_requests'] for e in executions)
        avg_health_rate = total_healthy / total_requests if total_requests > 0 else 0
        
        # 计算趋势（最近10次 vs 之前）
        recent = executions[:10]
        older = executions[10:20] if len(executions) > 10 else []
        
        recent_rate = sum(e['healthy_count'] for e in recent) / sum(e['total_requests'] for e in recent) if recent else 0
        older_rate = sum(e['healthy_count'] for e in older) / sum(e['total_requests'] for e in older) if older else recent_rate
        
        if recent_rate > older_rate + 0.05:
            trend = "improving"
        elif recent_rate < older_rate - 0.05:
            trend = "degrading"
        else:
            trend = "stable"
        
        # 获取失败最多的接口
        sql = """
            SELECT pr.method, pr.url, pr.consecutive_failures,
                   COUNT(hcr.id) as failure_count
            FROM production_requests pr
            LEFT JOIN health_check_results hcr ON pr.request_id = hcr.request_id AND hcr.success = 0
            WHERE hcr.checked_at >= datetime('now', '-' || %s || ' days')
            GROUP BY pr.request_id
            ORDER BY failure_count DESC
            LIMIT 10
        """
        top_failures = self.db.fetch_all(sql, (days,))
        
        return {
            "status": HealthStatus.HEALTHY.value if avg_health_rate >= 0.95 else 
                      HealthStatus.DEGRADED.value if avg_health_rate >= 0.8 else
                      HealthStatus.UNHEALTHY.value,
            "total_checks": len(executions),
            "avg_health_rate": avg_health_rate,
            "trend": trend,
            "latest_execution": executions[0] if executions else None,
            "top_failures": top_failures
        }
    
    def _normalize_url(self, url: str) -> str:
        """规范化 URL（移除动态参数）"""
        # 移除查询参数
        path = url.split('?')[0]
        # 替换数字ID
        path = re.sub(r'/\d+(?=/|$)', '/{id}', path)
        return path
    
    def _save_production_request(self, req: dict[str, Any], task_id: str, extra_tags: list[str] | None = None) -> bool:
        """保存请求到线上自测库"""
        # 生成请求ID
        content = f"{req['method']}:{req['url']}:{req.get('body', '')}"
        request_id = hashlib.md5(content.encode()).hexdigest()[:16]
        
        # 检查是否已存在
        existing = self.db.fetch_one(
            "SELECT request_id FROM production_requests WHERE request_id = %s",
            (request_id,)
        )
        if existing:
            return False
        
        sql = """
            INSERT INTO production_requests 
            (request_id, method, url, headers, body, query_params,
             expected_status_code, source, source_task_id, tags, is_enabled)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        headers = req.get('headers', {})
        if isinstance(headers, str):
            headers = json.loads(headers) if headers else {}
        
        query_params = req.get('query_params', {})
        if isinstance(query_params, str):
            query_params = json.loads(query_params) if query_params else {}
        
        # 推断期望状态码
        expected_status = req.get('http_status', 200)
        
        # 从 URL 提取标签，并合并额外标签
        tags = self._extract_tags_from_url(req['url'])
        if extra_tags:
            tags = list(set(tags + extra_tags))
        
        self.db.execute(sql, (
            request_id,
            req['method'],
            req['url'],
            json.dumps(headers, ensure_ascii=False),
            req.get('body'),
            json.dumps(query_params, ensure_ascii=False),
            expected_status,
            RequestSource.LOG_PARSE.value,
            task_id,
            json.dumps(tags, ensure_ascii=False),
            True
        ))
        
        return True
    
    def _extract_tags_from_url(self, url: str) -> list[str]:
        """从 URL 提取标签"""
        tags: list[str] = []
        path = url.split('?')[0]
        parts = path.strip('/').split('/')
        
        # 提取前两级路径作为标签
        if len(parts) >= 1 and parts[0]:
            tags.append(parts[0])
        if len(parts) >= 2 and parts[1] and not parts[1].isdigit():
            tags.append(f"{parts[0]}/{parts[1]}")
        
        return tags
    
    def _get_enabled_requests(self, tag_filter: str | None = None) -> list[dict[str, Any]]:
        """获取启用的监控请求"""
        if tag_filter:
            sql = """
                SELECT * FROM production_requests 
                WHERE is_enabled = 1 AND JSON_CONTAINS(tags, %s)
                ORDER BY url
            """
            rows = self.db.fetch_all(sql, (json.dumps(tag_filter),))
        else:
            sql = "SELECT * FROM production_requests WHERE is_enabled = 1 ORDER BY url"
            rows = self.db.fetch_all(sql)
        
        return [dict(row) for row in rows]
    
    def _create_execution_record(self, base_url: str, total: int) -> str:
        """创建执行记录"""
        execution_id = hashlib.md5(
            f"health_check:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]
        
        sql = """
            INSERT INTO health_check_executions 
            (execution_id, base_url, total_requests, status, started_at)
            VALUES (%s, %s, %s, %s, datetime('now'))
        """
        self.db.execute(sql, (execution_id, base_url, total, 'running'))
        
        return execution_id
    
    def _complete_execution_record(
        self,
        execution_id: str,
        healthy_count: int,
        unhealthy_count: int
    ) -> None:
        """完成执行记录"""
        sql = """
            UPDATE health_check_executions SET
                healthy_count = %s,
                unhealthy_count = %s,
                status = 'completed',
                completed_at = datetime('now')
            WHERE execution_id = %s
        """
        self.db.execute(sql, (healthy_count, unhealthy_count, execution_id))
    
    def _update_request_status(self, request_id: str, success: bool) -> None:
        """更新请求状态"""
        if success:
            sql = """
                UPDATE production_requests SET
                    last_check_at = datetime('now'),
                    last_check_status = 'healthy',
                    consecutive_failures = 0
                WHERE request_id = %s
            """
            self.db.execute(sql, (request_id,))
        else:
            sql = """
                UPDATE production_requests SET
                    last_check_at = datetime('now'),
                    last_check_status = 'unhealthy',
                    consecutive_failures = consecutive_failures + 1
                WHERE request_id = %s
            """
            self.db.execute(sql, (request_id,))
    
    def _record_failure(self, req: dict[str, Any], result: HealthCheckResult) -> None:
        """记录失败"""
        # 如果连续失败次数超过阈值，可以触发告警
        consecutive = req.get('consecutive_failures', 0) + 1
        if consecutive >= 3:
            self.logger.error(
                f"接口连续失败 {consecutive} 次: {req['method']} {req['url']}"
            )
            # 创建告警洞察
            self._create_alert_insight(req, result, consecutive)
    
    def _save_check_result(self, execution_id: str, result: HealthCheckResult) -> None:
        """保存检查结果"""
        sql = """
            INSERT INTO health_check_results 
            (execution_id, request_id, success, status_code, response_time_ms,
             response_body, error_message, ai_analysis, checked_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, datetime('now'))
        """
        self.db.execute(sql, (
            execution_id,
            result.request_id,
            result.success,
            result.status_code,
            result.response_time_ms,
            result.response_body[:5000] if result.response_body else None,
            result.error_message,
            json.dumps(result.ai_analysis, ensure_ascii=False) if result.ai_analysis else None
        ))
    
    def _result_to_dict(self, result: HealthCheckResult) -> dict[str, Any]:
        """转换结果为字典"""
        return {
            "request_id": result.request_id,
            "success": result.success,
            "status_code": result.status_code,
            "response_time_ms": result.response_time_ms,
            "error_message": result.error_message,
            "ai_analysis": result.ai_analysis,
            "checked_at": result.checked_at.isoformat() if result.checked_at else None
        }

    def _create_alert_insight(
        self,
        req: dict[str, Any],
        result: HealthCheckResult,
        consecutive_failures: int
    ) -> None:
        """创建告警洞察"""
        import uuid

        # 生成唯一的告警ID（基于请求ID和时间）
        alert_id = f"alert_{uuid.uuid4().hex[:12]}"

        # 构建告警详情
        details = {
            "request_id": req.get("request_id"),
            "method": req.get("method"),
            "url": req.get("url"),
            "consecutive_failures": consecutive_failures,
            "last_error": result.error_message,
            "last_status_code": result.status_code,
            "last_check_at": result.checked_at.isoformat() if result.checked_at else None
        }

        # 构建建议
        recommendations = [
            f"检查接口 {req.get('method')} {req.get('url')} 的服务状态",
            "查看服务日志排查错误原因",
            "确认网络连接和依赖服务状态"
        ]

        if result.status_code and result.status_code >= 500:
            recommendations.insert(0, "服务端错误，优先检查服务器状态和日志")
        elif result.status_code and result.status_code >= 400:
            recommendations.insert(0, "客户端错误，检查请求参数和认证状态")

        # 插入告警到 ai_insights 表
        sql = """
            INSERT INTO ai_insights
            (insight_id, insight_type, title, description, severity, confidence,
             details, recommendations, is_resolved, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, datetime('now'))
        """

        severity = 'high' if consecutive_failures >= 5 else 'medium'
        title = f"接口连续失败告警: {req.get('method')} {req.get('url', '')[:50]}"
        description = f"接口已连续失败 {consecutive_failures} 次，最后错误: {result.error_message or '未知错误'}"

        try:
            self.db.execute(sql, (
                alert_id,
                'consecutive_failure',  # 告警类型
                title,
                description,
                severity,
                0.95,  # 高置信度
                json.dumps(details, ensure_ascii=False),
                json.dumps(recommendations, ensure_ascii=False),
                False  # 未解决
            ))
            self.logger.info(f"已创建告警洞察: {alert_id}")
        except Exception as e:
            self.logger.error(f"创建告警洞察失败: {e}")
