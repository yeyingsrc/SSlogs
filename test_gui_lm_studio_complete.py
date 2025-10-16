#!/usr/bin/env python3
"""
完整的GUI LM Studio测试
模拟用户在GUI中填写模型名称并点击测试的过程
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

def simulate_gui_lm_studio_test():
    """模拟GUI中的LM Studio测试过程"""
    print("🧪 模拟GUI LM Studio测试过程")
    print("=" * 50)

    # 模拟用户输入
    model_type = "本地 (LM Studio)"
    model_name = "openai/gpt-oss-20b"

    print(f"模型类型: {model_type}")
    print(f"模型名称: {model_name}")

    try:
        # 1. 检查模型名称是否为空（GUI中的验证逻辑）
        if not model_name.strip():
            print("❌ 请先输入模型名称")
            return False

        # 2. 导入LM Studio相关模块（GUI中的导入逻辑）
        print("\n1. 导入LM Studio模块...")
        from core.lm_studio_connector import LMStudioConnector, LMStudioConfig, LMStudioAPIConfig, LMStudioModelConfig
        from core.ai_config_manager import get_ai_config_manager
        print("✅ 模块导入成功")

        # 3. 获取配置管理器（GUI中的配置获取逻辑）
        print("\n2. 获取配置...")
        config_manager = get_ai_config_manager()
        lm_config = config_manager.get_lm_studio_config()
        print(f"  主机: {lm_config.host}:{lm_config.port}")
        print(f"  API地址: {lm_config.api.base_url}")
        print(f"  首选模型: {lm_config.model.preferred_model or '未设置'}")

        # 4. 创建连接器（GUI中的连接器创建逻辑）
        print("\n3. 创建LM Studio连接器...")
        connector = LMStudioConnector(lm_config)
        print("✅ 连接器创建成功")

        # 5. 检查LM Studio连接（GUI中的连接检查逻辑）
        print("\n4. 检查LM Studio连接...")
        if connector.check_connection():
            print(f"✅ LM Studio连接成功！")
            print(f"  可用模型: {len(connector.available_models)}个")

            # 检查指定模型是否可用
            if model_name in connector.available_models:
                print(f"✅ 模型 '{model_name}' 直接可用")
            else:
                # 检查是否有映射
                actual_model_id = lm_config.get_actual_model_id(model_name)
                print(f"  映射后的实际ID: {actual_model_id}")

                if actual_model_id in connector.available_models:
                    print(f"✅ 模型 '{actual_model_id}' (映射后) 可用")
                else:
                    print(f"❌ 模型 '{model_name}' 不可用")
                    print("  可用模型:")
                    for model in connector.available_models[:5]:
                        print(f"    • {model}")
                    if len(connector.available_models) > 5:
                        print(f"    ... 还有 {len(connector.available_models) - 5} 个模型")
                    return False
        else:
            print("❌ 无法连接到LM Studio")
            print("请确保:")
            print("  1. LM Studio正在运行")
            print("  2. 本地服务器已启动 (端口1234)")
            print("  3. 已加载模型")
            return False

        # 6. 测试模型响应（GUI中的模型测试逻辑）
        print(f"\n5. 测试模型响应...")
        try:
            from core.lm_studio_connector import ChatMessage

            # 构建测试消息（与GUI中相同的消息）
            test_result = connector.chat_completion(
                messages=[ChatMessage(
                    role="user",
                    content="你好，请简单回复确认连接正常"
                )],
                model=model_name,  # 使用用户输入的模型名称
                temperature=0.3,
                max_tokens=100
            )

            if test_result:
                print(f"✅ LM Studio连接成功！")
                print(f"  模型响应:")
                print(f"  {test_result}")

                # 模拟GUI中的成功消息
                print(f"\n🎉 GUI会显示成功消息:")
                print(f"  LM Studio连接成功！")
                print(f"  模型响应: {test_result[:100]}...")
                return True
            else:
                print("❌ LM Studio连接成功但模型响应失败")
                # 模拟GUI中的警告消息
                print(f"\n⚠️ GUI会显示警告消息:")
                print(f"  LM Studio连接成功但模型响应失败")
                return False

        except Exception as e:
            print(f"❌ 模型响应测试异常: {e}")
            # 模拟GUI中的错误消息
            print(f"\n❌ GUI会显示错误消息:")
            print(f"  LM Studio连接测试失败: {str(e)}")
            return False

    except ImportError as e:
        print(f"❌ LM Studio模块未找到，请确保已安装相关依赖")
        print(f"  错误: {e}")
        # 模拟GUI中的警告消息
        print(f"\n⚠️ GUI会显示警告消息:")
        print(f"  LM Studio模块未找到，请确保已安装相关依赖")
        return False
    except Exception as e:
        print(f"❌ LM Studio连接测试失败: {str(e)}")
        # 模拟GUI中的错误消息
        print(f"\n❌ GUI会显示错误消息:")
        print(f"  LM Studio连接测试失败: {str(e)}")
        return False

def test_different_model_names():
    """测试不同的模型名称"""
    print("\n" + "=" * 50)
    print("🔍 测试不同的模型名称")
    print("=" * 50)

    test_models = [
        "openai/gpt-oss-20b",  # 用户使用的模型名称
        "gpt-oss-20b",        # LM Studio中的另一个变体
        "qwen/qwen3-vl-30b",  # 其他可用模型
    ]

    try:
        from core.lm_studio_connector import LMStudioConnector
        from core.ai_config_manager import get_ai_config_manager

        config_manager = get_ai_config_manager()
        lm_config = config_manager.get_lm_studio_config()
        connector = LMStudioConnector(lm_config)

        connector.check_connection()  # 刷新模型列表

        print(f"可用模型总数: {len(connector.available_models)}")

        for model_name in test_models:
            print(f"\n测试模型: {model_name}")

            # 检查是否可用
            actual_id = lm_config.get_actual_model_id(model_name)
            is_available = actual_id in connector.available_models

            print(f"  映射后ID: {actual_id}")
            print(f"  可用性: {'✅ 可用' if is_available else '❌ 不可用'}")

            if is_available:
                # 进行快速测试
                try:
                    from core.lm_studio_connector import ChatMessage
                    result = connector.chat_completion(
                        messages=[ChatMessage(role="user", content="测试")],
                        model=model_name,
                        max_tokens=10
                    )
                    print(f"  响应测试: {'✅ 成功' if result else '❌ 失败'}")
                    if result:
                        print(f"  响应内容: {result[:50]}...")
                except Exception as e:
                    print(f"  响应测试: ❌ 异常: {e}")

    except Exception as e:
        print(f"❌ 测试异常: {e}")

def main():
    """主函数"""
    print("🚀 完整GUI LM Studio测试")
    print("=" * 60)

    # 1. 模拟GUI测试过程
    success = simulate_gui_lm_studio_test()

    # 2. 测试不同模型名称
    test_different_model_names()

    print("\n" + "=" * 60)
    print("📊 测试总结:")
    print(f"  主要测试: {'✅ 成功' if success else '❌ 失败'}")

    if success:
        print("\n🎉 GUI LM Studio集成测试通过！")
        print("用户可以在GUI中:")
        print("  • 选择 '本地 (LM Studio)' 模型类型")
        print("  • 输入模型名称: openai/gpt-oss-20b")
        print("  • 点击 '测试AI连接' 获得成功结果")
        print("  • 启用AI分析进行日志分析")

        print("\n💡 使用提示:")
        print("  1. 确保LM Studio正在运行")
        print("  2. 确保本地服务器启动在端口1234")
        print("  3. 确保模型已完全加载")
        print("  4. 使用虚拟环境启动GUI: ./venv/bin/python launcher.py --gui")

    else:
        print("\n❌ GUI LM Studio集成测试失败")
        print("请检查:")
        print("  • LM Studio是否正在运行")
        print("  • 依赖模块是否正确安装")
        print("  • 配置文件是否正确")
        print("  • 模型名称是否正确")

if __name__ == "__main__":
    main()