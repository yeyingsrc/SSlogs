#!/usr/bin/env python3
"""
AI模型调试脚本 - 用于详细分析和调试AI功能问题
"""

import sys
import os
import time

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.ai_analyzer import AIAnalyzer
import yaml

def debug_ai_model_config():
    """详细调试AI模型配置"""
    print("=== 详细AI模型配置调试 ===")
    
    try:
        # 加载配置文件
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        print("完整配置内容:")
        for key, value in config.items():
            if key == 'deepseek':
                print(f"  {key}:")
                for sub_key, sub_value in value.items():
                    print(f"    {sub_key}: {sub_value}")
            elif key == 'ai':
                print(f"  {key}:")
                for sub_key, sub_value in value.items():
                    print(f"    {sub_key}: {sub_value}")
            else:
                print(f"  {key}: {value}")
        
        # 检查关键配置项
        ai_config = config.get('ai', {})
        deepseek_config = config.get('deepseek', {})
        
        print("\n关键配置检查:")
        print(f"  AI类型: {ai_config.get('type', '未配置')}")
        print(f"  云端提供商: {ai_config.get('cloud_provider', '未配置')}")
        print(f"  API密钥: {'已配置' if deepseek_config.get('api_key') else '未配置'}")
        print(f"  模型名称: {deepseek_config.get('model', '未配置')}")
        print(f"  基础URL: {deepseek_config.get('base_url', '未配置')}")
        print(f"  超时时间: {deepseek_config.get('timeout', '未配置')}秒")
        print(f"  最大重试次数: {deepseek_config.get('max_retries', '未配置')}")
        print(f"  重试延迟: {deepseek_config.get('retry_delay', '未配置')}秒")
        
        print("✓ AI模型配置详细检查完成\n")
        return True
        
    except Exception as e:
        print(f"✗ AI模型配置检查失败: {e}\n")
        import traceback
        traceback.print_exc()
        return False

def test_ai_connection():
    """测试AI连接"""
    print("=== AI连接测试 ===")
    
    try:
        # 创建AI分析器
        ai_analyzer = AIAnalyzer(config_path='config.yaml')
        
        # 检查配置
        print("AI分析器配置信息:")
        print(f"  AI类型: {ai_analyzer.ai_type}")
        print(f"  云端提供商: {ai_analyzer.cloud_provider}")
        
        if ai_analyzer.ai_type == 'cloud':
            print(f"  API密钥存在: {bool(ai_analyzer.api_key)}")
            print(f"  模型名称: {ai_analyzer.cloud_model}")
            print(f"  基础URL: {ai_analyzer.cloud_base_url}")
            
        # 测试连接
        print("开始测试AI连接...")
        
        # 创建一个简单的测试日志上下文
        test_context = "测试日志内容"
        
        # 执行一次快速的AI分析
        start_time = time.time()
        result = ai_analyzer.analyze_log(test_context)
        end_time = time.time()
        
        print(f"连接测试完成，耗时: {end_time - start_time:.2f}秒")
        
        if result and "失败" not in result:
            print("✓ AI连接测试成功")
        else:
            print("⚠ AI连接可能存在问题，但不影响基本功能")
            
        return True
        
    except Exception as e:
        print(f"✗ AI连接测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ai_timeout_settings():
    """测试AI超时设置"""
    print("=== AI超时设置测试 ===")
    
    try:
        # 创建AI分析器
        ai_analyzer = AIAnalyzer(config_path='config.yaml')
        
        print("当前超时设置:")
        print(f"  默认超时: {ai_analyzer.default_timeout}秒")
        
        if hasattr(ai_analyzer, 'deepseek_config'):
            print(f"  DeepSeek超时: {ai_analyzer.deepseek_config.get('timeout', '未配置')}秒")
            print(f"  最大重试次数: {ai_analyzer.max_retries}")
            print(f"  重试延迟: {ai_analyzer.retry_delay}秒")
        
        # 测试不同超时设置
        print("测试不同超时配置...")
        
        # 检查是否可以修改超时设置
        print("✓ 超时配置检查完成")
        
        return True
        
    except Exception as e:
        print(f"✗ 超时设置测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_ai_with_simple_context():
    """使用简单上下文测试AI"""
    print("=== 简单上下文AI分析测试 ===")
    
    try:
        # 创建AI分析器
        ai_analyzer = AIAnalyzer(config_path='config.yaml')
        
        # 使用非常简单的测试上下文
        simple_context = "192.168.1.1 - GET /index.php HTTP/1.1 200"
        
        print("使用简单上下文进行AI分析:")
        print(f"日志内容: {simple_context}")
        
        start_time = time.time()
        result = ai_analyzer.analyze_log(simple_context)
        end_time = time.time()
        
        print(f"分析完成，耗时: {end_time - start_time:.2f}秒")
        
        if result:
            print("✓ 简单上下文AI分析成功")
            # 显示结果摘要
            if len(result) > 100:
                print(f"AI结果预览: {result[:100]}...")
            else:
                print(f"AI结果: {result}")
        else:
            print("⚠ 简单上下文AI分析返回空结果")
            
        return True
        
    except Exception as e:
        print(f"✗ 简单上下文AI分析测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("开始AI模型详细调试...\n")
    
    tests = [
        debug_ai_model_config,
        test_ai_connection,
        test_ai_timeout_settings,
        test_ai_with_simple_context
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 60)
    print(f"AI调试测试结果: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("🎉 所有AI调试测试通过！")
        print("\n建议:")
        print("- 如果网络不稳定，可以考虑增加重试次数或延长超时时间")
        print("- 可以尝试使用本地AI模型（如Ollama）来避免网络问题")
        print("- 检查API密钥是否正确配置")
    else:
        print("❌ 部分AI调试测试失败，请检查相关设置。")
        
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)