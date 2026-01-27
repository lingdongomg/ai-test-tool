## ADDED Requirements

### Requirement: 知识条目管理
系统必须(SHALL)提供知识条目的完整生命周期管理能力，支持创建、读取、更新、删除操作。

知识条目必须包含以下核心属性：
- **类型(type)**: project_config（项目配置）| business_rule（业务规则）| module_context（模块上下文）| test_experience（测试经验）
- **标题(title)**: 简洁描述知识内容
- **内容(content)**: 知识的详细描述
- **范围(scope)**: 适用范围（如模块名、接口路径）
- **状态(status)**: active（活跃）| pending（待审核）| archived（已归档）
- **标签(tags)**: 用于灵活分类和检索

#### Scenario: 手动创建知识条目
- **WHEN** 用户通过API提交新知识（包含type、title、content）
- **THEN** 系统创建知识条目，状态设为active
- **AND** 系统为知识生成向量embedding并存储

#### Scenario: 更新知识条目
- **WHEN** 用户更新已存在的知识条目
- **THEN** 系统保存新版本，version字段递增
- **AND** 系统将旧版本记录到历史表
- **AND** 系统更新知识的向量embedding

#### Scenario: 删除知识条目
- **WHEN** 用户删除知识条目
- **THEN** 系统将知识状态设为archived（软删除）
- **AND** 知识不再出现在检索结果中

---

### Requirement: 知识分类体系
系统必须(SHALL)提供多维度的知识分类能力，支持按类型、子分类、标签组织知识。

#### Scenario: 按类型筛选知识
- **WHEN** 用户指定type=project_config查询知识
- **THEN** 系统返回所有类型为project_config的活跃知识

#### Scenario: 按标签筛选知识
- **WHEN** 用户指定tags=["auth", "game-id"]查询知识
- **THEN** 系统返回包含任一指定标签的活跃知识

#### Scenario: 组合条件筛选
- **WHEN** 用户同时指定type和tags进行查询
- **THEN** 系统返回同时满足类型条件和标签条件（OR逻辑）的知识

---

### Requirement: 语义知识检索
系统必须(SHALL)提供基于语义相似度的知识检索能力，支持混合检索策略。

检索策略采用三阶段流程：
1. 关键词预筛选：基于类型、标签、范围快速过滤
2. 语义排序：计算查询与知识的向量相似度
3. 上下文重排序：根据当前场景调整排名

#### Scenario: 语义检索相关知识
- **WHEN** 测试生成器查询"直播电商模块需要哪些header参数"
- **THEN** 系统返回与查询语义相关的知识列表
- **AND** 结果按相似度降序排列
- **AND** 包含game-id相关的业务规则知识

#### Scenario: 指定范围检索
- **WHEN** 查询时指定scope="/api/live/*"
- **THEN** 系统优先返回范围匹配的知识
- **AND** 其次返回通用知识（scope为空或通配符）

#### Scenario: 限制返回数量
- **WHEN** 查询时指定top_k=5
- **THEN** 系统最多返回5条最相关的知识

---

### Requirement: 知识自动学习
系统必须(SHALL)提供从日志解析和测试执行中自动提取知识的能力。

学习流程：
1. 触发学习：日志解析完成或测试执行完成
2. 知识提取：LLM分析内容，提取潜在知识
3. 待审核状态：提取的知识以pending状态存储
4. 人工确认：用户审核后转为active或拒绝

#### Scenario: 从日志解析中学习
- **WHEN** 日志解析器完成解析且enable_learning=true
- **THEN** 系统调用LLM分析解析结果
- **AND** 提取发现的业务规则和配置信息
- **AND** 将提取的知识以pending状态存储
- **AND** 记录来源为log_learning及对应的任务ID

#### Scenario: 从测试失败中学习
- **WHEN** 测试用例执行失败且分析出根因
- **THEN** 系统将失败原因和解决方案提取为测试经验知识
- **AND** 知识类型设为test_experience
- **AND** 知识状态设为pending待人工确认

#### Scenario: 审核待确认知识
- **WHEN** 用户确认pending状态的知识
- **THEN** 系统将知识状态更新为active
- **AND** 知识开始参与检索

#### Scenario: 拒绝无效知识
- **WHEN** 用户拒绝pending状态的知识
- **THEN** 系统将知识状态更新为archived
- **AND** 记录拒绝操作到历史

---

### Requirement: RAG上下文构建
系统必须(SHALL)提供RAG(检索增强生成)上下文构建能力，将检索到的知识转化为LLM可用的上下文格式。

#### Scenario: 构建测试生成上下文
- **WHEN** 测试生成器请求构建RAG上下文
- **GIVEN** 检索到多条相关知识
- **THEN** 系统按优先级和相关度组织知识
- **AND** 生成结构化的上下文文本
- **AND** 控制上下文长度不超过配置的token限制

#### Scenario: 上下文格式化
- **WHEN** 构建RAG上下文
- **THEN** 上下文包含清晰的知识分类标识
- **AND** 每条知识包含标题、内容、适用范围
- **AND** 高优先级知识排列在前

---

### Requirement: 知识版本控制
系统必须(SHALL)提供知识的版本控制能力，记录知识的变更历史。

#### Scenario: 记录变更历史
- **WHEN** 知识被更新
- **THEN** 系统创建历史记录，包含变更前的完整内容
- **AND** 记录变更时间、变更人、变更类型

#### Scenario: 查看历史版本
- **WHEN** 用户请求某知识的历史版本
- **THEN** 系统返回该知识的所有历史版本列表
- **AND** 包含每个版本的完整内容和元数据

---

### Requirement: 知识使用统计
系统必须(SHALL)记录知识的使用情况，用于评估知识质量和优化检索。

#### Scenario: 记录使用情况
- **WHEN** 知识被检索并应用于测试生成
- **THEN** 系统记录使用事件，包含使用场景和上下文

#### Scenario: 收集使用反馈
- **WHEN** 用户标记某次知识应用为"有帮助"或"无帮助"
- **THEN** 系统记录反馈到使用记录
- **AND** 反馈数据可用于优化知识排序

---

### Requirement: 向量化适配器
系统必须(SHALL)提供可插拔的文本向量化能力，支持多种embedding提供商。

支持的向量化方式（按优先级）：
1. LLM Provider的embedding接口（Ollama/OpenAI/Anthropic）
2. 本地sentence-transformers模型
3. TF-IDF降级方案

#### Scenario: 使用Ollama生成向量
- **WHEN** 配置使用Ollama作为LLM provider
- **AND** Ollama支持embedding接口
- **THEN** 系统使用Ollama生成文本向量

#### Scenario: 降级到本地模型
- **WHEN** LLM Provider不支持embedding
- **AND** 本地安装了sentence-transformers
- **THEN** 系统使用本地模型生成向量

#### Scenario: 降级到TF-IDF
- **WHEN** 向量化服务不可用
- **THEN** 系统使用TF-IDF生成稀疏向量
- **AND** 检索退化为关键词匹配

---

### Requirement: 知识库管理API
系统必须(SHALL)提供RESTful API用于知识库的管理操作。

#### Scenario: 获取知识列表
- **WHEN** 客户端GET请求 /api/knowledge
- **THEN** 返回分页的知识列表
- **AND** 支持type、status、tags筛选参数

#### Scenario: 创建知识
- **WHEN** 客户端POST请求 /api/knowledge，包含知识数据
- **THEN** 创建知识条目并返回
- **AND** 返回201状态码

#### Scenario: 更新知识
- **WHEN** 客户端PUT请求 /api/knowledge/{id}
- **THEN** 更新指定知识并返回
- **AND** 返回200状态码

#### Scenario: 删除知识
- **WHEN** 客户端DELETE请求 /api/knowledge/{id}
- **THEN** 归档指定知识
- **AND** 返回204状态码

#### Scenario: 批量审核
- **WHEN** 客户端POST请求 /api/knowledge/review，包含知识ID列表和操作
- **THEN** 批量更新知识状态
- **AND** 返回处理结果

#### Scenario: 检索测试
- **WHEN** 客户端POST请求 /api/knowledge/search，包含查询条件
- **THEN** 返回检索结果及相似度分数
- **AND** 用于调试检索效果

---

### Requirement: 知识库前端界面
系统必须(SHALL)提供Web界面用于知识库的可视化管理。

#### Scenario: 知识列表页面
- **WHEN** 用户访问知识库管理页面
- **THEN** 显示知识列表，支持分页
- **AND** 提供类型、状态、标签筛选器
- **AND** 提供全文搜索框

#### Scenario: 知识编辑页面
- **WHEN** 用户点击创建或编辑知识
- **THEN** 显示知识编辑表单
- **AND** 支持选择类型、输入标签
- **AND** 支持富文本编辑内容

#### Scenario: 待审核页面
- **WHEN** 用户访问待审核知识页面
- **THEN** 显示所有pending状态的知识
- **AND** 提供批量确认/拒绝操作
- **AND** 显示知识来源信息
