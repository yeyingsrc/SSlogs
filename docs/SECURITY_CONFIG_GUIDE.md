# 安全配置指南

## API密钥安全配置

### 方法1：环境变量（推荐）

#### Linux/macOS
在 `~/.bashrc` 或 `~/.zshrc` 中添加：

```bash
export SSLOGS_AI_API_KEY="your-actual-api-key"
export SSLOGS_AI_CLOUD_PROVIDER="deepseek"
export SSLOGS_AI_TYPE="cloud"
```

然后重新加载配置：
```bash
source ~/.bashrc  # 或 source ~/.zshrc
```

#### Windows PowerShell
```powershell
$env:SSLOGS_AI_API_KEY="your-actual-api-key"
$env:SSLOGS_AI_CLOUD_PROVIDER="deepseek"
$env:SSLOGS_AI_TYPE="cloud"
```

或者设置系统环境变量（永久）：
```powershell
[System.Environment]::SetEnvironmentVariable('SSLOGS_AI_API_KEY', 'your-actual-api-key', 'User')
```

#### 在特定会话中设置
```bash
# 一次性设置
SSLOGS_AI_API_KEY="your-key" python main.py --config config.yaml --ai

# 或在同一行中设置
export SSLOGS_AI_API_KEY="your-key" && python main.py --config config.yaml --ai
```

### 方法2：.env 文件（仅用于开发）

创建 `.env` 文件（添加到 `.gitignore`）：

```
SSLOGS_AI_API_KEY=your-actual-api-key
SSLOGS_AI_CLOUD_PROVIDER=deepseek
SSLOGS_AI_TYPE=cloud
```

然后使用 `python-dotenv` 加载：

```python
from dotenv import load_dotenv
load_dotenv()
```

### 方法3：配置文件加密（生产环境）

对于生产环境，建议使用加密配置：

```bash
# 安装加密工具
pip install cryptography

# 加密API密钥
python scripts/encrypt_config.py
```

## 支持的环境变量

| 变量名 | 描述 | 示例值 |
|--------|------|--------|
| `SSLOGS_AI_API_KEY` | AI服务API密钥 | `sk-xxx...` |
| `SSLOGS_AI_CLOUD_PROVIDER` | 云端AI提供商 | `deepseek`, `openai` |
| `SSLOGS_AI_LOCAL_PROVIDER` | 本地AI提供商 | `ollama`, `lm_studio` |
| `SSLOGS_AI_TYPE` | AI类型 | `cloud`, `local` |
| `SSLOGS_LOG_LEVEL` | 日志级别 | `INFO`, `DEBUG`, `ERROR` |

## 配置优先级

系统按以下优先级查找配置值：

1. 环境变量（最高优先级）
2. 配置文件 (`config.yaml`)
3. 默认值

## 安全最佳实践

### 1. 永不提交密钥到版本控制
```bash
# 添加到 .gitignore
echo ".env" >> .gitignore
echo "config.local.yaml" >> .gitignore
```

### 2. 使用不同的密钥环境
```bash
# 开发环境
export SSLOGS_AI_API_KEY="dev-api-key"

# 生产环境
export SSLOGS_AI_API_KEY="prod-api-key"
```

### 3. 定期轮换密钥
- 设置密钥过期提醒
- 使用密钥管理服务（如AWS Secrets Manager）
- 限制密钥权限范围

### 4. 监控密钥使用
- 检查异常API调用
- 设置使用配额和告警
- 记录密钥访问日志

## Docker 部署安全配置

### 使用 Docker Secrets
```yaml
# docker-compose.yml
version: '3.8'
services:
  sslogs:
    image: sslogs:latest
    secrets:
      - ai_api_key
    environment:
      - SSLOGS_AI_API_KEY_FILE=/run/secrets/ai_api_key

secrets:
  ai_api_key:
    file: ./secrets/ai_api_key.txt
```

### 使用环境变量文件
```bash
# 创建 .env 文件
cat > .env.production << EOF
SSLOGS_AI_API_KEY=your-production-key
SSLOGS_LOG_LEVEL=INFO
EOF

# 使用 docker-compose
docker-compose --env-file .env.production up -d
```

## 故障排查

### 密钥未生效
```bash
# 检查环境变量
echo $SSLOGS_AI_API_KEY

# 临时测试
SSLOGS_AI_API_KEY="test-key" python main.py --config config.yaml
```

### 配置验证
```bash
# 验证配置加载
python -c "from core.ai_analyzer import AIAnalyzer; ai = AIAnalyzer(); print('API Key configured:', bool(ai.api_key))"
```

## 相关文件

- `config.example.yaml` - 配置文件示例
- `DEPLOYMENT.md` - 部署指南
- `docs/AI_INTEGRATION.md` - AI集成文档
