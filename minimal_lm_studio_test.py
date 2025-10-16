#!/usr/bin/env python3
"""
最小化LM Studio测试（无外部依赖）
"""

import subprocess
import json
import sys
from pathlib import Path

def test_with_curl():
    """使用curl测试LM Studio"""
    print("🧪 使用curl测试LM Studio")
    print("=" * 40)

    model_name = "openai/gpt-oss-20b"

    # 1. 测试模型列表
    print("\n1. 测试模型列表...")
    try:
        result = subprocess.run([
            'curl', '-s', '--connect-timeout', '5',
            'http://127.0.0.1:1234/v1/models'
        ], capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            data = json.loads(result.stdout)
            models = data.get('data', [])
            print(f"✅ 连接成功！发现 {len(models)} 个模型")

            # 查找目标模型
            model_found = False
            for model in models:
                model_id = model.get('id', '')
                if model_id == model_name:
                    model_found = True
                    print(f"✅ 找到目标模型: {model_name}")
                    break

            if not model_found:
                print(f"❌ 未找到模型: {model_name}")
                print("可用模型:")
                for model in models[:5]:
                    print(f"  • {model.get('id', 'Unknown')}")
                return False
        else:
            print(f"❌ 获取模型列表失败: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

    # 2. 测试聊天请求
    print(f"\n2. 测试聊天请求...")
    try:
        payload = {
            "model": model_name,
            "messages": [
                {"role": "user", "content": "你好，请简单回复确认连接正常"}
            ],
            "temperature": 0.3,
            "max_tokens": 50
        }

        payload_str = json.dumps(payload)

        result = subprocess.run([
            'curl', '-s', '-X', 'POST',
            'http://127.0.0.1:1234/v1/chat/completions',
            '-H', 'Content-Type: application/json',
            '-d', payload_str
        ], capture_output=True, text=True, timeout=15)

        if result.returncode == 0:
            response = json.loads(result.stdout)
            content = response.get('choices', [{}])[0].get('message', {}).get('content', '')

            if content:
                print(f"✅ 聊天测试成功！")
                print(f"  响应: {content}")
                return True
            else:
                print("❌ 响应内容为空")
                print(f"完整响应: {result.stdout}")
                return False
        else:
            print(f"❌ 聊天请求失败: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ 聊天测试异常: {e}")
        return False

def check_config_file():
    """检查配置文件"""
    print("\n" + "=" * 40)
    print("📋 检查配置文件")
    print("=" * 40)

    config_file = Path("config/ai_config.yaml")
    if config_file.exists():
        print(f"✅ 配置文件存在: {config_file}")

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 检查关键配置
            if "lm_studio:" in content:
                print("✅ LM Studio配置存在")

            if "model_mapping:" in content:
                print("✅ 模型映射配置存在")

            if "openai/gpt-oss-20b" in content:
                print("✅ 找到模型名称配置")

            # 检查端口配置
            if "port: 1234" in content:
                print("✅ 端口配置正确")

            return True

        except Exception as e:
            print(f"❌ 读取配置文件失败: {e}")
            return False
    else:
        print(f"❌ 配置文件不存在: {config_file}")
        return False

def main():
    """主函数"""
    print("🚀 最小化LM Studio测试")
    print("=" * 50)

    # 检查配置文件
    config_ok = check_config_file()

    # 测试LM Studio连接
    lm_studio_ok = test_with_curl()

    print("\n" + "=" * 50)
    print("📊 测试结果:")
    print(f"  配置文件: {'✅ 正常' if config_ok else '❌ 有问题'}")
    print(f"  LM Studio连接: {'✅ 正常' if lm_studio_ok else '❌ 有问题'}")

    if config_ok and lm_studio_ok:
        print("\n🎉 基础测试通过！")
        print("LM Studio API工作正常，问题可能在于:")
        print("  • GUI中的依赖模块缺失")
        print("  • 配置管理器实现问题")
        print("  • 连接器配置问题")

        print("\n💡 建议安装缺失的依赖:")
        print("  pip install pyyaml requests aiohttp")

    elif lm_studio_ok:
        print("\n⚠️ LM Studio工作正常，但配置文件有问题")

    else:
        print("\n❌ LM Studio连接有问题")
        print("请确保:")
        print("  • LM Studio正在运行")
        print("  • 本地服务器已启动 (端口1234)")
        print("  • 模型已加载完成")

if __name__ == "__main__":
    main()