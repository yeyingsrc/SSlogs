#!/usr/bin/env python3
"""
SSlogs 测试运行脚本
执行完整的规则测试流程
"""

import os
import sys
import time
import argparse
from pathlib import Path
import json

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent))

from tests.test_framework import TestFramework

def main():
    parser = argparse.ArgumentParser(description='SSlogs 规则测试工具')
    parser.add_argument('--rule-dir', default='rules', help='规则目录路径')
    parser.add_argument('--generate-data', action='store_true', help='生成测试数据')
    parser.add_argument('--run-tests', action='store_true', help='运行测试')
    parser.add_argument('--generate-report', action='store_true', help='生成测试报告')
    parser.add_argument('--category', help='指定测试类别 (ai_ml, threat_intel, zero_trust, etc.)')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')

    args = parser.parse_args()

    # 创建测试框架
    framework = TestFramework(args.rule_dir)

    try:
        # 步骤1：生成测试数据
        if args.generate_data or not any([args.run_tests, args.generate_report]):
            print("🚀 开始生成测试数据...")
            test_logs = framework.generate_test_logs()
            print(f"✅ 测试数据生成完成，共 {len(test_logs)} 个类别")

        # 步骤2：运行测试
        if args.run_tests or not any([args.generate_data, args.generate_report]):
            print("🔍 开始加载规则引擎...")
            rule_engine = framework.load_rule_engine()

            print("🧪 开始运行规则测试...")
            if args.generate_data:
                results = framework.run_tests(rule_engine, test_logs)
            else:
                # 加载现有的测试数据
                test_logs = {}
                test_data_dir = Path(__file__).parent / "test_data"
                for test_file in test_data_dir.glob("*_test_logs.json"):
                    category = test_file.stem.replace("_test_logs", "")
                    with open(test_file, 'r', encoding='utf-8') as f:
                        test_logs[category] = json.load(f)

                results = framework.run_tests(rule_engine, test_logs)

            print(f"✅ 测试完成，总计 {framework.test_stats['total_tests']} 个测试")
            print(f"   通过: {framework.test_stats['passed_tests']}")
            print(f"   失败: {framework.test_stats['failed_tests']}")
            print(f"   错误: {framework.test_stats['error_tests']}")

        # 步骤3：生成报告
        if args.generate_report or not any([args.generate_data, args.run_tests]):
            print("📊 开始生成测试报告...")
            if args.run_tests:
                report_file = framework.generate_report(results)
            else:
                # 加载现有的测试结果（寻找test_results文件，不是validation_report）
                results_dir = Path(__file__).parent / "results"
                test_result_files = list(results_dir.glob("test_results_*.json"))
                if not test_result_files:
                    print("❌ 未找到测试结果文件，请先运行测试")
                    return 1

                latest_result = max(test_result_files, key=lambda x: x.stat().st_mtime)
                print(f"📂 加载测试结果文件: {latest_result.name}")
                with open(latest_result, 'r', encoding='utf-8') as f:
                    results = json.load(f)

                # 重新构建统计信息
                framework.test_stats = {
                    'total_tests': sum(len(category_results) for category_results in results.values()),
                    'passed_tests': sum(1 for category_results in results.values()
                                      for result in category_results if result.get('success', False)),
                    'failed_tests': sum(1 for category_results in results.values()
                                      for result in category_results if not result.get('success', False) and 'error' not in result),
                    'error_tests': sum(1 for category_results in results.values()
                                     for result in category_results if 'error' in result),
                    'test_results': results
                }

                report_file = framework.generate_report(results)

            print(f"✅ 测试报告已生成: {report_file}")

        # 显示详细结果
        if args.verbose and args.run_tests:
            print("\n📋 详细测试结果:")
            for category, category_results in results.items():
                print(f"\n🔸 {category}:")
                for result in category_results:
                    if result.get('success', False):
                        print(f"  ✅ {result['test_id']}: 匹配到 {result['matches']} 个规则")
                        for rule_name in result['matched_rules']:
                            print(f"     - {rule_name}")
                    else:
                        print(f"  ❌ {result['test_id']}: 未匹配到规则")
                        if 'error' in result:
                            print(f"     错误: {result['error']}")

    except Exception as e:
        print(f"❌ 测试执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())