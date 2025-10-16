#!/usr/bin/env python3
"""
测试修复后的GUI LM Studio连接功能
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

def test_fixed_lm_studio_connection():
    """测试修复后的LM Studio连接功能"""
    print("🔧 测试修复后的GUI LM Studio连接功能")
    print("=" * 60)

    try:
        # 导入修复后的模块
        from core.lm_studio_connector import LMStudioConnector, ChatMessage
        from core.ai_config_manager import get_ai_config_manager

        print("✅ 模块导入成功（包含ChatMessage）")

        # 创建连接器
        config_manager = get_ai_config_manager()
        lm_config = config_manager.get_lm_studio_config()
        connector = LMStudioConnector(lm_config)

        print("✅ 连接器创建成功")

        # 检查连接
        if connector.check_connection():
            print("✅ LM Studio连接成功")

            # 测试ChatMessage创建
            test_message = ChatMessage(
                role="user",
                content="你好，请简单回复确认连接正常"
            )
            print("✅ ChatMessage创建成功")

            # 测试聊天功能
            test_result = connector.chat_completion(
                messages=[test_message],
                model="openai/gpt-oss-20b"
            )

            if test_result:
                print(f"✅ 聊天测试成功！")
                print(f"  响应: {test_result[:100]}...")
                return True
            else:
                print("❌ 聊天测试失败")
                return False
        else:
            print("❌ LM Studio连接失败")
            return False

    except ImportError as e:
        print(f"❌ 模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

def test_gui_model_selection():
    """测试GUI模型选择功能"""
    print("\n" + "=" * 60)
    print("🖥️ 测试GUI模型选择和连接测试")
    print("=" * 60)

    try:
        # 模拟GUI操作流程
        from core.lm_studio_connector import LMStudioConnector, ChatMessage
        from core.ai_config_manager import get_ai_config_manager

        # 1. 模拟选择LM Studio模型类型
        model_type = "本地 (LM Studio)"
        print(f"1. 选择模型类型: {model_type}")

        # 2. 获取模型列表
        config_manager = get_ai_config_manager()
        lm_config = config_manager.get_lm_studio_config()
        connector = LMStudioConnector(lm_config)

        if connector.check_connection():
            models = connector.available_models
            print(f"2. 加载模型列表: {len(models)}个模型")

            # 3. 选择第一个模型
            if models:
                selected_model = models[0]
                print(f"3. 选择模型: {selected_model}")

                # 4. 测试连接（模拟GUI中的测试）
                test_message = ChatMessage(
                    role="user",
                    content="你好，请简单回复确认连接正常"
                )

                test_result = connector.chat_completion(
                    messages=[test_message],
                    model=selected_model
                )

                if test_result:
                    print("4. ✅ GUI连接测试成功！")
                    print(f"   模型响应: {test_result[:50]}...")
                    print("\n🎉 GUI功能完全正常！")
                    return True
                else:
                    print("4. ❌ GUI连接测试失败")
                    return False
            else:
                print("3. ❌ 无可用模型")
                return False
        else:
            print("2. ❌ 无法连接LM Studio")
            return False

    except Exception as e:
        print(f"❌ GUI测试异常: {e}")
        return False

def main():
    """主函数"""
    print("🚀 修复验证测试")
    print("=" * 70)

    # 1. 测试修复后的连接功能
    connection_success = test_fixed_lm_studio_connection()

    # 2. 测试GUI模型选择功能
    gui_success = test_gui_model_selection()

    print("\n" + "=" * 70)
    print("📊 修复验证结果:")
    print(f"  ChatMessage修复: {'✅ 成功' if connection_success else '❌ 失败'}")
    print(f"  GUI功能测试: {'✅ 成功' if gui_success else '❌ 失败'}")

    if connection_success and gui_success:
        print("\n🎉 修复完成！所有功能正常工作！")
        print("\n✨ 用户现在可以:")
        print("  • 在GUI中看到LM Studio模型下拉选择")
        print("  • 从下拉菜单选择可用模型")
        print("  • 点击测试按钮成功验证连接")
        print("  • 使用AI分析进行智能日志分析")

        print("\n💡 推荐使用步骤:")
        print("  1. 启动GUI: ./venv/bin/python launcher.py --gui")
        print("  2. 选择 'AI配置' 选项卡")
        print("  3. 选择 '本地 (LM Studio)'")
        print("  4. 从下拉菜单选择模型（如 openai/gpt-oss-20b）")
        print("  5. 点击 '测试AI连接' 验证")
        print("  6. 启用AI分析开始使用")

    else:
        print("\n❌ 修复验证失败")
        print("请检查相关功能是否正常工作")

if __name__ == "__main__":
    main()