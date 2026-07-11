# SSlogs API 参考文档

欢迎查阅 SSlogs 智能安全日志分析平台的 API 参考文档。

## 模块索引

### 核心模块

.. toctree::
   :maxdepth: 2

   core_parser
   core_rule_engine
   core_ai_analyzer
   core_reporter
   core_config_manager
   core_ip_utils
   core_performance
   core_exceptions

### 工具模块

.. toctree::
   :maxdepth: 2

   utils
   helpers

## 快速开始

### 安装

```bash
pip install -r requirements.txt
```

### 基本使用

```python
from core.parser import LogParser
from core.rule_engine import RuleEngine
from core.ai_analyzer import AIAnalyzer
from core.reporter import ReportGenerator

# 初始化组件
parser = LogParser(config['log_format'])
rule_engine = RuleEngine('rules')
ai_analyzer = AIAnalyzer('config.yaml')
reporter = ReportGenerator('output')

# 分析日志
log_entry = parser.parse_log_line(log_line)
matches = rule_engine.match_log(log_entry)
ai_result = ai_analyzer.analyze_log(log_context)
report = reporter.generate_report(matches, ai_results)
```

## 核心概念

### 日志解析

SSlogs 支持多种日志格式的解析，通过配置文件定义字段和正则表达式模式。

### 规则引擎

规则引擎使用 YAML 格式定义安全检测规则，支持多阶段匹配和威胁评分。

### AI分析

支持多种 AI 服务的安全分析，包括云端 DeepSeek 和本地 Ollama。

### 报告生成

生成 HTML、JSON、Markdown 等多种格式的安全分析报告。

## 索引和表格

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`