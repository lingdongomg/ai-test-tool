"""
LLM Prompt模板
定义各种场景的prompt模板
"""

# 日志解析Prompt - 核心智能分析
LOG_ANALYSIS_PROMPT = """你是一位资深的后端开发工程师和日志分析专家。请分析以下日志内容，提取所有的HTTP API请求信息。

## 日志内容
```
{log_content}
```

## 任务要求
1. 识别日志中所有的HTTP请求（GET/POST/PUT/DELETE/PATCH等）
2. 提取每个请求的完整信息
3. 识别错误、异常、警告信息
4. 分析请求之间的关联关系

## 输出格式
请严格按照以下JSON格式输出：
```json
{{
  "requests": [
    {{
      "request_id": "请求唯一标识（如果日志中有则提取，没有则生成UUID格式）",
      "timestamp": "时间戳",
      "method": "HTTP方法",
      "url": "请求URL路径",
      "headers": {{"header名": "header值"}},
      "body": "请求体（JSON字符串或null）",
      "http_status": 状态码数字,
      "response_time_ms": 响应时间毫秒数,
      "has_error": true/false,
      "error_message": "错误信息或空字符串",
      "has_warning": true/false,
      "warning_message": "警告信息或空字符串",
      "curl_command": "完整的curl命令"
    }}
  ],
  "errors": [
    {{
      "type": "错误类型",
      "message": "错误信息",
      "related_request_id": "关联的请求ID或null",
      "severity": "high/medium/low",
      "suggestion": "修复建议"
    }}
  ],
  "warnings": [
    {{
      "type": "警告类型",
      "message": "警告信息",
      "related_request_id": "关联的请求ID或null",
      "suggestion": "处理建议"
    }}
  ],
  "analysis": {{
    "total_requests": 请求总数,
    "success_count": 成功请求数,
    "error_count": 错误数,
    "warning_count": 警告数,
    "observations": ["观察到的问题或模式"]
  }}
}}
```

## 注意事项
1. 如果某个字段在日志中找不到，使用合理的默认值
2. curl命令要完整可执行，包含所有必要的headers和body
3. 仔细分析日志格式，不同系统的日志格式可能不同
4. 识别关联的日志行（同一请求可能有多行日志）

请开始分析："""


# 日志分类Prompt
LOG_CATEGORIZATION_PROMPT = """你是一位API架构师，请对以下API请求进行智能分类。

## 请求列表
```json
{requests_json}
```

## 分类要求
根据URL路径和业务语义进行分类，常见分类包括但不限于：
- 用户管理（user/auth/login/register）
- 商品管理（product/goods/item）
- 订单管理（order/trade）
- 支付相关（pay/payment）
- 文件上传（upload/file/cos）
- 系统配置（config/setting）
- 数据统计（stat/analytics）

## 输出格式
```json
{{
  "categorized_requests": [
    {{
      "url": "请求URL",
      "category": "分类名称",
      "sub_category": "子分类（可选）"
    }}
  ],
  "category_summary": {{
    "分类名称": 数量
  }}
}}
```

请开始分类："""


# 分析报告生成Prompt
ANALYSIS_REPORT_PROMPT = """你是一位资深的技术分析师，请根据以下数据生成一份专业的日志分析报告。

## 统计摘要
```json
{summary_data}
```

## 错误日志
```json
{error_logs}
```

## 警告日志
```json
{warning_logs}
```

## 性能数据
```json
{performance_data}
```

## 报告要求
请生成一份Markdown格式的分析报告，包含：

1. **执行摘要**：简要概述日志分析结果
2. **请求统计**：请求数量、成功率、响应时间分布
3. **问题分析**：
   - 错误分析：错误类型、频率、根因分析
   - 警告分析：警告类型、潜在风险
   - 性能问题：慢请求、超时等
4. **接口分类统计**：各类接口的调用情况
5. **风险评估**：识别潜在的系统风险
6. **改进建议**：具体可执行的优化建议

请使用专业但易懂的语言，适合技术团队阅读。"""


# 测试用例生成Prompt
TEST_CASE_GENERATION_PROMPT = """你是一位资深的测试工程师，请根据以下API信息生成测试用例。

## API信息
```json
{api_info}
```

## 示例请求
```json
{sample_requests}
```

## 测试策略: {test_strategy}
- comprehensive: 全面测试（正常、边界、异常、安全）
- quick: 快速测试（仅正常和基本异常）
- security: 安全测试（注入、越权、敏感信息）

## 输出格式
```json
{{
  "test_cases": [
    {{
      "id": "TC001",
      "name": "测试用例名称",
      "description": "测试描述",
      "category": "normal/boundary/exception/security",
      "priority": "high/medium/low",
      "method": "HTTP方法",
      "url": "请求URL",
      "headers": {{}},
      "body": {{}},
      "expected_status": 200,
      "expected_response_contains": ["期望响应包含的字段"],
      "validation_rules": ["验证规则"]
    }}
  ]
}}
```

请生成测试用例："""


# 结果验证Prompt
RESULT_VALIDATION_PROMPT = """你是一位测试专家，请验证以下测试结果是否符合预期。

## 测试用例
```json
{test_case}
```

## 实际响应
```json
{actual_response}
```

## 预期响应
```json
{expected_response}
```

## 输出格式
```json
{{
  "passed": true/false,
  "score": 0-100,
  "validations": [
    {{
      "rule": "验证规则",
      "passed": true/false,
      "actual": "实际值",
      "expected": "期望值",
      "message": "说明"
    }}
  ],
  "issues": ["发现的问题"],
  "suggestions": ["改进建议"]
}}
```

请验证："""


# Curl命令生成Prompt
CURL_GENERATION_PROMPT = """请根据以下请求信息生成curl命令。

## 请求信息
```json
{request_info}
```

## 基础URL
{base_url}

## 输出格式
```json
{{
  "curl_command": "完整的curl命令（单行）",
  "curl_command_formatted": "格式化的curl命令（多行，便于阅读）",
  "notes": "注意事项"
}}
```

请生成curl命令："""


# 日志问题诊断Prompt
LOG_DIAGNOSIS_PROMPT = """你是一位系统诊断专家，请分析以下异常日志并给出诊断结果。

## 异常日志
```
{error_logs}
```

## 上下文信息
```json
{context}
```

## 诊断要求
1. 识别问题根因
2. 评估影响范围
3. 提供解决方案
4. 给出预防措施

## 输出格式
```json
{{
  "diagnosis": {{
    "root_cause": "根本原因",
    "impact": "影响范围",
    "severity": "high/medium/low",
    "affected_services": ["受影响的服务"]
  }},
  "solutions": [
    {{
      "description": "解决方案描述",
      "steps": ["步骤1", "步骤2"],
      "priority": "immediate/short-term/long-term"
    }}
  ],
  "prevention": ["预防措施"]
}}
```

请开始诊断："""


# 带RAG上下文的日志分类Prompt
LOG_CATEGORIZATION_WITH_RAG_PROMPT = """你是一位API架构师，请对以下API请求进行智能分类。

{api_doc_context}

## 请求列表
```json
{requests_json}
```

## 分类要求
1. **优先使用接口文档中的标签**：如果请求URL在接口文档中有匹配，请使用文档中定义的标签作为分类
2. **第三方接口识别**：如果请求URL在接口文档中没有匹配，可能是第三方接口，请标记为"第三方接口"或根据URL特征推断合理分类
3. **保持分类一致性**：相同模块的接口应使用相同的分类名称

## 输出格式
```json
{{
  "categorized_requests": [
    {{
      "url": "请求URL",
      "category": "分类名称（优先使用文档标签）",
      "sub_category": "子分类（可选）",
      "source": "doc/inferred/third_party",
      "confidence": 0.0-1.0
    }}
  ],
  "category_summary": {{
    "分类名称": 数量
  }},
  "third_party_apis": [
    {{
      "url": "第三方接口URL",
      "inferred_service": "推断的服务名称"
    }}
  ]
}}
```

请开始分类："""


# 接口文档对比分析Prompt
API_DOC_COMPARISON_PROMPT = """你是一位API架构师和质量分析专家，请对比分析接口文档与实际日志的差异。

## 接口文档概览
{api_doc_summary}

## 覆盖分析数据
```json
{coverage_data}
```

## 分析任务
1. **文档完整性分析**：
   - 日志中出现但文档未收录的接口（可能是文档遗漏或新增接口）
   - 文档中有但日志中从未调用的接口（可能是废弃接口或测试覆盖不足）

2. **接口一致性分析**：
   - 检查请求参数是否与文档定义一致
   - 检查响应格式是否符合文档描述

3. **潜在问题识别**：
   - 可能的文档过期问题
   - 可能的代码实现与文档不符
   - 第三方接口依赖情况

## 输出格式
```json
{{
  "doc_completeness": {{
    "missing_in_doc": [
      {{
        "url": "未收录的接口URL",
        "method": "HTTP方法",
        "call_count": 调用次数,
        "recommendation": "建议（如：建议添加到文档）"
      }}
    ],
    "unused_in_doc": [
      {{
        "path": "文档中的接口路径",
        "method": "HTTP方法",
        "name": "接口名称",
        "recommendation": "建议（如：确认是否废弃）"
      }}
    ]
  }},
  "consistency_issues": [
    {{
      "endpoint": "接口路径",
      "issue_type": "parameter_mismatch/response_mismatch/other",
      "description": "问题描述",
      "severity": "high/medium/low"
    }}
  ],
  "third_party_dependencies": [
    {{
      "url_pattern": "第三方接口URL模式",
      "inferred_service": "推断的服务名",
      "call_count": 调用次数,
      "recommendation": "建议"
    }}
  ],
  "summary": {{
    "doc_coverage_rate": "文档覆盖率",
    "api_usage_rate": "接口使用率",
    "total_issues": 问题总数,
    "critical_issues": 严重问题数
  }},
  "recommendations": [
    "改进建议1",
    "改进建议2"
  ]
}}
```

请开始分析："""


# 带RAG上下文的测试用例生成Prompt
TEST_CASE_GENERATION_WITH_RAG_PROMPT = """你是一位资深的测试工程师，请根据以下API信息和接口文档生成测试用例。

{api_doc_context}

## 待测试API信息
```json
{api_info}
```

## 示例请求（来自日志）
```json
{sample_requests}
```

## 测试策略: {test_strategy}
- comprehensive: 全面测试（正常、边界、异常、安全）
- quick: 快速测试（仅正常和基本异常）
- security: 安全测试（注入、越权、敏感信息）

## 生成要求
1. **参考接口文档**：使用文档中定义的参数类型、取值范围、必填项等信息
2. **参考实际请求**：结合日志中的真实请求数据
3. **覆盖边界情况**：根据文档中的参数约束设计边界测试
4. **验证响应格式**：根据文档中的响应定义设计验证规则

## 输出格式
```json
{{
  "test_cases": [
    {{
      "id": "TC001",
      "name": "测试用例名称",
      "description": "测试描述",
      "category": "normal/boundary/exception/security",
      "priority": "high/medium/low",
      "method": "HTTP方法",
      "url": "请求URL",
      "headers": {{}},
      "body": {{}},
      "expected_status": 200,
      "expected_response_contains": ["期望响应包含的字段"],
      "validation_rules": ["验证规则"],
      "doc_reference": "引用的文档接口（如有）"
    }}
  ],
  "coverage_notes": "测试覆盖说明"
}}
```

请生成测试用例："""
