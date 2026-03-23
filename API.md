# SSlogs API 参考文档

## 目录
- [概述](#概述)
- [核心模块](#核心模块)
- [解析器 API](#解析器-api)
- [规则引擎 API](#规则引擎-api)
- [AI 分析器 API](#ai-分析器-api)
- [安全验证器 API](#安全验证器-api)
- [性能监控 API](#性能监控-api)
- [事件总线 API](#事件总线-api)
- [异常处理](#异常处理)
- [示例代码](#示例代码)

---

## 概述

SSlogs 提供了完整的 Python API，支持自定义扩展和集成。

### 导入方式

```python
# 导入核心模块
from core.parser import LogParser
from core.rule_engine import RuleEngine
from core.ai_analyzer import AIAnalyzer
from core.security_validator import SecurityValidator
from core.performance_monitor import PerformanceMonitor
from core.event_bus import EventBus, Event

# 或使用统一接口
from core.intelligent_log_analyzer import IntelligentLogAnalyzer
```

---

## 核心模块

### IntelligentLogAnalyzer

主分析器类，整合所有功能。

#### 初始化

```python
analyzer = IntelligentLogAnalyzer(config_path='config.yaml')
```

#### 主要方法

##### analyze_log_file()

分析日志文件。

```python
def analyze_log_file(
    file_path: str,
    output_dir: str = None,
    enable_ai: bool = True
) -> Dict[str, Any]:
    """
    分析日志文件

    Args:
        file_path: 日志文件路径
        output_dir: 输出目录
        enable_ai: 是否启用 AI 分析

    Returns:
        分析结果字典，包含:
        - summary: 摘要信息
        - threats: 威胁列表
        - statistics: 统计数据
        - report_path: 报告文件路径
    """
```

**示例:**
```python
result = analyzer.analyze_log_file(
    file_path='access.log',
    output_dir='output',
    enable_ai=True
)

print(f"发现威胁: {len(result['threats'])}")
print(f"报告位置: {result['report_path']}")
```

##### analyze_log_entries()

分析日志条目列表。

```python
def analyze_log_entries(
    entries: List[Dict[str, Any]],
    enable_ai: bool = True
) -> List[Dict[str, Any]]:
    """
    分析日志条目

    Args:
        entries: 日志条目列表
        enable_ai: 是否启用 AI 分析

    Returns:
        分析结果列表
    """
```

---

## 解析器 API

### LogParser

日志解析器类。

#### 初始化

```python
from core.parser import LogParser

parser = LogParser(config={
    'timestamp_format': '%Y-%m-%d %H:%M:%S',
    'field_separator': ',',
    'encoding': 'utf-8',
    'batch_size': 100
})
```

#### 主要方法

##### parse()

解析单行日志。

```python
def parse(log_line: str) -> Optional[Dict[str, Any]]:
    """
    解析日志行

    Args:
        log_line: 日志文本行

    Returns:
        解析后的字典，包含:
        - timestamp: 时间戳
        - ip: IP 地址
        - method: HTTP 方法
        - url: URL
        - status: HTTP 状态码
        - user_agent: 用户代理
        或 None（解析失败）
    """
```

**示例:**
```python
log_line = "2024-01-15 10:30:45,192.168.1.100,GET,/api/users,200,Mozilla/5.0"
result = parser.parse(log_line)

if result:
    print(f"IP: {result['ip']}")
    print(f"URL: {result['url']}")
```

##### parse_batch()

批量解析日志。

```python
def parse_batch(
    log_lines: List[str],
    show_progress: bool = False
) -> List[Dict[str, Any]]:
    """
    批量解析日志行

    Args:
        log_lines: 日志行列表
        show_progress: 是否显示进度

    Returns:
        解析结果列表
    """
```

##### parse_file()

解析日志文件。

```python
def parse_file(
    file_path: str,
    batch_size: int = 1000
) -> List[Dict[str, Any]]:
    """
    解析日志文件

    Args:
        file_path: 文件路径
        batch_size: 批处理大小

    Returns:
        解析结果列表
    """
```

---

## 规则引擎 API

### RuleEngine

安全规则引擎类。

#### 初始化

```python
from core.rule_engine import RuleEngine

engine = RuleEngine(config={
    'rules_dir': 'rules',
    'threat_threshold': 7.0,
    'enable_precompiled': True
})

# 加载规则
engine.load_rules()
```

#### 主要方法

##### analyze()

分析日志条目。

```python
def analyze(
    log_entry: Dict[str, Any]
) -> Optional[ThreatResult]:
    """
    分析日志条目

    Args:
        log_entry: 日志条目字典

    Returns:
        威胁结果对象，包含:
        - is_threat: 是否为威胁
        - threat_level: 威胁级别 (1.0-10.0)
        - category: 威胁类别
        - rule_id: 匹配的规则 ID
        - description: 描述
        - confidence: 置信度
        或 None（无威胁）
    """
```

**示例:**
```python
log_entry = {
    'timestamp': '2024-01-15 10:30:45',
    'ip': '192.168.1.100',
    'method': 'GET',
    'url': '/../../../etc/passwd',
    'status': 403
}

result = engine.analyze(log_entry)

if result and result.is_threat:
    print(f"威胁级别: {result.threat_level}")
    print(f"类别: {result.category}")
    print(f"描述: {result.description}")
```

##### analyze_batch()

批量分析。

```python
def analyze_batch(
    log_entries: List[Dict[str, Any]],
    callback: Optional[Callable] = None
) -> List[ThreatResult]:
    """
    批量分析日志条目

    Args:
        log_entries: 日志条目列表
        callback: 进度回调函数

    Returns:
        威胁结果列表
    """
```

##### add_rule()

动态添加规则。

```python
def add_rule(rule: Dict[str, Any]) -> None:
    """
    添加规则

    Args:
        rule: 规则字典，格式:
        {
            'id': 'rule_001',
            'name': 'SQL 注入检测',
            'category': 'sql_injection',
            'severity': 9.0,
            'pattern': r"(?i)(union\s+select|'\s+or\s+')",
            'description': '检测 SQL 注入攻击'
        }
    """
```

**示例:**
```python
engine.add_rule({
    'id': 'custom_rule_001',
    'name': '自定义 XSS 检测',
    'category': 'xss',
    'severity': 8.0,
    'pattern': r'<script[^>]*>.*?</script>',
    'description': '检测 XSS 脚本注入'
})
```

---

## AI 分析器 API

### AIAnalyzer

AI 增强分析器类。

#### 初始化

```python
from core.ai_analyzer import AIAnalyzer

analyzer = AIAnalyzer(config={
    'enabled': True,
    'provider': 'deepseek',  # deepseek, ollama, lm_studio
    'api_key': 'your_api_key',
    'model': 'deepseek-chat',
    'timeout': 30
})
```

#### 主要方法

##### analyze()

AI 分析日志条目。

```python
async def analyze(
    log_entry: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    使用 AI 分析日志条目

    Args:
        log_entry: 日志条目
        context: 额外上下文信息

    Returns:
        分析结果字典，包含:
        - threat_level: 威胁级别 (high, medium, low)
        - confidence: 置信度 (0.0-1.0)
        - analysis: 详细分析文本
        - attack_type: 攻击类型
        - recommendation: 建议措施
        - risk_score: 风险评分 (0-100)
    """
```

**示例:**
```python
import asyncio

log_entry = {
    'ip': '192.168.1.100',
    'url': '/api/users?id=1\' OR \'1\'=\'1',
    'method': 'GET'
}

async def analyze():
    result = await analyzer.analyze(log_entry)

    print(f"威胁级别: {result['threat_level']}")
    print(f"置信度: {result['confidence']}")
    print(f"分析: {result['analysis']}")
    print(f"建议: {result['recommendation']}")

asyncio.run(analyze())
```

##### analyze_batch()

批量 AI 分析。

```python
async def analyze_batch(
    log_entries: List[Dict[str, Any]],
    max_concurrent: int = 5
) -> List[Dict[str, Any]]:
    """
    批量 AI 分析

    Args:
        log_entries: 日志条目列表
        max_concurrent: 最大并发数

    Returns:
        分析结果列表
    """
```

---

## 安全验证器 API

### SecurityValidator

安全验证器类。

#### 初始化

```python
from core.security_validator import SecurityValidator

validator = SecurityValidator(
    validation_level='strict',  # strict, medium, lenient
    enable_cache=True
)
```

#### 主要方法

##### validate_input()

验证用户输入。

```python
def validate_input(
    input_str: str,
    input_type: str = 'general'
) -> Dict[str, Any]:
    """
    验证输入是否包含恶意内容

    Args:
        input_str: 输入字符串
        input_type: 输入类型 (general, url, sql, command)

    Returns:
        验证结果字典，包含:
        - is_malicious: 是否为恶意输入
        - threat_types: 威胁类型列表
        - risk_score: 风险评分 (0-10)
        - sanitized_input: 净化后的输入
        - details: 详细信息
    """
```

**示例:**
```python
user_input = "<script>alert('XSS')</script>"

result = validator.validate_input(user_input)

if result['is_malicious']:
    print(f"检测到威胁: {result['threat_types']}")
    print(f"风险评分: {result['risk_score']}")
    print(f"净化输入: {result['sanitized_input']}")
```

##### sanitize_input()

净化输入。

```python
def sanitize_input(
    input_str: str,
    remove_null_bytes: bool = True
) -> str:
    """
    净化输入字符串

    Args:
        input_str: 原始输入
        remove_null_bytes: 是否移除空字节

    Returns:
        净化后的字符串
    """
```

##### validate_batch()

批量验证。

```python
def validate_batch(
    inputs: List[str]
) -> List[Dict[str, Any]]:
    """
    批量验证输入

    Args:
        inputs: 输入列表

    Returns:
        验证结果列表
    """
```

---

## 性能监控 API

### PerformanceMonitor

性能监控主类。

#### 初始化

```python
from core.performance_monitor import get_performance_monitor

monitor = get_performance_monitor()
monitor.start(monitor_interval=5)  # 5秒采集间隔
```

#### 主要方法

##### record_metric()

记录自定义指标。

```python
def record_metric(
    name: str,
    value: float,
    tags: Optional[Dict[str, str]] = None
) -> None:
    """
    记录指标

    Args:
        name: 指标名称
        value: 指标值
        tags: 标签
    """
```

**示例:**
```python
monitor.metrics.record(
    name="custom.processing_time",
    value=123.45,
    tags={"operation": "parse", "file": "access.log"}
)
```

##### get_dashboard_data()

获取监控面板数据。

```python
def get_dashboard_data() -> Dict[str, Any]:
    """
    获取监控面板数据

    Returns:
        面板数据字典，包含:
        - timestamp: 时间戳
        - health: 健康状态
        - metrics: 关键指标
        - system: 系统资源
    """
```

##### export_metrics()

导出指标数据。

```python
def export_metrics(
    format: str = 'json'
) -> str:
    """
    导出指标

    Args:
        format: 导出格式 (json, prometheus)

    Returns:
        格式化后的指标字符串
    """
```

**示例:**
```python
# JSON 格式
json_metrics = monitor.export_metrics(format='json')

# Prometheus 格式
prom_metrics = monitor.export_metrics(format='prometheus')
```

### Timer

性能计时上下文管理器。

#### 使用示例

```python
from core.performance_monitor import Timer, get_performance_monitor

monitor = get_performance_monitor()

# 记录函数执行时间
with Timer(monitor.metrics, "function.execution_time"):
    # 你的代码
    result = some_function()

# 记录日志解析时间
with Timer(monitor.metrics, "parser.parse_time", {"file": "access.log"}):
    entries = parser.parse_file("access.log")
```

---

## 事件总线 API

### EventBus

事件总线类。

#### 初始化

```python
from core.event_bus import EventBus, Event

bus = EventBus()
```

#### 主要方法

##### subscribe()

订阅事件。

```python
def subscribe(
    event_type: str,
    handler: Callable[[Event], None],
    priority: str = 'medium'
) -> None:
    """
    订阅事件

    Args:
        event_type: 事件类型
        handler: 事件处理函数
        priority: 优先级 (high, medium, low)
    """
```

**示例:**
```python
def on_threat_detected(event):
    print(f"威胁检测: {event.data}")

bus.subscribe('threat.detected', on_threat_detected, priority='high')
```

##### publish()

发布事件。

```python
def publish(event: Event) -> None:
    """
    发布事件

    Args:
        event: 事件对象
    """
```

**示例:**
```python
event = Event(
    event_type='threat.detected',
    data={
        'ip': '192.168.1.100',
        'threat_level': 9.0,
        'category': 'sql_injection'
    },
    metadata={'source': 'rule_engine'}
)

bus.publish(event)
```

##### publish_async()

异步发布事件。

```python
async def publish_async(event: Event) -> None:
    """
    异步发布事件

    Args:
        event: 事件对象
    """
```

---

## 异常处理

### 异常类层次

```python
# 基础异常
class SSlogsError(Exception):
    """SSlogs 基础异常类"""
    pass

# 配置异常
class ConfigError(SSlogsError):
    """配置错误"""
    pass

# 解析异常
class ParseError(SSlogsError):
    """解析错误"""
    pass

# AI 服务异常
class AIServiceError(SSlogsError):
    """AI 服务错误"""
    pass

class AIAPIError(AIServiceError):
    """AI API 调用错误"""
    pass

class AITimeoutError(AIServiceError):
    """AI 超时错误"""
    pass

# 安全异常
class SecurityError(SSlogsError):
    """安全相关错误"""
    pass

class ValidationError(SecurityError):
    """验证错误"""
    pass

# 性能异常
class PerformanceError(SSlogsError):
    """性能相关错误"""
    pass
```

### 异常处理示例

```python
from core.exceptions import ParseError, AIServiceError

try:
    result = parser.parse(log_line)
except ParseError as e:
    print(f"解析失败: {e}")
    # 处理解析错误
except AIServiceError as e:
    print(f"AI 服务错误: {e}")
    # 处理 AI 服务错误
except Exception as e:
    print(f"未知错误: {e}")
    # 处理其他错误
```

---

## 示例代码

### 完整分析流程

```python
from core.intelligent_log_analyzer import IntelligentLogAnalyzer
from core.performance_monitor import get_performance_monitor

# 初始化
monitor = get_performance_monitor()
monitor.start()

analyzer = IntelligentLogAnalyzer('config.yaml')

# 分析日志文件
result = analyzer.analyze_log_file(
    file_path='logs/access.log',
    output_dir='output',
    enable_ai=True
)

# 输出结果
print(f"分析完成:")
print(f"  总条目: {result['summary']['total_entries']}")
print(f"  威胁数: {len(result['threats'])}")
print(f"  报告: {result['report_path']}")

# 停止监控
monitor.stop()
```

### 自定义规则

```python
from core.rule_engine import RuleEngine

# 初始化引擎
engine = RuleEngine()
engine.load_rules()

# 添加自定义规则
custom_rule = {
    'id': 'custom_001',
    'name': '敏感文件访问',
    'category': 'sensitive_file_access',
    'severity': 8.0,
    'pattern': r'/(etc/passwd|etc/shadow|windows/system32/config)',
    'description': '检测敏感系统文件访问'
}

engine.add_rule(custom_rule)

# 分析日志
log_entry = {
    'url': '/../../etc/passwd',
    'method': 'GET'
}

result = engine.analyze(log_entry)
if result and result.is_threat:
    print(f"检测到威胁: {result.description}")
```

### 事件驱动架构

```python
from core.event_bus import EventBus, Event

# 初始化事件总线
bus = EventBus()

# 定义事件处理器
def on_threat_detected(event):
    ip = event.data.get('ip')
    threat_level = event.data.get('threat_level')
    print(f"[ALERT] 威胁检测: IP={ip}, 级别={threat_level}")

    # 可以触发其他事件
    bus.publish(Event(
        event_type='alert.notify',
        data=event.data
    ))

def on_alert_notify(event):
    # 发送通知
    print(f"[NOTIFY] 发送告警通知...")

# 订阅事件
bus.subscribe('threat.detected', on_threat_detected, priority='high')
bus.subscribe('alert.notify', on_alert_notify)

# 发布事件
threat_event = Event(
    event_type='threat.detected',
    data={
        'ip': '192.168.1.100',
        'threat_level': 9.0,
        'category': 'sql_injection'
    }
)

bus.publish(threat_event)
```

### 异步 AI 分析

```python
import asyncio
from core.ai_analyzer import AIAnalyzer

async def analyze_with_ai():
    analyzer = AIAnalyzer(config={
        'provider': 'ollama',
        'api_url': 'http://localhost:11434',
        'model': 'llama2'
    })

    logs = [
        {'ip': '192.168.1.100', 'url': '/../../../etc/passwd'},
        {'ip': '192.168.1.101', 'url': '/api/users'},
    ]

    # 批量分析
    results = await analyzer.analyze_batch(logs, max_concurrent=3)

    for log, result in zip(logs, results):
        print(f"URL: {log['url']}")
        print(f"威胁级别: {result['threat_level']}")
        print(f"分析: {result['analysis']}\n")

asyncio.run(analyze_with_ai())
```

---

## 更多资源

- **完整文档**: [README.md](README.md)
- **部署指南**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **示例代码**: [examples/](examples/)
- **贡献指南**: [CONTRIBUTING.md](CONTRIBUTING.md)

---

**版本**: 3.1.0
**最后更新**: 2024-12-23
