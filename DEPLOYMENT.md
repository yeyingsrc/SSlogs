# SSlogs 部署和运维指南

## 目录
- [系统要求](#系统要求)
- [快速开始](#快速开始)
- [详细安装](#详细安装)
- [配置说明](#配置说明)
- [运行应用](#运行应用)
- [Docker 部署](#docker-部署)
- [性能优化](#性能优化)
- [监控和日志](#监控和日志)
- [故障排除](#故障排除)
- [安全最佳实践](#安全最佳实践)

---

## 系统要求

### 最低配置
- **操作系统**: Linux, macOS, Windows
- **Python**: 3.8+
- **内存**: 4GB RAM
- **磁盘**: 2GB 可用空间
- **CPU**: 2 核

### 推荐配置
- **内存**: 8GB+ RAM
- **磁盘**: 10GB+ SSD
- **CPU**: 4+ 核
- **GPU** (可选): 用于 AI 分析加速

### 可选服务
- **Ollama**: 本地 AI 模型部署
- **Redis**: 分布式缓存
- **PostgreSQL**: 持久化存储

---

## 快速开始

### 方式 1: 使用配置向导（推荐）

```bash
# 克隆仓库
git clone https://github.com/yourusername/SSlogs.git
cd SSlogs

# 运行配置向导
python scripts/config_wizard.py

# 安装依赖
pip install -r requirements.txt

# 启动应用
python start_optimized_gui.py
```

### 方式 2: 使用 Poetry

```bash
# 安装 Poetry
curl -sSL https://install.python-poetry.org | python3 -

# 安装依赖
poetry install

# 激活虚拟环境
poetry shell

# 启动应用
poetry run sslogs-gui
```

### 方式 3: 使用 Docker

```bash
# 构建镜像
docker build -t sslogs:latest .

# 运行容器
docker run -d --name sslogs \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/output:/app/output \
  sslogs:latest
```

---

## 详细安装

### 1. 环境准备

#### Linux (Ubuntu/Debian)
```bash
# 更新系统
sudo apt-get update

# 安装系统依赖
sudo apt-get install -y \
    python3.10 \
    python3-pip \
    python3-venv \
    git \
    curl \
    wget

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate
```

#### macOS
```bash
# 安装 Homebrew（如果未安装）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装 Python
brew install python@3.10 git

# 创建虚拟环境
python3.10 -m venv venv
source venv/bin/activate
```

#### Windows
```powershell
# 安装 Python 3.10+
# 下载: https://www.python.org/downloads/

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
.\venv\Scripts\activate
```

### 2. 安装依赖

#### 使用 pip
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 使用 Poetry
```bash
# 安装 Poetry（如果未安装）
curl -sSL https://install.python-poetry.org | python3 -

# 安装项目依赖
poetry install
```

### 3. GeoIP 数据库（可选）

```bash
# 下载 GeoLite2 数据库
mkdir -p data/geoip
cd data/geoip

# 下载 MaxMind GeoLite2 数据库（需要注册账号）
wget https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-Country&suffix=tar.gz
tar -xzf GeoLite2-Country.tar.gz
```

---

## 配置说明

### 配置文件结构

```yaml
# config.yaml
basic:
  app_name: SSlogs
  version: 3.1.0
  debug: false
  timezone: Asia/Shanghai

log_parser:
  timestamp_format: "%Y-%m-%d %H:%M:%S"
  field_separator: ","
  encoding: utf-8
  batch_size: 100

ai_analyzer:
  enabled: true
  provider: ollama  # deepseek, ollama, lm_studio
  api_url: http://localhost:11434
  model: llama2
  timeout: 30

performance:
  max_workers: 4
  batch_size: 100
  memory_limit_mb: 0
  enable_caching: true

output:
  output_dir: output
  log_dir: logs
  report_format: html
```

### 环境变量

创建 `.env` 文件：

```bash
# AI 服务密钥
DEEPSEEK_API_KEY=your_api_key_here

# Ollama 配置
OLLAMA_API_URL=http://localhost:11434

# LM Studio 配置
LM_STUDIO_API_URL=http://localhost:1234/v1

# 缓存配置
REDIS_URL=redis://localhost:6379

# 数据库配置（可选）
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=sslogs
POSTGRES_USER=sslogs
POSTGRES_PASSWORD=your_password
```

---

## 运行应用

### GUI 模式

```bash
python start_optimized_gui.py
```

### CLI 模式

```bash
python -m core.intelligent_log_analyzer --input logs/access.log --output output/report.html
```

### 批处理模式

```bash
python -m core.intelligent_log_analyzer \
  --input-dir /var/log/nginx \
  --output-dir output \
  --batch-size 1000 \
  --enable-ai \
  --ai-provider ollama
```

---

## Docker 部署

### 使用 Docker Compose（推荐）

```bash
# 完整部署（包含 AI 服务）
docker-compose --profile ai --profile cache up -d

# 仅启动主应用
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 使用部署脚本

```bash
# 构建镜像
./scripts/docker_deploy.sh build

# 运行容器
./scripts/docker_deploy.sh run

# 完整部署（包含 AI 服务）
./scripts/docker_deploy.sh full

# 查看日志
./scripts/docker_deploy.sh logs

# 进入容器 shell
./scripts/docker_deploy.sh shell

# 清理
./scripts/docker_deploy.sh clean
```

### Docker 高级配置

#### 自定义配置

```bash
docker run -d \
  --name sslogs \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/data:/app/data \
  -e DEEPSEEK_API_KEY=your_key \
  -e TZ=Asia/Shanghai \
  --restart unless-stopped \
  sslogs:latest
```

#### GUI 版本（需要 X11）

```bash
# macOS/Linux
docker run -d \
  --name sslogs-gui \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -e DISPLAY=$DISPLAY \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  sslogs:latest

# Windows (需要 VcXsrv)
docker run -d \
  --name sslogs-gui \
  -e DISPLAY=host.docker.internal:0 \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  sslogs:latest
```

---

## 性能优化

### 1. 系统级优化

#### 调整文件描述符限制
```bash
# Linux
ulimit -n 65536

# 永久设置
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf
```

#### 优化内存使用
```bash
# 调整 swap
sudo sysctl vm.swappiness=10

# 永久设置
echo "vm.swappiness=10" | sudo tee -a /etc/sysctl.conf
```

### 2. 应用级优化

#### 配置调优
```yaml
# config.yaml
performance:
  max_workers: 8  # 根据 CPU 核心数调整
  batch_size: 500  # 增加批处理大小
  enable_caching: true
  cache_ttl: 3600

log_parser:
  batch_size: 1000  # 增加解析批大小

ai_analyzer:
  timeout: 60  # 增加超时时间
  max_concurrent_requests: 10  # 并发请求数
```

#### 启用 Redis 缓存
```yaml
# config.yaml
cache:
  backend: redis
  redis_url: redis://localhost:6379
  default_ttl: 3600
  max_memory: 1gb
```

### 3. AI 性能优化

#### 使用本地 AI
```yaml
ai_analyzer:
  enabled: true
  provider: ollama  # 本地部署，无网络延迟
  model: llama2:13b  # 使用更大模型
```

#### 批量分析
```yaml
ai_analyzer:
  batch_analysis: true
  batch_size: 50  # 批量处理日志条目
  max_retries: 3
```

---

## 监控和日志

### 1. 应用监控

SSlogs 内置性能监控模块，可通过以下方式启用：

```python
from core.performance_monitor import get_performance_monitor

# 获取监控实例
monitor = get_performance_monitor()

# 启动监控
monitor.start(monitor_interval=5)

# 获取监控数据
dashboard_data = monitor.get_dashboard_data()
print(dashboard_data)
```

### 2. 日志管理

#### 日志位置
- 应用日志: `logs/sslogs.log`
- 错误日志: `logs/error.log`
- AI 分析日志: `logs/ai_analysis.log`

#### 日志轮转
```yaml
# config.yaml
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  rotation:
    max_size: 100MB
    backup_count: 10
```

### 3. 性能指标

#### 查看系统资源
```bash
# 实时监控
python -c "
from core.performance_monitor import get_performance_monitor
monitor = get_performance_monitor()
monitor.start()
import time
time.sleep(10)
print(monitor.get_dashboard_data())
"
```

#### 导出指标
```python
# 导出 JSON 格式
monitor.export_metrics(format='json')

# 导出 Prometheus 格式
monitor.export_metrics(format='prometheus')
```

---

## 故障排除

### 常见问题

#### 1. 依赖安装失败

```bash
# 问题: pip 安装超时
# 解决: 使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 问题: PyQt6 安装失败
# 解决: 安装系统依赖
sudo apt-get install -y libx11-6 libxext6 libxrender1 libxtst6
```

#### 2. AI 服务连接失败

```bash
# 问题: 无法连接到 Ollama
# 解决: 检查 Ollama 服务状态
curl http://localhost:11434/api/tags

# 启动 Ollama
ollama serve

# 拉取模型
ollama pull llama2
```

#### 3. 内存不足

```bash
# 问题: 处理大文件时内存溢出
# 解决: 使用内存优化处理器
python -c "
from core.memory_optimized_processor import MemoryOptimizedProcessor
processor = MemoryOptimizedProcessor()
processor.process_large_file('large_log_file.log')
"

# 或者减少批处理大小
# config.yaml
performance:
  batch_size: 50  # 减少批大小
  memory_limit_mb: 4096  # 限制内存使用
```

#### 4. GUI 显示问题

```bash
# macOS/Linux: X11 转发问题
export DISPLAY=:0
python start_optimized_gui.py

# 或使用 VNC
xvnc :99
export DISPLAY=:99
python start_optimized_gui.py
```

### 调试模式

```bash
# 启用调试日志
export LOG_LEVEL=DEBUG
python start_optimized_gui.py

# 或在配置文件中
basic:
  debug: true
```

---

## 安全最佳实践

### 1. 密钥管理

```bash
# 使用环境变量存储敏感信息
export DEEPSEEK_API_KEY="your_key_here"

# 或使用密钥管理服务
export AWS_SECRET_NAME="sslogs/api_keys"
```

### 2. 权限控制

```bash
# 限制配置文件权限
chmod 600 config.yaml
chmod 600 .env

# 使用专用用户运行
useradd -r -s /bin/false sslogs
chown -R sslogs:sslogs /opt/sslogs
```

### 3. 网络安全

```yaml
# 限制 API 访问
ai_analyzer:
  allowed_hosts:
    - localhost
    - 192.168.1.0/24

# 启用 HTTPS
api:
  ssl_cert: /path/to/cert.pem
  ssl_key: /path/to/key.pem
```

### 4. 输入验证

```yaml
# 配置安全级别
security:
  validation_level: strict  # strict, medium, lenient
  max_input_size: 10485760  # 10MB
  enable_sanitize: true
```

---

## 升级和维护

### 升级

```bash
# 备份配置
cp config.yaml config.yaml.bak
cp .env .env.bak

# 更新代码
git pull origin main

# 更新依赖
pip install -r requirements.txt --upgrade

# 或使用 Poetry
poetry update
```

### 定期维护

```bash
# 清理日志
find logs/ -name "*.log" -mtime +30 -delete

# 清理缓存
find output/ -name "*.cache" -mtime +7 -delete

# 检查磁盘空间
df -h

# 检查服务状态
systemctl status sslogs
```

---

## 支持和贡献

- 文档: [https://docs.sslogs.com](https://docs.sslogs.com)
- 问题反馈: [GitHub Issues](https://github.com/yourusername/SSlogs/issues)
- 贡献指南: [CONTRIBUTING.md](CONTRIBUTING.md)

---

**许可证**: MIT License
**版本**: 3.1.0
**最后更新**: 2024-12-23
