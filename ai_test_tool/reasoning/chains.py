"""
内置推理链模板

提供常用的推理链实现：错误诊断、性能分析、根因分析、安全审计等
"""

from typing import Any

from .models import ThinkingStep, ChainConfig, ChainResult, StepType
from .engine import ChainOfThoughtEngine
from ..llm.provider import LLMProvider


# ============================================================
# 错误诊断推理链
# ============================================================

class ErrorDiagnosisChain:
    """
    错误诊断推理链

    步骤：
    1. 错误识别：识别日志中的错误类型和严重程度
    2. 上下文分析：分析错误发生的上下文环境
    3. 模式匹配：匹配已知错误模式
    4. 影响评估：评估错误影响范围
    5. 解决建议：生成解决方案建议
    """

    STEPS = [
        ThinkingStep(
            step_id="identify_errors",
            name="错误识别",
            description="识别日志中的错误类型和严重程度",
            step_type=StepType.EXTRACTION,
            order=1,
            output_key="identified_errors",
            prompt_template="""分析以下日志内容，识别其中的错误信息。

## 日志内容
```
{log_content}
```

## 任务
1. 识别所有错误（ERROR、FATAL、Exception等）
2. 对每个错误进行分类
3. 评估错误严重程度

## 输出格式（JSON）
```json
{{
  "errors": [
    {{
      "type": "错误类型（如：ConnectionError、TimeoutError、NullPointerException等）",
      "severity": "critical/high/medium/low",
      "message": "错误消息",
      "location": "错误位置（文件/行号，如有）",
      "count": 出现次数
    }}
  ],
  "summary": {{
    "total_errors": 错误总数,
    "critical_count": 严重错误数,
    "primary_error_type": "主要错误类型"
  }}
}}
```

请直接输出JSON："""
        ),

        ThinkingStep(
            step_id="analyze_context",
            name="上下文分析",
            description="分析错误发生的上下文环境",
            step_type=StepType.ANALYSIS,
            order=2,
            depends_on=["identify_errors"],
            output_key="error_context",
            prompt_template="""基于已识别的错误，分析错误发生的上下文。

## 已识别的错误
```json
{identified_errors}
```

## 原始日志
```
{log_content}
```

## 任务
1. 分析错误发生前后的日志
2. 识别可能的触发条件
3. 找出相关的请求或操作

## 输出格式（JSON）
```json
{{
  "trigger_conditions": ["可能的触发条件列表"],
  "related_operations": ["相关的操作或请求"],
  "environment_factors": ["环境因素（如时间、负载等）"],
  "error_sequence": "错误发生的顺序描述",
  "first_error_time": "首次错误时间",
  "affected_components": ["受影响的组件"]
}}
```

请直接输出JSON："""
        ),

        ThinkingStep(
            step_id="match_patterns",
            name="模式匹配",
            description="匹配已知错误模式",
            step_type=StepType.INFERENCE,
            order=3,
            depends_on=["identify_errors", "analyze_context"],
            output_key="matched_patterns",
            prompt_template="""基于错误信息和上下文，匹配已知的错误模式。

## 已识别的错误
```json
{identified_errors}
```

## 上下文分析
```json
{error_context}
```

## 常见错误模式
- 连接池耗尽：大量ConnectionTimeout，通常在高负载时
- 内存泄漏：OOM错误，随时间增长
- 死锁：数据库锁等待超时
- 级联故障：一个服务故障导致多个依赖服务失败
- 配置错误：启动时就出现的错误
- 网络抖动：间歇性的连接错误

## 任务
判断当前错误最可能匹配哪种模式，并说明理由。

## 输出格式（JSON）
```json
{{
  "matched_pattern": "匹配的模式名称",
  "confidence": 0.0-1.0之间的置信度,
  "matching_evidence": ["支持该判断的证据"],
  "alternative_patterns": [
    {{
      "pattern": "其他可能的模式",
      "confidence": 置信度
    }}
  ]
}}
```

请直接输出JSON："""
        ),

        ThinkingStep(
            step_id="assess_impact",
            name="影响评估",
            description="评估错误影响范围",
            step_type=StepType.ANALYSIS,
            order=4,
            depends_on=["analyze_context"],
            output_key="impact_assessment",
            prompt_template="""评估错误的影响范围。

## 上下文分析
```json
{error_context}
```

## 错误信息
```json
{identified_errors}
```

## 任务
评估此错误对系统和用户的影响。

## 输出格式（JSON）
```json
{{
  "impact_scope": "single_service/multiple_services/system_wide",
  "affected_users": "none/partial/all",
  "business_impact": "none/low/medium/high/critical",
  "data_integrity": "intact/partially_affected/corrupted",
  "service_availability": "正常/降级/不可用",
  "recovery_complexity": "automatic/simple/moderate/complex",
  "detailed_impact": "详细影响描述"
}}
```

请直接输出JSON："""
        ),

        ThinkingStep(
            step_id="generate_solutions",
            name="解决建议",
            description="生成解决方案建议",
            step_type=StepType.SYNTHESIS,
            order=5,
            depends_on=["match_patterns", "assess_impact"],
            output_key="solutions",
            prompt_template="""基于分析结果，生成解决方案建议。

## 匹配的模式
```json
{matched_patterns}
```

## 影响评估
```json
{impact_assessment}
```

## 错误信息
```json
{identified_errors}
```

## 任务
1. 提供立即解决方案
2. 提供短期优化建议
3. 提供长期预防措施

## 输出格式（JSON）
```json
{{
  "immediate_actions": [
    {{
      "action": "立即执行的操作",
      "priority": 1-5,
      "expected_result": "预期结果"
    }}
  ],
  "short_term_fixes": [
    {{
      "fix": "短期修复方案",
      "effort": "low/medium/high",
      "risk": "low/medium/high"
    }}
  ],
  "long_term_prevention": ["长期预防措施"],
  "monitoring_suggestions": ["监控建议"]
}}
```

请直接输出JSON："""
        ),
    ]

    def __init__(self, llm_provider: LLMProvider | None = None):
        config = ChainConfig(
            chain_id="error_diagnosis",
            name="错误诊断推理链",
            description="多步骤错误诊断分析",
            max_steps=5,
            stop_on_error=False
        )
        self.engine = ChainOfThoughtEngine(llm_provider, config)
        self.engine.add_steps(self.STEPS)

    def diagnose(self, log_content: str, **kwargs: Any) -> ChainResult:
        """执行错误诊断"""
        return self.engine.execute({
            "log_content": log_content,
            **kwargs
        })


# ============================================================
# 性能分析推理链
# ============================================================

class PerformanceAnalysisChain:
    """
    性能分析推理链

    步骤：
    1. 指标提取：从日志/数据中提取性能指标
    2. 基线对比：与正常基线对比
    3. 瓶颈定位：识别性能瓶颈
    4. 优化建议：生成优化建议
    """

    STEPS = [
        ThinkingStep(
            step_id="extract_metrics",
            name="指标提取",
            description="提取性能相关指标",
            step_type=StepType.EXTRACTION,
            order=1,
            output_key="performance_metrics",
            prompt_template="""从以下数据中提取性能指标。

## 请求数据
```json
{requests}
```

## 任务
提取以下性能指标：
1. 响应时间分布（平均、P50、P90、P99、最大值）
2. 吞吐量
3. 错误率
4. 慢请求统计

## 输出格式（JSON）
```json
{{
  "response_time": {{
    "avg_ms": 平均响应时间,
    "p50_ms": P50,
    "p90_ms": P90,
    "p99_ms": P99,
    "max_ms": 最大值,
    "min_ms": 最小值
  }},
  "throughput": {{
    "total_requests": 总请求数,
    "time_range_seconds": 时间范围
  }},
  "error_rate": 错误率（0-1）,
  "slow_requests": {{
    "count": 慢请求数量,
    "threshold_ms": 慢请求阈值,
    "percentage": 慢请求占比
  }},
  "by_endpoint": [
    {{
      "endpoint": "接口路径",
      "count": 请求数,
      "avg_ms": 平均响应时间,
      "error_rate": 错误率
    }}
  ]
}}
```

请直接输出JSON："""
        ),

        ThinkingStep(
            step_id="compare_baseline",
            name="基线对比",
            description="与正常基线对比分析",
            step_type=StepType.ANALYSIS,
            order=2,
            depends_on=["extract_metrics"],
            output_key="baseline_comparison",
            prompt_template="""将当前性能指标与一般基线对比。

## 当前指标
```json
{performance_metrics}
```

## 通用性能基线参考
- 优秀：P99 < 500ms，错误率 < 0.1%
- 良好：P99 < 1000ms，错误率 < 1%
- 一般：P99 < 3000ms，错误率 < 5%
- 较差：P99 > 3000ms 或 错误率 > 5%

## 任务
1. 评估当前性能水平
2. 识别异常指标
3. 判断性能趋势

## 输出格式（JSON）
```json
{{
  "overall_rating": "优秀/良好/一般/较差",
  "abnormal_metrics": [
    {{
      "metric": "指标名称",
      "current_value": 当前值,
      "expected_range": "期望范围",
      "severity": "warning/error/critical"
    }}
  ],
  "healthy_metrics": ["正常的指标列表"],
  "trend_analysis": "性能趋势判断"
}}
```

请直接输出JSON："""
        ),

        ThinkingStep(
            step_id="locate_bottleneck",
            name="瓶颈定位",
            description="识别性能瓶颈",
            step_type=StepType.INFERENCE,
            order=3,
            depends_on=["extract_metrics", "compare_baseline"],
            output_key="bottlenecks",
            prompt_template="""基于性能分析结果，定位性能瓶颈。

## 性能指标
```json
{performance_metrics}
```

## 基线对比
```json
{baseline_comparison}
```

## 任务
1. 识别主要性能瓶颈
2. 分析瓶颈原因
3. 评估瓶颈影响

## 输出格式（JSON）
```json
{{
  "bottlenecks": [
    {{
      "location": "瓶颈位置（接口/组件）",
      "type": "cpu/memory/io/network/database/external_service",
      "severity": "high/medium/low",
      "evidence": ["支持判断的证据"],
      "estimated_impact": "对整体性能的影响程度"
    }}
  ],
  "root_bottleneck": "最关键的瓶颈",
  "chain_effect": "瓶颈的连锁影响描述"
}}
```

请直接输出JSON："""
        ),

        ThinkingStep(
            step_id="optimization_suggestions",
            name="优化建议",
            description="生成性能优化建议",
            step_type=StepType.SYNTHESIS,
            order=4,
            depends_on=["bottlenecks"],
            output_key="optimizations",
            prompt_template="""基于瓶颈分析，生成优化建议。

## 性能瓶颈
```json
{bottlenecks}
```

## 任务
为每个瓶颈提供具体的优化建议。

## 输出格式（JSON）
```json
{{
  "optimizations": [
    {{
      "target": "优化目标",
      "current_state": "当前状态",
      "expected_improvement": "预期改善效果",
      "actions": [
        {{
          "action": "具体操作",
          "complexity": "low/medium/high",
          "risk": "low/medium/high"
        }}
      ]
    }}
  ],
  "quick_wins": ["立即可见效的优化"],
  "priority_order": ["按优先级排序的优化项"],
  "estimated_overall_improvement": "整体预期改善"
}}
```

请直接输出JSON："""
        ),
    ]

    def __init__(self, llm_provider: LLMProvider | None = None):
        config = ChainConfig(
            chain_id="performance_analysis",
            name="性能分析推理链",
            description="多步骤性能分析",
            max_steps=4,
            stop_on_error=False
        )
        self.engine = ChainOfThoughtEngine(llm_provider, config)
        self.engine.add_steps(self.STEPS)

    def analyze(self, requests: list[dict[str, Any]], **kwargs: Any) -> ChainResult:
        """执行性能分析"""
        import json
        return self.engine.execute({
            "requests": json.dumps(requests[:100], ensure_ascii=False, indent=2),
            **kwargs
        })


# ============================================================
# 根因分析推理链
# ============================================================

class RootCauseChain:
    """
    根因分析推理链

    步骤：
    1. 症状收集：收集所有异常症状
    2. 时序分析：分析事件时序关系
    3. 因果推理：建立因果关系
    4. 根因定位：确定根本原因
    5. 验证建议：提供验证方案
    """

    STEPS = [
        ThinkingStep(
            step_id="collect_symptoms",
            name="症状收集",
            description="收集所有异常症状",
            step_type=StepType.EXTRACTION,
            order=1,
            output_key="symptoms",
            prompt_template="""收集日志和数据中的所有异常症状。

## 日志内容
```
{log_content}
```

## 请求数据
```json
{requests}
```

## 任务
识别所有异常症状，包括：
1. 错误和异常
2. 性能异常
3. 行为异常

## 输出格式（JSON）
```json
{{
  "symptoms": [
    {{
      "id": "S1",
      "type": "error/performance/behavior",
      "description": "症状描述",
      "first_occurrence": "首次出现时间",
      "frequency": "发生频率",
      "affected_area": "影响范围"
    }}
  ],
  "symptom_count": 症状总数,
  "most_frequent": "最频繁的症状"
}}
```

请直接输出JSON："""
        ),

        ThinkingStep(
            step_id="temporal_analysis",
            name="时序分析",
            description="分析事件时序关系",
            step_type=StepType.ANALYSIS,
            order=2,
            depends_on=["collect_symptoms"],
            output_key="temporal_relations",
            prompt_template="""分析症状之间的时序关系。

## 收集的症状
```json
{symptoms}
```

## 任务
1. 按时间排序所有症状
2. 识别症状之间的先后关系
3. 找出最早出现的异常

## 输出格式（JSON）
```json
{{
  "timeline": [
    {{
      "time": "时间点",
      "symptom_id": "症状ID",
      "event": "事件描述"
    }}
  ],
  "first_anomaly": {{
    "symptom_id": "最早症状ID",
    "time": "时间",
    "description": "描述"
  }},
  "temporal_patterns": [
    {{
      "pattern": "时序模式描述",
      "involved_symptoms": ["涉及的症状ID"]
    }}
  ]
}}
```

请直接输出JSON："""
        ),

        ThinkingStep(
            step_id="causal_reasoning",
            name="因果推理",
            description="建立因果关系",
            step_type=StepType.INFERENCE,
            order=3,
            depends_on=["collect_symptoms", "temporal_analysis"],
            output_key="causal_relations",
            prompt_template="""基于症状和时序分析，推理因果关系。

## 症状
```json
{symptoms}
```

## 时序关系
```json
{temporal_relations}
```

## 任务
1. 建立症状之间的因果关系
2. 区分直接原因和间接原因
3. 识别因果链条

## 输出格式（JSON）
```json
{{
  "causal_chains": [
    {{
      "chain_id": "C1",
      "cause": "原因症状ID",
      "effects": ["结果症状ID列表"],
      "confidence": 0.0-1.0,
      "reasoning": "推理依据"
    }}
  ],
  "direct_causes": ["直接原因症状ID"],
  "indirect_causes": ["间接原因症状ID"],
  "unknown_relations": ["无法确定因果的症状"]
}}
```

请直接输出JSON："""
        ),

        ThinkingStep(
            step_id="locate_root_cause",
            name="根因定位",
            description="确定根本原因",
            step_type=StepType.SYNTHESIS,
            order=4,
            depends_on=["causal_reasoning"],
            output_key="root_cause",
            prompt_template="""基于因果分析，确定根本原因。

## 因果关系
```json
{causal_relations}
```

## 时序分析
```json
{temporal_relations}
```

## 任务
确定问题的根本原因，并评估置信度。

## 输出格式（JSON）
```json
{{
  "root_cause": {{
    "summary": "根本原因的一句话描述",
    "category": "配置错误/代码bug/资源不足/外部依赖/人为操作/未知",
    "confidence": 0.0-1.0,
    "evidence": ["支持该结论的证据"],
    "related_symptoms": ["相关症状ID"]
  }},
  "alternative_causes": [
    {{
      "summary": "备选原因",
      "confidence": 置信度,
      "reason_for_lower_confidence": "置信度较低的原因"
    }}
  ],
  "uncertainty_factors": ["不确定因素"]
}}
```

请直接输出JSON："""
        ),

        ThinkingStep(
            step_id="verification_plan",
            name="验证建议",
            description="提供验证方案",
            step_type=StepType.ACTION,
            order=5,
            depends_on=["locate_root_cause"],
            output_key="verification",
            prompt_template="""为根因分析结论提供验证方案。

## 根因分析结果
```json
{root_cause}
```

## 任务
提供验证根因的具体方案。

## 输出格式（JSON）
```json
{{
  "verification_steps": [
    {{
      "step": 1,
      "action": "验证操作",
      "expected_result": "如果根因正确，预期结果",
      "alternative_result": "如果根因错误，可能结果"
    }}
  ],
  "diagnostic_commands": ["可执行的诊断命令"],
  "logs_to_check": ["需要检查的日志"],
  "metrics_to_monitor": ["需要监控的指标"],
  "fix_suggestion": {{
    "immediate": "立即修复建议",
    "permanent": "永久修复建议"
  }}
}}
```

请直接输出JSON："""
        ),
    ]

    def __init__(self, llm_provider: LLMProvider | None = None):
        config = ChainConfig(
            chain_id="root_cause_analysis",
            name="根因分析推理链",
            description="多步骤根因分析",
            max_steps=5,
            stop_on_error=False
        )
        self.engine = ChainOfThoughtEngine(llm_provider, config)
        self.engine.add_steps(self.STEPS)

    def analyze(
        self,
        log_content: str = "",
        requests: list[dict[str, Any]] | None = None,
        **kwargs: Any
    ) -> ChainResult:
        """执行根因分析"""
        import json
        return self.engine.execute({
            "log_content": log_content,
            "requests": json.dumps(requests or [], ensure_ascii=False, indent=2),
            **kwargs
        })


# ============================================================
# 安全审计推理链
# ============================================================

class SecurityAuditChain:
    """
    安全审计推理链

    步骤：
    1. 威胁识别：识别潜在安全威胁
    2. 漏洞分析：分析安全漏洞
    3. 风险评估：评估安全风险
    4. 修复建议：提供安全修复建议
    """

    STEPS = [
        ThinkingStep(
            step_id="identify_threats",
            name="威胁识别",
            description="识别潜在安全威胁",
            step_type=StepType.EXTRACTION,
            order=1,
            output_key="threats",
            prompt_template="""分析日志中的安全威胁。

## 日志内容
```
{log_content}
```

## 请求数据
```json
{requests}
```

## 威胁类型检查清单
- SQL注入尝试
- XSS攻击
- 认证绕过
- 暴力破解
- 敏感信息泄露
- 异常访问模式

## 输出格式（JSON）
```json
{{
  "threats": [
    {{
      "type": "威胁类型",
      "severity": "critical/high/medium/low",
      "evidence": "证据",
      "source_ip": "来源IP（如有）",
      "target": "攻击目标"
    }}
  ],
  "threat_summary": {{
    "total": 威胁总数,
    "critical": 严重威胁数,
    "high": 高危威胁数
  }}
}}
```

请直接输出JSON："""
        ),

        ThinkingStep(
            step_id="vulnerability_analysis",
            name="漏洞分析",
            description="分析安全漏洞",
            step_type=StepType.ANALYSIS,
            order=2,
            depends_on=["identify_threats"],
            output_key="vulnerabilities",
            prompt_template="""基于威胁分析，识别系统漏洞。

## 识别的威胁
```json
{threats}
```

## 任务
分析可能被利用的系统漏洞。

## 输出格式（JSON）
```json
{{
  "vulnerabilities": [
    {{
      "id": "VULN-001",
      "name": "漏洞名称",
      "type": "injection/auth/config/etc",
      "location": "漏洞位置",
      "exploitability": "easy/medium/hard",
      "related_threats": ["相关威胁"]
    }}
  ],
  "attack_surface": "攻击面描述"
}}
```

请直接输出JSON："""
        ),

        ThinkingStep(
            step_id="risk_assessment",
            name="风险评估",
            description="评估安全风险",
            step_type=StepType.INFERENCE,
            order=3,
            depends_on=["identify_threats", "vulnerability_analysis"],
            output_key="risk_assessment",
            prompt_template="""评估整体安全风险。

## 威胁
```json
{threats}
```

## 漏洞
```json
{vulnerabilities}
```

## 输出格式（JSON）
```json
{{
  "overall_risk_level": "critical/high/medium/low",
  "risk_score": 0-100,
  "risk_factors": [
    {{
      "factor": "风险因素",
      "weight": 权重,
      "current_state": "当前状态"
    }}
  ],
  "immediate_concerns": ["需要立即关注的问题"],
  "compliance_issues": ["合规问题（如有）"]
}}
```

请直接输出JSON："""
        ),

        ThinkingStep(
            step_id="security_recommendations",
            name="修复建议",
            description="提供安全修复建议",
            step_type=StepType.SYNTHESIS,
            order=4,
            depends_on=["risk_assessment"],
            output_key="recommendations",
            prompt_template="""基于风险评估，提供安全修复建议。

## 风险评估
```json
{risk_assessment}
```

## 漏洞
```json
{vulnerabilities}
```

## 输出格式（JSON）
```json
{{
  "immediate_actions": [
    {{
      "action": "立即执行的安全措施",
      "priority": 1-5,
      "addresses": ["解决的问题"]
    }}
  ],
  "short_term_fixes": ["短期修复建议"],
  "long_term_improvements": ["长期安全改进"],
  "monitoring_recommendations": ["安全监控建议"],
  "security_best_practices": ["应遵循的安全最佳实践"]
}}
```

请直接输出JSON："""
        ),
    ]

    def __init__(self, llm_provider: LLMProvider | None = None):
        config = ChainConfig(
            chain_id="security_audit",
            name="安全审计推理链",
            description="多步骤安全审计分析",
            max_steps=4,
            stop_on_error=False
        )
        self.engine = ChainOfThoughtEngine(llm_provider, config)
        self.engine.add_steps(self.STEPS)

    def audit(
        self,
        log_content: str = "",
        requests: list[dict[str, Any]] | None = None,
        **kwargs: Any
    ) -> ChainResult:
        """执行安全审计"""
        import json
        return self.engine.execute({
            "log_content": log_content,
            "requests": json.dumps(requests or [], ensure_ascii=False, indent=2),
            **kwargs
        })
