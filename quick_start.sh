#!/bin/bash

# SSlogs AI模型管理器快速启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
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

# 检查Python环境
check_python() {
    print_info "检查Python环境..."

    if ! command -v python3 &> /dev/null; then
        print_error "未找到Python3，请先安装Python 3.8+"
        exit 1
    fi

    python_version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
    print_success "Python版本: $python_version"
}

# 检查依赖
check_dependencies() {
    print_info "检查Python依赖..."

    required_packages=("flask" "flask-cors" "aiohttp" "pydantic")
    missing_packages=()

    for package in "${required_packages[@]}"; do
        if ! python3 -c "import $package" 2>/dev/null; then
            missing_packages+=("$package")
        fi
    done

    if [ ${#missing_packages[@]} -ne 0 ]; then
        print_warning "缺少以下依赖: ${missing_packages[*]}"
        print_info "正在安装依赖..."

        # 构建pip安装命令
        pip_args="install"
        for package in "${missing_packages[@]}"; do
            pip_args="$pip_args $package"
        done

        python3 -m pip $pip_args

        if [ $? -eq 0 ]; then
            print_success "依赖安装完成"
        else
            print_error "依赖安装失败，请手动运行: pip3 install ${missing_packages[*]}"
            exit 1
        fi
    else
        print_success "所有依赖已安装"
    fi
}

# 检查LM Studio
check_lm_studio() {
    print_info "检查LM Studio状态..."

    if curl -s http://127.0.0.1:1234/v1/models > /dev/null 2>&1; then
        print_success "LM Studio连接正常"

        # 获取模型数量
        model_count=$(curl -s http://127.0.0.1:1234/v1/models | python3 -c "import sys, json; data = json.load(sys.stdin); print(len(data.get('data', [])))" 2>/dev/null || echo "0")
        print_info "可用模型数量: $model_count"

        if [ "$model_count" -eq 0 ]; then
            print_warning "LM Studio已连接但未加载模型"
            print_info "请在LM Studio中加载一个模型"
        fi
    else
        print_warning "无法连接到LM Studio"
        print_info "请确保:"
        print_info "1. LM Studio正在运行"
        print_info "2. 本地服务器已启动 (端口1234)"
        print_info "3. 已加载至少一个模型"
    fi
}

# 创建日志目录
create_log_dir() {
    if [ ! -d "logs" ]; then
        print_info "创建日志目录..."
        mkdir -p logs
        print_success "日志目录已创建"
    fi
}

# 启动模型管理器
start_manager() {
    print_info "启动SSlogs AI模型管理器..."

    # 检查端口是否被占用
    if lsof -i :8080 >/dev/null 2>&1; then
        print_warning "端口8080已被占用"
        read -p "是否使用端口8081? (y/n): " -n 1 -r
        echo

        if [[ $REPLY =~ ^[Yy]$ ]]; then
            PORT=8081
        else
            print_error "请先释放端口8080或选择其他端口"
            exit 1
        fi
    else
        PORT=8080
    fi

    print_info "启动Web服务器 (端口: $PORT)..."

    # 启动服务器
    python3 start_model_manager.py --port $PORT

    # 如果启动失败，尝试不同的方式
    if [ $? -ne 0 ]; then
        print_warning "启动脚本失败，尝试直接启动..."
        python3 web/model_api.py
    fi
}

# 显示帮助
show_help() {
    echo "SSlogs AI模型管理器快速启动脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示此帮助信息"
    echo "  --check-only   仅检查环境，不启动服务器"
    echo "  --cli          启动命令行界面而不是Web界面"
    echo "  --port PORT    指定端口号 (默认: 8080)"
    echo ""
    echo "示例:"
    echo "  $0                    # 启动Web界面"
    echo "  $0 --check-only       # 仅检查环境"
    echo "  $0 --cli              # 启动命令行界面"
    echo "  $0 --port 9000        # 使用端口9000"
}

# 启动命令行界面
start_cli() {
    print_info "启动命令行界面..."
    print_info "使用 'python3 cli/model_cli.py --help' 查看命令帮助"

    # 显示当前状态
    python3 cli/model_cli.py status

    echo ""
    print_info "常用命令:"
    echo "  python3 cli/model_cli.py list              # 列出所有模型"
    echo "  python3 cli/model_cli.py current           # 显示当前模型"
    echo "  python3 cli/model_cli.py select <model>    # 选择模型"
    echo "  python3 cli/model_cli.py test <model>      # 测试模型"
    echo "  python3 cli/model_cli.py recommend         # 获取推荐"
}

# 主函数
main() {
    echo "🚀 SSlogs AI模型管理器快速启动"
    echo "=================================="

    # 解析命令行参数
    CHECK_ONLY=false
    CLI_MODE=false
    PORT=8080

    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            --check-only)
                CHECK_ONLY=true
                shift
                ;;
            --cli)
                CLI_MODE=true
                shift
                ;;
            --port)
                PORT="$2"
                shift 2
                ;;
            *)
                print_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # 环境检查
    check_python
    check_dependencies
    create_log_dir
    check_lm_studio

    if [ "$CHECK_ONLY" = true ]; then
        echo ""
        print_success "环境检查完成!"

        if curl -s http://127.0.0.1:1234/v1/models > /dev/null 2>&1; then
            print_success "✅ 环境就绪，可以启动模型管理器"
        else
            print_warning "⚠️ LM Studio未连接，但可以启动管理界面进行配置"
        fi
        exit 0
    fi

    echo ""
    print_success "环境检查完成!"

    # 启动相应界面
    if [ "$CLI_MODE" = true ]; then
        start_cli
    else
        start_manager
    fi
}

# 捕获中断信号
trap 'print_info "正在停止..."; exit 0' INT TERM

# 运行主函数
main "$@"