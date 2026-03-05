#!/usr/bin/env python3
"""
AI测试工具 - API服务启动脚本
该文件内容使用AI生成，注意识别准确性
Python 3.13+ 兼容
"""

import argparse
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 加载 .env 文件
from dotenv import load_dotenv
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    load_dotenv(_env_file)
else:
    load_dotenv()


def main() -> int:
    parser = argparse.ArgumentParser(
        description='AI测试工具 - API服务',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--host',
        default=os.getenv('SERVER_HOST', '0.0.0.0'),
        help='监听地址 (默认: 0.0.0.0，可通过 SERVER_HOST 环境变量配置)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=int(os.getenv('SERVER_PORT', '8000')),
        help='监听端口 (默认: 8000，可通过 SERVER_PORT 环境变量配置)'
    )
    parser.add_argument(
        '--reload',
        action='store_true',
        help='开发模式，自动重载'
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=int(os.getenv('SERVER_WORKERS', '1')),
        help='工作进程数 (默认: 1，可通过 SERVER_WORKERS 环境变量配置)'
    )
    parser.add_argument(
        '--log-level',
        default=os.getenv('LOG_LEVEL', 'info'),
        choices=['critical', 'error', 'warning', 'info', 'debug'],
        help='日志级别 (默认: info)'
    )
    parser.add_argument(
        '--access-log',
        action='store_true',
        default=os.getenv('ACCESS_LOG', 'true').lower() in ('true', '1'),
        help='启用访问日志 (默认: 启用)'
    )
    parser.add_argument(
        '--timeout-keep-alive',
        type=int,
        default=int(os.getenv('TIMEOUT_KEEP_ALIVE', '5')),
        help='Keep-alive 超时秒数 (默认: 5)'
    )
    parser.add_argument(
        '--timeout-graceful-shutdown',
        type=int,
        default=int(os.getenv('TIMEOUT_GRACEFUL_SHUTDOWN', '30')),
        help='优雅关闭超时秒数 (默认: 30)'
    )
    
    args = parser.parse_args()
    
    try:
        import uvicorn
        from ai_test_tool.api import create_app
        
        app = create_app()
        
        print(f"启动 AI Test Tool API 服务...")
        print(f"   地址: http://{args.host}:{args.port}")
        print(f"   文档: http://{args.host}:{args.port}/docs")
        print(f"   workers: {args.workers}, log_level: {args.log_level}")
        
        uvicorn.run(
            "ai_test_tool.api:create_app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            workers=args.workers if not args.reload else 1,
            factory=True,
            log_level=args.log_level,
            access_log=args.access_log,
            timeout_keep_alive=args.timeout_keep_alive,
            timeout_graceful_shutdown=args.timeout_graceful_shutdown,
        )
        
        return 0
        
    except ImportError as e:
        print(f"错误: 缺少依赖 - {e}", file=sys.stderr)
        print("请运行: pip install fastapi uvicorn python-multipart", file=sys.stderr)
        return 1
    except OSError as e:
        print(f"启动失败 (端口可能被占用): {e}", file=sys.stderr)
        return 1
    except Exception as e:
        import traceback
        print(f"启动失败: {e}", file=sys.stderr)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
