#!/usr/bin/env python3
"""
测试GUI中的LM Studio连接逻辑
模拟GUI中的测试过程
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

def test_lm_studio_as_in_gui():
    """按照GUI中的逻辑测试LM Studio连接"""
    print("🧪 模拟GUI LM Studio测试逻辑")
    print("=" * 50)

    model_name = "openai/gpt-oss-20b"
    print(f"测试模型名称: {model_name}")

    try:
        # 1. 导入模块（GUI中的导入逻辑）
        print("\n1. 导入模块...")
        from core.lm_studio_connector import LMStudioConnector, LMStudioConfig, LMStudioAPIConfig, LMStudioModelConfig
        from core.ai_config_manager import get_ai_config_manager
        print("✅ 模块导入成功")

        # 2. 获取配置管理器
        print("\n2. 获取配置...")
        config_manager = get_ai_config_manager()
        lm_config = config_manager.get_lm_studio_config()
        print(f"  主机: {lm_config.host}:{lm_config.port}")
        print(f"  首选模型: {lm_config.model.preferred_model or '未设置'}")
        print(f"  模型映射: {lm_config.model.model_mapping}")

        # 3. 创建连接器
        print("\n3. 创建连接器...")
        connector = LMStudioConnector(lm_config)
        print("✅ 连接器创建成功")

        # 4. 检查连接
        print("\n4. 检查LM Studio连接...")
        if connector.check_connection():
            print(f"✅ 连接成功！")
            print(f"  可用模型: {len(connector.available_models)}个")
            print(f"  当前模型: {connector.current_model}")

            # 显示可用模型
            if connector.available_models:
                print("  📋 可用模型列表:")
                for model in connector.available_models[:5]:  # 只显示前5个
                    print(f"    • {model}")
                if len(connector.available_models) > 5:
                    print(f"    ... 还有 {len(connector.available_models) - 5} 个模型")
        else:
            print("❌ 连接失败")
            return False

        # 5. 检查指定模型是否可用
        print(f"\n5. 检查模型 '{model_name}' 是否可用...")
        actual_model_id = lm_config.get_actual_model_id(model_name)
        print(f"  映射后的实际ID: {actual_model_id}")

        if actual_model_id in connector.available_models:
            print(f"✅ 模型 '{actual_model_id}' 可用")
        else:
            print(f"❌ 模型 '{actual_model_id}' 不可用")
            print("  可用模型:")
            for model in connector.available_models:
                print(f"    • {model}")
            return False

        # 6. 测试模型响应
        print(f"\n6. 测试模型响应...")
        try:
            from core.lm_studio_connector import ChatMessage

            test_result = connector.chat_completion(
                messages=[ChatMessage(
                    role="user",
                    content="你好，请简单回复确认连接正常"
                )],
                model=model_name  # 使用原始模型名称
            )

            if test_result:
                print(f"✅ 模型响应成功！")
                print(f"  响应: {test_result[:100]}...")
                return True
            else:
                print("❌ 模型响应失败")
                return False

        except Exception as e:
            print(f"❌ 模型响应异常: {e}")
            import traceback
            traceback.print_exc()
            return False

    except ImportError as e:
        print(f"❌ 模块导入失败: {e}")
        print("请确保已安装相关依赖:")
        print("  pip install requests aiohttp")
        return False
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_direct_request():
    """直接使用requests测试（绕过连接器）"""
    print("\n" + "=" * 50)
    print("🔗 直接API测试")
    print("=" * 50)

    import requests

    model_name = "openai/gpt-oss-20b"
    url = "http://127.0.0.1:1234/v1/chat/completions"

    payload = {
        "model": model_name,
        "messages": [
            {"role": "user", "content": "你好，请简单回复确认连接正常"}
        ],
        "temperature": 0.3,
        "max_tokens": 50
    }

    try:
        print(f"发送请求到: {url}")
        print(f"使用模型: {model_name}")

        response = requests.post(url, json=payload, timeout=10)

        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            print(f"✅ 直接API测试成功！")
            print(f"  响应: {content}")
            return True
        else:
            print(f"❌ API请求失败: HTTP {response.status_code}")
            print(f"  响应: {response.text}")
            return False

    except Exception as e:
        print(f"❌ API请求异常: {e}")
        return False

def main():
    """主函数"""
    print("🚀 GUI LM Studio 连接测试")
    print("=" * 60)

    # 测试GUI逻辑
    gui_success = test_lm_studio_as_in_gui()

    # 测试直接API
    api_success = test_direct_request()

    print("\n" + "=" * 60)
    print("📊 测试结果:")
    print(f"  GUI逻辑测试: {'✅ 成功' if gui_success else '❌ 失败'}")
    print(f"  直接API测试: {'✅ 成功' if api_success else '❌ 失败'}")

    if gui_success and api_success:
        print("\n🎉 所有测试通过！LM Studio应该可以在GUI中正常工作。")
    elif api_success and not gui_success:
        print("\n⚠️ 直接API正常，但GUI逻辑有问题。")
        print("建议检查:")
        print("  • 配置文件是否正确加载")
        print("  • 模型名称映射是否正确")
        print("  • 连接器实现是否有问题")
    else:
        print("\n❌ 基础连接有问题，请检查:")
        print("  • LM Studio是否正在运行")
        print("  • 端口1234是否可用")
        print("  • 模型是否已加载")

if __name__ == "__main__":
    main()