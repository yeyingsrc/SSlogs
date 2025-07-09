# 🔍 应急分析溯源日志工具

一个功能强大的Web日志安全分析工具，集成了规则引擎、AI智能分析和多格式报告生成，专为安全应急响应和威胁溯源而设计。

## ✨ 核心特性

- 🎯 **智能日志解析** - 支持多种Web日志格式，可通过配置文件灵活扩展
- 🛡️ **规则引擎** - 基于YAML规则的攻击检测（SQL注入、XSS、路径遍历等）
- 🤖 **AI增强分析** - 集成DeepSeek/Ollama进行智能日志分析和威胁评估
- 🌍 **地理位置分析** - IP地理位置识别和访问统计
- 📊 **多格式报告** - 生成HTML、Markdown、JSON格式的详细分析报告
- ⚡ **高性能处理** - 支持大文件和压缩文件的高效处理（支持145万+日志条目）
- 🔧 **高度可配置** - 所有功能通过配置文件管理，无需修改代码
- 🎯 **智能过滤** - 支持高风险成功攻击的精准筛选和TOP N分析
- 📈 **攻击趋势** - 攻击类型TOP10统计和趋势分析

## 🏗️ 系统架构

```
日志分析工具
├── 核心模块 (core/)
│   ├── parser.py      # 日志解析器
│   ├── rule_engine.py # 规则引擎  
│   ├── ai_analyzer.py # AI分析器
│   ├── reporter.py    # 报告生成器
│   └── ip_utils.py    # IP工具集
├── 规则库 (rules/)    # YAML安全规则
├── 配置 (config.yaml) # 主配置文件
└── 输出 (output/)     # 分析报告
```

## 🚀 快速开始

### 环境要求

- **Python 3.8+**
- **pip** (Python包管理器)
- **可选**: Ollama (本地AI模型)

### 安装步骤

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd SSlogs
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置GeoIP数据库** (IP地理位置分析)
   ```bash
   # 下载GeoLite2数据库
   wget https://github.com/mojolabs-id/GeoLite2-Database/raw/main/GeoLite2-Country.mmdb
   mv GeoLite2-Country.mmdb config/
   ```

4. **配置API密钥**
   
   编辑 `config.yaml` 文件：
   ```yaml
   deepseek:
     api_key: "your-api-key-here"  # 替换为实际API密钥
   ```

## 📖 使用方法

### 基本用法

```bash
# 基础日志分析（交互式输入主机IP）
python main.py --config config.yaml

# 启用AI智能分析（推荐）
python main.py --config config.yaml --ai

# 直接指定主机IP地址
python main.py --config config.yaml --ai --server-ip 192.168.1.100

# 从日志样例自动生成解析规则
python main.py --generate-rules "192.168.1.1 [10/Oct/2023:13:55:36] \"GET /index.php HTTP/1.1\" 200 1234"
```

#### 🔧 主机IP配置说明

工具启动时会要求输入服务器主机IP地址，用于生成完整的分析报告：

1. **交互式输入**：运行时提示输入IP地址，自动验证格式
2. **命令行指定**：使用 `--server-ip` 参数直接指定
3. **配置文件设置**：在 `config.yaml` 中预设默认IP

```
==================================================
欢迎使用应急分析溯源日志工具
==================================================
请输入服务器主机IP地址: 192.168.1.100
开始分析主机 192.168.1.100 的日志...
==================================================
```

### AI分析特性

本工具的AI分析模块支持智能过滤和深度分析：

- **智能筛选**: 只分析高风险且攻击成功的事件
- **成功判定**: 基于HTTP状态码（200、201、202、204、301、302、304）
- **TOP N分析**: 默认分析最关键的5个事件
- **深度评估**: 包含攻击分析、影响评估、应急措施、威胁情报

### 配置选项

#### 1. 日志格式配置
```yaml
log_format:
  fields:
    src_ip: '(\d+\.\d+\.\d+\.\d+)'
    timestamp: '\[(.*?)\]' 
    request_method: '"([A-Z]+)'
    status_code: '(\d{3})'
```

#### 2. AI智能分析配置
```yaml
ai_analysis:
  # 是否只分析高风险事件
  high_risk_only: true
  # 是否只分析攻击成功的事件  
  successful_attacks_only: true
  # 攻击成功的HTTP状态码定义
  success_status_codes: ['200', '201', '202', '204', '301', '302', '304']
  # AI分析的最大事件数量
  max_ai_analysis: 5
  # 高风险严重级别定义
  high_risk_severity: "high"
```

#### 3. AI服务配置
```yaml
# 使用云端DeepSeek（推荐）
ai:
  type: "cloud"
  cloud_provider: "deepseek"

deepseek:
  api_key: "your-api-key-here"
  model: "deepseek-ai/DeepSeek-V3"
  base_url: "https://api.siliconflow.cn/v1/chat/completions"

# 使用本地Ollama
ai:
  type: "local"
  local_provider: "ollama"

ollama:
  model: "deepseek-r1:14b"
  base_url: "http://localhost:11434/api/chat"
```

#### 4. 性能优化配置
```yaml
analysis:
  batch_size: 1000        # 批处理大小
  max_events: 100         # 最大事件数量
  memory_limit_mb: 500    # 内存限制(MB)
```

## 🛡️ 安全规则

工具内置了40+个安全检测规则，涵盖：

- **注入攻击**: SQL注入、NoSQL注入、LDAP注入
- **跨站攻击**: XSS、CSRF、SSRF
- **文件攻击**: 路径遍历、文件包含、文件上传
- **扫描检测**: 目录扫描、漏洞扫描、工具识别
- **其他威胁**: WebShell、暴力破解、协议攻击

### 自定义规则

在 `rules/` 目录下创建YAML文件：

```yaml
name: "自定义SQL注入检测"
pattern:
  url: "(union.*select|insert.*into)"
  user_agent: "(sqlmap|havij)"
severity: "high"
category: "injection"
description: "检测SQL注入攻击尝试"
```

## 📊 分析报告

### HTML报告特性（全新升级）
- 📈 **威胁统计仪表板** - 安全事件总数和严重程度分布
- 🎯 **攻击类型TOP10** - 最活跃的攻击类型排名和趋势
- 🌍 **外网IP优先显示** - 外部威胁IP地理分布和风险评级
- 🏠 **内网IP访问统计** - 内部网络访问模式分析
- 🚨 **安全事件时间线** - 按严重程度排序的详细事件
- 🤖 **AI深度分析** - 针对高风险成功攻击的专业分析
- 📱 **响应式设计** - 支持桌面和移动设备

### 报告布局结构
1. **📊 概览统计卡片** - 事件总数、高中低危事件统计
2. **🎯 攻击类型TOP10** - 排名、类型、数量、占比、最高风险级别
3. **🌍 外网IP访问排名** - IP、访问次数、地理位置、风险等级
4. **🏠 内网IP访问排名** - 内部网络访问统计
5. **🚨 安全事件详情** - 攻击详情、AI分析、处置建议

### 多格式输出
- **HTML格式** - 现代化Web界面，适合查看和演示
- **Markdown格式** - 文档友好，适合报告归档
- **JSON格式** - 结构化数据，适合自动化处理

### AI分析报告内容
每个高风险成功攻击事件的AI分析包含：
- **攻击分析** - 具体攻击类型、技术手段、载荷危害程度
- **影响评估** - 系统损害、数据风险、业务影响
- **应急措施** - 立即阻断措施、系统加固建议
- **威胁情报** - 攻击者特征、组织分析、后续威胁评估

## 🧪 测试验证

运行测试脚本验证功能：

```bash
python test_log_analyzer.py
```

测试覆盖：
- ✅ 日志解析器
- ✅ 规则引擎匹配  
- ✅ AI分析功能
- ✅ 报告生成器

## 🔧 高级配置

### 性能优化
```yaml
analysis:
  batch_size: 1000          # 批处理大小（推荐1000）
  context_lines: 5          # 上下文行数
  max_events: 100           # 最大事件数
  memory_limit_mb: 500      # 内存限制（MB）
```

### AI配置调优
```yaml
deepseek:
  max_tokens: 2048          # 最大令牌数
  temperature: 0.7          # 创造性参数（0.0-1.0）
  timeout: 30               # 请求超时（秒）

# AI分析精细控制
ai_analysis:
  high_risk_only: true      # 仅分析高风险事件
  successful_attacks_only: true  # 仅分析成功攻击
  max_ai_analysis: 5        # 分析事件数量限制
```

### 规则引擎优化
```yaml
rules:
  default_severity: "medium"
  case_sensitive: false
  max_matches: 50
```

### 文件格式支持
工具支持多种日志文件格式：
- `.log` - 标准日志文件
- `.gz` - Gzip压缩文件
- `.tar.gz` - Tar Gzip压缩包
- `.zip` - ZIP压缩包
- `.rar` - RAR压缩包

### 大规模日志处理
- **支持规模**: 145万+日志条目
- **处理方式**: 批量处理，内存友好
- **压缩支持**: 自动解压多种压缩格式
- **内存管理**: 自动垃圾回收，防止内存溢出

## 📁 项目结构

```
SSlogs/
├── main.py                    # 主程序入口
├── config.yaml               # 主配置文件
├── requirements.txt          # Python依赖
├── test_log_analyzer.py     # 测试脚本
├── core/                    # 核心模块
│   ├── __init__.py
│   ├── parser.py           # 日志解析器
│   ├── rule_engine.py      # 规则引擎
│   ├── ai_analyzer.py      # AI分析器
│   ├── reporter.py         # 报告生成器
│   └── ip_utils.py         # IP工具
├── rules/                  # 安全规则库
│   ├── sql_injection.yaml
│   ├── xss_attack.yaml
│   └── ...
├── config/                 # 配置目录
│   └── GeoLite2-Country.mmdb
├── logs/                   # 测试日志
├── output/                 # 分析报告
└── README.md
```

## 🤝 贡献指南

1. **Fork** 项目
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送分支 (`git push origin feature/amazing-feature`)
5. 创建 **Pull Request**

### 开发建议
- 遵循PEP 8编码规范
- 添加适当的注释和文档
- 编写测试用例
- 更新相关文档

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🆘 支持与帮助

### 常见问题

**Q: 日志解析失败怎么办？**
A: 检查日志格式配置，或使用 `--generate-rules` 自动生成解析规则

**Q: AI分析返回错误？**
A: 检查API密钥配置和网络连接，或切换到本地Ollama模式

**Q: 规则不匹配？**  
A: 验证规则语法，检查正则表达式，启用调试日志查看详情

### 技术支持

- 📧 **邮件支持**: support@example.com
- 💬 **讨论区**: [GitHub Discussions](链接)
- 🐛 **问题反馈**: [GitHub Issues](链接)

## 🔄 更新日志

### v2.2.0 (最新)
- ✨ **交互式主机IP输入**: 启动时自动提示输入服务器主机IP地址
- 🔧 **IP地址验证**: 自动验证IP格式，确保输入正确性
- 📋 **命令行IP参数**: 新增 `--server-ip` 参数，支持直接指定主机IP
- 📊 **报告完整性**: 基于主机IP生成更完整准确的分析报告
- 🎯 **用户体验**: 改进交互界面，清晰的操作引导和反馈

### v2.1.0
- ✨ **智能AI过滤**: 只分析高风险成功攻击的TOP5事件
- 🎯 **攻击类型TOP10**: 新增攻击类型排名和趋势分析
- 🌍 **外网IP优先**: 调整报告布局，外网IP访问排名前置
- 🚀 **性能优化**: 支持145万+日志条目的高效处理
- 🤖 **AI提示优化**: 针对成功攻击的专业安全分析
- 📊 **报告增强**: 现代化界面设计和用户体验提升
- 🔧 **配置升级**: AI分析配置项精细化控制

### v2.0.0
- ✨ 新增AI智能分析功能
- 🎨 改进HTML报告界面
- 🚀 优化性能和内存使用
- 🛡️ 增强安全规则库
- 📱 支持JSON格式报告

### v1.0.0
- 🎉 首次发布
- 📝 基础日志解析功能
- 🔍 规则引擎实现
- 📊 HTML报告生成

---

**⚡ 让日志分析更智能，让威胁溯源更高效！** 🚀