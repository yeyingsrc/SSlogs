#!/usr/bin/env python3
"""
SSlogs AI模型管理器启动脚本
"""

import sys
import os
import argparse
import logging
import webbrowser
import time
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from web.model_api import create_model_management_server
from core.model_manager import get_model_manager
from core.ai_config_manager import get_ai_config_manager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(project_root / 'logs' / 'model_manager.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def check_dependencies():
    """检查依赖"""
    missing_deps = []

    try:
        import flask
    except ImportError:
        missing_deps.append("flask")

    try:
        import flask_cors
    except ImportError:
        missing_deps.append("flask-cors")

    try:
        import aiohttp
    except ImportError:
        missing_deps.append("aiohttp")

    try:
        import pydantic
    except ImportError:
        missing_deps.append("pydantic")

    if missing_deps:
        logger.error(f"缺少依赖: {', '.join(missing_deps)}")
        logger.info("请运行以下命令安装依赖:")
        logger.info(f"pip install {' '.join(missing_deps)}")
        return False

    return True

def check_lm_studio():
    """检查LM Studio状态"""
    try:
        model_manager = get_model_manager()
        status = model_manager.get_server_status()

        if status.connected:
            logger.info("✅ LM Studio连接正常")
            logger.info(f"   服务器: {status.host}:{status.port}")
            logger.info(f"   可用模型: {status.available_models_count}个")
            logger.info(f"   响应时间: {status.response_time:.2f}秒")

            if status.current_model:
                logger.info(f"   当前模型: {status.current_model}")
            else:
                logger.warning("   ⚠️ 未加载模型")
        else:
            logger.warning("⚠️ LM Studio未连接")
            logger.info("请确保:")
            logger.info("1. LM Studio正在运行")
            logger.info("2. 本地服务器已启动 (通常在 http://127.0.0.1:1234)")
            logger.info("3. 已加载至少一个语言模型")

            return False

    except Exception as e:
        logger.error(f"检查LM Studio失败: {e}")
        return False

    return True

def ensure_log_directory():
    """确保日志目录存在"""
    log_dir = project_root / 'logs'
    log_dir.mkdir(exist_ok=True)
    return log_dir

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='SSlogs AI模型管理器')
    parser.add_argument('--host', default='0.0.0.0', help='服务器主机地址 (默认: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8080, help='服务器端口 (默认: 8080)')
    parser.add_argument('--debug', action='store_true', help='启用调试模式')
    parser.add_argument('--no-browser', action='store_true', help='不自动打开浏览器')
    parser.add_argument('--check-only', action='store_true', help='仅检查依赖和环境，不启动服务器')

    args = parser.parse_args()

    print("🚀 SSlogs AI模型管理器")
    print("=" * 50)

    # 确保日志目录存在
    ensure_log_directory()

    # 检查依赖
    print("📦 检查依赖...")
    if not check_dependencies():
        sys.exit(1)
    print("✅ 依赖检查通过")

    # 检查LM Studio
    print("\n🔗 检查LM Studio状态...")
    lm_studio_ok = check_lm_studio()

    if args.check_only:
        print("\n✅ 环境检查完成")
        if lm_studio_ok:
            print("✅ 所有检查通过，可以启动模型管理器")
        else:
            print("⚠️ LM Studio未连接，但可以启动管理界面进行配置")
        return

    # 创建服务器
    print(f"\n🌐 启动Web服务器...")
    print(f"   地址: http://{args.host}:{args.port}")
    print(f"   调试模式: {'开启' if args.debug else '关闭'}")

    # 在新线程中启动服务器
    import threading

    server_func = create_model_management_server(
        host=args.host,
        port=args.port,
        debug=args.debug
    )

    server_thread = threading.Thread(target=server_func, daemon=True)
    server_thread.start()

    # 等待服务器启动
    print("⏳ 等待服务器启动...")
    time.sleep(2)

    # 打开浏览器
    if not args.no_browser:
        try:
            url = f"http://127.0.0.1:{args.port}"
            print(f"🌐 正在打开浏览器: {url}")
            webbrowser.open(url)
        except Exception as e:
            logger.warning(f"无法自动打开浏览器: {e}")
            print(f"请手动访问: http://127.0.0.1:{args.port}")

    print("\n✅ 模型管理器已启动!")
    print("📋 功能说明:")
    print("   • 查看LM Studio连接状态")
    print("   • 刷新和选择本地模型")
    print("   • 测试模型响应")
    print("   • 获取模型推荐")
    print("   • 配置AI功能参数")
    print("\n按 Ctrl+C 停止服务器")

    try:
        # 保持主线程运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n⏹️ 正在停止服务器...")
        print("✅ 服务器已停止")
        sys.exit(0)

if __name__ == "__main__":
    main()