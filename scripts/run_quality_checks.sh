#!/bin/bash

# SSlogs 代码质量和安全检查脚本
# 运行所有代码质量工具和安全扫描

set -e

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
    echo -e "${color}[INFO]${NC} ${message}"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 创建报告目录
mkdir -p reports

print_message "$BLUE" "=========================================="
print_message "$BLUE" "SSlogs 代码质量和安全检查"
print_message "$BLUE" "=========================================="
echo ""

# 1. 代码格式化检查 (Black)
print_message "$BLUE" "1/7. 运行 Black 代码格式化检查..."
if command -v black &> /dev/null; then
    if black --check --diff core/ 2>&1 | tee reports/black_check.txt; then
        print_success "代码格式检查通过"
    else
        print_warning "代码格式检查发现问题，运行 'black core/' 修复"
    fi
else
    print_warning "Black 未安装，跳过格式检查"
fi
echo ""

# 2. Flake8 代码检查
print_message "$BLUE" "2/7. 运行 Flake8 代码检查..."
if command -v flake8 &> /dev/null; then
    if flake8 core/ --max-line-length=100 --exclude=venv,virtualenv --statistics 2>&1 | tee reports/flake8_report.txt; then
        print_success "Flake8 检查通过"
    else
        print_warning "Flake8 发现代码风格问题"
    fi
else
    print_warning "Flake8 未安装，跳过检查"
fi
echo ""

# 3. Pylint 代码质量分析
print_message "$BLUE" "3/7. 运行 Pylint 代码质量分析..."
if command -v pylint &> /dev/null; then
    if pylint core/ --rcfile=setup.cfg --output-format=text --reports=n 2>&1 | tee reports/pylint_report.txt; then
        print_success "Pylint 检查通过"
    else
        print_warning "Pylint 发现代码质量问题"
    fi
else
    print_warning "Pylint 未安装，跳过检查"
fi
echo ""

# 4. MyPy 类型检查
print_message "$BLUE" "4/7. 运行 MyPy 类型检查..."
if command -v mypy &> /dev/null; then
    if mypy core/ --config-file=setup.cfg 2>&1 | tee reports/mypy_report.txt; then
        print_success "MyPy 类型检查通过"
    else
        print_warning "MyPy 发现类型问题"
    fi
else
    print_warning "MyPy 未安装，跳过类型检查"
fi
echo ""

# 5. Bandit 安全扫描
print_message "$BLUE" "5/7. 运行 Bandit 安全漏洞扫描..."
if command -v bandit &> /dev/null; then
    if bandit -r core/ -c .bandit -f screen -o reports/bandit_report.txt; then
        print_success "Bandit 安全扫描通过"
    else
        print_warning "Bandit 发现安全问题"
    fi
else
    print_warning "Bandit 未安装，跳过安全扫描"
fi
echo ""

# 6. Safety 依赖安全检查
print_message "$BLUE" "6/7. 运行 Safety 依赖安全检查..."
if command -v safety &> /dev/null; then
    if safety check --file requirements.txt 2>&1 | tee reports/safety_report.txt; then
        print_success "Safety 依赖安全检查通过"
    else
        print_warning "Safety 发现依赖安全问题"
    fi
else
    print_warning "Safety 未安装，跳过依赖检查"
fi
echo ""

# 7. 运行单元测试
print_message "$BLUE" "7/7. 运行单元测试..."
if command -v pytest &> /dev/null; then
    if pytest tests/ -v --tb=short --cov=core --cov-report=html:htmlcov --cov-report=term-missing 2>&1 | tee reports/pytest_report.txt; then
        print_success "单元测试通过"
    else
        print_error "单元测试失败"
    fi
else
    print_warning "pytest 未安装，跳过单元测试"
fi
echo ""

# 生成汇总报告
print_message "$BLUE" "=========================================="
print_message "$BLUE" "检查完成！"
print_message "$BLUE" "=========================================="
print_message "$BLUE" "报告位置: reports/ 目录"
print_message "$BLUE" "覆盖率报告: htmlcov/index.html"
echo ""

# 显示汇总
print_message "$YELLOW" "检查结果汇总:"
echo "- Black 格式检查: reports/black_check.txt"
echo "- Flake8 检查: reports/flake8_report.txt"
echo "- Pylint 检查: reports/pylint_report.txt"
echo "- MyPy 类型检查: reports/mypy_report.txt"
echo "- Bandit 安全扫描: reports/bandit_report.txt"
echo "- Safety 依赖检查: reports/safety_report.txt"
echo "- Pytest 测试: reports/pytest_report.txt"
echo ""
