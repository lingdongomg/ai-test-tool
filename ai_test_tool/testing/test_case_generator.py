"""
智能测试用例生成器
基于日志样例自动生成测试用例
Python 3.13+ 兼容

该文件内容使用AI生成，注意识别准确性
"""

import json
import re
from typing import Any
from dataclasses import dataclass, field, asdict
from enum import Enum

from ..parser.log_parser import ParsedRequest
from ..llm.chains import TestCaseGeneratorChain, KnowledgeEnhancedTestGeneratorChain
from ..utils.logger import get_logger

# 知识库集成（可选依赖）
try:
    from ..knowledge import KnowledgeRetriever, RAGContextBuilder, get_knowledge_store
    KNOWLEDGE_ENABLED = True
except ImportError:
    KNOWLEDGE_ENABLED = False


class TestCaseCategory(Enum):
    """测试用例类别"""
    NORMAL = "normal"           # 正常场景
    BOUNDARY = "boundary"       # 边界值
    EXCEPTION = "exception"     # 异常场景
    PERFORMANCE = "performance" # 性能测试
    SECURITY = "security"       # 安全测试


class TestCasePriority(Enum):
    """测试用例优先级"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ValidationRule:
    """验证规则"""
    field: str                  # 字段路径
    rule: str                   # 规则类型: equals, contains, exists, type, range
    expected_value: Any = None  # 期望值
    description: str = ""       # 规则描述


@dataclass
class ExpectedResult:
    """期望结果"""
    status_code: int = 200
    response_contains: list[str] = field(default_factory=list)
    response_not_contains: list[str] = field(default_factory=list)
    max_response_time_ms: int = 3000
    validation_rules: list[ValidationRule] = field(default_factory=list)


@dataclass
class TestCase:
    """测试用例"""
    id: str
    name: str
    description: str
    category: TestCaseCategory
    priority: TestCasePriority
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    body: dict[str, Any] | None = None
    query_params: dict[str, str] = field(default_factory=dict)
    expected: ExpectedResult = field(default_factory=ExpectedResult)
    tags: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)  # 依赖的测试用例ID
    
    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        result['category'] = self.category.value
        result['priority'] = self.priority.value
        return result
    
    def to_curl(self, base_url: str = "") -> str:
        """生成curl命令"""
        full_url = f"{base_url}{self.url}" if base_url else self.url
        
        # 添加查询参数
        if self.query_params:
            params = "&".join(f"{k}={v}" for k, v in self.query_params.items())
            full_url = f"{full_url}?{params}" if "?" not in full_url else f"{full_url}&{params}"
        
        parts = ["curl"]
        
        if self.method.upper() != "GET":
            parts.append(f"-X {self.method.upper()}")
        
        parts.append(f'"{full_url}"')
        
        for key, value in self.headers.items():
            parts.append(f'-H "{key}: {value}"')
        
        if self.body:
            if "Content-Type" not in self.headers:
                parts.append('-H "Content-Type: application/json"')
            body_str = json.dumps(self.body, ensure_ascii=False)
            parts.append(f"-d '{body_str}'")
        
        return " \\\n  ".join(parts)


class TestCaseGenerator:
    """智能测试用例生成器"""
    
    def __init__(
        self, 
        llm_chain: TestCaseGeneratorChain | None = None, 
        verbose: bool = False,
        enable_knowledge: bool = True
    ) -> None:
        self.llm_chain = llm_chain
        self.verbose = verbose
        self.logger = get_logger(verbose)
        self._case_counter = 0
        
        # 知识库集成
        self._knowledge_enabled = enable_knowledge and KNOWLEDGE_ENABLED
        self._knowledge_retriever: Any = None
        self._rag_builder: Any = None
        self._knowledge_chain: KnowledgeEnhancedTestGeneratorChain | None = None
        
        if self._knowledge_enabled:
            self._init_knowledge_components()
    
    def _init_knowledge_components(self) -> None:
        """初始化知识库组件"""
        try:
            store = get_knowledge_store()
            self._knowledge_retriever = KnowledgeRetriever(store)
            self._rag_builder = RAGContextBuilder(self._knowledge_retriever)
            self._knowledge_chain = KnowledgeEnhancedTestGeneratorChain(verbose=self.verbose)
            self.logger.info("知识库组件初始化成功")
        except Exception as e:
            self.logger.warn(f"知识库组件初始化失败: {e}")
            self._knowledge_enabled = False
    
    def generate_from_requests(
        self,
        requests: list[ParsedRequest],
        test_strategy: str = "comprehensive"
    ) -> list[TestCase]:
        """
        从请求列表生成测试用例
        
        Args:
            requests: 解析后的请求列表
            test_strategy: 测试策略 (comprehensive/quick/security)
            
        Returns:
            测试用例列表
        """
        test_cases: list[TestCase] = []
        
        self.logger.start_step("测试用例生成")
        
        # 按URL分组
        url_groups = self._group_requests_by_url(requests)
        
        total_groups = len(url_groups)
        for i, (url, reqs) in enumerate(url_groups.items()):
            self.logger.debug(f"处理接口 {i+1}/{total_groups}: {url[:50]}")
            
            # 为每个接口生成测试用例
            cases = self._generate_for_endpoint(url, reqs, test_strategy)
            test_cases.extend(cases)
        
        self.logger.end_step(f"生成 {len(test_cases)} 个用例")
        
        return test_cases
    
    def _group_requests_by_url(
        self,
        requests: list[ParsedRequest]
    ) -> dict[str, list[ParsedRequest]]:
        """按URL分组请求"""
        groups: dict[str, list[ParsedRequest]] = {}
        for req in requests:
            # 规范化URL（移除查询参数中的动态值）
            base_url = self._normalize_url(req.url)
            key = f"{req.method}:{base_url}"
            
            if key not in groups:
                groups[key] = []
            groups[key].append(req)
        
        return groups
    
    def _normalize_url(self, url: str) -> str:
        """规范化URL"""
        # 移除查询参数中的动态值（如ID、时间戳等）
        path = url.split('?')[0]
        
        # 替换路径中的数字ID为占位符
        path = re.sub(r'/\d+(?=/|$)', '/{id}', path)
        
        return path
    
    def _generate_for_endpoint(
        self,
        endpoint_key: str,
        requests: list[ParsedRequest],
        test_strategy: str
    ) -> list[TestCase]:
        """为单个接口生成测试用例"""
        method, url = endpoint_key.split(':', 1)
        
        # 收集样本数据
        sample_bodies: list[dict[str, Any]] = []
        for r in requests:
            if r.body and r.body.startswith('{'):
                try:
                    sample_bodies.append(json.loads(r.body))
                except json.JSONDecodeError:
                    pass
        sample_bodies = sample_bodies[:5]
        
        sample_headers: dict[str, str] = {}
        for r in requests:
            sample_headers.update(r.headers)
        
        # 收集响应状态
        status_codes = list(set(r.http_status for r in requests if r.http_status > 0))
        
        test_cases: list[TestCase] = []
        
        # 1. 生成正常场景测试用例
        normal_cases = self._generate_normal_cases(
            method, url, sample_headers, sample_bodies, status_codes
        )
        test_cases.extend(normal_cases)
        
        # 2. 生成边界值测试用例
        if test_strategy in ["comprehensive", "security"]:
            boundary_cases = self._generate_boundary_cases(
                method, url, sample_headers, sample_bodies
            )
            test_cases.extend(boundary_cases)
        
        # 3. 生成异常场景测试用例
        exception_cases = self._generate_exception_cases(
            method, url, sample_headers, sample_bodies
        )
        test_cases.extend(exception_cases)
        
        # 4. 使用LLM增强测试用例
        if self.llm_chain and sample_bodies:
            llm_cases = self._generate_llm_cases(
                method, url, sample_headers, sample_bodies, test_strategy
            )
            test_cases.extend(llm_cases)
        
        return test_cases
    
    def _generate_normal_cases(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        sample_bodies: list[dict[str, Any]],
        status_codes: list[int]
    ) -> list[TestCase]:
        """生成正常场景测试用例"""
        cases: list[TestCase] = []
        
        # 基于样本生成正常测试用例
        for i, body in enumerate(sample_bodies[:3]):
            self._case_counter += 1
            case = TestCase(
                id=f"TC{self._case_counter:04d}",
                name=f"正常请求测试 - {self._extract_endpoint_name(url)}",
                description="基于日志样本的正常请求测试",
                category=TestCaseCategory.NORMAL,
                priority=TestCasePriority.HIGH,
                method=method,
                url=url,
                headers=headers.copy(),
                body=body,
                expected=ExpectedResult(
                    status_code=200,
                    max_response_time_ms=3000
                ),
                tags=["normal", "sample-based"]
            )
            cases.append(case)
        
        # 如果没有body，生成无body的测试用例
        if not sample_bodies:
            self._case_counter += 1
            case = TestCase(
                id=f"TC{self._case_counter:04d}",
                name=f"正常请求测试 - {self._extract_endpoint_name(url)}",
                description="基础请求测试",
                category=TestCaseCategory.NORMAL,
                priority=TestCasePriority.HIGH,
                method=method,
                url=url,
                headers=headers.copy(),
                expected=ExpectedResult(status_code=200)
            )
            cases.append(case)
        
        return cases
    
    def _generate_boundary_cases(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        sample_bodies: list[dict[str, Any]]
    ) -> list[TestCase]:
        """生成边界值测试用例"""
        cases: list[TestCase] = []
        
        if not sample_bodies:
            return cases
        
        # 分析样本body的字段类型
        sample = sample_bodies[0]
        
        for field_name, value in sample.items():
            # 数字类型边界测试
            if isinstance(value, (int, float)):
                # 最小值测试
                self._case_counter += 1
                min_body = sample.copy()
                min_body[field_name] = 0
                cases.append(TestCase(
                    id=f"TC{self._case_counter:04d}",
                    name=f"边界值测试 - {field_name}最小值",
                    description=f"测试{field_name}字段的最小边界值",
                    category=TestCaseCategory.BOUNDARY,
                    priority=TestCasePriority.MEDIUM,
                    method=method,
                    url=url,
                    headers=headers.copy(),
                    body=min_body,
                    expected=ExpectedResult(status_code=200),
                    tags=["boundary", f"field:{field_name}"]
                ))
                
                # 最大值测试
                self._case_counter += 1
                max_body = sample.copy()
                max_body[field_name] = 999999999
                cases.append(TestCase(
                    id=f"TC{self._case_counter:04d}",
                    name=f"边界值测试 - {field_name}最大值",
                    description=f"测试{field_name}字段的最大边界值",
                    category=TestCaseCategory.BOUNDARY,
                    priority=TestCasePriority.MEDIUM,
                    method=method,
                    url=url,
                    headers=headers.copy(),
                    body=max_body,
                    expected=ExpectedResult(status_code=200),
                    tags=["boundary", f"field:{field_name}"]
                ))
            
            # 字符串类型边界测试
            elif isinstance(value, str):
                # 空字符串测试
                self._case_counter += 1
                empty_body = sample.copy()
                empty_body[field_name] = ""
                cases.append(TestCase(
                    id=f"TC{self._case_counter:04d}",
                    name=f"边界值测试 - {field_name}空字符串",
                    description=f"测试{field_name}字段为空字符串",
                    category=TestCaseCategory.BOUNDARY,
                    priority=TestCasePriority.MEDIUM,
                    method=method,
                    url=url,
                    headers=headers.copy(),
                    body=empty_body,
                    expected=ExpectedResult(status_code=200),
                    tags=["boundary", f"field:{field_name}"]
                ))
            
            # 数组类型边界测试
            elif isinstance(value, list):
                # 空数组测试
                self._case_counter += 1
                empty_arr_body = sample.copy()
                empty_arr_body[field_name] = []
                cases.append(TestCase(
                    id=f"TC{self._case_counter:04d}",
                    name=f"边界值测试 - {field_name}空数组",
                    description=f"测试{field_name}字段为空数组",
                    category=TestCaseCategory.BOUNDARY,
                    priority=TestCasePriority.MEDIUM,
                    method=method,
                    url=url,
                    headers=headers.copy(),
                    body=empty_arr_body,
                    expected=ExpectedResult(status_code=200),
                    tags=["boundary", f"field:{field_name}"]
                ))
        
        return cases[:10]  # 限制数量
    
    def _generate_exception_cases(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        sample_bodies: list[dict[str, Any]]
    ) -> list[TestCase]:
        """生成异常场景测试用例"""
        cases: list[TestCase] = []
        
        # 1. 缺少必要header测试
        if headers:
            self._case_counter += 1
            cases.append(TestCase(
                id=f"TC{self._case_counter:04d}",
                name="异常测试 - 缺少Header",
                description="测试缺少必要Header的情况",
                category=TestCaseCategory.EXCEPTION,
                priority=TestCasePriority.HIGH,
                method=method,
                url=url,
                headers={},  # 空header
                body=sample_bodies[0] if sample_bodies else None,
                expected=ExpectedResult(status_code=401),
                tags=["exception", "auth"]
            ))
        
        # 2. 空body测试（对于需要body的请求）
        if method.upper() in ["POST", "PUT", "PATCH"] and sample_bodies:
            self._case_counter += 1
            cases.append(TestCase(
                id=f"TC{self._case_counter:04d}",
                name="异常测试 - 空请求体",
                description="测试请求体为空的情况",
                category=TestCaseCategory.EXCEPTION,
                priority=TestCasePriority.HIGH,
                method=method,
                url=url,
                headers=headers.copy(),
                body={},
                expected=ExpectedResult(status_code=400),
                tags=["exception", "validation"]
            ))
        
        # 3. 无效JSON测试
        if sample_bodies:
            self._case_counter += 1
            cases.append(TestCase(
                id=f"TC{self._case_counter:04d}",
                name="异常测试 - 类型错误",
                description="测试字段类型错误的情况",
                category=TestCaseCategory.EXCEPTION,
                priority=TestCasePriority.MEDIUM,
                method=method,
                url=url,
                headers=headers.copy(),
                body={"invalid": "type_test", "page": "not_a_number"},
                expected=ExpectedResult(status_code=400),
                tags=["exception", "type-error"]
            ))
        
        return cases
    
    def _generate_llm_cases(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        sample_bodies: list[dict[str, Any]],
        test_strategy: str
    ) -> list[TestCase]:
        """使用LLM生成测试用例（带知识库增强）"""
        try:
            # 尝试使用知识增强的LLM生成
            if self._knowledge_enabled and self._knowledge_chain and self._rag_builder:
                return self._generate_knowledge_enhanced_cases(
                    method, url, headers, sample_bodies, test_strategy
                )
            
            # 降级到普通LLM生成
            return self._generate_basic_llm_cases(
                method, url, headers, sample_bodies, test_strategy
            )
            
        except Exception as e:
            self.logger.error(f"LLM生成测试用例失败: {e}")
            return []
    
    def _generate_knowledge_enhanced_cases(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        sample_bodies: list[dict[str, Any]],
        test_strategy: str
    ) -> list[TestCase]:
        """使用知识库增强的LLM生成测试用例"""
        self.logger.ai_start("知识增强测试用例生成", f"{method} {url}")
        
        # 构建API信息
        api_info = {
            "method": method,
            "url": url,
            "headers": headers,
            "sample_bodies": sample_bodies
        }
        
        sample_requests = [
            {"method": method, "url": url, "body": body}
            for body in sample_bodies
        ]
        
        # 构建RAG上下文
        query = f"{method} {url} 接口测试"
        knowledge_context = self._rag_builder.build_context(
            query=query,
            scope=url,
            max_entries=10
        )
        
        if knowledge_context:
            self.logger.info(f"检索到相关知识，构建RAG上下文")
        
        # 使用知识增强的Chain生成
        result = self._knowledge_chain.generate_test_cases(
            api_info=api_info,
            sample_requests=sample_requests,
            knowledge_context=knowledge_context or "无特定知识库信息",
            test_strategy=test_strategy
        )
        
        cases = self._parse_llm_test_cases(result, method, url, headers)
        
        # 记录知识使用情况
        if knowledge_context and cases:
            self._record_knowledge_usage(url, len(cases))
        
        self.logger.ai_end(f"生成 {len(cases)} 个知识增强用例")
        return cases[:5]
    
    def _generate_basic_llm_cases(
        self,
        method: str,
        url: str,
        headers: dict[str, str],
        sample_bodies: list[dict[str, Any]],
        test_strategy: str
    ) -> list[TestCase]:
        """使用基础LLM生成测试用例"""
        self.logger.ai_start("LLM测试用例生成", f"{method} {url}")
        
        api_info = {
            "method": method,
            "url": url,
            "headers": headers,
            "sample_bodies": sample_bodies
        }
        
        sample_requests = [
            {"method": method, "url": url, "body": body}
            for body in sample_bodies
        ]
        
        result = self.llm_chain.generate_test_cases(
            api_info=api_info,
            sample_requests=sample_requests,
            test_strategy=test_strategy
        )
        
        cases = self._parse_llm_test_cases(result, method, url, headers)
        
        self.logger.ai_end(f"生成 {len(cases)} 个用例")
        return cases[:5]
    
    def _parse_llm_test_cases(
        self,
        result: dict[str, Any],
        method: str,
        url: str,
        headers: dict[str, str]
    ) -> list[TestCase]:
        """解析LLM返回的测试用例"""
        cases: list[TestCase] = []
        
        for tc_data in result.get("test_cases", []):
            try:
                self._case_counter += 1
                
                # 处理知识增强生成的格式
                request_data = tc_data.get("request", tc_data)
                expected_data = tc_data.get("expected", {})
                
                case = TestCase(
                    id=f"TC{self._case_counter:04d}",
                    name=tc_data.get("name", "LLM生成用例"),
                    description=tc_data.get("description", ""),
                    category=TestCaseCategory(tc_data.get("category", "normal")),
                    priority=TestCasePriority(tc_data.get("priority", "medium")),
                    method=request_data.get("method", method),
                    url=request_data.get("url", url),
                    headers=request_data.get("headers", tc_data.get("headers", headers)),
                    body=request_data.get("body", tc_data.get("body")),
                    query_params=request_data.get("query_params", tc_data.get("query_params", {})),
                    expected=ExpectedResult(
                        status_code=expected_data.get("status_code", tc_data.get("expected_status", 200)),
                        max_response_time_ms=expected_data.get("max_response_time_ms", 3000)
                    ),
                    tags=["llm-generated"] + tc_data.get("knowledge_applied", [])
                )
                cases.append(case)
            except Exception:
                continue
        
        return cases
    
    def _record_knowledge_usage(self, scope: str, case_count: int) -> None:
        """记录知识使用情况（用于反馈优化）"""
        try:
            if self._knowledge_retriever:
                # 简单记录，后续可扩展为详细的使用追踪
                self.logger.debug(f"知识库使用: scope={scope}, generated_cases={case_count}")
        except Exception:
            pass
    
    def _extract_endpoint_name(self, url: str) -> str:
        """从URL提取接口名称"""
        path = url.split('?')[0]
        parts = path.strip('/').split('/')
        return parts[-1] if parts else "unknown"
    
    def export_test_cases(
        self,
        test_cases: list[TestCase],
        output_path: str,
        format: str = "json"
    ) -> str:
        """导出测试用例"""
        from pathlib import Path
        from datetime import datetime
        
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == "json":
            data = {
                "test_suite": {
                    "total_cases": len(test_cases),
                    "generated_at": datetime.now().isoformat()
                },
                "test_cases": [tc.to_dict() for tc in test_cases]
            }
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        
        elif format == "curl":
            with open(path, 'w', encoding='utf-8') as f:
                for tc in test_cases:
                    f.write(f"# {tc.id}: {tc.name}\n")
                    f.write(f"# {tc.description}\n")
                    f.write(tc.to_curl() + "\n\n")
        
        return str(path)
