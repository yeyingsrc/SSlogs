# SSlogs AI模型管理器使用指南

## 概述

SSlogs AI模型管理器提供了一个直观的Web界面，用于管理LM Studio本地模型。您可以轻松地刷新、选择和测试不同的AI模型，为安全日志分析配置最佳的AI助手。

## 功能特性

### 🔗 服务器状态监控
- 实时显示LM Studio连接状态
- 监控服务器响应时间
- 显示可用模型数量
- 查看当前加载的模型

### 🤖 模型管理
- **刷新模型列表**: 自动发现LM Studio中加载的模型
- **模型信息显示**: 显示模型参数、量化方式、兼容性评分
- **一键选择**: 快速切换AI分析使用的模型
- **智能推荐**: 根据不同用途推荐最适合的模型

### 🧪 模型测试
- **实时测试**: 发送测试消息验证模型响应
- **响应时间监控**: 测量模型处理速度
- **自定义测试**: 使用自定义提示词测试模型

### ⚙️ 配置管理
- **AI功能开关**: 启用/禁用不同的AI功能
- **性能调优**: 调整并发数、批处理大小等参数
- **安全配置**: 设置敏感信息过滤规则

## 快速开始

### 1. 环境准备

#### 安装依赖
```bash
pip install flask flask-cors aiohttp pydantic
```

#### 启动LM Studio
1. 下载并安装 [LM Studio](https://lmstudio.ai/)
2. 在LM Studio中下载一个适合的模型（推荐Llama 3 8B Instruct）
3. 启动本地服务器（默认端口1234）

### 2. 启动模型管理器

#### 方法一：使用启动脚本（推荐）
```bash
# 进入项目目录
cd /path/to/SSlogs

# 启动模型管理器
python start_model_manager.py

# 自定义端口
python start_model_manager.py --port 8080

# 调试模式
python start_model_manager.py --debug

# 仅检查环境，不启动服务器
python start_model_manager.py --check-only
```

#### 方法二：直接运行
```bash
python web/model_api.py
```

### 3. 访问管理界面

启动成功后，在浏览器中访问：
- 本地访问: http://127.0.0.1:8080
- 局域网访问: http://[您的IP地址]:8080

## 界面使用指南

### 主界面布局

```
┌─────────────────────────────────────────┐
│  🤖 SSlogs AI模型管理                    │
├─────────────────────────────────────────┤
│  🔗 LM Studio服务器状态                  │
│  ┌─────────┬─────────┬─────────┬───────┐ │
│  │ 已连接   │ 地址:端口 │ 模型数 │ 响应时间│ │
│  └─────────┴─────────┴─────────┴───────┘ │
├─────────────────────────────────────────┤
│  [🔄刷新模型] [⭐获取推荐] [用途选择▼]    │
├─────────────────────────────────────────┤
│  ┌─────────模型卡片─────────────────────┐ │
│  │ ⭐模型名称               [选择][测试] │ │
│  │ model-id-string                     │ │
│  │ [8B] [Q4_K_M] 📋当前                 │ │
│  │ 模型描述信息...                      │ │
│  │ 兼容性: ████████ 4.5/5.0             │ │
│  └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### 操作步骤

#### 1. 检查服务器状态
- 打开页面后自动检查LM Studio连接状态
- ✅ **已连接**: 绿色状态，显示服务器信息
- ❌ **未连接**: 红色状态，显示错误信息和解决方案

#### 2. 刷新模型列表
- 点击 **"🔄 刷新模型列表"** 按钮
- 系统会扫描LM Studio中加载的所有模型
- 每个模型显示详细信息：
  - 模型名称和ID
  - 参数大小（如7B、13B）
  - 量化方式（如Q4_K_M、Q8_0）
  - 兼容性评分（0-5分）
  - 推荐标记（⭐）

#### 3. 选择模型
- 在模型卡片中点击 **"选择"** 按钮
- 系统会自动更新配置
- 选中的模型会显示 **"📋 当前"** 标记
- 页面会显示成功消息

#### 4. 测试模型
- 点击模型卡片中的 **"测试"** 按钮
- 在弹出的对话框中：
  - 查看模型名称
  - 输入测试提示词（默认为自我介绍）
  - 点击 **"开始测试"**
- 查看测试结果：
  - 响应时间
  - 模型回复内容
  - 错误信息（如果有）

#### 5. 获取推荐
- 选择使用场景：
  - **通用用途**: 适合日常使用
  - **安全分析**: 专为安全日志分析优化
  - **速度优先**: 选择响应最快的模型
- 点击 **"⭐ 获取推荐"** 按钮
- 系统会根据场景重新排序模型列表

## API接口

如果您需要在其他应用中集成模型管理功能，可以使用以下API接口：

### 获取服务器状态
```http
GET /api/status
```

响应：
```json
{
  "success": true,
  "status": {
    "connected": true,
    "host": "127.0.0.1",
    "port": 1234,
    "model_loaded": true,
    "current_model": "llama-3-8b-instruct",
    "available_models_count": 3,
    "response_time": 0.85
  }
}
```

### 获取模型列表
```http
GET /api/models
```

响应：
```json
{
  "success": true,
  "models": [
    {
      "id": "llama-3-8b-instruct",
      "name": "Llama 3 8B (Instruct)",
      "parameters": "8B",
      "quantization": "Q4_K_M",
      "recommended": true,
      "compatibility_score": 4.5,
      "description": "Llama系列模型，8B参数，适合对话和指令跟随"
    }
  ],
  "current_model": "llama-3-8b-instruct"
}
```

### 选择模型
```http
POST /api/select_model
Content-Type: application/json

{
  "model_id": "llama-3-8b-instruct"
}
```

响应：
```json
{
  "success": true,
  "message": "已选择模型: llama-3-8b-instruct",
  "model_id": "llama-3-8b-instruct"
}
```

### 测试模型
```http
POST /api/test_model
Content-Type: application/json

{
  "model_id": "llama-3-8b-instruct",
  "prompt": "你好，请简单介绍一下自己。"
}
```

响应：
```json
{
  "success": true,
  "response": "您好！我是Llama 3...",
  "response_time": 1.23,
  "model_id": "llama-3-8b-instruct"
}
```

### 获取模型推荐
```http
GET /api/recommendations?use_case=security_analysis
```

响应：
```json
{
  "success": true,
  "models": [...],
  "use_case": "security_analysis"
}
```

## 配置说明

### 模型推荐配置

在 `config/ai_config.yaml` 中可以调整模型推荐逻辑：

```yaml
model_compatibility:
  # 支持的模型系列
  supported_series:
    - "llama"
    - "qwen"
    - "mistral"
    - "yi"

  # 偏好的模型大小（参数数量）
  preferred_sizes:
    - 7
    - 8
    - 13
    - 34

  # 避免的模型特征
  avoid_features:
    - "base"    # 基础模型（未调优）
    - "raw"     # 原始模型
```

### 性能配置

```yaml
performance:
  max_concurrent_requests: 5
  batch_size: 10
  request_timeout: 30
  batch_timeout: 60
```

### AI功能开关

```yaml
ai_features:
  threat_analysis: true          # 威胁分析
  natural_language_query: true   # 自然语言查询
  rule_explanation: true         # 规则解释
  security_recommendations: true # 安全建议
  batch_analysis: true          # 批量分析
```

## 故障排除

### 常见问题

#### 1. 无法连接到LM Studio
**症状**: 页面显示"❌ 连接失败"

**解决方案**:
1. 确保LM Studio正在运行
2. 检查本地服务器是否启动（端口1234）
3. 确认已加载至少一个模型
4. 检查防火墙设置

#### 2. 模型列表为空
**症状**: 显示"未发现可用模型"

**解决方案**:
1. 在LM Studio中加载一个模型
2. 点击"刷新模型列表"
3. 确保模型完全加载完成

#### 3. 选择模型失败
**症状**: 点击"选择"后显示错误

**解决方案**:
1. 检查配置文件权限
2. 确认模型ID正确
3. 重启LM Studio服务器

#### 4. 测试模型无响应
**症状**: 测试时一直加载中

**解决方案**:
1. 检查模型是否完全加载
2. 尝试更简单的测试提示词
3. 查看LM Studio控制台错误信息

#### 5. Web界面无法访问
**症状**: 浏览器无法打开管理页面

**解决方案**:
1. 检查端口是否被占用
2. 尝试使用不同的端口
3. 检查防火墙设置
4. 确认Python依赖已安装

### 日志查看

查看详细日志：
```bash
# 查看模型管理器日志
tail -f logs/model_manager.log

# 查看AI分析日志
tail -f logs/ai_analysis.log

# 启动时显示详细日志
python start_model_manager.py --debug
```

### 性能优化

#### 提高响应速度
1. 选择较小的模型（7B/8B）
2. 使用Q4量化
3. 调整AI配置中的超时设置
4. 启用缓存功能

#### 减少内存使用
1. 选择合适的模型大小
2. 关闭不必要的LM Studio功能
3. 调整批处理大小

## 安全注意事项

### 数据隐私
- 所有AI分析在本地进行，数据不会上传到外部服务器
- 可以配置敏感信息过滤，保护关键数据

### 访问控制
- 默认绑定到0.0.0.0，允许局域网访问
- 建议在生产环境中配置防火墙规则
- 可以修改启动参数限制访问范围

### 模型安全
- 仅使用可信来源的模型
- 定期更新模型版本
- 监控模型输出内容

## 高级用法

### 命令行工具

```bash
# 检查环境和依赖
python start_model_manager.py --check-only

# 指定端口启动
python start_model_manager.py --port 9000

# 调试模式
python start_model_manager.py --debug

# 不自动打开浏览器
python start_model_manager.py --no-browser
```

### 集成到现有应用

```python
from core.model_manager import get_model_manager

# 获取模型管理器
manager = get_model_manager()

# 刷新模型列表
models = manager.refresh_models()

# 选择模型
success = manager.select_model("llama-3-8b-instruct")

# 测试模型
result = manager.test_model("llama-3-8b-instruct", "测试提示词")
```

### 批量操作

```python
# 导出模型列表
export_data = manager.export_model_list("json")

# 获取推荐模型
recommendations = manager.get_model_recommendations("security_analysis")

# 批量测试模型
for model in models[:3]:
    result = manager.test_model(model.id, "简单测试")
    print(f"{model.name}: {result['success']}")
```

## 更新日志

### v1.0.0
- ✅ 初始版本发布
- ✅ Web界面模型管理
- ✅ LM Studio集成
- ✅ 模型测试功能
- ✅ 智能推荐系统
- ✅ RESTful API接口

### 未来计划
- 🔄 模型性能监控图表
- 🔄 批量模型测试
- 🔄 模型版本管理
- 🔄 配置导入/导出
- 🔄 多语言界面支持

## 支持与反馈

如果您在使用过程中遇到问题或有功能建议，请：

1. 查看本文档的故障排除部分
2. 检查日志文件获取详细错误信息
3. 在项目仓库提交Issue
4. 联系技术支持

---

**感谢使用SSlogs AI模型管理器！** 🚀