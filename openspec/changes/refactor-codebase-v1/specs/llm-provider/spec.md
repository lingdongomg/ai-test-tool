# LLM Provider Specification Changes

<!-- 该文件内容使用AI生成，注意识别准确性 -->

## ADDED Requirements

### Requirement: Base LLM Provider Interface
系统 SHALL 定义统一的 LLM Provider 抽象基类，所有具体 Provider 实现该接口。

#### Scenario: Provider interface
- **WHEN** 创建新的 LLM Provider
- **THEN** 必须继承 `BaseLLMProvider` 类
- **AND** 实现 `chat()` 和 `stream_chat()` 抽象方法

#### Scenario: Provider factory
- **WHEN** 根据配置创建 Provider 实例
- **THEN** 使用工厂方法 `create_provider(provider_type)` 创建
- **AND** 返回正确类型的 Provider 实例

## MODIFIED Requirements

### Requirement: LLM Provider Implementations
系统 SHALL 简化各 Provider 实现，移除重复代码。

#### Scenario: Ollama provider
- **WHEN** 使用 Ollama Provider
- **THEN** 继承 BaseLLMProvider
- **AND** 仅实现 Ollama 特有的配置和调用逻辑

#### Scenario: OpenAI provider
- **WHEN** 使用 OpenAI Provider
- **THEN** 继承 BaseLLMProvider
- **AND** 仅实现 OpenAI 特有的配置和调用逻辑

#### Scenario: Anthropic provider
- **WHEN** 使用 Anthropic Provider
- **THEN** 继承 BaseLLMProvider
- **AND** 仅实现 Anthropic 特有的配置和调用逻辑
