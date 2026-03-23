# SSlogs 安全日志分析平台 - Docker 镜像
# 多阶段构建，优化镜像大小和安全性

# ===========================
# 阶段1: 基础环境
# ===========================
FROM python:3.10-slim AS base

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    # 基础工具
    curl \
    wget \
    ca-certificates \
    # GeoIP 数据库依赖
    libmaxminddb0 \
    # 文本处理
    grep \
    sed \
    # 清理缓存
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# ===========================
# 阶段2: 依赖安装
# ===========================
FROM base AS dependencies

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# ===========================
# 阶段3: 开发环境
# ===========================
FROM dependencies AS development

# 安装开发工具
RUN pip install --no-cache-dir \
    pytest>=7.4.0 \
    pytest-cov>=4.1.0 \
    black>=23.7.0 \
    flake8>=6.1.0 \
    pylint>=2.17.0 \
    mypy>=1.5.0 \
    bandit>=1.7.5 \
    safety>=2.3.0

# 复制应用代码
COPY . .

# 暴露端口（如果有 Web 服务）
EXPOSE 8000

# 默认命令
CMD ["python", "-m", "pytest", "tests/"]

# ===========================
# 阶段4: 生产环境
# ===========================
FROM dependencies AS production

# 创建非 root 用户
RUN groupadd -r sslogs && useradd -r -g sslogs sslogs

# 复制应用代码
COPY --chown=sslogs:sslogs . .

# 创建必要的目录
RUN mkdir -p /app/logs /app/output /app/data && \
    chown -R sslogs:sslogs /app/logs /app/output /app/data

# 切换到非 root 用户
USER sslogs

# 工作目录
WORKDIR /app

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# 默认命令 - 启动 GUI 应用
CMD ["python", "start_optimized_gui.py"]

# ===========================
# 阶段5: GUI 版本
# ===========================
FROM production AS gui

# 安装 GUI 相关依赖（需要 X11 转发或 VNC）
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    # X11 库
    libx11-6 \
    libxext6 \
    libxrender1 \
    libxtst6 \
    # Qt 依赖
    libgl1-mesa-glx \
    libglib2.0-0 \
    # 清理
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER sslogs

# 默认启动 GUI
CMD ["python", "start_optimized_gui.py"]

# ===========================
# 阶段6: CLI 版本
# ===========================
FROM production AS cli

# 默认启动 CLI
CMD ["python", "-m", "core.intelligent_log_analyzer"]
