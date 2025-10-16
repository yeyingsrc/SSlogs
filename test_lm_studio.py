#!/usr/bin/env python3
"""
LM Studio连接测试脚本
用于诊断模型名称和连接问题
"""

import requests
import json
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from core.lm_studio_connector import LMStudioConnector, LMStudioConfig
from core.ai_config_manager import get_ai_config_manager

def test_lm_studio_connection():
    """测试LM Studio连接"""
    print("🔍 LM Studio连接诊断")
    print("=" * 50)

    # 1. 测试基本连接
    print("\n1. 测试基本连接...")
    try:
        response = requests.get("http://127.0.0.1:1234/v1/models", timeout=5)
        if response.status_code == 200:
            models = response.json().get("data", [])
            print(f"✅ 连接成功！发现 {len(models)} 个模型")

            if models:
                print("\n📋 可用模型列表:")
                for i, model in enumerate(models, 1):
                    model_id = model.get("id", "Unknown")
                    print(f"  {i}. {model_id}")
            else:
                print("❌ 未发现可用模型，请确保在LM Studio中加载了模型")
                return False
        else:
            print(f"❌ 连接失败: HTTP {response.status_code}")
            print(f"响应: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 连接异常: {e}")
        print("请确保:")
        print("  • LM Studio正在运行")
        print("  • 本地服务器已启动 (端口1234)")
        print("  • 已加载至少一个模型")
        return False

    # 2. 测试配置管理器
    print("\n2. 测试配置管理器...")
    try:
        config_manager = get_ai_config_manager()
        lm_config = config_manager.get_lm_studio_config()
        print(f"✅ 配置加载成功")
        print(f"  主机: {lm_config.host}:{lm_config.port}")
        print(f"  API地址: {lm_config.api.base_url}")
        print(f"  首选模型: {lm_config.model.preferred_model or '未设置'}")
        print(f"  模型映射: {len(lm_config.model.model_mapping)}个")

        if lm_config.model.model_mapping:
            print("  📝 映射关系:")
            for actual, mapped in lm_config.model.model_mapping.items():
                print(f"    {actual} → {mapped}")
        else:
            print("  ⚠️ 无模型名称映射")
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return False

    # 3. 测试连接器
    print("\n3. 测试LM Studio连接器...")
    try:
        connector = LMStudioConnector(lm_config)

        if connector.check_connection():
            print("✅ 连接器测试成功")
            print(f"  可用模型: {len(connector.available_models)}个")
            print(f"  当前模型: {connector.current_model or '未设置'}")
        else:
            print("❌ 连接器测试失败")
            return False
    except Exception as e:
        print(f"❌ 连接器异常: {e}")
        return False

    # 4. 测试模型名称
    print("\n4. 测试模型名称...")
    test_model_name = "openai/gpt-oss-20b"
    print(f"测试模型名称: {test_model_name}")

    # 检查是否为映射名称
    actual_model_id = lm_config.get_actual_model_id(test_model_name)
    print(f"映射后的实际ID: {actual_model_id}")

    # 检查模型是否可用
    if actual_model_id in connector.available_models:
        print(f"✅ 模型 {actual_model_id} 可用")
    else:
        print(f"❌ 模型 {actual_model_id} 不可用")
        print("可用模型:")
        for model in connector.available_models:
            print(f"  • {model}")

        # 建议解决方案
        if connector.available_models:
            suggested_model = connector.available_models[0]
            print(f"\n💡 建议:")
            print(f"1. 使用可用模型: {suggested_model}")
            print(f"2. 或在配置中添加映射:")
            print(f"   model_mapping:")
            print(f"     '{suggested_model}': '{test_model_name}'")

    # 5. 测试聊天请求
    print("\n5. 测试聊天请求...")
    try:
        # 使用第一个可用模型进行测试
        if connector.available_models:
            test_model = connector.available_models[0]
            print(f"使用模型: {test_model}")

            from core.lm_studio_connector import ChatMessage
            messages = [
                ChatMessage(role="user", content="你好，请简单回复确认连接正常")
            ]

            result = connector.chat_completion(
                messages=messages,
                model=test_model,
                max_tokens=50,
                temperature=0.3
            )

            if result:
                print(f"✅ 聊天测试成功")
                print(f"回复: {result[:100]}...")
            else:
                print("❌ 聊天测试失败")
        else:
            print("❌ 无可用模型进行测试")
    except Exception as e:
        print(f"❌ 聊天测试异常: {e}")

    return True

def main():
    """主函数"""
    print("🚀 LM Studio连接诊断工具")
    print("=" * 60)

    try:
        success = test_lm_studio_connection()

        print("\n" + "=" * 60)
        if success:
            print("✅ 诊断完成")
        else:
            print("❌ 诊断发现问题，请根据上述信息进行修复")

    except KeyboardInterrupt:
        print("\n\n⏹️ 诊断被用户中断")
    except Exception as e:
        print(f"\n❌ 诊断过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()