#!/usr/bin/env python3
"""
AI测试工具 - API服务启动脚本
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
        default=1,
        help='工作进程数 (默认: 1)'
    )
    
    args = parser.parse_args()
    
    try:
        import uvicorn
        from ai_test_tool.api import create_app
        
        app = create_app()
        
        print(f"启动 AI Test Tool API 服务...")
        print(f"   地址: http://{args.host}:{args.port}")
        print(f"   文档: http://{args.host}:{args.port}/docs")
        
        uvicorn.run(
            "ai_test_tool.api:create_app",
            host=args.host,
            port=args.port,
            reload=args.reload,
            workers=args.workers if not args.reload else 1,
            factory=True
        )
        
        return 0
        
    except ImportError as e:
        print(f"错误: 缺少依赖 - {e}")
        print("请运行: pip install fastapi uvicorn python-multipart")
        return 1
    except Exception as e:
        print(f"启动失败: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
