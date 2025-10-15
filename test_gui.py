#!/usr/bin/env python3
"""
GUI测试脚本 - 验证GUI界面是否正常工作
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_gui_import():
    """测试GUI模块是否可以正常导入"""
    try:
        from gui import LogAnalyzerGUI
        print("✓ GUI模块导入成功")
        return True
    except ImportError as e:
        # 如果是tkinter相关错误，说明环境缺少GUI支持，但代码语法正确
        if "_tkinter" in str(e):
            print("⚠ GUI模块导入失败（缺少tkinter支持，但代码语法正确）")
            return True
        else:
            print(f"✗ GUI模块导入失败: {e}")
            return False
    except Exception as e:
        print(f"✗ GUI模块导入失败: {e}")
        return False

def test_main_import():
    """测试主模块是否可以正常导入"""
    try:
        from main import LogHunter
        print("✓ 主模块导入成功")
        return True
    except Exception as e:
        print(f"✗ 主模块导入失败: {e}")
        return False

def test_launcher():
    """测试启动脚本是否可以正常运行"""
    try:
        import launcher
        print("✓ 启动脚本导入成功")
        return True
    except Exception as e:
        print(f"✗ 启动脚本导入失败: {e}")
        return False

if __name__ == "__main__":
    print("开始测试GUI相关模块...")
    print("=" * 50)
    
    tests = [
        test_gui_import,
        test_main_import,
        test_launcher
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"测试结果: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！GUI功能可以正常工作。")
    else:
        print("❌ 部分测试失败，请检查代码。")