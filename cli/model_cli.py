#!/usr/bin/env python3
"""
SSlogs AI模型管理命令行工具
"""

import sys
import os
import argparse
import json
from pathlib import Path
from typing import List, Dict, Any

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.model_manager import get_model_manager, ModelInfo
from core.ai_config_manager import get_ai_config_manager

def print_header(title: str):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_subheader(title: str):
    """打印子标题"""
    print(f"\n--- {title} ---")

def format_model_info(model: ModelInfo, detailed: bool = False) -> str:
    """格式化模型信息"""
    status = []
    if model.recommended:
        status.append("⭐推荐")

    lines = [
        f"📱 {model.name}",
        f"   ID: {model.id}",
    ]

    if model.parameters:
        status.append(f"🔢{model.parameters}")
    if model.quantization:
        status.append(f"🎯{model.quantization}")

    if status:
        lines.append(f"   标签: {' '.join(status)}")

    lines.append(f"   兼容性: {model.compatibility_score:.1f}/5.0")

    if detailed and model.description:
        lines.append(f"   描述: {model.description}")

    return '\n'.join(lines)

def cmd_status(args):
    """显示服务器状态"""
    print_header("LM Studio服务器状态")

    manager = get_model_manager()
    status = manager.get_server_status(force_refresh=args.refresh)

    if status.connected:
        print("✅ 连接状态: 已连接")
        print(f"🌐 服务器地址: {status.host}:{status.port}")
        print(f"📊 可用模型数: {status.available_models_count}")
        print(f"⏱️ 响应时间: {status.response_time:.2f}秒")

        if status.current_model:
            print(f"🎯 当前模型: {status.current_model}")
        else:
            print("⚠️ 当前模型: 未加载")
    else:
        print("❌ 连接状态: 未连接")
        if status.error_message:
            print(f"错误信息: {status.error_message}")

        print("\n建议:")
        print("1. 确保LM Studio正在运行")
        print("2. 启动本地服务器 (通常在端口1234)")
        print("3. 加载至少一个语言模型")

def cmd_list(args):
    """列出可用模型"""
    print_header("可用模型列表")

    manager = get_model_manager()
    models = manager.refresh_models(force_refresh=args.refresh)

    if not models:
        print("😔 未发现可用模型")
        print("请确保在LM Studio中加载了模型")
        return

    current_model = manager.get_current_model()
    current_id = current_model.id if current_model else None

    print(f"共发现 {len(models)} 个模型:\n")

    for i, model in enumerate(models, 1):
        print(f"{i}. {format_model_info(model, detailed=args.detailed)}")
        if model.id == current_id:
            print("   ✅ 当前选中")
        print()

    if args.recommendations:
        print_subheader("推荐模型")
        recommended = [m for m in models if m.recommended][:3]
        if recommended:
            for model in recommended:
                print(f"⭐ {format_model_info(model)}")
                print()
        else:
            print("暂无推荐模型")

def cmd_select(args):
    """选择模型"""
    print_header(f"选择模型: {args.model_id}")

    manager = get_model_manager()

    # 验证模型是否存在
    models = manager.refresh_models()
    model_ids = [m.id for m in models]

    if args.model_id not in model_ids:
        print(f"❌ 模型 '{args.model_id}' 不存在")
        print("\n可用模型:")
        for model in models:
            print(f"  - {model.id}")
        return

    # 选择模型
    success = manager.select_model(args.model_id)

    if success:
        print(f"✅ 已选择模型: {args.model_id}")

        # 获取模型信息
        model = next((m for m in models if m.id == args.model_id), None)
        if model:
            print(f"\n模型信息:")
            print(format_model_info(model, detailed=True))
    else:
        print("❌ 选择模型失败")

def cmd_test(args):
    """测试模型"""
    print_header(f"测试模型: {args.model_id}")

    manager = get_model_manager()

    print("正在测试模型响应...")
    result = manager.test_model(args.model_id, args.prompt)

    if result['success']:
        print("✅ 测试成功")
        print(f"⏱️ 响应时间: {result['response_time']:.2f}秒")
        print(f"\n📝 模型回复:")
        print("-" * 40)
        print(result['response'])
        print("-" * 40)
    else:
        print("❌ 测试失败")
        if result.get('error'):
            print(f"错误: {result['error']}")

def cmd_recommend(args):
    """获取模型推荐"""
    print_header(f"模型推荐 - {args.use_case}")

    manager = get_model_manager()
    recommendations = manager.get_model_recommendations(args.use_case)

    if not recommendations:
        print("😔 暂无推荐模型")
        return

    print(f"为您推荐以下 {len(recommendations)} 个模型:\n")

    for i, model in enumerate(recommendations, 1):
        print(f"{i}. {format_model_info(model, detailed=True)}")
        print()

    # 显示推荐理由
    use_case_descriptions = {
        "general": "适合日常使用，平衡性能和质量",
        "security_analysis": "专为安全日志分析优化，逻辑推理能力强",
        "speed": "响应速度快，适合实时分析"
    }

    if args.use_case in use_case_descriptions:
        print(f"📋 推荐理由: {use_case_descriptions[args.use_case]}")

def cmd_current(args):
    """显示当前模型"""
    print_header("当前选中模型")

    manager = get_model_manager()
    current = manager.get_current_model()

    if current:
        print(format_model_info(current, detailed=True))

        # 显示使用状态
        status = manager.get_server_status()
        if status.current_model == current.id:
            print("✅ 模型已加载并在LM Studio中运行")
        else:
            print("⚠️ 模型已选择但未在LM Studio中加载")
    else:
        print("😔 未选择任何模型")
        print("\n使用以下命令选择模型:")
        print("python cli/model_cli.py select <model_id>")
        print("python cli/model_cli.py list  # 查看可用模型")

def cmd_export(args):
    """导出模型列表"""
    print_header("导出模型列表")

    manager = get_model_manager()

    if args.format == "json":
        data = manager.export_model_list("json")
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(data)
            print(f"✅ 已导出到: {args.output}")
        else:
            print(data)

    elif args.format == "csv":
        data = manager.export_model_list("csv")
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(data)
            print(f"✅ 已导出到: {args.output}")
        else:
            print(data)

    else:
        print(f"❌ 不支持的格式: {args.format}")

def cmd_config(args):
    """显示配置"""
    print_header("AI配置信息")

    config_manager = get_ai_config_manager()
    config = config_manager.get_full_config()

    if args.section:
        if args.section in config:
            print(f"📋 {args.section} 配置:")
            print(json.dumps(config[args.section], indent=2, ensure_ascii=False))
        else:
            print(f"❌ 配置节 '{args.section}' 不存在")
            print(f"可用配置节: {', '.join(config.keys())}")
    else:
        print("📋 完整配置:")
        print(json.dumps(config, indent=2, ensure_ascii=False))

def cmd_search(args):
    """搜索模型"""
    print_header(f"搜索模型: {args.query}")

    manager = get_model_manager()
    models = manager.refresh_models()

    query_lower = args.query.lower()
    results = []

    for model in models:
        # 在名称、ID、描述中搜索
        if (query_lower in model.name.lower() or
            query_lower in model.id.lower() or
            (model.description and query_lower in model.description.lower())):
            results.append(model)

    if not results:
        print(f"😔 未找到匹配 '{args.query}' 的模型")
        return

    print(f"找到 {len(results)} 个匹配的模型:\n")

    for i, model in enumerate(results, 1):
        print(f"{i}. {format_model_info(model, detailed=args.detailed)}")
        print()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='SSlogs AI模型管理命令行工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  %(prog)s status                    # 显示服务器状态
  %(prog)s list                      # 列出所有模型
  %(prog)s list --recommendations    # 显示推荐模型
  %(prog)s select llama-3-8b-instruct  # 选择模型
  %(prog)s test llama-3-8b-instruct     # 测试模型
  %(prog)s recommend --use-case security_analysis  # 获取安全分析推荐
  %(prog)s current                   # 显示当前模型
  %(prog)s search llama              # 搜索包含'llama'的模型
  %(prog)s export --format json      # 导出模型列表
        """
    )

    parser.add_argument('--refresh', action='store_true', help='强制刷新数据')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细信息')

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # status命令
    status_parser = subparsers.add_parser('status', help='显示服务器状态')
    status_parser.add_argument('--refresh', action='store_true', help='刷新状态')

    # list命令
    list_parser = subparsers.add_parser('list', help='列出可用模型')
    list_parser.add_argument('--refresh', action='store_true', help='刷新模型列表')
    list_parser.add_argument('--detailed', '-d', action='store_true', help='显示详细信息')
    list_parser.add_argument('--recommendations', '-r', action='store_true', help='显示推荐标记')

    # select命令
    select_parser = subparsers.add_parser('select', help='选择模型')
    select_parser.add_argument('model_id', help='模型ID')

    # test命令
    test_parser = subparsers.add_parser('test', help='测试模型')
    test_parser.add_argument('model_id', help='模型ID')
    test_parser.add_argument('--prompt', '-p', default='你好，请简单介绍一下自己。', help='测试提示词')

    # recommend命令
    recommend_parser = subparsers.add_parser('recommend', help='获取模型推荐')
    recommend_parser.add_argument('--use-case', choices=['general', 'security_analysis', 'speed'],
                                 default='general', help='使用场景')

    # current命令
    current_parser = subparsers.add_parser('current', help='显示当前模型')

    # export命令
    export_parser = subparsers.add_parser('export', help='导出模型列表')
    export_parser.add_argument('--format', choices=['json', 'csv'], default='json', help='导出格式')
    export_parser.add_argument('--output', '-o', help='输出文件路径')

    # config命令
    config_parser = subparsers.add_parser('config', help='显示配置信息')
    config_parser.add_argument('--section', '-s', help='显示特定配置节')

    # search命令
    search_parser = subparsers.add_parser('search', help='搜索模型')
    search_parser.add_argument('query', help='搜索关键词')
    search_parser.add_argument('--detailed', '-d', action='store_true', help='显示详细信息')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        if args.command == 'status':
            cmd_status(args)
        elif args.command == 'list':
            cmd_list(args)
        elif args.command == 'select':
            cmd_select(args)
        elif args.command == 'test':
            cmd_test(args)
        elif args.command == 'recommend':
            cmd_recommend(args)
        elif args.command == 'current':
            cmd_current(args)
        elif args.command == 'export':
            cmd_export(args)
        elif args.command == 'config':
            cmd_config(args)
        elif args.command == 'search':
            cmd_search(args)
        else:
            print(f"❌ 未知命令: {args.command}")
            parser.print_help()

    except KeyboardInterrupt:
        print("\n\n⏹️ 操作已取消")
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()