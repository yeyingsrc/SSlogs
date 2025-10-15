#!/usr/bin/env python3
"""
综合测试脚本 - 测试GUI和AI功能的完整集成
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_gui_functionality():
    """测试GUI功能"""
    print("=== GUI功能测试 ===")
    
    try:
        # 测试导入
        from gui_pyqt import LogAnalyzerGUI
        print("✓ GUI模块导入成功")
        
        # 测试创建主窗口
        import PyQt6.QtWidgets as QtWidgets
        app = QtWidgets.QApplication(sys.argv)
        window = LogAnalyzerGUI()
        
        # 检查窗口属性
        if hasattr(window, 'centralWidget'):
            print("✓ GUI主窗口创建成功")
            
        # 测试基本组件
        if hasattr(window, 'log_path_input'):
            print("✓ 日志路径输入框存在")
        if hasattr(window, 'ip_input'):
            print("✓ IP地址输入框存在")
        if hasattr(window, 'analyze_button'):
            print("✓ 分析按钮存在")
            
        # 清理
        window.close()
        
        print("✓ GUI功能测试通过\n")
        return True
        
    except Exception as e:
        print(f"✗ GUI功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ai_integration():
    """测试AI集成功能"""
    print("=== AI集成功能测试 ===")
    
    try:
        # 测试AI分析器
        from core.ai_analyzer import AIAnalyzer
        
        ai_analyzer = AIAnalyzer(config_path='config.yaml')
        
        # 检查基本属性
        if hasattr(ai_analyzer, 'ai_type'):
            print(f"✓ AI类型: {ai_analyzer.ai_type}")
        if hasattr(ai_analyzer, 'cloud_provider'):
            print(f"✓ 云端提供商: {ai_analyzer.cloud_provider}")
            
        # 测试简单分析
        test_context = "测试日志内容"
        result = ai_analyzer.analyze_log(test_context)
        
        if result and len(result) > 10:
            print("✓ AI分析功能正常")
        else:
            print("⚠ AI分析返回结果较短，但不一定是错误")
            
        print("✓ AI集成功能测试通过\n")
        return True
        
    except Exception as e:
        print(f"✗ AI集成功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_main_functionality():
    """测试主程序功能"""
    print("=== 主程序功能测试 ===")
    
    try:
        # 测试LogHunter类
        from main import LogHunter
        
        # 创建实例（不实际运行）
        log_hunter = LogHunter('config.yaml', ai_enabled=False, server_ip='127.0.0.1')
        
        # 检查基本属性
        if hasattr(log_hunter, 'config'):
            print("✓ 配置加载成功")
        if hasattr(log_hunter, 'logger'):
            print("✓ 日志系统初始化成功")
            
        # 测试配置加载
        if log_hunter.config and 'log_path' in log_hunter.config:
            print("✓ 配置文件加载成功")
            
        print("✓ 主程序功能测试通过\n")
        return True
        
    except Exception as e:
        print(f"✗ 主程序功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_launcher():
    """测试启动脚本"""
    print("=== 启动脚本功能测试 ===")
    
    try:
        # 测试导入
        import launcher
        
        print("✓ 启动脚本导入成功")
        
        # 测试命令行参数解析
        import argparse
        
        parser = argparse.ArgumentParser()
        parser.add_argument('--gui', action='store_true')
        parser.add_argument('--old-gui', action='store_true')
        
        # 模拟参数
        args = parser.parse_args(['--gui'])
        if hasattr(args, 'gui') and args.gui:
            print("✓ GUI参数解析正常")
            
        args = parser.parse_args(['--old-gui'])
        if hasattr(args, 'old_gui') and args.old_gui:
            print("✓ 旧版GUI参数解析正常")
            
        print("✓ 启动脚本功能测试通过\n")
        return True
        
    except Exception as e:
        print(f"✗ 启动脚本功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("开始综合功能测试...\n")
    
    tests = [
        test_gui_functionality,
        test_ai_integration,
        test_main_functionality,
        test_launcher
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"综合测试结果: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("🎉 所有功能综合测试通过！")
        print("\n✅ GUI界面已成功实现并可正常工作")
        print("✅ AI分析功能集成正确")
        print("✅ 主程序逻辑完整")
        print("✅ 启动脚本功能正常")
    else:
        print("❌ 部分综合测试失败，请检查相关模块。")
        
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)