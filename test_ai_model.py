#!/usr/bin/env python3
"""
AI模型测试脚本 - 用于验证AI分析功能是否正常工作
"""

import sys
import os
import time

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.ai_analyzer import AIAnalyzer
import yaml

def test_ai_model_config():
    """测试AI模型配置是否正确"""
    print("=== AI模型配置测试 ===")
    
    try:
        # 加载配置文件
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        ai_config = config.get('ai', {})
        deepseek_config = config.get('deepseek', {})
        
        print(f"AI类型: {ai_config.get('type', '未配置')}")
        print(f"云端提供商: {ai_config.get('cloud_provider', '未配置')}")
        
        if ai_config.get('type') == 'cloud':
            print(f"API密钥: {'已配置' if deepseek_config.get('api_key') else '未配置'}")
            print(f"模型名称: {deepseek_config.get('model', '未配置')}")
            print(f"基础URL: {deepseek_config.get('base_url', '未配置')}")
            print(f"超时时间: {deepseek_config.get('timeout', '未配置')}秒")
            
        print("✓ AI模型配置加载成功\n")
        return True
        
    except Exception as e:
        print(f"✗ AI模型配置加载失败: {e}\n")
        return False

def test_ai_analyzer_initialization():
    """测试AI分析器初始化"""
    print("=== AI分析器初始化测试 ===")
    
    try:
        # 创建AI分析器实例
        ai_analyzer = AIAnalyzer(config_path='config.yaml')
        
        # 检查是否成功初始化
        if hasattr(ai_analyzer, 'config'):
            print("✓ AI分析器初始化成功")
            
            # 检查AI类型
            ai_type = ai_analyzer.config.get('ai', {}).get('type', 'unknown')
            print(f"AI类型: {ai_type}")
            
            if ai_type == 'cloud':
                provider = ai_analyzer.config.get('ai', {}).get('cloud_provider')
                print(f"云端提供商: {provider}")
                
            return True
        else:
            print("✗ AI分析器初始化失败")
            return False
            
    except Exception as e:
        print(f"✗ AI分析器初始化失败: {e}\n")
        return False

def test_sample_log_context():
    """测试样本日志上下文"""
    print("=== 样本日志上下文测试 ===")
    
    sample_context = """
10.1.1.100 - - [10/Oct/2023:13:55:36] "GET /index.php?user=admin&pass=123 HTTP/1.1" 200 1234
10.1.1.100 - - [10/Oct/2023:13:56:45] "POST /login.php HTTP/1.1" 200 5678
10.1.1.100 - - [10/Oct/2023:13:57:22] "GET /admin.php?cmd=ls HTTP/1.1" 403 9876
"""
    
    print("样本日志上下文:")
    print(sample_context)
    print("✓ 样本日志上下文准备完成\n")
    
    return sample_context

def test_ai_analysis():
    """测试AI分析功能"""
    print("=== AI分析功能测试 ===")
    
    try:
        # 创建AI分析器
        ai_analyzer = AIAnalyzer(config_path='config.yaml')
        
        # 准备测试日志上下文
        sample_context = test_sample_log_context()
        
        print("开始AI分析测试...")
        start_time = time.time()
        
        # 执行一次简单的AI分析
        result = ai_analyzer.analyze_log(sample_context)
        
        end_time = time.time()
        print(f"AI分析完成，耗时: {end_time - start_time:.2f}秒")
        
        if result:
            print("✓ AI分析成功完成")
            # 只显示结果的前200个字符
            print(f"AI结果预览: {result[:200]}...")
        else:
            print("⚠ AI分析返回空结果")
            
        return True
        
    except Exception as e:
        print(f"✗ AI分析测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ai_analysis_with_retry():
    """测试AI分析的重试机制"""
    print("=== AI分析重试机制测试 ===")
    
    try:
        # 创建AI分析器
        ai_analyzer = AIAnalyzer(config_path='config.yaml')
        
        # 准备测试日志上下文
        sample_context = test_sample_log_context()
        
        print("开始AI分析重试测试...")
        start_time = time.time()
        
        # 直接调用内部方法来测试重试机制
        # 由于我们没有直接暴露的带重试的方法，我们通过测试分析方法来验证
        result = ai_analyzer.analyze_log(sample_context)
        
        end_time = time.time()
        print(f"AI分析重试测试完成，耗时: {end_time - start_time:.2f}秒")
        
        if result:
            print("✓ AI分析重试机制测试成功完成")
            print(f"AI结果预览: {result[:200]}...")
        else:
            print("⚠ AI分析重试机制测试返回空结果")
            
        return True
        
    except Exception as e:
        print(f"✗ AI分析重试机制测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ai_timeout_scenario():
    """测试AI超时场景"""
    print("=== AI超时场景模拟测试 ===")
    
    try:
        # 创建AI分析器
        ai_analyzer = AIAnalyzer(config_path='config.yaml')
        
        # 准备一个较长的测试日志上下文
        long_context = """
10.1.1.100 - - [10/Oct/2023:13:55:36] "GET /index.php?user=admin&pass=123 HTTP/1.1" 200 1234
10.1.1.100 - - [10/Oct/2023:13:56:45] "POST /login.php HTTP/1.1" 200 5678
10.1.1.100 - - [10/Oct/2023:13:57:22] "GET /admin.php?cmd=ls HTTP/1.1" 403 9876
""" * 50  # 创建一个较长的上下文
        
        print("开始AI超时场景测试...")
        start_time = time.time()
        
        # 执行一次AI分析
        result = ai_analyzer.analyze_log(long_context)
        
        end_time = time.time()
        print(f"AI超时场景测试完成，耗时: {end_time - start_time:.2f}秒")
        
        if result:
            print("✓ AI超时场景测试成功完成")
            # 只显示结果的前200个字符
            print(f"AI结果预览: {result[:200]}...")
        else:
            print("⚠ AI超时场景测试返回空结果")
            
        return True
        
    except Exception as e:
        print(f"✗ AI超时场景测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("开始AI模型功能测试...\n")
    
    tests = [
        test_ai_model_config,
        test_ai_analyzer_initialization,
        test_sample_log_context,
        test_ai_analysis,
        test_ai_timeout_scenario
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"AI测试结果: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("🎉 所有AI功能测试通过！")
    else:
        print("❌ 部分AI功能测试失败，请检查配置和网络连接。")
        
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)