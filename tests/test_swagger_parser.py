"""
Swagger/OpenAPI 解析器测试

重点测试 $ref 解析、参数提取、请求体解析
"""

import pytest
from ai_test_tool.importer.swagger_parser import SwaggerParser


# ===================================================================
# 测试数据
# ===================================================================

SWAGGER_2_WITH_REFS = {
    "swagger": "2.0",
    "info": {"title": "Test API", "version": "1.0"},
    "basePath": "/api",
    "paths": {
        "/users": {
            "post": {
                "summary": "Create user",
                "operationId": "createUser",
                "tags": ["users"],
                "parameters": [
                    {
                        "name": "body",
                        "in": "body",
                        "required": True,
                        "schema": {"$ref": "#/definitions/CreateUserRequest"}
                    },
                    {
                        "name": "X-Request-ID",
                        "in": "header",
                        "required": False,
                        "type": "string",
                        "description": "Request trace ID"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Success",
                        "schema": {"$ref": "#/definitions/UserResponse"}
                    },
                    "400": {
                        "description": "Bad request"
                    }
                }
            },
            "get": {
                "summary": "List users",
                "parameters": [
                    {
                        "name": "page",
                        "in": "query",
                        "required": False,
                        "type": "integer",
                        "description": "Page number"
                    },
                    {
                        "name": "size",
                        "in": "query",
                        "required": False,
                        "type": "integer",
                        "description": "Page size"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "User list",
                        "schema": {
                            "type": "array",
                            "items": {"$ref": "#/definitions/UserResponse"}
                        }
                    }
                }
            }
        },
        "/users/{id}": {
            "get": {
                "summary": "Get user by ID",
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "type": "integer"
                    }
                ],
                "responses": {
                    "200": {
                        "description": "User detail",
                        "schema": {"$ref": "#/definitions/UserResponse"}
                    }
                }
            }
        }
    },
    "definitions": {
        "CreateUserRequest": {
            "type": "object",
            "required": ["name", "email"],
            "properties": {
                "name": {"type": "string", "description": "User name", "example": "John"},
                "email": {"type": "string", "format": "email", "description": "Email address"},
                "age": {"type": "integer", "minimum": 0, "maximum": 150},
                "address": {"$ref": "#/definitions/Address"}
            }
        },
        "Address": {
            "type": "object",
            "properties": {
                "street": {"type": "string"},
                "city": {"type": "string"},
                "zip": {"type": "string"}
            }
        },
        "UserResponse": {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
                "email": {"type": "string"},
                "created_at": {"type": "string", "format": "date-time"}
            }
        }
    }
}


OPENAPI_3_WITH_REFS = {
    "openapi": "3.0.0",
    "info": {"title": "Test API", "version": "2.0"},
    "paths": {
        "/products": {
            "post": {
                "summary": "Create product",
                "tags": ["products"],
                "requestBody": {
                    "required": True,
                    "description": "Product data",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ProductRequest"}
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "Created",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Product"}
                            }
                        }
                    }
                }
            },
            "get": {
                "summary": "List products",
                "parameters": [
                    {"$ref": "#/components/parameters/PageParam"},
                    {"$ref": "#/components/parameters/SizeParam"}
                ],
                "responses": {
                    "200": {
                        "description": "Product list",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/Product"}
                                }
                            }
                        }
                    }
                }
            }
        }
    },
    "components": {
        "schemas": {
            "ProductRequest": {
                "type": "object",
                "required": ["name", "price"],
                "properties": {
                    "name": {"type": "string", "example": "Widget"},
                    "price": {"type": "number", "minimum": 0},
                    "category": {"$ref": "#/components/schemas/Category"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            },
            "Category": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"}
                }
            },
            "Product": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                    "price": {"type": "number"},
                    "created_at": {"type": "string", "format": "date-time"}
                }
            }
        },
        "parameters": {
            "PageParam": {
                "name": "page",
                "in": "query",
                "required": False,
                "schema": {"type": "integer", "default": 1},
                "description": "Page number"
            },
            "SizeParam": {
                "name": "size",
                "in": "query",
                "required": False,
                "schema": {"type": "integer", "default": 20},
                "description": "Page size"
            }
        }
    }
}


CIRCULAR_REF_DOC = {
    "swagger": "2.0",
    "info": {"title": "Circular", "version": "1.0"},
    "paths": {
        "/tree": {
            "get": {
                "summary": "Get tree",
                "responses": {
                    "200": {
                        "description": "Tree node",
                        "schema": {"$ref": "#/definitions/TreeNode"}
                    }
                }
            }
        }
    },
    "definitions": {
        "TreeNode": {
            "type": "object",
            "properties": {
                "value": {"type": "string"},
                "children": {
                    "type": "array",
                    "items": {"$ref": "#/definitions/TreeNode"}
                }
            }
        }
    }
}


SWAGGER_2_NO_REFS = {
    "swagger": "2.0",
    "info": {"title": "Simple API", "version": "1.0"},
    "paths": {
        "/health": {
            "get": {
                "summary": "Health check",
                "responses": {
                    "200": {
                        "description": "OK",
                        "schema": {"type": "object", "properties": {"status": {"type": "string"}}}
                    }
                }
            }
        }
    }
}


ALLOF_DOC = {
    "openapi": "3.0.0",
    "info": {"title": "AllOf Test", "version": "1.0"},
    "paths": {
        "/items": {
            "post": {
                "summary": "Create item",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "allOf": [
                                    {"$ref": "#/components/schemas/BaseItem"},
                                    {"$ref": "#/components/schemas/ItemExtras"}
                                ]
                            }
                        }
                    }
                },
                "responses": {"201": {"description": "Created"}}
            }
        }
    },
    "components": {
        "schemas": {
            "BaseItem": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"}
                }
            },
            "ItemExtras": {
                "type": "object",
                "properties": {
                    "weight": {"type": "number"},
                    "color": {"type": "string"}
                }
            }
        }
    }
}


# ===================================================================
# 测试用例
# ===================================================================

class TestSwaggerParserRefResolution:
    """$ref 解析测试"""

    def setup_method(self):
        self.parser = SwaggerParser()

    def test_swagger2_body_ref_resolved(self):
        """Swagger 2.0: body 参数的 $ref 应被完整展开"""
        endpoints = self.parser.parse(SWAGGER_2_WITH_REFS)
        post_ep = next(e for e in endpoints if e.method == "POST" and "/users" == e.path.rstrip("/").split("/api")[-1])

        # request_body.schema 应包含展开后的 properties
        rb = post_ep.request_body
        assert rb, "request_body should not be empty"
        schema = rb.get("schema", {})
        assert "properties" in schema, f"Schema should have properties, got: {schema}"
        props = schema["properties"]
        assert "name" in props
        assert "email" in props
        assert "age" in props
        assert props["name"]["type"] == "string"
        assert props["age"]["type"] == "integer"

    def test_swagger2_nested_ref_resolved(self):
        """Swagger 2.0: 嵌套的 $ref (Address) 应被递归展开"""
        endpoints = self.parser.parse(SWAGGER_2_WITH_REFS)
        post_ep = next(e for e in endpoints if e.method == "POST")

        schema = post_ep.request_body["schema"]
        address = schema["properties"]["address"]
        # address 不应该还是 $ref，而应是展开后的对象
        assert "$ref" not in address, f"address should be resolved, got: {address}"
        assert "properties" in address
        assert "street" in address["properties"]

    def test_swagger2_response_ref_resolved(self):
        """Swagger 2.0: 响应 schema 的 $ref 应被展开"""
        endpoints = self.parser.parse(SWAGGER_2_WITH_REFS)
        post_ep = next(e for e in endpoints if e.method == "POST")

        resp_200 = post_ep.responses.get("200", {})
        schema = resp_200.get("schema", {})
        assert "properties" in schema, f"Response schema should have properties, got: {schema}"
        assert "id" in schema["properties"]

    def test_swagger2_array_items_ref_resolved(self):
        """Swagger 2.0: 数组 items 中的 $ref 应被展开"""
        endpoints = self.parser.parse(SWAGGER_2_WITH_REFS)
        get_users = next(e for e in endpoints if e.method == "GET" and "/users" == e.path.rstrip("/").split("/api")[-1])

        resp_200 = get_users.responses["200"]
        schema = resp_200["schema"]
        assert schema["type"] == "array"
        items = schema["items"]
        assert "$ref" not in items
        assert "properties" in items
        assert "name" in items["properties"]

    def test_swagger2_parameters_preserved(self):
        """Swagger 2.0: 非 body 参数应正确保留"""
        endpoints = self.parser.parse(SWAGGER_2_WITH_REFS)
        get_users = next(e for e in endpoints if e.method == "GET" and "/users" == e.path.rstrip("/").split("/api")[-1])

        params = get_users.parameters
        assert len(params) == 2
        page_param = next(p for p in params if p["name"] == "page")
        assert page_param["in"] == "query"
        assert page_param["type"] == "integer"

    def test_openapi3_requestbody_ref_resolved(self):
        """OpenAPI 3.0: requestBody 中 schema 的 $ref 应被展开"""
        endpoints = self.parser.parse(OPENAPI_3_WITH_REFS)
        post_ep = next(e for e in endpoints if e.method == "POST")

        rb = post_ep.request_body
        assert rb["required"] is True
        schema = rb["content"]["application/json"]["schema"]
        assert "properties" in schema, f"Schema should have properties, got: {schema}"
        assert "name" in schema["properties"]
        assert "price" in schema["properties"]

    def test_openapi3_nested_ref_in_requestbody(self):
        """OpenAPI 3.0: requestBody 内嵌套的 $ref 应被递归展开"""
        endpoints = self.parser.parse(OPENAPI_3_WITH_REFS)
        post_ep = next(e for e in endpoints if e.method == "POST")

        schema = post_ep.request_body["content"]["application/json"]["schema"]
        category = schema["properties"]["category"]
        assert "$ref" not in category
        assert category["type"] == "object"
        assert "id" in category["properties"]
        assert "name" in category["properties"]

    def test_openapi3_parameter_ref_resolved(self):
        """OpenAPI 3.0: 参数级别的 $ref 应被解析"""
        endpoints = self.parser.parse(OPENAPI_3_WITH_REFS)
        get_ep = next(e for e in endpoints if e.method == "GET")

        params = get_ep.parameters
        assert len(params) == 2
        page_param = next(p for p in params if p["name"] == "page")
        assert page_param["in"] == "query"
        assert page_param["schema"]["type"] == "integer"

    def test_openapi3_response_ref_resolved(self):
        """OpenAPI 3.0: 响应 content 内的 $ref 应被展开"""
        endpoints = self.parser.parse(OPENAPI_3_WITH_REFS)
        post_ep = next(e for e in endpoints if e.method == "POST")

        resp_201 = post_ep.responses["201"]
        schema = resp_201["content"]["application/json"]["schema"]
        assert "properties" in schema
        assert "id" in schema["properties"]

    def test_circular_ref_does_not_crash(self):
        """循环引用不应导致无限递归"""
        endpoints = self.parser.parse(CIRCULAR_REF_DOC)
        assert len(endpoints) == 1
        # 应该成功解析而不崩溃
        resp = endpoints[0].responses["200"]["schema"]
        assert resp.get("type") == "object"
        assert "properties" in resp

    def test_no_refs_still_works(self):
        """没有 $ref 的文档应正常工作"""
        endpoints = self.parser.parse(SWAGGER_2_NO_REFS)
        assert len(endpoints) == 1
        assert endpoints[0].method == "GET"

    def test_allof_merge(self):
        """allOf 应被正确合并"""
        endpoints = self.parser.parse(ALLOF_DOC)
        assert len(endpoints) == 1
        rb = endpoints[0].request_body
        schema = rb["content"]["application/json"]["schema"]
        props = schema.get("properties", {})
        # 应合并 BaseItem + ItemExtras
        assert "name" in props
        assert "description" in props
        assert "weight" in props
        assert "color" in props

    def test_missing_ref_target(self):
        """引用不存在的 definition 不应崩溃"""
        doc = {
            "swagger": "2.0",
            "info": {"title": "Test", "version": "1.0"},
            "paths": {
                "/test": {
                    "post": {
                        "summary": "test",
                        "parameters": [{
                            "name": "body",
                            "in": "body",
                            "schema": {"$ref": "#/definitions/NonExistent"}
                        }],
                        "responses": {"200": {"description": "OK"}}
                    }
                }
            },
            "definitions": {}
        }
        endpoints = self.parser.parse(doc)
        assert len(endpoints) == 1
        # schema 应为空字典（引用目标不存在）
        assert endpoints[0].request_body["schema"] == {}


class TestSwaggerParserBasic:
    """基础解析测试"""

    def setup_method(self):
        self.parser = SwaggerParser()

    def test_swagger2_base_path(self):
        """Swagger 2.0: basePath 应正确拼接到路径"""
        endpoints = self.parser.parse(SWAGGER_2_WITH_REFS)
        paths = [e.path for e in endpoints]
        assert all(p.startswith("/api/") for p in paths)

    def test_swagger2_tags_extracted(self):
        """标签应被正确提取"""
        self.parser.parse(SWAGGER_2_WITH_REFS)
        tags = self.parser.get_tags()
        assert "users" in tags

    def test_openapi3_tags_extracted(self):
        """OpenAPI 3.0: 标签应被正确提取"""
        self.parser.parse(OPENAPI_3_WITH_REFS)
        tags = self.parser.get_tags()
        assert "products" in tags

    def test_endpoint_count(self):
        """Swagger 2.0: 端点数量正确"""
        endpoints = self.parser.parse(SWAGGER_2_WITH_REFS)
        assert len(endpoints) == 3  # POST /users, GET /users, GET /users/{id}

    def test_endpoint_id_unique(self):
        """端点 ID 应唯一"""
        endpoints = self.parser.parse(SWAGGER_2_WITH_REFS)
        ids = [e.endpoint_id for e in endpoints]
        assert len(ids) == len(set(ids))
