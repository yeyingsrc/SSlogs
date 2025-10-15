#!/usr/bin/env python3
"""
应急分析溯源日志工具 - 启动脚本

使用方法:
    # 命令行模式
    python launcher.py
    
    # GUI模式 (PyQt6)
    python launcher.py --gui
    
    # 旧版GUI模式
    python launcher.py --old-gui
"""

import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description='应急分析溯源日志工具')
    parser.add_argument('--gui', action='store_true', help='启动PyQt6图形用户界面')
    parser.add_argument('--old-gui', action='store_true', help='启动旧版tkinter图形用户界面')
    
    args = parser.parse_args()
    
    if args.gui:
        # 启动PyQt6 GUI模式
        try:
            from gui_pyqt import main as pyqt_main
            pyqt_main()
        except ImportError as e:
            print(f"无法启动PyQt6 GUI界面: {e}")
            print("请确保已安装PyQt6依赖")
            sys.exit(1)
    elif args.old_gui:
        # 启动旧版tkinter GUI模式
        try:
            from gui import main as tk_main
            tk_main()
        except ImportError as e:
            print(f"无法启动tkinter GUI界面: {e}")
            sys.exit(1)
    else:
        # 启动命令行模式
        try:
            from main import main as cli_main
            cli_main()
        except ImportError as e:
            print(f"无法启动命令行界面: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()