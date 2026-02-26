"""
测试用例生成器测试

重点测试 Swagger 2.0 / OpenAPI 3.0 body 格式兼容
"""

import pytest
from ai_test_tool.services.endpoint_test_generator import EndpointTestGeneratorService


class TestExtractBodySchema:
    """_extract_body_schema 和 _generate_request_body 格式兼容测试"""

    def setup_method(self):
        self.service = EndpointTestGeneratorService.__new__(EndpointTestGeneratorService)

    def test_openapi3_format(self):
        """OpenAPI 3.0 格式：content.application/json.schema"""
        request_body = {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "example": "Alice"},
                            "age": {"type": "integer"}
                        }
                    }
                }
            }
        }
        schema = self.service._extract_body_schema(request_body)
        assert schema["type"] == "object"
        assert "name" in schema["properties"]

        body = self.service._generate_request_body(request_body)
        assert body["name"] == "Alice"  # 使用 example
        assert body["age"] == 1  # 默认整数

    def test_swagger2_format(self):
        """Swagger 2.0 格式：schema 直接在顶层"""
        request_body = {
            "required": True,
            "schema": {
                "type": "object",
                "properties": {
                    "username": {"type": "string"},
                    "password": {"type": "string"},
                    "remember": {"type": "boolean"}
                }
            },
            "description": "Login credentials"
        }
        schema = self.service._extract_body_schema(request_body)
        assert "properties" in schema
        assert "username" in schema["properties"]

        body = self.service._generate_request_body(request_body)
        assert body["username"] == "test_username"
        assert body["password"] == "test_password"
        assert body["remember"] is True

    def test_empty_request_body(self):
        """空请求体应返回空字典"""
        assert self.service._extract_body_schema({}) == {}
        assert self.service._generate_request_body({}) == {}

    def test_schema_with_example(self):
        """schema 有 example 时应直接使用"""
        request_body = {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "example": {"foo": "bar", "count": 42},
                        "properties": {
                            "foo": {"type": "string"},
                            "count": {"type": "integer"}
                        }
                    }
                }
            }
        }
        body = self.service._generate_request_body(request_body)
        assert body == {"foo": "bar", "count": 42}

    def test_property_types(self):
        """各种属性类型应生成正确的示例值"""
        request_body = {
            "schema": {
                "type": "object",
                "properties": {
                    "str_field": {"type": "string"},
                    "int_field": {"type": "integer"},
                    "num_field": {"type": "number"},
                    "bool_field": {"type": "boolean"},
                    "arr_field": {"type": "array"},
                    "obj_field": {"type": "object"}
                }
            }
        }
        body = self.service._generate_request_body(request_body)
        assert isinstance(body["str_field"], str)
        assert isinstance(body["int_field"], int)
        assert isinstance(body["num_field"], float)
        assert isinstance(body["bool_field"], bool)
        assert isinstance(body["arr_field"], list)
        assert isinstance(body["obj_field"], dict)

    def test_property_with_default(self):
        """属性有 default 时应使用默认值"""
        request_body = {
            "schema": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "default": "active"},
                    "count": {"type": "integer", "default": 10}
                }
            }
        }
        body = self.service._generate_request_body(request_body)
        assert body["status"] == "active"
        assert body["count"] == 10


class TestBoundaryCasesBodyCompat:
    """_create_boundary_cases 的 body 格式兼容测试"""

    def setup_method(self):
        self.service = EndpointTestGeneratorService.__new__(EndpointTestGeneratorService)

    def test_swagger2_body_params_extracted(self):
        """Swagger 2.0 格式的 request_body 中的属性应被提取为边界测试参数"""
        endpoint = {"method": "POST", "path": "/users"}
        parameters = []
        request_body = {
            "schema": {
                "type": "object",
                "properties": {
                    "age": {"type": "integer", "minimum": 0, "maximum": 150},
                    "name": {"type": "string", "maxLength": 100}
                }
            }
        }
        cases = self.service._create_boundary_cases(endpoint, parameters, request_body)
        # 应为 age 和 name 生成边界测试
        assert len(cases) > 0
        case_names = [c.name for c in cases]
        assert any("age" in name for name in case_names)

    def test_openapi3_body_params_extracted(self):
        """OpenAPI 3.0 格式同样应提取参数"""
        endpoint = {"method": "POST", "path": "/items"}
        parameters = []
        request_body = {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "price": {"type": "number", "minimum": 0, "maximum": 99999},
                            "title": {"type": "string", "maxLength": 200}
                        }
                    }
                }
            }
        }
        cases = self.service._create_boundary_cases(endpoint, parameters, request_body)
        assert len(cases) > 0
        case_names = [c.name for c in cases]
        assert any("price" in name for name in case_names)


class TestGenerateSampleValue:
    """_generate_sample_value 测试"""

    def setup_method(self):
        self.service = EndpointTestGeneratorService.__new__(EndpointTestGeneratorService)

    def test_integer_param(self):
        val = self.service._generate_sample_value({"type": "integer"})
        assert val == "1"

    def test_example_takes_priority(self):
        val = self.service._generate_sample_value({"type": "string", "schema": {"example": "hello"}})
        # example 在 schema 内，param 外层没有 example 时走 type
        val2 = self.service._generate_sample_value({"type": "string", "example": "hello"})
        assert val2 == "hello"

    def test_enum_value(self):
        val = self.service._generate_sample_value({"type": "string", "enum": ["active", "inactive"]})
        assert val == "active"

    def test_email_format(self):
        val = self.service._generate_sample_value({"type": "string", "format": "email"})
        assert "@" in val
