#!/bin/bash
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
