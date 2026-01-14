"""
功能4: AI 增强功能服务
提供各种 AI 驱动的智能辅助功能
"""

import json
import hashlib
from typing import Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from ..database import get_db_manager
from ..llm.provider import get_llm_provider, LLMProvider
from ..llm.chains import LogAnalysisChain, ReportGeneratorChain
from ..utils.logger import get_logger


class InsightType(Enum):
    """洞察类型"""
    API_CHANGE = "api_change"              # 接口变更检测
    PERFORMANCE_TREND = "performance_trend"  # 性能趋势分析
    USAGE_PATTERN = "usage_pattern"        # 使用模式分析
    RISK_ASSESSMENT = "risk_assessment"    # 风险评估
    OPTIMIZATION = "optimization"          # 优化建议
    COVERAGE_GAP = "coverage_gap"          # 覆盖率缺口


@dataclass
class AIInsight:
    """AI 洞察"""
    insight_id: str
    insight_type: InsightType
    title: str
    description: str
    severity: str  # high, medium, low
    confidence: float  # 0-1
    details: dict[str, Any] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


class AIAssistantService:
    """
    AI 智能助手服务
    
    功能：
    1. 智能接口变更检测 - 对比新旧接口文档，发现变更
    2. 性能趋势分析 - 分析接口性能变化趋势
    3. 智能测试建议 - 基于历史数据推荐测试重点
    4. 风险评估 - 评估接口变更的风险
    5. 代码生成 - 生成测试代码、Mock 数据等
    """
    
    def __init__(self, verbose: bool = False):
        self.logger = get_logger(verbose)
        self.verbose = verbose
        self.db = get_db_manager()
        self._provider: LLMProvider | None = None
    
    @property
    def provider(self) -> LLMProvider:
        """懒加载 LLM Provider"""
        if self._provider is None:
            self._provider = get_llm_provider()
        return self._provider
    
    # ==================== 功能1: 接口变更检测 ====================
    
    def detect_api_changes(
        self,
        old_endpoints: list[dict[str, Any]],
        new_endpoints: list[dict[str, Any]]
    ) -> list[AIInsight]:
        """
        检测接口变更
        
        Args:
            old_endpoints: 旧版本接口列表
            new_endpoints: 新版本接口列表
            
        Returns:
            变更洞察列表
        """
        self.logger.start_step("检测接口变更")
        
        insights: list[AIInsight] = []
        
        old_map = {f"{e['method']}:{e['path']}": e for e in old_endpoints}
        new_map = {f"{e['method']}:{e['path']}": e for e in new_endpoints}
        
        old_keys = set(old_map.keys())
        new_keys = set(new_map.keys())
        
        # 新增接口
        added = new_keys - old_keys
        for key in added:
            ep = new_map[key]
            insights.append(AIInsight(
                insight_id=hashlib.md5(f"added:{key}".encode()).hexdigest()[:16],
                insight_type=InsightType.API_CHANGE,
                title=f"新增接口: {ep['method']} {ep['path']}",
                description=f"发现新增接口 {ep.get('name', '')}",
                severity="medium",
                confidence=1.0,
                details={"change_type": "added", "endpoint": ep},
                recommendations=["为新接口编写测试用例", "检查接口文档是否完整"]
            ))
        
        # 删除接口
        removed = old_keys - new_keys
        for key in removed:
            ep = old_map[key]
            insights.append(AIInsight(
                insight_id=hashlib.md5(f"removed:{key}".encode()).hexdigest()[:16],
                insight_type=InsightType.API_CHANGE,
                title=f"删除接口: {ep['method']} {ep['path']}",
                description=f"接口 {ep.get('name', '')} 已被删除",
                severity="high",
                confidence=1.0,
                details={"change_type": "removed", "endpoint": ep},
                recommendations=["确认删除是否符合预期", "检查是否有依赖此接口的功能", "更新相关测试用例"]
            ))
        
        # 修改接口
        common = old_keys & new_keys
        for key in common:
            old_ep = old_map[key]
            new_ep = new_map[key]
            
            changes = self._compare_endpoints(old_ep, new_ep)
            if changes:
                severity = "high" if any(c.get("breaking") for c in changes) else "medium"
                insights.append(AIInsight(
                    insight_id=hashlib.md5(f"modified:{key}".encode()).hexdigest()[:16],
                    insight_type=InsightType.API_CHANGE,
                    title=f"修改接口: {new_ep['method']} {new_ep['path']}",
                    description=f"接口 {new_ep.get('name', '')} 发生变更: {', '.join(c['field'] for c in changes)}",
                    severity=severity,
                    confidence=1.0,
                    details={
                        "change_type": "modified",
                        "changes": changes,
                        "old_endpoint": old_ep,
                        "new_endpoint": new_ep
                    },
                    recommendations=self._get_change_recommendations(changes)
                ))
        
        self.logger.end_step(f"发现 {len(insights)} 个变更")
        
        return insights
    
    def _compare_endpoints(
        self,
        old_ep: dict[str, Any],
        new_ep: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """比较两个接口的差异"""
        changes: list[dict[str, Any]] = []
        
        # 比较参数
        old_params = self._normalize_params(old_ep.get('parameters', []))
        new_params = self._normalize_params(new_ep.get('parameters', []))
        
        old_param_names = set(old_params.keys())
        new_param_names = set(new_params.keys())
        
        # 新增参数
        for name in new_param_names - old_param_names:
            param = new_params[name]
            changes.append({
                "field": f"parameter:{name}",
                "type": "added",
                "breaking": param.get('required', False),
                "description": f"新增{'必填' if param.get('required') else '可选'}参数 {name}"
            })
        
        # 删除参数
        for name in old_param_names - new_param_names:
            changes.append({
                "field": f"parameter:{name}",
                "type": "removed",
                "breaking": True,
                "description": f"删除参数 {name}"
            })
        
        # 修改参数
        for name in old_param_names & new_param_names:
            old_param = old_params[name]
            new_param = new_params[name]
            
            if old_param.get('type') != new_param.get('type'):
                changes.append({
                    "field": f"parameter:{name}:type",
                    "type": "modified",
                    "breaking": True,
                    "description": f"参数 {name} 类型从 {old_param.get('type')} 改为 {new_param.get('type')}"
                })
            
            if not old_param.get('required') and new_param.get('required'):
                changes.append({
                    "field": f"parameter:{name}:required",
                    "type": "modified",
                    "breaking": True,
                    "description": f"参数 {name} 从可选变为必填"
                })
        
        # 比较请求体
        old_body = old_ep.get('request_body', {})
        new_body = new_ep.get('request_body', {})
        if isinstance(old_body, str):
            old_body = json.loads(old_body) if old_body else {}
        if isinstance(new_body, str):
            new_body = json.loads(new_body) if new_body else {}
        
        if old_body != new_body:
            changes.append({
                "field": "request_body",
                "type": "modified",
                "breaking": True,
                "description": "请求体结构发生变化"
            })
        
        # 比较响应
        old_responses = old_ep.get('responses', {})
        new_responses = new_ep.get('responses', {})
        if isinstance(old_responses, str):
            old_responses = json.loads(old_responses) if old_responses else {}
        if isinstance(new_responses, str):
            new_responses = json.loads(new_responses) if new_responses else {}
        
        if old_responses != new_responses:
            changes.append({
                "field": "responses",
                "type": "modified",
                "breaking": False,
                "description": "响应结构发生变化"
            })
        
        return changes
    
    def _normalize_params(self, params: Any) -> dict[str, dict]:
        """规范化参数列表为字典"""
        if isinstance(params, str):
            params = json.loads(params) if params else []
        if not isinstance(params, list):
            return {}
        return {p.get('name', ''): p for p in params if p.get('name')}
    
    def _get_change_recommendations(self, changes: list[dict]) -> list[str]:
        """根据变更生成建议"""
        recommendations: list[str] = []
        
        has_breaking = any(c.get("breaking") for c in changes)
        if has_breaking:
            recommendations.append("此变更可能影响现有功能，建议进行回归测试")
        
        param_changes = [c for c in changes if c['field'].startswith('parameter:')]
        if param_changes:
            recommendations.append("更新相关测试用例的参数")
        
        body_changes = [c for c in changes if c['field'] == 'request_body']
        if body_changes:
            recommendations.append("检查请求体结构变化是否兼容")
        
        response_changes = [c for c in changes if c['field'] == 'responses']
        if response_changes:
            recommendations.append("更新响应断言")
        
        return recommendations
    
    # ==================== 功能2: 性能趋势分析 ====================
    
    def analyze_performance_trend(
        self,
        endpoint_id: str | None = None,
        days: int = 7
    ) -> list[AIInsight]:
        """
        分析性能趋势
        
        Args:
            endpoint_id: 接口ID，为空则分析所有接口
            days: 分析天数
            
        Returns:
            性能洞察列表
        """
        self.logger.start_step("分析性能趋势")
        
        insights: list[AIInsight] = []
        
        # 获取测试执行结果（test_cases 表没有 endpoint_id 列，通过 case_id 前缀匹配）
        if endpoint_id:
            sql = """
                SELECT tc.case_id, tc.method, tc.url, tr.actual_response_time_ms,
                       tr.status, tr.executed_at
                FROM test_results tr
                JOIN test_cases tc ON tr.case_id = tc.case_id
                WHERE tc.case_id LIKE %s
                AND tr.executed_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                ORDER BY tr.executed_at
            """
            results = self.db.fetch_all(sql, (f"{endpoint_id}%", days))
        else:
            sql = """
                SELECT tc.case_id, tc.method, tc.url, tr.actual_response_time_ms,
                       tr.status, tr.executed_at
                FROM test_results tr
                JOIN test_cases tc ON tr.case_id = tc.case_id
                WHERE tr.executed_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                ORDER BY tr.executed_at
            """
            results = self.db.fetch_all(sql, (days,))
        
        if not results:
            self.logger.warn("没有足够的执行数据进行分析")
            return insights
        
        # 按接口分组分析
        from collections import defaultdict
        endpoint_data: dict[str, list] = defaultdict(list)
        
        for r in results:
            key = f"{r['method']}:{r['url']}"
            endpoint_data[key].append({
                "response_time": float(r['actual_response_time_ms'] or 0),
                "status": r['status'],
                "executed_at": r['executed_at']
            })
        
        for endpoint_key, data in endpoint_data.items():
            if len(data) < 5:  # 数据太少
                continue
            
            # 计算趋势
            times = [d['response_time'] for d in data]
            recent = times[-5:]
            older = times[:-5] if len(times) > 5 else times[:len(times)//2]
            
            if not older:
                continue
            
            recent_avg = sum(recent) / len(recent)
            older_avg = sum(older) / len(older)
            
            # 性能下降检测
            if recent_avg > older_avg * 1.5 and recent_avg > 1000:  # 响应时间增加50%且超过1秒
                change_pct = (recent_avg - older_avg) / older_avg * 100
                insights.append(AIInsight(
                    insight_id=hashlib.md5(f"perf_degraded:{endpoint_key}".encode()).hexdigest()[:16],
                    insight_type=InsightType.PERFORMANCE_TREND,
                    title=f"性能下降: {endpoint_key.split(':')[1][:50]}",
                    description=f"接口响应时间从 {older_avg:.0f}ms 增加到 {recent_avg:.0f}ms (+{change_pct:.0f}%)",
                    severity="high" if change_pct > 100 else "medium",
                    confidence=0.8,
                    details={
                        "endpoint": endpoint_key,
                        "old_avg_ms": older_avg,
                        "new_avg_ms": recent_avg,
                        "change_percent": change_pct
                    },
                    recommendations=[
                        "检查是否有新的性能瓶颈",
                        "分析慢查询日志",
                        "检查依赖服务响应时间"
                    ]
                ))
            
            # 性能改善检测
            elif recent_avg < older_avg * 0.7:
                change_pct = (older_avg - recent_avg) / older_avg * 100
                insights.append(AIInsight(
                    insight_id=hashlib.md5(f"perf_improved:{endpoint_key}".encode()).hexdigest()[:16],
                    insight_type=InsightType.PERFORMANCE_TREND,
                    title=f"性能改善: {endpoint_key.split(':')[1][:50]}",
                    description=f"接口响应时间从 {older_avg:.0f}ms 降低到 {recent_avg:.0f}ms (-{change_pct:.0f}%)",
                    severity="low",
                    confidence=0.8,
                    details={
                        "endpoint": endpoint_key,
                        "old_avg_ms": older_avg,
                        "new_avg_ms": recent_avg,
                        "change_percent": -change_pct
                    }
                ))
            
            # 错误率分析
            error_count = sum(1 for d in data if d['status'] in ['failed', 'error'])
            error_rate = error_count / len(data)
            
            if error_rate > 0.1:  # 错误率超过10%
                insights.append(AIInsight(
                    insight_id=hashlib.md5(f"error_rate:{endpoint_key}".encode()).hexdigest()[:16],
                    insight_type=InsightType.RISK_ASSESSMENT,
                    title=f"高错误率: {endpoint_key.split(':')[1][:50]}",
                    description=f"接口错误率 {error_rate:.0%} ({error_count}/{len(data)})",
                    severity="high" if error_rate > 0.3 else "medium",
                    confidence=0.9,
                    details={
                        "endpoint": endpoint_key,
                        "error_rate": error_rate,
                        "error_count": error_count,
                        "total_count": len(data)
                    },
                    recommendations=[
                        "检查错误日志定位问题",
                        "验证测试用例是否正确",
                        "检查接口实现是否有bug"
                    ]
                ))
        
        self.logger.end_step(f"发现 {len(insights)} 个性能洞察")
        
        return insights
    
    # ==================== 功能3: 智能测试建议 ====================
    
    def get_test_recommendations(self) -> list[AIInsight]:
        """
        获取智能测试建议
        
        基于历史数据分析，推荐测试重点
        """
        self.logger.start_step("生成测试建议")
        
        insights: list[AIInsight] = []
        
        # 1. 检查测试覆盖率缺口
        coverage_insights = self._analyze_coverage_gaps()
        insights.extend(coverage_insights)
        
        # 2. 分析高风险接口
        risk_insights = self._analyze_high_risk_endpoints()
        insights.extend(risk_insights)
        
        # 3. 推荐优先测试的接口
        priority_insights = self._get_priority_recommendations()
        insights.extend(priority_insights)
        
        self.logger.end_step(f"生成 {len(insights)} 条建议")
        
        return insights
    
    def analyze_coverage_gaps(self) -> list[AIInsight]:
        """分析测试覆盖率缺口（公开方法）"""
        self.logger.start_step("分析覆盖率缺口")
        insights = self._analyze_coverage_gaps()
        self.logger.end_step(f"发现 {len(insights)} 个覆盖率问题")
        return insights
    
    def identify_high_risk_endpoints(self) -> list[AIInsight]:
        """识别高风险接口（公开方法）"""
        self.logger.start_step("识别高风险接口")
        insights = self._analyze_high_risk_endpoints()
        self.logger.end_step(f"发现 {len(insights)} 个高风险接口")
        return insights
    
    def _analyze_coverage_gaps(self) -> list[AIInsight]:
        """分析测试覆盖率缺口"""
        insights: list[AIInsight] = []
        
        # 获取没有测试用例的接口（通过 case_id 前缀匹配）
        sql = """
            SELECT e.endpoint_id, e.method, e.path, e.name
            FROM api_endpoints e
            WHERE NOT EXISTS (
                SELECT 1 FROM test_cases tc WHERE tc.case_id LIKE CONCAT(e.endpoint_id, '%')
            )
            ORDER BY e.path
        """
        uncovered = self.db.fetch_all(sql)
        
        if uncovered:
            insights.append(AIInsight(
                insight_id=hashlib.md5(f"coverage_gap:{len(uncovered)}".encode()).hexdigest()[:16],
                insight_type=InsightType.COVERAGE_GAP,
                title=f"发现 {len(uncovered)} 个接口未覆盖测试",
                description="以下接口没有对应的测试用例",
                severity="medium",
                confidence=1.0,
                details={
                    "uncovered_endpoints": [
                        {"method": e['method'], "path": e['path'], "name": e.get('name', '')}
                        for e in uncovered[:20]
                    ],
                    "total_uncovered": len(uncovered)
                },
                recommendations=[
                    "为这些接口生成测试用例",
                    "优先覆盖核心业务接口"
                ]
            ))
        
        return insights
    
    def _analyze_high_risk_endpoints(self) -> list[AIInsight]:
        """分析高风险接口"""
        insights: list[AIInsight] = []
        
        # 获取最近失败率高的接口（从 test_results 和 test_cases 查询）
        sql = """
            SELECT tc.case_id, tc.method, tc.url,
                   COUNT(*) as total,
                   SUM(CASE WHEN tr.status IN ('failed', 'error') THEN 1 ELSE 0 END) as failures
            FROM test_results tr
            JOIN test_cases tc ON tr.case_id = tc.case_id
            WHERE tr.executed_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            GROUP BY tc.case_id, tc.method, tc.url
            HAVING failures > 0
            ORDER BY failures / total DESC
            LIMIT 10
        """
        high_risk = self.db.fetch_all(sql)
        
        for ep in high_risk:
            failure_rate = ep['failures'] / ep['total']
            if failure_rate > 0.2:  # 失败率超过20%
                insights.append(AIInsight(
                    insight_id=hashlib.md5(f"high_risk:{ep['case_id']}".encode()).hexdigest()[:16],
                    insight_type=InsightType.RISK_ASSESSMENT,
                    title=f"高风险接口: {ep['method']} {ep['url'][:50]}",
                    description=f"最近7天失败率 {failure_rate:.0%} ({ep['failures']}/{ep['total']})",
                    severity="high" if failure_rate > 0.5 else "medium",
                    confidence=0.9,
                    details={
                        "case_id": ep['case_id'],
                        "failure_rate": failure_rate,
                        "failures": ep['failures'],
                        "total": ep['total']
                    },
                    recommendations=[
                        "优先修复此接口的问题",
                        "增加更多测试用例覆盖边界情况",
                        "检查测试环境是否稳定"
                    ]
                ))
        
        return insights
    
    def _get_priority_recommendations(self) -> list[AIInsight]:
        """获取优先测试建议"""
        insights: list[AIInsight] = []
        
        # 获取最近修改但未测试的接口（通过 case_id 前缀匹配）
        sql = """
            SELECT e.endpoint_id, e.method, e.path, e.name, e.updated_at
            FROM api_endpoints e
            WHERE e.updated_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
            AND NOT EXISTS (
                SELECT 1 FROM test_cases tc 
                JOIN test_results tr ON tc.case_id = tr.case_id
                WHERE tc.case_id LIKE CONCAT(e.endpoint_id, '%')
                AND tr.executed_at >= e.updated_at
            )
            ORDER BY e.updated_at DESC
            LIMIT 10
        """
        recently_changed = self.db.fetch_all(sql)
        
        if recently_changed:
            insights.append(AIInsight(
                insight_id=hashlib.md5(f"priority_test:{len(recently_changed)}".encode()).hexdigest()[:16],
                insight_type=InsightType.OPTIMIZATION,
                title=f"建议优先测试 {len(recently_changed)} 个最近修改的接口",
                description="这些接口最近有更新但尚未进行测试",
                severity="medium",
                confidence=0.85,
                details={
                    "endpoints": [
                        {
                            "method": e['method'],
                            "path": e['path'],
                            "name": e.get('name', ''),
                            "updated_at": e['updated_at'].isoformat() if e.get('updated_at') else None
                        }
                        for e in recently_changed
                    ]
                },
                recommendations=[
                    "对这些接口执行回归测试",
                    "检查变更是否引入新问题"
                ]
            ))
        
        return insights
    
    # ==================== 功能4: 代码生成 ====================
    
    def generate_mock_data(
        self,
        endpoint_id: str,
        count: int = 5
    ) -> dict[str, Any]:
        """
        为接口生成 Mock 数据
        
        Args:
            endpoint_id: 接口ID
            count: 生成数量
            
        Returns:
            Mock 数据
        """
        self.logger.ai_start("生成Mock数据", endpoint_id)
        
        # 获取接口信息
        sql = "SELECT * FROM api_endpoints WHERE endpoint_id = %s"
        endpoint = self.db.fetch_one(sql, (endpoint_id,))
        
        if not endpoint:
            raise ValueError(f"接口不存在: {endpoint_id}")
        
        # 解析响应定义
        responses = endpoint.get('responses', {})
        if isinstance(responses, str):
            responses = json.loads(responses) if responses else {}
        
        # 构建提示词
        prompt = f"""根据以下接口定义，生成 {count} 个符合规范的 Mock 响应数据。

接口信息：
- 方法: {endpoint['method']}
- 路径: {endpoint['path']}
- 名称: {endpoint.get('name', '')}
- 描述: {endpoint.get('description', '')}

响应定义：
{json.dumps(responses, ensure_ascii=False, indent=2)}

请生成 {count} 个不同的 Mock 响应数据，以 JSON 数组格式返回。
每个响应应该：
1. 符合响应定义的结构
2. 包含合理的示例数据
3. 数据多样化，覆盖不同场景

只返回 JSON 数组，不要其他说明："""
        
        response = self.provider.generate(prompt)
        
        # 解析响应
        try:
            # 尝试提取 JSON
            import re
            json_match = re.search(r'\[[\s\S]*\]', response)
            if json_match:
                mock_data = json.loads(json_match.group(0))
            else:
                mock_data = json.loads(response)
        except json.JSONDecodeError:
            mock_data = [{"error": "生成失败", "raw_response": response[:500]}]
        
        self.logger.ai_end(f"生成 {len(mock_data)} 个Mock数据")
        
        return {
            "endpoint_id": endpoint_id,
            "method": endpoint['method'],
            "path": endpoint['path'],
            "mock_responses": mock_data
        }
    
    def generate_test_code(
        self,
        endpoint_id: str,
        language: str = "python",
        framework: str = "pytest"
    ) -> str:
        """
        为接口生成测试代码
        
        Args:
            endpoint_id: 接口ID
            language: 编程语言
            framework: 测试框架
            
        Returns:
            测试代码
        """
        self.logger.ai_start("生成测试代码", f"{endpoint_id} ({language}/{framework})")
        
        # 获取接口信息
        sql = "SELECT * FROM api_endpoints WHERE endpoint_id = %s"
        endpoint = self.db.fetch_one(sql, (endpoint_id,))
        
        if not endpoint:
            raise ValueError(f"接口不存在: {endpoint_id}")
        
        # 获取该接口的测试用例（通过 case_id 前缀匹配）
        sql = "SELECT * FROM test_cases WHERE case_id LIKE %s LIMIT 10"
        test_cases = self.db.fetch_all(sql, (f"{endpoint_id}%",))
        
        # 构建提示词
        prompt = f"""根据以下接口信息和测试用例，生成 {language} 语言的 {framework} 测试代码。

接口信息：
- 方法: {endpoint['method']}
- 路径: {endpoint['path']}
- 名称: {endpoint.get('name', '')}
- 参数: {endpoint.get('parameters', '[]')}
- 请求体: {endpoint.get('request_body', '{}')}

测试用例：
{json.dumps([{
    'name': tc['name'],
    'category': tc['category'],
    'body': tc.get('body'),
    'expected_status_code': tc.get('expected_status_code', 200)
} for tc in test_cases], ensure_ascii=False, indent=2)}

请生成完整的测试代码，包括：
1. 必要的导入语句
2. 测试类或测试函数
3. 正常场景测试
4. 异常场景测试
5. 边界值测试（如果适用）

代码要求：
- 使用 {framework} 框架
- 包含清晰的注释
- 使用参数化测试（如果适用）
- 包含断言验证

只返回代码，不要其他说明："""
        
        code = self.provider.generate(prompt)
        
        # 清理代码（移除 markdown 代码块标记）
        import re
        code = re.sub(r'^```\w*\n?', '', code)
        code = re.sub(r'\n?```$', '', code)
        
        self.logger.ai_end("代码生成完成")
        
        return code
    
    # ==================== 功能5: 智能问答 ====================
    
    def ask_question(
        self,
        question: str,
        context: dict[str, Any] | None = None
    ) -> str:
        """
        智能问答
        
        Args:
            question: 问题
            context: 上下文信息
            
        Returns:
            回答
        """
        self.logger.ai_start("智能问答", question[:50])
        
        # 构建上下文
        context_str = ""
        if context:
            context_str = f"\n\n上下文信息：\n{json.dumps(context, ensure_ascii=False, indent=2)}"
        
        # 获取一些统计数据作为背景
        stats = self._get_system_stats()
        
        prompt = f"""你是一个 API 测试工具的智能助手。请根据以下信息回答用户的问题。

系统统计：
- 接口总数: {stats.get('endpoint_count', 0)}
- 测试用例数: {stats.get('test_case_count', 0)}
- 最近执行数: {stats.get('recent_executions', 0)}
- 平均成功率: {stats.get('avg_success_rate', 0):.1%}
{context_str}

用户问题：{question}

请提供清晰、准确、有帮助的回答。如果问题涉及具体数据，请基于上述统计信息回答。"""
        
        answer = self.provider.generate(prompt)
        
        self.logger.ai_end("回答完成")
        
        return answer
    
    def _get_system_stats(self) -> dict[str, Any]:
        """获取系统统计数据"""
        stats: dict[str, Any] = {}
        
        # 接口数量
        result = self.db.fetch_one("SELECT COUNT(*) as count FROM api_endpoints")
        stats['endpoint_count'] = result['count'] if result else 0
        
        # 测试用例数量
        result = self.db.fetch_one("SELECT COUNT(*) as count FROM test_cases")
        stats['test_case_count'] = result['count'] if result else 0
        
        # 最近7天执行数
        result = self.db.fetch_one("""
            SELECT COUNT(*) as count FROM test_results
            WHERE executed_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        """)
        stats['recent_executions'] = result['count'] if result else 0
        
        # 平均成功率
        result = self.db.fetch_one("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) as passed
            FROM test_results
            WHERE executed_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        """)
        if result and result['total'] > 0:
            stats['avg_success_rate'] = result['passed'] / result['total']
        else:
            stats['avg_success_rate'] = 0
        
        return stats
