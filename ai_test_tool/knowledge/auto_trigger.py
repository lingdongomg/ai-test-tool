"""
知识自动学习触发器

在关键事件（日志分析完成、测试执行完成、文档导入完成）后
异步触发知识提取，无需用户手动操作。

通过 KNOWLEDGE_AUTO_LEARN=false 环境变量可关闭自动学习。
"""

import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)


def _is_auto_learn_enabled() -> bool:
    """检查自动学习是否启用"""
    try:
        from ..config.settings import get_config
        return get_config().knowledge.auto_learn
    except Exception:
        import os
        return os.environ.get('KNOWLEDGE_AUTO_LEARN', 'true').lower() in ('true', '1', 'yes')


def _run_in_background(func, *args, **kwargs):
    """在后台线程中运行，避免阻塞主请求"""
    def wrapper():
        try:
            func(*args, **kwargs)
        except Exception as e:
            logger.error(f"后台知识学习失败: {e}")
    thread = threading.Thread(target=wrapper, daemon=True)
    thread.start()


def trigger_learn_from_task(task_id: str, auto_approve: bool = True) -> None:
    """
    日志分析任务完成后自动触发知识学习

    在 tasks.py 中任务状态变为 COMPLETED 时调用
    """
    if not _is_auto_learn_enabled():
        return

    def _learn():
        try:
            from ..api.dependencies import get_knowledge_learner
            learner = get_knowledge_learner()
            created_ids, items_detail = learner.learn_from_task(
                task_id=task_id,
                auto_approve=auto_approve,
            )
            if created_ids:
                logger.info(f"自动知识学习: 从任务 {task_id} 提取了 {len(created_ids)} 条知识")
            else:
                logger.info(f"自动知识学习: 任务 {task_id} 未提取到新知识")
        except Exception as e:
            logger.warning(f"自动知识学习失败 (task={task_id}): {e}")

    _run_in_background(_learn)


def trigger_learn_from_test_results(
    test_results: list[dict[str, Any]],
    execution_id: str = ""
) -> None:
    """
    测试执行完成后自动触发知识学习

    在 test_executor.py 中测试批次完成时调用
    """
    if not _is_auto_learn_enabled():
        return

    # 只有包含失败用例时才触发
    has_failures = any(r.get('status') in ('failed', 'error') for r in test_results)
    if not has_failures:
        return

    def _learn():
        try:
            from ..api.dependencies import get_knowledge_learner
            learner = get_knowledge_learner()
            suggestions = learner.extract_from_test_results(test_results, execution_id)
            if suggestions:
                created_count = 0
                for s in suggestions:
                    if s.confidence >= 0.3:
                        learner.store.create_from_suggestion(s, "auto_test_learning")
                        created_count += 1
                logger.info(f"自动知识学习: 从测试 {execution_id} 提取了 {created_count} 条知识")
        except Exception as e:
            logger.warning(f"自动知识学习失败 (execution={execution_id}): {e}")

    _run_in_background(_learn)


def trigger_learn_from_api_doc(
    api_doc: dict[str, Any],
    source_file: str = ""
) -> None:
    """
    API 文档导入完成后自动触发知识学习

    在 imports.py 中文档导入成功后调用
    """
    if not _is_auto_learn_enabled():
        return

    def _learn():
        try:
            from ..api.dependencies import get_knowledge_learner
            learner = get_knowledge_learner()
            suggestions = learner.extract_from_api_doc(api_doc, source_file)
            if suggestions:
                created_count = 0
                for s in suggestions:
                    if s.confidence >= 0.3:
                        learner.store.create_from_suggestion(s, "auto_doc_learning")
                        created_count += 1
                logger.info(f"自动知识学习: 从文档 {source_file} 提取了 {created_count} 条知识")
        except Exception as e:
            logger.warning(f"自动知识学习失败 (doc={source_file}): {e}")

    _run_in_background(_learn)
