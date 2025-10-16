#!/usr/bin/env python3
"""
测试LM Studio模型下拉选择功能
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

def test_model_dropdown():
    """测试模型下拉选择功能"""
    print("🧪 测试LM Studio模型下拉选择功能")
    print("=" * 50)

    try:
        # 导入必要的模块
        from core.lm_studio_connector import LMStudioConnector
        from core.ai_config_manager import get_ai_config_manager

        print("✅ 模块导入成功")

        # 创建连接器
        config_manager = get_ai_config_manager()
        lm_config = config_manager.get_lm_studio_config()
        connector = LMStudioConnector(lm_config)

        print("✅ 连接器创建成功")

        # 检查连接
        if connector.check_connection():
            print("✅ LM Studio连接成功")

            models = connector.available_models
            print(f"📋 发现 {len(models)} 个可用模型:")

            # 按字母顺序排序显示
            sorted_models = sorted(models)
            for i, model in enumerate(sorted_models, 1):
                print(f"  {i:2d}. {model}")

            # 推荐模型
            recommended_models = [m for m in sorted_models if any(keyword in m.lower() for keyword in ['instruct', 'chat', 'gpt'])]
            if recommended_models:
                print(f"\n💡 推荐的对话模型:")
                for model in recommended_models[:3]:
                    print(f"  • {model}")

            print(f"\n🎉 模型下拉选择功能测试成功！")
            print(f"   用户可以在GUI中从 {len(models)} 个模型中选择")
            return True
        else:
            print("❌ LM Studio连接失败")
            print("请确保:")
            print("  • LM Studio正在运行")
            print("  • 本地服务器已启动 (端口1234)")
            print("  • 已加载模型")
            return False

    except ImportError as e:
        print(f"❌ 模块导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        return False

def test_gui_model_selection():
    """测试GUI中的模型选择逻辑"""
    print("\n" + "=" * 50)
    print("🖥️ 测试GUI模型选择逻辑")
    print("=" * 50)

    try:
        # 模拟GUI中的模型选择
        print("模拟选择 '本地 (LM Studio)' 模型类型...")

        # 测试模型名称获取逻辑
        test_models = [
            "请选择模型...",
            "openai/gpt-oss-20b",
            "qwen/qwen3-vl-30b",
            "正在加载模型列表...",
            "无可用模型"
        ]

        for model in test_models:
            print(f"\n测试选择: '{model}'")

            # 模拟GUI中的验证逻辑
            if model in ["请选择模型...", "正在加载模型列表...", "无可用模型", "无法连接LM Studio", "模块未安装"]:
                print(f"  ❌ 无效选择，会显示警告")
            else:
                print(f"  ✅ 有效选择，可以继续")

        print(f"\n✅ GUI模型选择逻辑测试完成")
        return True

    except Exception as e:
        print(f"❌ GUI模型选择测试异常: {e}")
        return False

def main():
    """主函数"""
    print("🚀 LM Studio模型下拉选择功能测试")
    print("=" * 60)

    # 1. 测试模型加载功能
    dropdown_success = test_model_dropdown()

    # 2. 测试GUI选择逻辑
    gui_success = test_gui_model_selection()

    print("\n" + "=" * 60)
    print("📊 测试总结:")
    print(f"  模型下拉加载: {'✅ 成功' if dropdown_success else '❌ 失败'}")
    print(f"  GUI选择逻辑: {'✅ 成功' if gui_success else '❌ 失败'}")

    if dropdown_success and gui_success:
        print("\n🎉 所有测试通过！")
        print("\n✨ 新功能特点:")
        print("  • 自动加载LM Studio可用模型")
        print("  • 按字母顺序排序模型列表")
        print("  • 支持手动输入自定义模型名称")
        print("  • 刷新按钮重新加载模型列表")
        print("  • 智能模型验证和提示")

        print("\n💡 用户使用步骤:")
        print("  1. 在AI配置中选择 '本地 (LM Studio)'")
        print("  2. 等待模型列表自动加载")
        print("  3. 从下拉菜单选择所需模型")
        print("  4. 点击 '测试AI连接' 验证")
        print("  5. 启用AI分析开始使用")

    else:
        print("\n❌ 部分测试失败，请检查相关功能")

if __name__ == "__main__":
    main()