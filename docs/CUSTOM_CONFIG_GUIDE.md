# SSlogs 自定义配置指南

## 概述

SSlogs AI系统支持灵活的自定义配置功能，允许您：
- 自定义LM Studio API地址和参数
- 映射模型名称为自定义名称
- 使用OpenAI兼容的API格式
- 通过Web界面管理配置
- 测试API连接和响应

## 🚀 快速开始

### 1. 启动Web管理界面

```bash
# 方法一：使用快速启动脚本
./quick_start.sh

# 方法二：使用Python脚本
python3 start_model_manager.py
```

访问 http://127.0.0.1:8080 打开管理界面

### 2. 配置自定义设置

1. 点击界面中的 **"⚙️ 配置"** 按钮
2. 在弹出的配置对话框中设置：
   - API基础URL
   - API密钥（可选）
   - 模型参数
   - 模型名称映射

### 3. 测试API连接

1. 点击 **"🧪 API测试"** 按钮
2. 配置测试参数：
   - API地址
   - 模型名称
   - 测试消息
   - 高级参数
3. 点击 **"🧪 测试API"** 查看结果

## 🔧 配置选项详解

### LM Studio API配置

```yaml
lm_studio:
  api:
    # API基础路径
    base_url: "http://127.0.0.1:1234/v1"

    # 自定义端点
    chat_endpoint: "/chat/completions"
    models_endpoint: "/models"

    # API认证（通常LM Studio不需要）
    api_key: ""

    # 自定义请求头
    headers:
      Content-Type: "application/json"
      User-Agent: "SSlogs-AI/1.0"
```

### 模型配置

```yaml
lm_studio:
  model:
    # 首选模型（支持自定义名称）
    preferred_model: "openai/gpt-oss-20b"

    # 模型名称映射
    model_mapping:
      "llama-3-8b-instruct": "openai/gpt-oss-20b"
      "qwen-7b-chat": "custom/security-analyzer-v1"
      "mistral-7b-instruct": "assistant/code-helper"

    # 模型参数
    max_tokens: 2048
    temperature: 0.7
    top_p: 0.9
    frequency_penalty: 0.0
    presence_penalty: 0.0
    stream: false
    response_format:
      type: "text"
```

## 🌐 OpenAI兼容API

### 使用curl测试

```bash
curl http://localhost:1234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai/gpt-oss-20b",
    "messages": [
      { "role": "system", "content": "Always answer in rhymes. Today is Thursday" },
      { "role": "user", "content": "What day is it today?" }
    ],
    "temperature": 0.7,
    "max_tokens": -1,
    "stream": false
  }'
```

### 使用Python测试

```python
import requests

response = requests.post(
    "http://localhost:1234/v1/chat/completions",
    headers={"Content-Type": "application/json"},
    json={
        "model": "openai/gpt-oss-20b",
        "messages": [
            {"role": "system", "content": "Always answer in rhymes. Today is Thursday"},
            {"role": "user", "content": "What day is it today?"}
        ],
        "temperature": 0.7,
        "max_tokens": -1,
        "stream": False
    }
)

result = response.json()
print(result["choices"][0]["message"]["content"])
```

## 📱 Web界面功能

### 配置管理
- **API配置**: 设置API地址、密钥、端点
- **模型配置**: 调整温度、令牌数、Top-P等参数
- **模型映射**: 管理实际模型ID与显示名称的映射关系

### API测试
- **连接测试**: 验证API地址是否可访问
- **模型测试**: 测试特定模型的响应
- **参数调试**: 调整温度、令牌数等参数
- **响应分析**: 查看响应时间、令牌使用等信息

### 实时监控
- **服务器状态**: 显示LM Studio连接状态
- **模型列表**: 展示所有可用模型
- **性能指标**: 监控响应时间和吞吐量

## 🔌 API接口

### 配置管理API

#### 获取配置
```http
GET /api/config
```

响应：
```json
{
  "success": true,
  "config": {
    "lm_studio": {
      "api": {
        "base_url": "http://127.0.0.1:1234/v1",
        "api_key": ""
      },
      "model": {
        "preferred_model": "openai/gpt-oss-20b",
        "model_mapping": {
          "llama-3-8b-instruct": "openai/gpt-oss-20b"
        }
      }
    }
  }
}
```

#### 更新配置
```http
POST /api/config
Content-Type: application/json

{
  "lm_studio": {
    "api": {
      "base_url": "http://127.0.0.1:1234/v1"
    },
    "model": {
      "preferred_model": "openai/gpt-oss-20b",
      "model_mapping": {
        "llama-3-8b-instruct": "openai/gpt-oss-20b"
      }
    }
  }
}
```

### 模型映射API

#### 添加映射
```http
POST /api/add_model_mapping
Content-Type: application/json

{
  "actual_model_id": "llama-3-8b-instruct",
  "display_name": "openai/gpt-oss-20b"
}
```

#### 删除映射
```http
POST /api/remove_model_mapping
Content-Type: application/json

{
  "actual_model_id": "llama-3-8b-instruct"
}
```

#### 获取所有映射
```http
GET /api/model_mappings
```

### API测试接口

#### 测试OpenAI兼容API
```http
POST /api/test_openai_api
Content-Type: application/json

{
  "api_url": "http://localhost:1234/v1/chat/completions",
  "api_key": "",
  "model_name": "openai/gpt-oss-20b",
  "system_prompt": "Always answer in rhymes. Today is Thursday",
  "test_message": "What day is it today?",
  "temperature": 0.7,
  "max_tokens": -1,
  "stream": false
}
```

## 🛠️ 高级用法

### 1. 多环境配置

创建不同环境的配置文件：

```yaml
# config/ai_config.dev.yaml
lm_studio:
  api:
    base_url: "http://dev-server:1234/v1"
  model:
    preferred_model: "dev-model"

# config/ai_config.prod.yaml
lm_studio:
  api:
    base_url: "http://prod-server:1234/v1"
  model:
    preferred_model: "prod-model"
```

### 2. 模型别名策略

使用有意义的模型别名：

```yaml
model_mapping:
  # 安全分析专用
  "llama-3-8b-instruct": "security/analyzer-v2"
  "qwen-7b-chat": "security/threat-detector-v1"

  # 代码生成专用
  "codellama-13b-instruct": "code/assistant-pro"
  "deepseek-coder-6.7b": "code/python-expert"

  # 通用对话
  "mistral-7b-instruct": "chat/general-purpose"
  "yi-34b-chat": "chat/advanced-assistant"
```

### 3. 参数预设

为不同用途创建参数预设：

```python
# 安全分析配置
security_config = LMStudioModelConfig(
    temperature=0.2,    # 低温度确保一致性
    max_tokens=1024,    # 适中的输出长度
    top_p=0.8           # 保守的采样策略
)

# 创意写作配置
creative_config = LMStudioModelConfig(
    temperature=0.9,    # 高温度增加创造性
    max_tokens=2048,    # 更长的输出
    top_p=0.95          # 更开放的采样
)
```

### 4. 批量模型映射

```python
# 批量添加模型映射
mappings = {
    "llama-3-8b-instruct": "openai/gpt-oss-20b",
    "llama-3-70b-instruct": "openai/gpt-oss-70b",
    "qwen-7b-chat": "custom/qwen-7b",
    "qwen-14b-chat": "custom/qwen-14b"
}

for actual_id, display_name in mappings.items():
    # 调用API添加映射
    add_model_mapping(actual_id, display_name)
```

## 🔍 故障排除

### 常见问题

#### 1. API连接失败
**症状**: API测试返回连接错误

**解决方案**:
- 检查LM Studio是否正在运行
- 确认API地址和端口正确
- 检查防火墙设置
- 验证模型是否已加载

#### 2. 模型名称映射无效
**症状**: 使用自定义模型名称时出现错误

**解决方案**:
- 确认映射关系配置正确
- 检查实际模型ID是否存在
- 重新加载配置
- 查看日志获取详细错误信息

#### 3. 配置保存失败
**症状**: Web界面无法保存配置

**解决方案**:
- 检查配置文件权限
- 确认磁盘空间充足
- 验证配置格式是否正确
- 查看服务器日志

### 调试技巧

#### 1. 启用详细日志
```yaml
logging:
  level: "DEBUG"
  detailed_logging: true
  log_requests: true
  log_responses: true
```

#### 2. 使用命令行工具
```bash
# 测试API连接
python3 cli/model_cli.py status

# 查看模型列表
python3 cli/model_cli.py list

# 测试特定模型
python3 cli/model_cli.py test llama-3-8b-instruct
```

#### 3. 检查配置文件
```bash
# 验证配置格式
python3 -c "import yaml; yaml.safe_load(open('config/ai_config.yaml'))"

# 查看当前配置
python3 cli/model_cli.py config --section lm_studio
```

## 📚 示例代码

### 使用自定义配置的完整示例

```python
from core.lm_studio_connector import LMStudioConnector, LMStudioConfig, LMStudioAPIConfig, LMStudioModelConfig

# 创建自定义配置
api_config = LMStudioAPIConfig(
    base_url="http://127.0.0.1:1234/v1",
    headers={"User-Agent": "MyApp/1.0"}
)

model_config = LMStudioModelConfig(
    preferred_model="openai/gpt-oss-20b",
    model_mapping={
        "llama-3-8b-instruct": "openai/gpt-oss-20b"
    },
    temperature=0.7,
    max_tokens=2048
)

config = LMStudioConfig(
    api=api_config,
    model=model_config
)

# 创建连接器
connector = LMStudioConnector(config)

# 测试连接
if connector.check_connection():
    print("连接成功!")

    # 发送聊天请求
    messages = [
        {"role": "user", "content": "你好，请介绍一下你自己"}
    ]

    response = connector.chat_completion(
        messages=[LMStudioConnector.ChatMessage(**msg) for msg in messages],
        model="openai/gpt-oss-20b"  # 使用映射的名称
    )

    print(f"AI回复: {response}")
else:
    print("连接失败!")
```

## 🎯 最佳实践

### 1. 模型命名规范
- 使用有意义的名称：`security/analyzer` 而不是 `model1`
- 包含用途信息：`code/python-expert` 而不是 `python-model`
- 版本控制：`analyzer/v2.0` 而不是 `analyzer-new`

### 2. 配置管理
- 为不同环境创建不同配置文件
- 使用版本控制管理配置变更
- 定期备份重要配置
- 记录配置变更的原因和影响

### 3. 性能优化
- 根据用途调整模型参数
- 使用缓存减少重复请求
- 监控API响应时间和错误率
- 合理设置超时和重试策略

### 4. 安全考虑
- 不要在配置中存储敏感信息
- 使用环境变量存储API密钥
- 限制API访问权限
- 定期更新和审查配置

---

**通过这份指南，您应该能够充分利用SSlogs的自定义配置功能，打造适合自己需求的AI分析系统！** 🚀