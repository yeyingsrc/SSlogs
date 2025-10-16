#!/usr/bin/env python3
"""
SSlogs GUI快速启动脚本
支持PyQt6图形界面和LM Studio集成
"""

import sys
import os
import subprocess
import webbrowser
from pathlib import Path
import time

def print_banner():
    """打印启动横幅"""
    print("🚀 SSlogs GUI快速启动器")
    print("=" * 50)
    print("应急分析溯源日志工具 - 图形界面版")
    print("支持LM Studio本地AI模型集成")
    print("=" * 50)

def check_dependencies():
    """检查依赖"""
    print("\n📦 检查依赖...")

    # 检查PyQt6
    try:
        import PyQt6
        print("✅ PyQt6 已安装")
    except ImportError:
        print("❌ PyQt6 未安装")
        print("请运行: pip install PyQt6")
        return False

    # 检查其他必要模块
    required_modules = ['requests', 'yaml', 'psutil']
    missing_modules = []

    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)

    if missing_modules:
        print(f"❌ 缺少依赖: {', '.join(missing_modules)}")
        print(f"请运行: pip install {' '.join(missing_modules)}")
        return False

    print("✅ 所有依赖已安装")
    return True

def check_lm_studio():
    """检查LM Studio状态"""
    print("\n🔗 检查LM Studio状态...")

    try:
        import requests
        response = requests.get("http://127.0.0.1:1234/v1/models", timeout=5)
        if response.status_code == 200:
            models = response.json().get("data", [])
            print(f"✅ LM Studio连接正常")
            print(f"   可用模型: {len(models)}个")
            if models:
                print("   模型列表:")
                for i, model in enumerate(models[:3], 1):
                    print(f"   {i}. {model.get('id', 'Unknown')}")
                if len(models) > 3:
                    print(f"   ... 还有 {len(models) - 3} 个模型")
            return True
        else:
            print("❌ LM Studio响应异常")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到LM Studio")
        print("请确保:")
        print("   1. LM Studio正在运行")
        print("   2. 本地服务器已启动 (端口1234)")
        print("   3. 已加载至少一个模型")
        return False
    except Exception as e:
        print(f"❌ 检查LM Studio时发生错误: {e}")
        return False

def start_lm_studio_manager():
    """启动LM Studio管理器"""
    print("\n🤖 启动LM Studio管理器...")

    try:
        script_path = Path(__file__).parent / "start_model_manager.py"
        if script_path.exists():
            print(f"   启动脚本: {script_path}")

            # 在后台启动
            process = subprocess.Popen([
                sys.executable, str(script_path),
                "--no-browser"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            print("✅ LM Studio管理器启动成功")
            print("   Web界面: http://127.0.0.1:8080")
            print("   功能:")
            print("   • 查看LM Studio连接状态")
            print("   • 刷新和选择模型")
            print("   • 配置API参数")
            print("   • 测试模型响应")
            print("   • 管理模型名称映射")

            # 等待一下让服务器启动
            time.sleep(2)
            return True
        else:
            print(f"❌ 找不到启动脚本: {script_path}")
            return False

    except Exception as e:
        print(f"❌ 启动LM Studio管理器失败: {e}")
        return False

def start_gui():
    """启动PyQt6 GUI"""
    print("\n🖥️ 启动PyQt6图形界面...")

    try:
        # 导入GUI模块
        from gui_pyqt import main as gui_main

        print("✅ 启动图形界面")
        print("   功能:")
        print("   • 日志分析配置")
        print("   • AI模型选择 (LM Studio/云端/Ollama)")
        print("   • 实时分析进度")
        print("   • LM Studio状态监控")
        print("   • 集成LM Studio管理界面")

        # 启动GUI
        gui_main()
        return True

    except ImportError as e:
        print(f"❌ 启动GUI失败: {e}")
        print("请检查PyQt6依赖安装")
        return False
    except Exception as e:
        print(f"❌ 启动GUI时发生错误: {e}")
        return False

def main():
    """主函数"""
    print_banner()

    # 检查依赖
    if not check_dependencies():
        input("\n按回车键退出...")
        sys.exit(1)

    # 检查LM Studio（可选）
    lm_studio_available = check_lm_studio()

    # 启动LM Studio管理器
    lm_studio_manager_started = False
    if lm_studio_available:
        response = input("\n是否启动LM Studio管理器? (y/n): ").lower()
        if response in ['y', 'yes', '']:
            lm_studio_manager_started = start_lm_studio_manager()

    # 启动GUI
    print(f"\n🚀 启动SSlogs图形界面...")

    if not start_gui():
        input("\n按回车键退出...")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ 启动被用户中断")
    except Exception as e:
        print(f"\n❌ 启动过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        input("\n按回车键退出...")
    finally:
        print("\n感谢使用SSlogs! 🎉")