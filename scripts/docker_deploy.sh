#!/bin/bash

# SSlogs Docker 部署脚本
# 简化 Docker 构建和部署流程

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_message() {
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

# 显示使用说明
show_usage() {
    cat << EOF
SSlogs Docker 部署脚本

用法: ./docker_deploy.sh [选项]

选项:
    build           构建 Docker 镜像
    run             运行容器
    run-gui         运行 GUI 版本
    run-dev         运行开发环境
    stop            停止容器
    restart         重启容器
    logs            查看日志
    shell           进入容器 shell
    clean           清理容器和镜像
    full            完整部署（包含 AI 服务）
    help            显示此帮助信息

示例:
    ./docker_deploy.sh build          # 构建镜像
    ./docker_deploy.sh run            # 运行应用
    ./docker_deploy.sh full           # 完整部署
    ./docker_deploy.sh logs           # 查看日志
EOF
}

# 构建镜像
build_image() {
    print_message "构建 Docker 镜像..."

    # 构建生产镜像
    docker build \
        --target production \
        --tag sslogs:latest \
        --tag sslogs:$(date +%Y%m%d) \
        .

    print_success "镜像构建完成"
}

# 运行容器
run_container() {
    print_message "启动 SSlogs 容器..."

    # 检查配置文件
    if [ ! -f "config.yaml" ]; then
        print_warning "未找到 config.yaml，使用默认配置"
    fi

    # 创建必要的目录
    mkdir -p logs output data

    docker run -d \
        --name sslogs \
        --restart unless-stopped \
        -v $(pwd)/config.yaml:/app/config.yaml:ro \
        -v $(pwd)/logs:/app/logs \
        -v $(pwd)/output:/app/output \
        -v $(pwd)/data:/app/data \
        -e PYTHONUNBUFFERED=1 \
        sslogs:latest

    print_success "容器已启动"
    print_message "使用 'docker logs -f sslogs' 查看日志"
}

# 运行 GUI 版本
run_gui() {
    print_message "启动 SSlogs GUI 容器..."

    # 检查 X11
    if [ -z "$DISPLAY" ]; then
        print_error "未找到 DISPLAY 环境变量"
        print_message "请确保 X11 服务正在运行"
        exit 1
    fi

    # 创建必要的目录
    mkdir -p logs output data

    docker run -d \
        --name sslogs-gui \
        --restart unless-stopped \
        -v $(pwd)/config.yaml:/app/config.yaml:ro \
        -v $(pwd)/logs:/app/logs \
        -v $(pwd)/output:/app/output \
        -v $(pwd)/data:/app/data \
        -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
        -e DISPLAY=$DISPLAY \
        -e PYTHONUNBUFFERED=1 \
        sslogs:latest

    print_success "GUI 容器已启动"
}

# 运行开发环境
run_dev() {
    print_message "启动开发环境..."

    docker run -it \
        --name sslogs-dev \
        -v $(pwd):/app \
        -v $(pwd)/logs:/app/logs \
        -v $(pwd)/output:/app/output \
        -e PYTHONUNBUFFERED=1 \
        sslogs:latest \
        /bin/bash
}

# 停止容器
stop_container() {
    print_message "停止容器..."
    docker stop sslogs sslogs-gui 2>/dev/null || true
    print_success "容器已停止"
}

# 重启容器
restart_container() {
    print_message "重启容器..."
    docker restart sslogs 2>/dev/null || print_warning "sslogs 容器未运行"
    print_success "容器已重启"
}

# 查看日志
show_logs() {
    if [ "$1" == "-f" ]; then
        docker logs -f sslogs
    else
        docker logs --tail 100 sslogs
    fi
}

# 进入容器 shell
enter_shell() {
    print_message "进入容器 shell..."
    docker exec -it sslogs /bin/bash
}

# 清理
clean() {
    print_message "清理容器和镜像..."

    read -p "确定要清理所有容器和镜像吗? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker stop sslogs sslogs-gui sslogs-dev 2>/dev/null || true
        docker rm sslogs sslogs-gui sslogs-dev 2>/dev/null || true
        docker rmi sslogs:latest 2>/dev/null || true
        print_success "清理完成"
    else
        print_message "取消清理"
    fi
}

# 完整部署
full_deploy() {
    print_message "完整部署 SSlogs 环境..."

    # 构建镜像
    build_image

    # 使用 docker-compose 启动所有服务
    if command -v docker-compose &> /dev/null; then
        docker-compose --profile ai --profile cache up -d
    elif docker compose version &> /dev/null; then
        docker compose --profile ai --profile cache up -d
    else
        print_error "未找到 docker-compose"
        exit 1
    fi

    print_success "完整部署完成"
    print_message "服务列表:"
    docker ps --filter "name=sslogs"
}

# 主函数
main() {
    case "$1" in
        build)
            build_image
            ;;
        run)
            run_container
            ;;
        run-gui)
            run_gui
            ;;
        run-dev)
            run_dev
            ;;
        stop)
            stop_container
            ;;
        restart)
            restart_container
            ;;
        logs)
            show_logs "$2"
            ;;
        shell)
            enter_shell
            ;;
        clean)
            clean
            ;;
        full)
            full_deploy
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            print_error "未知选项: $1"
            show_usage
            exit 1
            ;;
    esac
}

# 执行主函数
if [ $# -eq 0 ]; then
    show_usage
else
    main "$@"
fi
