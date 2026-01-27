# 技术设计文档

<!-- 该文件内容使用AI生成，注意识别准确性 -->

## Context

AI Test Tool 项目经过快速迭代开发后，积累了大量技术债务：
- 代码重复率高
- 数据库表设计分散
- 大文件难以维护
- 缺乏统一的抽象层

本次重构旨在提升代码质量和可维护性，同时保持功能完整性和 API 兼容性。

## Goals / Non-Goals

### Goals
- 减少代码重复，提升复用性
- 精简数据库表设计
- 拆分大文件，提升可维护性
- 建立统一的抽象模式

### Non-Goals
- 不引入新功能
- 不更换技术栈（保持 SQLite、FastAPI、LangChain）
- 不进行 UI 重构

## Decisions

### 1. 数据库表精简策略

**Decision**: 合并和移除以下表

| 操作 | 表名 | 原因 |
|------|------|------|
| 移除 | `scheduled_tasks` | 定时任务可通过外部工具（cron）实现 |
| 移除 | `ai_insights` | 功能与 `analysis_reports` 重叠 |
| 合并 | `test_case_versions` + `test_case_change_logs` → `test_case_history` | 功能相似 |
| 移除 | `production_requests` | 监控数据应存储在专用监控系统 |

**保留的核心表** (13张):
1. `analysis_tasks` - 分析任务
2. `parsed_requests` - 解析请求
3. `test_cases` - 测试用例
4. `test_results` - 测试结果
5. `analysis_reports` - 分析报告
6. `api_tags` - 接口标签
7. `api_endpoints` - 接口端点
8. `api_endpoint_tags` - 关联表
9. `test_scenarios` - 测试场景
10. `scenario_steps` - 场景步骤
11. `scenario_executions` - 执行记录
12. `step_results` - 步骤结果
13. `test_case_history` - 用例历史（合并后）

### 2. Model 基类设计

```python
from dataclasses import dataclass, asdict
from typing import TypeVar, Type, Dict, Any
from datetime import datetime

T = TypeVar('T', bound='BaseModel')

@dataclass
class BaseModel:
    """基础模型类，提供通用的序列化方法"""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，自动处理 datetime"""
        result = asdict(self)
        for key, value in result.items():
            if isinstance(value, datetime):
                result[key] = value.isoformat()
        return result
    
    @classmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """从字典创建实例"""
        # 过滤掉不存在的字段
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)
```

### 3. Repository 基类设计

```python
from typing import TypeVar, Generic, Type, List, Optional
from .models import BaseModel

T = TypeVar('T', bound=BaseModel)

class BaseRepository(Generic[T]):
    """通用 Repository 基类"""
    
    def __init__(self, db_connection, table_name: str, model_class: Type[T]):
        self.db = db_connection
        self.table_name = table_name
        self.model_class = model_class
    
    def get_by_id(self, id: str) -> Optional[T]:
        """根据 ID 获取单条记录"""
        pass
    
    def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """获取所有记录"""
        pass
    
    def create(self, model: T) -> T:
        """创建记录"""
        pass
    
    def update(self, id: str, model: T) -> T:
        """更新记录"""
        pass
    
    def delete(self, id: str) -> bool:
        """删除记录"""
        pass
```

### 4. LLM Provider 抽象

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, AsyncIterator

class BaseLLMProvider(ABC):
    """LLM Provider 抽象基类"""
    
    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """同步聊天"""
        pass
    
    @abstractmethod
    async def stream_chat(self, messages: List[Dict[str, str]], **kwargs) -> AsyncIterator[str]:
        """流式聊天"""
        pass
```

### 5. 文件拆分策略

**development.py (1000行) 拆分为:**
- `routes/development/__init__.py` - 路由注册
- `routes/development/endpoints.py` - 接口管理 (~300行)
- `routes/development/test_cases.py` - 测试用例管理 (~400行)
- `routes/development/executions.py` - 执行管理 (~300行)

**models.py (845行) 拆分为:**
- `models/base.py` - 基类
- `models/task.py` - 任务相关模型
- `models/test.py` - 测试相关模型
- `models/api.py` - API 相关模型
- `models/scenario.py` - 场景相关模型

## Risks / Trade-offs

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 数据库迁移失败 | 数据丢失 | 迁移前备份数据 |
| API 不兼容 | 前端功能异常 | 保持 API 签名不变 |
| 引入新 bug | 功能异常 | 分步重构，每步验证 |

## Migration Plan

1. **阶段一**: 数据库重构
   - 备份现有数据
   - 创建新 schema
   - 数据迁移脚本
   - 验证数据完整性

2. **阶段二**: Model 和 Repository 重构
   - 创建基类
   - 逐个迁移现有类
   - 单元测试验证

3. **阶段三**: 路由拆分
   - 拆分大文件
   - 保持 API 不变
   - 集成测试验证

4. **阶段四**: 清理和优化
   - 移除死代码
   - 优化导入
   - 最终验证

## Open Questions

- 是否需要保留历史测试数据？
- 监控数据的存储策略是否需要调整？
