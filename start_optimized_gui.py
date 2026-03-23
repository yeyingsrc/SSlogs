#!/usr/bin/env python3
"""
SSlogs v3.1 优化版GUI启动器
快速启动增强版GUI界面
"""

import sys
import os
from pathlib import Path

def check_requirements():
    """检查运行要求"""
    try:
        # 检查Python版本
        if sys.version_info < (3, 8):
            print("❌ 需要Python 3.8或更高版本")
            return False

        # 检查必需的模块
        required_modules = {
            'PyQt6': 'PyQt6',
            'PyYAML': 'yaml',
            'requests': 'requests',
            'aiohttp': 'aiohttp',
            'aiofiles': 'aiofiles',
            'cryptography': 'cryptography',
            'psutil': 'psutil'
        }

        missing_modules = []
        for display_name, module_name in required_modules.items():
            try:
                __import__(module_name)
            except ImportError:
                missing_modules.append(display_name)

        if missing_modules:
            print(f"❌ 缺少必需模块: {', '.join(missing_modules)}")
            print("请运行: pip install -r requirements.txt")
            return False

        return True

    except Exception as e:
        print(f"❌ 检查要求时发生错误: {e}")
        return False

def start_gui():
    """启动GUI"""
    try:
        print("🚀 启动 SSlogs v3.1 优化版GUI...")

        # 添加项目根目录到Python路径
        project_root = Path(__file__).parent
        sys.path.insert(0, str(project_root))

        # 导入并启动GUI
        from gui_optimized import main
        main()

    except ImportError as e:
        print(f"❌ 导入GUI模块失败: {e}")
        print("请确保所有必需的文件都存在")
        return False

    except Exception as e:
        print(f"❌ 启动GUI时发生错误: {e}")
        return False

    return True

def main():
    """主函数"""
    print("🛡️ SSlogs v3.1 - 企业级智能安全日志分析平台")
    print("=" * 60)

    # 检查运行要求
    if not check_requirements():
        sys.exit(1)

    # 启动GUI
    if not start_gui():
        sys.exit(1)

if __name__ == "__main__":
    main()