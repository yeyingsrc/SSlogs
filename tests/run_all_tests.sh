#!/bin/bash

# SSlogs 规则测试一键运行脚本
# 执行完整的测试流程：生成数据 -> 运行测试 -> 验证结果 -> 生成报告

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# 检查Python环境
check_python() {
    print_message $BLUE "🔍 检查Python环境..."

    if ! command -v python3 &> /dev/null; then
        print_message $RED "❌ Python3 未安装，请先安装Python3"
        exit 1
    fi

    python_version=$(python3 --version | cut -d' ' -f2)
    print_message $GREEN "✅ Python版本: $python_version"
}

# 检查项目结构
check_project_structure() {
    print_message $BLUE "🔍 检查项目结构..."

    if [ ! -f "core/rule_engine.py" ]; then
        print_message $RED "❌ 规则引擎文件不存在: core/rule_engine.py"
        exit 1
    fi

    if [ ! -d "rules" ]; then
        print_message $RED "❌ 规则目录不存在: rules"
        exit 1
    fi

    rule_count=$(find rules -name "*.yaml" | wc -l)
    print_message $GREEN "✅ 找到 $rule_count 个规则文件"
}

# 运行完整测试
run_complete_test() {
    print_message $YELLOW "🚀 开始运行完整测试流程..."

    # 进入项目根目录
    cd "$(dirname "$0")/.."

    print_message $BLUE "📊 步骤1: 生成测试数据"
    python3 tests/run_tests.py --generate-data --verbose

    print_message $BLUE "🧪 步骤2: 运行规则测试"
    python3 tests/run_tests.py --run-tests --verbose

    print_message $BLUE "📋 步骤3: 验证测试结果"
    python3 tests/result_validator.py --verbose

    print_message $BLUE "📄 步骤4: 生成测试报告"
    python3 tests/run_tests.py --generate-report --verbose

    print_message $GREEN "🎉 测试完成！"
}

# 显示结果摘要
show_summary() {
    print_message $BLUE "📋 测试结果摘要:"

    # 查找最新的测试结果文件
    latest_result=$(find tests/results -name "test_results_*.json" -type f | sort | tail -1)

    if [ -n "$latest_result" ]; then
        # 使用Python解析结果并显示摘要
        python3 -c "
import json
import sys

try:
    with open('$latest_result', 'r') as f:
        results = json.load(f)

    total_tests = sum(len(category) for category in results.values())
    passed_tests = sum(1 for category in results.values() for test in category if test.get('success', False))
    failed_tests = sum(1 for category in results.values() for test in category if not test.get('success', False) and 'error' not in test)
    error_tests = sum(1 for category in results.values() for test in category if 'error' in test)

    success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

    print(f'  总测试数: {total_tests}')
    print(f'  通过测试: {passed_tests}')
    print(f'  失败测试: {failed_tests}')
    print(f'  错误测试: {error_tests}')
    print(f'  成功率: {success_rate:.1f}%')

    if success_rate >= 80:
        print('  🟢 测试结果: 优秀')
    elif success_rate >= 60:
        print('  🟡 测试结果: 良好')
    else:
        print('  🔴 测试结果: 需要改进')

except Exception as e:
    print(f'  ❌ 无法解析测试结果: {e}')
    sys.exit(1)
"
    else
        print_message $YELLOW "⚠️  未找到测试结果文件"
    fi

    # 显示报告文件位置
    latest_report=$(find tests/reports -name "test_report_*.html" -type f | sort | tail -1)
    if [ -n "$latest_report" ]; then
        print_message $GREEN "📄 测试报告: $latest_report"
        print_message $BLUE "💡 在浏览器中打开报告查看详细结果"
    fi

    # 显示验证报告
    latest_validation=$(find tests/results -name "validation_report_*.json" -type f | sort | tail -1)
    if [ -n "$latest_validation" ]; then
        python3 -c "
import json

try:
    with open('$latest_validation', 'r') as f:
        validation = json.load(f)

    print(f'🔍 验证评分: {validation.get(\"overall_score\", 0):.1f}/100')
    print(f'📊 验证状态: {\"通过\" if validation.get(\"validation_passed\", False) else \"未通过\"}')

except Exception:
    pass
"
    fi
}

# 清理旧数据
cleanup_old_data() {
    print_message $BLUE "🧹 清理旧的测试数据..."

    # 保留最近的3个测试结果
    find tests/results -name "test_results_*.json" -type f | sort -r | tail -n +4 | xargs rm -f 2>/dev/null || true
    find tests/reports -name "test_report_*.html" -type f | sort -r | tail -n +4 | xargs rm -f 2>/dev/null || true
    find tests/results -name "validation_report_*.json" -type f | sort -r | tail -n +4 | xargs rm -f 2>/dev/null || true

    print_message $GREEN "✅ 清理完成"
}

# 显示帮助信息
show_help() {
    echo "SSlogs 规则测试工具"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示此帮助信息"
    echo "  -c, --check    仅检查环境和项目结构"
    echo "  -t, --test     运行测试"
    echo "  -s, --summary  显示测试结果摘要"
    echo "  --clean        清理旧的测试数据"
    echo ""
    echo "示例:"
    echo "  $0              # 运行完整测试流程"
    echo "  $0 --check      # 仅检查环境"
    echo "  $0 --summary    # 显示最新测试结果摘要"
}

# 主函数
main() {
    echo "🛡️  SSlogs 规则测试工具"
    echo "=================================="

    case "${1:-}" in
        -h|--help)
            show_help
            exit 0
            ;;
        -c|--check)
            check_python
            check_project_structure
            exit 0
            ;;
        --clean)
            cleanup_old_data
            exit 0
            ;;
        -s|--summary)
            show_summary
            exit 0
            ;;
        -t|--test|"")
            check_python
            check_project_structure
            cleanup_old_data
            run_complete_test
            show_summary
            exit 0
            ;;
        *)
            print_message $RED "❌ 未知选项: $1"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"