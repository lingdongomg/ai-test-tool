"""
Postman 解析器测试

重点测试 headers 保存到 parameters
"""

import pytest
from ai_test_tool.importer.postman_parser import PostmanParser


POSTMAN_COLLECTION = {
    "info": {
        "_postman_id": "test-collection",
        "name": "Test API",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
    },
    "item": [
        {
            "name": "Auth",
            "item": [
                {
                    "name": "Login",
                    "request": {
                        "method": "POST",
                        "header": [
                            {"key": "Content-Type", "value": "application/json"},
                            {"key": "X-API-Key", "value": "test-key-123", "description": "API key"},
                            {"key": "X-Disabled", "value": "skip", "disabled": True}
                        ],
                        "body": {
                            "mode": "raw",
                            "raw": '{"username": "admin", "password": "secret"}',
                            "options": {"raw": {"language": "json"}}
                        },
                        "url": {
                            "raw": "https://api.example.com/auth/login",
                            "path": ["auth", "login"],
                            "query": [
                                {"key": "redirect", "value": "/dashboard", "description": "Redirect URL"}
                            ]
                        }
                    }
                }
            ]
        },
        {
            "name": "Get User",
            "request": {
                "method": "GET",
                "header": [
                    {"key": "Authorization", "value": "Bearer {{token}}"}
                ],
                "url": {
                    "raw": "https://api.example.com/users/:userId",
                    "path": ["users", ":userId"],
                    "variable": [
                        {"key": "userId", "value": "123", "description": "User ID"}
                    ]
                }
            }
        }
    ]
}


class TestPostmanParserHeaders:
    """Postman 解析器 headers 测试"""

    def setup_method(self):
        self.parser = PostmanParser()
        self.parser.source_file = "test.json"

    def test_headers_stored_as_parameters(self):
        """请求头应作为 in: header 类型参数保存"""
        endpoints = self.parser.parse(POSTMAN_COLLECTION)
        login_ep = next(e for e in endpoints if e.method == "POST")

        header_params = [p for p in login_ep.parameters if p["in"] == "header"]
        # Content-Type 和 X-API-Key（X-Disabled 被跳过因为 disabled=True）
        assert len(header_params) == 2

        header_names = {p["name"] for p in header_params}
        assert "Content-Type" in header_names
        assert "X-API-Key" in header_names
        assert "X-Disabled" not in header_names  # disabled 的 header 不应包含

    def test_query_params_preserved(self):
        """查询参数应正确保留"""
        endpoints = self.parser.parse(POSTMAN_COLLECTION)
        login_ep = next(e for e in endpoints if e.method == "POST")

        query_params = [p for p in login_ep.parameters if p["in"] == "query"]
        assert len(query_params) == 1
        assert query_params[0]["name"] == "redirect"

    def test_path_params_preserved(self):
        """路径参数应正确保留"""
        endpoints = self.parser.parse(POSTMAN_COLLECTION)
        get_user = next(e for e in endpoints if e.method == "GET")

        path_params = [p for p in get_user.parameters if p["in"] == "path"]
        assert len(path_params) == 1
        assert path_params[0]["name"] == "userId"

    def test_request_body_parsed(self):
        """请求体应正确解析"""
        endpoints = self.parser.parse(POSTMAN_COLLECTION)
        login_ep = next(e for e in endpoints if e.method == "POST")

        rb = login_ep.request_body
        assert rb["mode"] == "raw"
        assert "content" in rb

    def test_folder_as_tags(self):
        """文件夹名应作为标签"""
        endpoints = self.parser.parse(POSTMAN_COLLECTION)
        login_ep = next(e for e in endpoints if e.method == "POST")
        assert "Auth" in login_ep.tags

    def test_tags_extracted(self):
        """文件夹标签应被提取"""
        self.parser.parse(POSTMAN_COLLECTION)
        tags = self.parser.get_tags()
        assert "Auth" in tags

    def test_endpoint_count(self):
        """端点数量正确"""
        endpoints = self.parser.parse(POSTMAN_COLLECTION)
        assert len(endpoints) == 2
