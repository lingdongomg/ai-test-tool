"""
功能1: 接口文档自动生成测试用例服务
根据导入的接口文档，为每个接口自动生成完整的测试用例
"""

import json
import hashlib
from typing import Any
from dataclasses import dataclass, field
from datetime import datetime

from ..database import get_db_manager
from ..database.models import ApiEndpoint, TestCaseRecord, TestCaseCategory, TestCasePriority
from ..llm.chains import TestCaseGeneratorChain
from ..llm.provider import get_llm_provider
from ..utils.logger import get_logger


@dataclass
class GeneratedTestCase:
    """生成的测试用例"""
    name: str
    description: str
    category: str  # normal, boundary, exception, security
    priority: str  # high, medium, low
    method: str
    url: str
    headers: dict[str, str] = field(default_factory=dict)
    body: dict[str, Any] | None = None
    query_params: dict[str, str] = field(default_factory=dict)
    expected_status_code: int = 200
    assertions: list[dict[str, Any]] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


class EndpointTestGeneratorService:
    """
    接口测试用例生成服务
    
    功能：
    1. 从接口文档自动生成测试用例
    2. 支持多种测试类型：正常、边界、异常、安全
    3. 基于接口参数定义智能生成测试数据
    4. 支持批量生成和单接口生成
    """
    
    def __init__(self, verbose: bool = False):
        self.logger = get_logger(verbose)
        self.verbose = verbose
        self.db = get_db_manager()
        self._llm_chain: TestCaseGeneratorChain | None = None
    
    @property
    def llm_chain(self) -> TestCaseGeneratorChain:
        """懒加载 LLM Chain"""
        if self._llm_chain is None:
            provider = get_llm_provider()
            self._llm_chain = TestCaseGeneratorChain(provider, self.verbose)
        return self._llm_chain
    
    def generate_for_endpoint(
        self,
        endpoint_id: str,
        test_types: list[str] | None = None,
        save_to_db: bool = True
    ) -> list[GeneratedTestCase]:
        """
        为单个接口生成测试用例
        
        Args:
            endpoint_id: 接口ID
            test_types: 要生成的测试类型，默认全部
            save_to_db: 是否保存到数据库
            
        Returns:
            生成的测试用例列表
        """
        # 获取接口信息
        endpoint = self._get_endpoint(endpoint_id)
        if not endpoint:
            raise ValueError(f"接口不存在: {endpoint_id}")
        
        self.logger.info(f"为接口生成测试用例: {endpoint['method']} {endpoint['path']}")
        
        # 生成测试用例
        test_cases = self._generate_test_cases(endpoint, test_types)
        
        # 保存到数据库
        if save_to_db and test_cases:
            self._save_test_cases(endpoint_id, test_cases)
        
        return test_cases
    
    def generate_for_all_endpoints(
        self,
        tag_filter: str | None = None,
        test_types: list[str] | None = None,
        skip_existing: bool = True,
        save_to_db: bool = True
    ) -> dict[str, Any]:
        """
        为所有接口批量生成测试用例
        
        Args:
            tag_filter: 按标签筛选接口
            test_types: 要生成的测试类型
            skip_existing: 是否跳过已有测试用例的接口
            save_to_db: 是否保存到数据库
            
        Returns:
            生成统计结果
        """
        self.logger.start_step("批量生成测试用例")
        
        # 获取所有接口
        endpoints = self._get_all_endpoints(tag_filter)
        
        if skip_existing:
            # 过滤掉已有测试用例的接口
            endpoints = self._filter_endpoints_without_cases(endpoints)
        
        total = len(endpoints)
        success_count = 0
        failed_count = 0
        total_cases = 0
        errors: list[str] = []
        
        for i, endpoint in enumerate(endpoints):
            try:
                self.logger.debug(f"处理接口 {i+1}/{total}: {endpoint['method']} {endpoint['path']}")
                
                test_cases = self._generate_test_cases(endpoint, test_types)
                
                if save_to_db and test_cases:
                    self._save_test_cases(endpoint['endpoint_id'], test_cases)
                
                success_count += 1
                total_cases += len(test_cases)
                
            except Exception as e:
                failed_count += 1
                errors.append(f"{endpoint['method']} {endpoint['path']}: {str(e)}")
                self.logger.error(f"生成失败: {e}")
        
        self.logger.end_step(f"完成: {success_count}个接口, {total_cases}个用例")
        
        return {
            "total_endpoints": total,
            "success_count": success_count,
            "failed_count": failed_count,
            "total_cases_generated": total_cases,
            "errors": errors
        }
    
    def _generate_test_cases(
        self,
        endpoint: dict[str, Any],
        test_types: list[str] | None = None
    ) -> list[GeneratedTestCase]:
        """生成测试用例的核心逻辑"""
        test_types = test_types or ["normal", "boundary", "exception", "security"]
        test_cases: list[GeneratedTestCase] = []
        
        # 1. 基于规则生成基础测试用例
        rule_based_cases = self._generate_rule_based_cases(endpoint, test_types)
        test_cases.extend(rule_based_cases)
        
        # 2. 使用 AI 增强生成更智能的测试用例
        try:
            ai_cases = self._generate_ai_cases(endpoint, test_types)
            test_cases.extend(ai_cases)
        except Exception as e:
            self.logger.warn(f"AI 生成失败，仅使用规则生成: {e}")
        
        # 去重
        test_cases = self._deduplicate_cases(test_cases)
        
        return test_cases
    
    def _generate_rule_based_cases(
        self,
        endpoint: dict[str, Any],
        test_types: list[str]
    ) -> list[GeneratedTestCase]:
        """基于规则生成测试用例"""
        cases: list[GeneratedTestCase] = []
        
        method = endpoint['method']
        path = endpoint['path']
        parameters = endpoint.get('parameters') or []
        request_body = endpoint.get('request_body') or {}
        
        # 解析参数
        if isinstance(parameters, str):
            parameters = json.loads(parameters) if parameters else []
        if isinstance(request_body, str):
            request_body = json.loads(request_body) if request_body else {}
        
        # 1. 正常场景测试
        if "normal" in test_types:
            cases.append(self._create_normal_case(endpoint, parameters, request_body))
        
        # 2. 边界值测试
        if "boundary" in test_types:
            cases.extend(self._create_boundary_cases(endpoint, parameters, request_body))
        
        # 3. 异常场景测试
        if "exception" in test_types:
            cases.extend(self._create_exception_cases(endpoint, parameters, request_body))
        
        # 4. 安全测试
        if "security" in test_types:
            cases.extend(self._create_security_cases(endpoint, parameters, request_body))
        
        return cases
    
    def _create_normal_case(
        self,
        endpoint: dict[str, Any],
        parameters: list[dict],
        request_body: dict
    ) -> GeneratedTestCase:
        """创建正常场景测试用例"""
        method = endpoint['method']
        path = endpoint['path']
        
        # 生成正常的请求参数
        query_params = {}
        headers = {"Content-Type": "application/json"}
        body = None
        
        # 处理 query 参数
        for param in parameters:
            if param.get('in') == 'query':
                query_params[param['name']] = self._generate_sample_value(param)
        
        # 处理 request body
        if request_body and method.upper() in ['POST', 'PUT', 'PATCH']:
            body = self._generate_request_body(request_body)
        
        return GeneratedTestCase(
            name=f"正常请求 - {endpoint.get('name', path)}",
            description=f"验证 {method} {path} 接口的正常请求场景",
            category="normal",
            priority="high",
            method=method,
            url=path,
            headers=headers,
            body=body,
            query_params=query_params,
            expected_status_code=200,
            assertions=[
                {"type": "status_code", "operator": "equals", "expected": 200},
                {"type": "response_time", "operator": "less_than", "expected": 3000}
            ],
            tags=["normal", "auto-generated"]
        )
    
    def _create_boundary_cases(
        self,
        endpoint: dict[str, Any],
        parameters: list[dict],
        request_body: dict
    ) -> list[GeneratedTestCase]:
        """创建边界值测试用例"""
        cases: list[GeneratedTestCase] = []
        method = endpoint['method']
        path = endpoint['path']
        
        # 分析参数的边界值
        all_params = list(parameters)
        
        # 从 request_body 提取参数
        if request_body:
            schema = request_body.get('content', {}).get('application/json', {}).get('schema', {})
            properties = schema.get('properties', {})
            for name, prop in properties.items():
                all_params.append({
                    'name': name,
                    'in': 'body',
                    'schema': prop
                })
        
        for param in all_params:
            param_name = param.get('name', '')
            schema = param.get('schema', param)
            param_type = schema.get('type', 'string')
            
            # 数字类型边界
            if param_type in ['integer', 'number']:
                minimum = schema.get('minimum')
                maximum = schema.get('maximum')
                
                if minimum is not None:
                    cases.append(GeneratedTestCase(
                        name=f"边界值 - {param_name} 最小值",
                        description=f"测试 {param_name} 参数的最小边界值 {minimum}",
                        category="boundary",
                        priority="medium",
                        method=method,
                        url=path,
                        headers={"Content-Type": "application/json"},
                        body={param_name: minimum} if param.get('in') == 'body' else None,
                        query_params={param_name: str(minimum)} if param.get('in') == 'query' else {},
                        expected_status_code=200,
                        tags=["boundary", f"param:{param_name}"]
                    ))
                
                if maximum is not None:
                    cases.append(GeneratedTestCase(
                        name=f"边界值 - {param_name} 最大值",
                        description=f"测试 {param_name} 参数的最大边界值 {maximum}",
                        category="boundary",
                        priority="medium",
                        method=method,
                        url=path,
                        headers={"Content-Type": "application/json"},
                        body={param_name: maximum} if param.get('in') == 'body' else None,
                        query_params={param_name: str(maximum)} if param.get('in') == 'query' else {},
                        expected_status_code=200,
                        tags=["boundary", f"param:{param_name}"]
                    ))
            
            # 字符串类型边界
            elif param_type == 'string':
                min_length = schema.get('minLength', 0)
                max_length = schema.get('maxLength')
                
                # 空字符串测试
                cases.append(GeneratedTestCase(
                    name=f"边界值 - {param_name} 空字符串",
                    description=f"测试 {param_name} 参数为空字符串",
                    category="boundary",
                    priority="medium",
                    method=method,
                    url=path,
                    headers={"Content-Type": "application/json"},
                    body={param_name: ""} if param.get('in') == 'body' else None,
                    query_params={param_name: ""} if param.get('in') == 'query' else {},
                    expected_status_code=400 if schema.get('required') else 200,
                    tags=["boundary", f"param:{param_name}"]
                ))
                
                if max_length:
                    # 超长字符串测试
                    cases.append(GeneratedTestCase(
                        name=f"边界值 - {param_name} 超长字符串",
                        description=f"测试 {param_name} 参数超过最大长度 {max_length}",
                        category="boundary",
                        priority="medium",
                        method=method,
                        url=path,
                        headers={"Content-Type": "application/json"},
                        body={param_name: "x" * (max_length + 10)} if param.get('in') == 'body' else None,
                        query_params={param_name: "x" * (max_length + 10)} if param.get('in') == 'query' else {},
                        expected_status_code=400,
                        tags=["boundary", f"param:{param_name}"]
                    ))
        
        return cases[:10]  # 限制数量
    
    def _create_exception_cases(
        self,
        endpoint: dict[str, Any],
        parameters: list[dict],
        request_body: dict
    ) -> list[GeneratedTestCase]:
        """创建异常场景测试用例"""
        cases: list[GeneratedTestCase] = []
        method = endpoint['method']
        path = endpoint['path']
        
        # 1. 缺少必填参数
        required_params = [p for p in parameters if p.get('required')]
        if required_params:
            cases.append(GeneratedTestCase(
                name=f"异常 - 缺少必填参数",
                description="测试缺少所有必填参数的情况",
                category="exception",
                priority="high",
                method=method,
                url=path,
                headers={"Content-Type": "application/json"},
                body={} if method.upper() in ['POST', 'PUT', 'PATCH'] else None,
                query_params={},
                expected_status_code=400,
                assertions=[
                    {"type": "status_code", "operator": "in", "expected": [400, 422]}
                ],
                tags=["exception", "validation"]
            ))
        
        # 2. 类型错误
        for param in parameters[:3]:
            param_name = param.get('name', '')
            schema = param.get('schema', param)
            param_type = schema.get('type', 'string')
            
            if param_type in ['integer', 'number']:
                # 传字符串给数字类型
                cases.append(GeneratedTestCase(
                    name=f"异常 - {param_name} 类型错误",
                    description=f"测试 {param_name} 参数传入字符串而非数字",
                    category="exception",
                    priority="high",
                    method=method,
                    url=path,
                    headers={"Content-Type": "application/json"},
                    body={param_name: "not_a_number"} if param.get('in') == 'body' else None,
                    query_params={param_name: "not_a_number"} if param.get('in') == 'query' else {},
                    expected_status_code=400,
                    tags=["exception", "type-error", f"param:{param_name}"]
                ))
        
        # 3. 无效的 HTTP 方法
        invalid_methods = ['DELETE', 'PATCH'] if method.upper() == 'GET' else ['GET']
        for invalid_method in invalid_methods[:1]:
            cases.append(GeneratedTestCase(
                name=f"异常 - 无效HTTP方法 {invalid_method}",
                description=f"测试使用 {invalid_method} 方法请求接口",
                category="exception",
                priority="low",
                method=invalid_method,
                url=path,
                headers={"Content-Type": "application/json"},
                expected_status_code=405,
                tags=["exception", "method-not-allowed"]
            ))
        
        # 4. 空请求体（对于需要body的接口）
        if method.upper() in ['POST', 'PUT', 'PATCH'] and request_body:
            cases.append(GeneratedTestCase(
                name=f"异常 - 空请求体",
                description="测试请求体为空的情况",
                category="exception",
                priority="high",
                method=method,
                url=path,
                headers={"Content-Type": "application/json"},
                body={},
                expected_status_code=400,
                tags=["exception", "empty-body"]
            ))
        
        return cases
    
    def _create_security_cases(
        self,
        endpoint: dict[str, Any],
        parameters: list[dict],
        request_body: dict
    ) -> list[GeneratedTestCase]:
        """创建安全测试用例"""
        cases: list[GeneratedTestCase] = []
        method = endpoint['method']
        path = endpoint['path']
        
        # 1. SQL 注入测试
        sql_payloads = ["' OR '1'='1", "1; DROP TABLE users--", "1 UNION SELECT * FROM users"]
        for param in parameters[:2]:
            param_name = param.get('name', '')
            cases.append(GeneratedTestCase(
                name=f"安全 - SQL注入 {param_name}",
                description=f"测试 {param_name} 参数的 SQL 注入防护",
                category="security",
                priority="high",
                method=method,
                url=path,
                headers={"Content-Type": "application/json"},
                body={param_name: sql_payloads[0]} if param.get('in') == 'body' else None,
                query_params={param_name: sql_payloads[0]} if param.get('in') == 'query' else {},
                expected_status_code=400,
                assertions=[
                    {"type": "status_code", "operator": "in", "expected": [400, 403, 200]},
                    {"type": "response_body", "operator": "not_contains", "expected": "error"}
                ],
                tags=["security", "sql-injection", f"param:{param_name}"]
            ))
        
        # 2. XSS 测试
        xss_payload = "<script>alert('xss')</script>"
        for param in parameters[:2]:
            param_name = param.get('name', '')
            schema = param.get('schema', param)
            if schema.get('type') == 'string':
                cases.append(GeneratedTestCase(
                    name=f"安全 - XSS {param_name}",
                    description=f"测试 {param_name} 参数的 XSS 防护",
                    category="security",
                    priority="high",
                    method=method,
                    url=path,
                    headers={"Content-Type": "application/json"},
                    body={param_name: xss_payload} if param.get('in') == 'body' else None,
                    query_params={param_name: xss_payload} if param.get('in') == 'query' else {},
                    expected_status_code=200,
                    assertions=[
                        {"type": "response_body", "operator": "not_contains", "expected": "<script>"}
                    ],
                    tags=["security", "xss", f"param:{param_name}"]
                ))
        
        # 3. 未授权访问测试
        cases.append(GeneratedTestCase(
            name=f"安全 - 未授权访问",
            description="测试不带认证信息的请求",
            category="security",
            priority="high",
            method=method,
            url=path,
            headers={},  # 不带认证头
            expected_status_code=401,
            assertions=[
                {"type": "status_code", "operator": "in", "expected": [401, 403, 200]}
            ],
            tags=["security", "auth"]
        ))
        
        return cases[:5]  # 限制数量
    
    def _generate_ai_cases(
        self,
        endpoint: dict[str, Any],
        test_types: list[str]
    ) -> list[GeneratedTestCase]:
        """使用 AI 生成更智能的测试用例"""
        self.logger.ai_start("AI测试用例生成", f"{endpoint['method']} {endpoint['path']}")
        
        # 准备 API 信息
        api_info = {
            "method": endpoint['method'],
            "path": endpoint['path'],
            "name": endpoint.get('name', ''),
            "description": endpoint.get('description', ''),
            "parameters": endpoint.get('parameters', []),
            "request_body": endpoint.get('request_body', {}),
            "responses": endpoint.get('responses', {})
        }
        
        # 调用 LLM 生成
        result = self.llm_chain.generate_test_cases(
            api_info=api_info,
            sample_requests=[],
            test_strategy="comprehensive"
        )
        
        cases: list[GeneratedTestCase] = []
        for tc_data in result.get("test_cases", []):
            try:
                case = GeneratedTestCase(
                    name=tc_data.get("name", "AI生成用例"),
                    description=tc_data.get("description", ""),
                    category=tc_data.get("category", "normal"),
                    priority=tc_data.get("priority", "medium"),
                    method=tc_data.get("request", {}).get("method", endpoint['method']),
                    url=tc_data.get("request", {}).get("url", endpoint['path']),
                    headers=tc_data.get("request", {}).get("headers", {}),
                    body=tc_data.get("request", {}).get("body"),
                    query_params=tc_data.get("request", {}).get("query_params", {}),
                    expected_status_code=tc_data.get("expected", {}).get("status_code", 200),
                    assertions=tc_data.get("assertions", []),
                    tags=["ai-generated"] + tc_data.get("tags", [])
                )
                cases.append(case)
            except Exception:
                continue
        
        self.logger.ai_end(f"生成 {len(cases)} 个用例")
        return cases[:5]  # 限制 AI 生成数量
    
    def _generate_sample_value(self, param: dict) -> str:
        """根据参数定义生成示例值"""
        schema = param.get('schema', param)
        param_type = schema.get('type', 'string')
        param_format = schema.get('format', '')
        enum_values = schema.get('enum')
        example = schema.get('example')
        default = schema.get('default')
        
        if example is not None:
            return str(example)
        if default is not None:
            return str(default)
        if enum_values:
            return str(enum_values[0])
        
        if param_type == 'integer':
            return "1"
        elif param_type == 'number':
            return "1.0"
        elif param_type == 'boolean':
            return "true"
        elif param_format == 'date':
            return datetime.now().strftime('%Y-%m-%d')
        elif param_format == 'date-time':
            return datetime.now().isoformat()
        elif param_format == 'email':
            return "test@example.com"
        elif param_format == 'uuid':
            return "550e8400-e29b-41d4-a716-446655440000"
        else:
            return "test_value"
    
    def _generate_request_body(self, request_body: dict) -> dict[str, Any]:
        """根据 request_body 定义生成请求体"""
        content = request_body.get('content', {})
        json_content = content.get('application/json', {})
        schema = json_content.get('schema', {})
        
        if schema.get('example'):
            return schema['example']
        
        properties = schema.get('properties', {})
        body: dict[str, Any] = {}
        
        for name, prop in properties.items():
            prop_type = prop.get('type', 'string')
            example = prop.get('example')
            default = prop.get('default')
            
            if example is not None:
                body[name] = example
            elif default is not None:
                body[name] = default
            elif prop_type == 'string':
                body[name] = f"test_{name}"
            elif prop_type == 'integer':
                body[name] = 1
            elif prop_type == 'number':
                body[name] = 1.0
            elif prop_type == 'boolean':
                body[name] = True
            elif prop_type == 'array':
                body[name] = []
            elif prop_type == 'object':
                body[name] = {}
        
        return body
    
    def _deduplicate_cases(self, cases: list[GeneratedTestCase]) -> list[GeneratedTestCase]:
        """去重测试用例"""
        seen: set[str] = set()
        unique_cases: list[GeneratedTestCase] = []
        
        for case in cases:
            # 基于关键字段生成唯一标识
            key = f"{case.method}:{case.url}:{case.category}:{json.dumps(case.body, sort_keys=True) if case.body else ''}"
            key_hash = hashlib.md5(key.encode()).hexdigest()
            
            if key_hash not in seen:
                seen.add(key_hash)
                unique_cases.append(case)
        
        return unique_cases
    
    def _get_endpoint(self, endpoint_id: str) -> dict[str, Any] | None:
        """获取单个接口"""
        sql = "SELECT * FROM api_endpoints WHERE endpoint_id = %s"
        row = self.db.fetch_one(sql, (endpoint_id,))
        if row:
            return self._parse_endpoint_row(row)
        return None
    
    def _get_all_endpoints(self, tag_filter: str | None = None) -> list[dict[str, Any]]:
        """获取所有接口"""
        if tag_filter:
            sql = """
                SELECT e.* FROM api_endpoints e
                JOIN api_endpoint_tags et ON e.endpoint_id = et.endpoint_id
                JOIN api_tags t ON et.tag_id = t.id
                WHERE t.name = %s
                ORDER BY e.path, e.method
            """
            rows = self.db.fetch_all(sql, (tag_filter,))
        else:
            sql = "SELECT * FROM api_endpoints ORDER BY path, method"
            rows = self.db.fetch_all(sql)
        
        return [self._parse_endpoint_row(row) for row in rows]
    
    def _filter_endpoints_without_cases(self, endpoints: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """过滤掉已有测试用例的接口"""
        result: list[dict[str, Any]] = []
        for ep in endpoints:
            # test_cases 表没有 endpoint_id 列，通过 case_id 前缀匹配
            sql = "SELECT COUNT(*) as count FROM test_cases WHERE case_id LIKE %s"
            row = self.db.fetch_one(sql, (f"{ep['endpoint_id']}%",))
            if row and row['count'] == 0:
                result.append(ep)
        return result
    
    def _parse_endpoint_row(self, row: dict[str, Any]) -> dict[str, Any]:
        """解析数据库行"""
        endpoint = dict(row)
        if isinstance(endpoint.get('parameters'), str):
            endpoint['parameters'] = json.loads(endpoint['parameters']) if endpoint['parameters'] else []
        if isinstance(endpoint.get('request_body'), str):
            endpoint['request_body'] = json.loads(endpoint['request_body']) if endpoint['request_body'] else {}
        if isinstance(endpoint.get('responses'), str):
            endpoint['responses'] = json.loads(endpoint['responses']) if endpoint['responses'] else {}
        return endpoint
    
    def _save_test_cases(self, endpoint_id: str, test_cases: list[GeneratedTestCase]) -> None:
        """保存测试用例到数据库"""
        for case in test_cases:
            # case_id 以 endpoint_id 为前缀，便于后续通过前缀匹配查询
            case_id = f"{endpoint_id}_{hashlib.md5(f'{case.name}:{case.category}'.encode()).hexdigest()[:8]}"
            
            # 检查是否已存在
            existing = self.db.fetch_one(
                "SELECT case_id FROM test_cases WHERE case_id = %s",
                (case_id,)
            )
            if existing:
                continue
            
            # 注意：test_cases 表没有 endpoint_id 列，使用 task_id 存储 endpoint_id
            sql = """
                INSERT INTO test_cases 
                (case_id, task_id, name, description, category, priority,
                 method, url, headers, body, query_params, expected_status_code,
                 expected_response, max_response_time_ms, tags, is_enabled)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            self.db.execute(sql, (
                case_id,
                endpoint_id,  # 使用 task_id 字段存储 endpoint_id
                case.name[:255],
                case.description[:16000] if case.description else "",
                case.category,
                case.priority,
                case.method,
                case.url,
                json.dumps(case.headers, ensure_ascii=False),
                json.dumps(case.body, ensure_ascii=False) if case.body else None,
                json.dumps(case.query_params, ensure_ascii=False),
                case.expected_status_code,
                json.dumps({}, ensure_ascii=False),  # expected_response
                3000,  # max_response_time_ms
                json.dumps(case.tags, ensure_ascii=False),
                True
            ))
        
        self.logger.debug(f"保存 {len(test_cases)} 个测试用例到数据库")
