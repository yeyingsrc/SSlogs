#!/usr/bin/env python3
"""
自定义配置和OpenAI兼容API演示脚本
展示如何使用自定义模型名称和API配置
"""

import asyncio
import json
import sys
import time
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.lm_studio_connector import LMStudioConnector, LMStudioConfig, LMStudioAPIConfig, LMStudioModelConfig
from core.ai_config_manager import get_ai_config_manager
from core.model_manager import get_model_manager

def demo_custom_config():
    """演示自定义配置功能"""
    print("🚀 SSlogs 自定义配置演示")
    print("=" * 60)

    # 1. 创建自定义配置
    print("\n1. 创建自定义LM Studio配置")

    api_config = LMStudioAPIConfig(
        base_url="http://127.0.0.1:1234/v1",
        chat_endpoint="/chat/completions",
        models_endpoint="/models",
        api_key="",  # LM Studio通常不需要API密钥
        headers={
            "Content-Type": "application/json",
            "User-Agent": "SSlogs-AI-Demo/1.0"
        }
    )

    model_config = LMStudioModelConfig(
        preferred_model="openai/gpt-oss-20b",  # 使用自定义模型名称
        model_mapping={
            # 将实际模型ID映射为自定义名称
            "llama-3-8b-instruct": "openai/gpt-oss-20b",
            "qwen-7b-chat": "custom/security-analyzer-v1",
            "mistral-7b-instruct": "assistant/code-helper"
        },
        max_tokens=2048,
        temperature=0.7,
        top_p=0.9,
        frequency_penalty=0.0,
        presence_penalty=0.0,
        stream=False,
        response_format={"type": "text"}
    )

    config = LMStudioConfig(
        host="127.0.0.1",
        port=1234,
        timeout=30,
        retry_attempts=3,
        retry_delay=1.0,
        api=api_config,
        model=model_config
    )

    print(f"✅ 自定义配置创建完成")
    print(f"   API地址: {config.api.base_url}")
    print(f"   自定义模型名称: {config.model.preferred_model}")
    print(f"   模型映射数量: {len(config.model.model_mapping)}")

    # 2. 使用配置创建连接器
    print("\n2. 使用自定义配置创建连接器")
    connector = LMStudioConnector(config)

    # 检查连接
    if connector.check_connection():
        print("✅ 连接成功")
        print(f"   可用模型: {len(connector.available_models)}个")

        # 显示模型映射
        print("\n3. 模型名称映射:")
        for actual_id, display_name in config.model.model_mapping.items():
            print(f"   {actual_id} → {display_name}")
    else:
        print("❌ 连接失败，请确保LM Studio正在运行")
        return

    # 3. 测试OpenAI兼容API调用
    print("\n4. 测试OpenAI兼容API调用")
    test_message = [
        {"role": "system", "content": "Always answer in rhymes. Today is Thursday"},
        {"role": "user", "content": "What day is it today?"}
    ]

    try:
        response = connector.chat_completion(
            messages=[LMStudioConnector.ChatMessage(role=msg["role"], content=msg["content"]) for msg in test_message],
            model="openai/gpt-oss-20b",  # 使用映射的模型名称
            temperature=0.7,
            max_tokens=-1,
            stream=False
        )

        if response:
            print("✅ API调用成功")
            print(f"   响应: {response}")
        else:
            print("❌ API调用失败")
    except Exception as e:
        print(f"❌ API调用异常: {e}")

def demo_config_manager():
    """演示配置管理器功能"""
    print("\n" + "=" * 60)
    print("🔧 配置管理器演示")
    print("=" * 60)

    config_manager = get_ai_config_manager()

    # 1. 获取当前配置
    print("\n1. 获取当前配置")
    current_config = config_manager.get_full_config()
    lm_config = current_config.get('lm_studio', {})

    print(f"   主机: {lm_config.get('host', 'N/A')}")
    print(f"   端口: {lm_config.get('port', 'N/A')}")
    print(f"   API地址: {lm_config.get('api', {}).get('base_url', 'N/A')}")
    print(f"   首选模型: {lm_config.get('model', {}).get('preferred_model', 'N/A')}")

    # 2. 更新配置
    print("\n2. 更新配置")
    new_config = {
        "lm_studio": {
            "api": {
                "base_url": "http://127.0.0.1:1234/v1",
                "chat_endpoint": "/chat/completions",
                "models_endpoint": "/models",
                "api_key": ""
            },
            "model": {
                "preferred_model": "openai/gpt-oss-20b",
                "model_mapping": {
                    "llama-3-8b-instruct": "openai/gpt-oss-20b",
                    "qwen-7b-chat": "custom/security-analyzer"
                },
                "max_tokens": 2048,
                "temperature": 0.7,
                "top_p": 0.9
            }
        }
    }

    # 模拟更新配置（实际保存需要调用API）
    print("   模拟配置更新:")
    print(f"   - API地址: {new_config['lm_studio']['api']['base_url']}")
    print(f"   - 首选模型: {new_config['lm_studio']['model']['preferred_model']}")
    print(f"   - 模型映射: {len(new_config['lm_studio']['model']['model_mapping'])}个")

def demo_model_manager():
    """演示模型管理器功能"""
    print("\n" + "=" * 60)
    print("🤖 模型管理器演示")
    print("=" * 60)

    model_manager = get_model_manager()

    # 1. 获取服务器状态
    print("\n1. 检查服务器状态")
    status = model_manager.get_server_status()
    print(f"   连接状态: {'✅ 已连接' if status.connected else '❌ 未连接'}")
    if status.connected:
        print(f"   服务器地址: {status.host}:{status.port}")
        print(f"   可用模型数: {status.available_models_count}")
        print(f"   响应时间: {status.response_time:.2f}秒")

    # 2. 刷新模型列表
    print("\n2. 刷新模型列表")
    try:
        models = model_manager.refresh_models()
        print(f"   发现 {len(models)} 个模型")

        for i, model in enumerate(models[:3], 1):  # 只显示前3个
            print(f"   {i}. {model.name} (ID: {model.id})")
            print(f"      兼容性: {model.compatibility_score:.1f}/5.0")
            print(f"      推荐: {'是' if model.recommended else '否'}")
    except Exception as e:
        print(f"   ❌ 刷新失败: {e}")

def demo_openai_api_format():
    """演示OpenAI格式API调用"""
    print("\n" + "=" * 60)
    print("🔌 OpenAI兼容API演示")
    print("=" * 60)

    # 模拟curl命令
    print("\n1. 等效的curl命令:")
    curl_command = '''curl http://localhost:1234/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "openai/gpt-oss-20b",
    "messages": [
      { "role": "system", "content": "Always answer in rhymes. Today is Thursday" },
      { "role": "user", "content": "What day is it today?" }
    ],
    "temperature": 0.7,
    "max_tokens": -1,
    "stream": false
  }''''

    print(curl_command)

    # 2. Python代码示例
    print("\n2. Python调用示例:")
    python_example = '''
import requests

response = requests.post(
    "http://localhost:1234/v1/chat/completions",
    headers={"Content-Type": "application/json"},
    json={
        "model": "openai/gpt-oss-20b",
        "messages": [
            {"role": "system", "content": "Always answer in rhymes. Today is Thursday"},
            {"role": "user", "content": "What day is it today?"}
        ],
        "temperature": 0.7,
        "max_tokens": -1,
        "stream": False
    }
)

result = response.json()
print(result["choices"][0]["message"]["content"])
'''
    print(python_example)

def main():
    """主函数"""
    try:
        demo_custom_config()
        demo_config_manager()
        demo_model_manager()
        demo_openai_api_format()

        print("\n" + "=" * 60)
        print("🎉 演示完成!")
        print("=" * 60)
        print("\n💡 提示:")
        print("1. 启动LM Studio并加载模型")
        print("2. 使用Web界面进行交互式配置: http://127.0.0.1:8080")
        print("3. 通过API接口管理配置和测试模型")
        print("4. 支持自定义模型名称映射")

    except KeyboardInterrupt:
        print("\n\n⏹️ 演示被用户中断")
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()