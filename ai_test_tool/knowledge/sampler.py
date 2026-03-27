# 该文件内容使用AI生成，注意识别准确性
"""
智能日志采样器

对超大日志文件进行分层采样，确保在有限资源下覆盖关键信息：
- 头部采样：启动/配置信息
- 尾部采样：最新状态
- 错误行优先：ERROR/WARN/FATAL 关键词行
- 均匀采样：覆盖时间分布
"""

import re
import random
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# 错误关键词模式（优先采样）
_ERROR_KEYWORDS = re.compile(
    r'\b(ERROR|FATAL|CRITICAL|EXCEPTION|TRACEBACK|PANIC|FAIL|WARN|WARNING)\b',
    re.IGNORECASE
)


class SmartLogSampler:
    """分层日志采样器"""

    def __init__(
        self,
        head_lines: int = 200,
        tail_lines: int = 200,
        error_lines: int = 500,
        uniform_lines: int = 600,
    ) -> None:
        self.head_lines = head_lines
        self.tail_lines = tail_lines
        self.error_lines = error_lines
        self.uniform_lines = uniform_lines
        self.max_total = head_lines + tail_lines + error_lines + uniform_lines

    def sample_file(self, file_path: str) -> list[str]:
        """
        对日志文件进行分层采样

        Args:
            file_path: 日志文件路径

        Returns:
            采样后的日志行列表（保持原始顺序）
        """
        path = Path(file_path)
        if not path.exists():
            return []

        # 第一遍：收集头部、尾部、错误行索引
        total_lines = 0
        error_indices: list[int] = []
        tail_buffer: list[tuple[int, str]] = []

        head_result: list[tuple[int, str]] = []

        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f):
                stripped = line.rstrip('\n')
                total_lines = i + 1

                # 头部
                if i < self.head_lines:
                    head_result.append((i, stripped))

                # 错误行
                if _ERROR_KEYWORDS.search(stripped):
                    error_indices.append(i)

                # 尾部（滑动窗口）
                tail_buffer.append((i, stripped))
                if len(tail_buffer) > self.tail_lines:
                    tail_buffer.pop(0)

        # 如果文件行数 <= max_total，直接返回全部
        if total_lines <= self.max_total:
            logger.info(f"文件 {total_lines} 行 <= 采样上限 {self.max_total}，返回全部内容")
            all_lines: list[str] = []
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    all_lines.append(line.rstrip('\n'))
            return all_lines

        # 收集已选中的行号
        selected_indices: set[int] = set()

        # 头部行号
        for idx, _ in head_result:
            selected_indices.add(idx)

        # 尾部行号
        for idx, _ in tail_buffer:
            selected_indices.add(idx)

        # 错误行（排除已选中的，随机采样上限个）
        available_errors = [i for i in error_indices if i not in selected_indices]
        if len(available_errors) > self.error_lines:
            available_errors = random.sample(available_errors, self.error_lines)
        selected_indices.update(available_errors)

        # 均匀采样（排除已选中的）
        remaining_budget = self.max_total - len(selected_indices)
        if remaining_budget > 0 and total_lines > len(selected_indices):
            all_indices = set(range(total_lines)) - selected_indices
            uniform_count = min(remaining_budget, self.uniform_lines, len(all_indices))
            if uniform_count > 0:
                # 均匀分布采样
                step = max(1, len(all_indices) // uniform_count)
                sorted_remaining = sorted(all_indices)
                uniform_sample = sorted_remaining[::step][:uniform_count]
                selected_indices.update(uniform_sample)

        # 第二遍：按行号顺序读取选中的行
        sorted_indices = sorted(selected_indices)
        index_set = set(sorted_indices)
        result: list[str] = []

        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f):
                if i in index_set:
                    result.append(line.rstrip('\n'))
                if i > sorted_indices[-1] if sorted_indices else 0:
                    break

        logger.info(
            f"采样完成: {total_lines} 行 → {len(result)} 行 "
            f"(头部 {len(head_result)}, 尾部 {len(tail_buffer)}, "
            f"错误 {len(available_errors)}, 均匀 {len(result) - len(head_result) - len(tail_buffer) - len(available_errors)})"
        )

        return result

    def sample_lines(self, lines: list[str]) -> list[str]:
        """
        对已加载的行列表进行采样

        Args:
            lines: 日志行列表

        Returns:
            采样后的行列表
        """
        if len(lines) <= self.max_total:
            return lines

        selected_indices: set[int] = set()

        # 头部
        for i in range(min(self.head_lines, len(lines))):
            selected_indices.add(i)

        # 尾部
        for i in range(max(0, len(lines) - self.tail_lines), len(lines)):
            selected_indices.add(i)

        # 错误行
        error_indices = [
            i for i in range(len(lines))
            if i not in selected_indices and _ERROR_KEYWORDS.search(lines[i])
        ]
        if len(error_indices) > self.error_lines:
            error_indices = random.sample(error_indices, self.error_lines)
        selected_indices.update(error_indices)

        # 均匀采样
        remaining = self.max_total - len(selected_indices)
        if remaining > 0:
            available = sorted(set(range(len(lines))) - selected_indices)
            step = max(1, len(available) // remaining)
            uniform = available[::step][:remaining]
            selected_indices.update(uniform)

        return [lines[i] for i in sorted(selected_indices)]
