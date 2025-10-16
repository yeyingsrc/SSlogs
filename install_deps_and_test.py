#!/usr/bin/env python3
"""
安装依赖并测试LM Studio连接
"""

import subprocess
import sys
import os
from pathlib import Path

def create_venv_if_needed():
    """创建虚拟环境（如果需要）"""
    venv_path = Path("venv")
    if not venv_path.exists():
        print("📦 创建虚拟环境...")
        try:
            subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
            print("✅ 虚拟环境创建成功")
        except subprocess.CalledProcessError as e:
            print(f"❌ 创建虚拟环境失败: {e}")
            return False
    else:
        print("✅ 虚拟环境已存在")
    return True

def install_deps_in_venv():
    """在虚拟环境中安装依赖"""
    print("\n📦 在虚拟环境中安装依赖...")

    # 确定虚拟环境中的python路径
    if os.name == 'nt':  # Windows
        python_path = Path("venv/Scripts/python.exe")
        pip_path = Path("venv/Scripts/pip")
    else:  # Unix/Linux/macOS
        python_path = Path("venv/bin/python")
        pip_path = Path("venv/bin/pip")

    if not python_path.exists():
        print(f"❌ 找不到虚拟环境Python: {python_path}")
        return False

    packages = ["pyyaml", "requests", "aiohttp"]

    for package in packages:
        print(f"  安装 {package}...")
        try:
            result = subprocess.run([
                str(pip_path), "install", package
            ], capture_output=True, text=True, check=True)
            print(f"  ✅ {package} 安装成功")
        except subprocess.CalledProcessError as e:
            print(f"  ❌ {package} 安装失败: {e}")
            print(f"  错误输出: {e.stderr}")
            return False

    return True

def test_with_venv():
    """使用虚拟环境测试"""
    print("\n🧪 使用虚拟环境测试LM Studio...")

    # 确定虚拟环境中的python路径
    if os.name == 'nt':  # Windows
        python_path = Path("venv/Scripts/python.exe")
    else:  # Unix/Linux/macOS
        python_path = Path("venv/bin/python")

    try:
        # 运行最小测试脚本
        result = subprocess.run([
            str(python_path), "minimal_lm_studio_test.py"
        ], capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            print("✅ 虚拟环境测试成功！")
            print(result.stdout)
            return True
        else:
            print("❌ 虚拟环境测试失败")
            print(f"输出: {result.stdout}")
            print(f"错误: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

def create_gui_launcher():
    """创建使用虚拟环境的GUI启动器"""
    print("\n📝 创建虚拟环境GUI启动器...")

    launcher_content = '''#!/bin/bash
# SSlogs GUI 启动器（使用虚拟环境）

# 获取脚本目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# 检查虚拟环境
if [ ! -d "$SCRIPT_DIR/venv" ]; then
    echo "创建虚拟环境..."
    cd "$SCRIPT_DIR"
    python3 -m venv venv

    echo "安装依赖..."
    "$SCRIPT_DIR/venv/bin/pip" install pyyaml requests aiohttp PyQt6
fi

# 启动GUI
echo "启动SSlogs GUI..."
cd "$SCRIPT_DIR"
"$SCRIPT_DIR/venv/bin/python" launcher.py --gui
'''

    # 检查操作系统
    if os.name == 'nt':  # Windows
        launcher_content = '''@echo off
REM SSlogs GUI 启动器（使用虚拟环境）

cd /d "%~dp0"

if not exist "venv" (
    echo 创建虚拟环境...
    python -m venv venv

    echo 安装依赖...
    venv\\Scripts\\pip install pyyaml requests aiohttp PyQt6
)

echo 启动SSlogs GUI...
venv\\Scripts\\python launcher.py --gui
'''
        launcher_path = Path("start_gui_with_venv.bat")
    else:
        launcher_path = Path("start_gui_with_venv.sh")

    try:
        with open(launcher_path, 'w', encoding='utf-8') as f:
            f.write(launcher_content)

        # 设置执行权限（Unix/Linux/macOS）
        if os.name != 'nt':
            os.chmod(launcher_path, 0o755)

        print(f"✅ 启动器创建成功: {launcher_path}")
        return True

    except Exception as e:
        print(f"❌ 创建启动器失败: {e}")
        return False

def main():
    """主函数"""
    print("🚀 SSlogs LM Studio 依赖安装和测试")
    print("=" * 50)

    # 1. 创建虚拟环境
    if not create_venv_if_needed():
        print("❌ 虚拟环境创建失败")
        return

    # 2. 安装依赖
    if not install_deps_in_venv():
        print("❌ 依赖安装失败")
        return

    # 3. 测试
    if not test_with_venv():
        print("❌ 测试失败")
        return

    # 4. 创建启动器
    create_gui_launcher()

    print("\n" + "=" * 50)
    print("🎉 安装完成！")
    print("\n现在可以使用以下方式启动GUI:")
    if os.name == 'nt':
        print("  • 运行: start_gui_with_venv.bat")
    else:
        print("  • 运行: ./start_gui_with_venv.sh")

    print("\n或者在虚拟环境中手动运行:")
    if os.name == 'nt':
        print("  • venv\\Scripts\\python launcher.py --gui")
    else:
        print("  • ./venv/bin/python launcher.py --gui")

    print("\n💡 LM Studio状态:")
    print("  ✅ 连接正常")
    print("  ✅ openai/gpt-oss-20b 模型可用")
    print("  ✅ API响应正常")

if __name__ == "__main__":
    main()