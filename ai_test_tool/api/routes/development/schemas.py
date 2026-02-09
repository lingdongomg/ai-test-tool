"""
开发自测模块 - 请求/响应模型
该文件内容使用AI生成，注意识别准确性
"""

from pydantic import BaseModel, Field


class GenerateTestsRequest(BaseModel):
    """生成测试用例请求"""
    endpoint_ids: list[str] | None = Field(default=None, description="接口ID列表，为空则全部")
    tag_filter: str | None = Field(default=None, description="按标签筛选")
    test_types: list[str] | None = Field(
        default=None,
        description="测试类型: normal, boundary, exception, security"
    )
    use_ai: bool = Field(default=True, description="是否使用AI增强生成")
    skip_existing: bool = Field(default=True, description="跳过已有测试用例的接口")


class ExecuteTestsRequest(BaseModel):
    """执行测试请求"""
    test_case_ids: list[str] | None = Field(default=None, description="测试用例ID列表")
    endpoint_id: str | None = Field(default=None, description="按接口筛选")
    tag_filter: str | None = Field(default=None, description="按标签筛选")
    base_url: str = Field(..., description="目标服务器URL")
    environment: str = Field(default="local", description="环境: local/test/staging/production")


class TestExecutionResult(BaseModel):
    """测试执行结果"""
    execution_id: str
    total: int
    passed: int
    failed: int
    skipped: int
    pass_rate: float
    duration_ms: float


class UpdateTestCaseRequest(BaseModel):
    """更新测试用例请求"""
    name: str | None = Field(default=None, description="用例名称")
    description: str | None = Field(default=None, description="用例描述")
    category: str | None = Field(default=None, description="用例类别: normal, boundary, exception, performance, security")
    priority: str | None = Field(default=None, description="优先级: high, medium, low")
    method: str | None = Field(default=None, description="HTTP方法")
    url: str | None = Field(default=None, description="请求URL")
    headers: dict | None = Field(default=None, description="请求头")
    body: dict | None = Field(default=None, description="请求体")
    query_params: dict | None = Field(default=None, description="查询参数")
    expected_status_code: int | None = Field(default=None, description="期望状态码")
    expected_response: dict | None = Field(default=None, description="期望响应")
    assertions: list | None = Field(default=None, description="断言规则")
    max_response_time_ms: int | None = Field(default=None, description="最大响应时间(ms)")
    is_enabled: bool | None = Field(default=None, description="是否启用")
