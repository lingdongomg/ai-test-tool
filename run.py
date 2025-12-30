#!/usr/bin/env python3
"""
AI测试工具 - 命令行入口
Python 3.13+ 兼容
"""

import argparse
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ai_test_tool.core import AITestTool
from ai_test_tool.config import AppConfig, LLMConfig, TestConfig


def main() -> int:
    parser = argparse.ArgumentParser(
        description='AI测试工具 - 智能日志分析和自动化测试',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本使用 - AI智能分析日志
  python run.py -f logo.json

  # 限制处理行数
  python run.py -f logo.json -m 10000

  # 执行测试
  python run.py -f logo.json --run-tests --base-url http://localhost:8080

  # 显示详细日志
  python run.py -f logo.json -v
        """
    )
    
    # 基本参数
    parser.add_argument(
        '-f', '--file',
        required=True,
        help='日志文件路径'
    )
    parser.add_argument(
        '-m', '--max-lines',
        type=int,
        default=None,
        help='最大处理行数'
    )
    
    # LLM配置
    parser.add_argument(
        '--llm-provider',
        choices=['ollama', 'openai', 'anthropic'],
        default='ollama',
        help='LLM提供商 (默认: ollama)'
    )
    parser.add_argument(
        '--llm-model',
        default='qwen3:8b',
        help='LLM模型名称 (默认: qwen3:8b)'
    )
    parser.add_argument(
        '--api-key',
        default=None,
        help='LLM API密钥 (用于OpenAI/Anthropic)'
    )
    
    # 测试配置
    parser.add_argument(
        '--run-tests',
        action='store_true',
        help='执行生成的测试用例'
    )
    parser.add_argument(
        '--base-url',
        default='http://localhost:8080',
        help='测试目标基础URL (默认: http://localhost:8080)'
    )
    parser.add_argument(
        '--concurrent',
        type=int,
        default=5,
        help='并发请求数 (默认: 5)'
    )
    parser.add_argument(
        '--test-strategy',
        choices=['comprehensive', 'quick', 'security'],
        default='comprehensive',
        help='测试策略 (默认: comprehensive)'
    )
    
    # 日志级别
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='显示详细的AI处理日志'
    )
    
    args = parser.parse_args()
    
    # 构建配置
    config = AppConfig(
        llm=LLMConfig(
            provider=args.llm_provider,  # type: ignore
            model=args.llm_model,
            api_key=args.api_key
        ),
        test=TestConfig(
            base_url=args.base_url,
            concurrent_requests=args.concurrent
        )
    )
    
    # 创建工具实例
    tool = AITestTool(config=config, verbose=args.verbose)
    
    try:
        # 运行完整流程
        result = tool.run_full_pipeline(
            log_file=args.file,
            max_lines=args.max_lines,
            test_strategy=args.test_strategy,
            run_tests=args.run_tests,
            base_url=args.base_url
        )
        
        tool.logger.separator()
        tool.logger.info("执行结果摘要:")
        tool.logger.info(f"   任务ID: {result['task_id']}")
        tool.logger.info(f"   解析请求数: {result['parsed_requests']}")
        tool.logger.info(f"   生成测试用例: {result['test_cases']}")
        
        if result.get('test_results'):
            tool.logger.info(f"   执行测试数: {result['test_results']}")
        
        tool.logger.info(f"   报告已存储: {', '.join(result.get('reports_saved', []))}")
        tool.logger.separator()
        
        return 0
        
    except FileNotFoundError as e:
        tool.logger.error(f"文件不存在: {e}")
        return 1
    except RuntimeError as e:
        tool.logger.error(f"运行时错误: {e}")
        return 1
    except Exception as e:
        tool.logger.error(f"执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        tool.close()


if __name__ == "__main__":
    sys.exit(main())
