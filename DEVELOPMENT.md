# SSlogs 开发指南

## 📋 目录

- [开发环境设置](#开发环境设置)
- [项目架构](#项目架构)
- [代码规范](#代码规范)
- [测试指南](#测试指南)
- [调试技巧](#调试技巧)
- [性能优化](#性能优化)
- [部署流程](#部署流程)

## 🛠️ 开发环境设置

### 前置要求

- Python 3.8 或更高版本
- Git
- 推荐使用虚拟环境
- IDE (推荐 VS Code 或 PyCharm)

### 环境搭建

#### 1. 克隆项目

```bash
git clone https://github.com/yourusername/SSlogs.git
cd SSlogs
```

#### 2. 创建虚拟环境

```bash
# 使用 venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 使用 conda (可选)
conda create -n sslogs python=3.11
conda activate sslogs
```

#### 3. 安装开发依赖

```bash
# 安装基础依赖
pip install -r requirements.txt

# 安装开发工具
pip install -r requirements-dev.txt
```

#### 4. 配置开发环境

创建 `.env` 文件用于开发环境配置：

```bash
# 复制示例配置
cp .env.example .env

# 编辑配置文件
# 设置你的开发环境变量
```

#### 5. 运行测试验证环境

```bash
# 运行所有测试
pytest tests/

# 运行单个测试文件
pytest tests/unit/test_parser.py

# 查看测试覆盖率
pytest --cov=core --cov-report=html
```

### IDE 配置

#### VS Code

安装推荐的扩展：
- Python
- Python Test Explorer
- YAML
- Todo Tree

配置 `.vscode/settings.json`：

```json
{
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.linting.flake8Enabled": true,
    "python.testing.pytestEnabled": true,
    "python.testing.unittestEnabled": false,
    "editor.formatOnSave": true,
    "python.formatting.provider": "black"
}
```

#### PyCharm

1. 设置 Python 解释器指向虚拟环境
2. 启用 pytest 测试框架
3. 配置代码风格检查（PEP 8）
4. 设置类型检查（mypy）

## 🏗️ 项目架构

### 核心模块

```
core/
├── __init__.py              # 模块初始化
├── parser.py                # 日志解析器
├── rule_engine.py           # 规则匹配引擎
├── ai_analyzer.py           # AI分析器
├── reporter.py              # 报告生成器
├── config_manager.py        # 配置管理器
├── ip_utils.py              # IP工具集
├── performance.py           # 性能监控
└── exceptions.py            # 自定义异常
```

### 模块职责

#### parser.py - 日志解析器
- 解析各种格式的日志文件
- 提取关键安全字段
- 支持自定义解析规则

#### rule_engine.py - 规则引擎
- 加载和编译安全检测规则
- 多阶段威胁匹配
- 聚合分析和事件关联
- 威胁评分计算

#### ai_analyzer.py - AI分析器
- 集成多种AI服务（DeepSeek、Ollama、LM Studio）
- 智能威胁分析
- 专家级安全报告生成
- 降级和容错机制

#### reporter.py - 报告生成器
- 多格式报告生成（HTML、JSON、Markdown）
- 可视化威胁统计
- 地理位置分析
- 趋势分析

### 数据流

```
日志文件 → Parser → RuleEngine → AIAnalyzer → Reporter → 报告输出
         ↓          ↓           ↓          ↓
      解析结果    匹配规则    威胁评分    格式化输出
```

### 配置系统

```yaml
config.yaml                 # 主配置文件
├── log_path               # 日志路径
├── log_format            # 日志格式
├── rule_dir              # 规则目录
├── ai                    # AI配置
│   ├── type             # AI类型
│   └── providers        # 服务提供者
├── analysis             # 分析配置
└── output_dir          # 输出目录
```

## 📝 代码规范

### PEP 8 遵循

```python
# 好的示例
class LogParser:
    """日志解析器类"""

    def __init__(self, config: Dict[str, Any]):
        """初始化解析器

        Args:
            config: 配置字典
        """
        self.config = config

    def parse_line(self, line: str) -> Optional[Dict[str, Any]]:
        """解析单行日志

        Args:
            line: 日志行

        Returns:
            解析后的字典，失败返回 None
        """
        try:
            return self._parse(line)
        except Exception as e:
            logger.error(f"解析失败: {e}")
            return None
```

### 类型注解

```python
from typing import Dict, List, Optional, Any, Callable

def analyze_logs(
    logs: List[Dict[str, Any]],
    rules: List[Dict[str, Any]],
    callback: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """分析日志条目"""
    results = {}
    for log in logs:
        # 处理逻辑
        pass
    return results
```

### 文档字符串

```python
def method_with_complex_signature(
    param1: str,
    param2: int,
    param3: Optional[Dict[str, Any]] = None
) -> bool:
    """方法简短描述

    详细描述可以跨越多行，解释方法的用途、
    实现细节和注意事项。

    Args:
        param1: 参数1的描述
        param2: 参数2的描述
        param3: 可选参数的描述

    Returns:
        返回值的描述

    Raises:
        ValueError: 当参数无效时
        KeyError: 当键不存在时

    Examples:
        >>> method_with_complex_signature("test", 42)
        True
    """
    pass
```

### 异常处理

```python
# 定义自定义异常
class SSlogsError(Exception):
    """基础异常类"""
    pass

class ParserError(SSlogsError):
    """解析器异常"""
    pass

# 使用异常
def parse_log(file_path: str) -> List[Dict]:
    """解析日志文件"""
    try:
        with open(file_path, 'r') as f:
            return [parse_line(line) for line in f]
    except FileNotFoundError:
        raise ParserError(f"文件不存在: {file_path}")
    except PermissionError:
        raise ParserError(f"无权限读取: {file_path}")
```

## 🧪 测试指南

### 测试结构

```
tests/
├── unit/                  # 单元测试
│   ├── test_parser.py
│   ├── test_rule_engine.py
│   ├── test_ai_analyzer.py
│   └── test_performance.py
├── integration/           # 集成测试
│   └── test_integration.py
├── benchmark/            # 性能测试
│   └── performance_benchmark.py
└── README.md            # 测试文档
```

### 编写测试

#### 单元测试示例

```python
import pytest
from core.parser import LogParser

class TestLogParser:
    """日志解析器测试"""

    @pytest.fixture
    def parser(self):
        """创建解析器实例"""
        config = {
            'type': 'web',
            'fields': {
                'ip': r'(\d+\.\d+\.\d+\.\d+)',
                'timestamp': r'\[(.*?)\]'
            }
        }
        return LogParser(config)

    def test_parse_normal_log(self, parser):
        """测试正常日志解析"""
        log = '192.168.1.1 [10/Oct/2023:13:55:36] "GET / HTTP/1.1" 200'
        result = parser.parse_log_line(log)

        assert result is not None
        assert result['ip'] == '192.168.1.1'
        assert 'timestamp' in result

    def test_parse_invalid_log(self, parser):
        """测试无效日志处理"""
        log = 'invalid log format'
        result = parser.parse_log_line(log)

        assert result is None
```

#### 集成测试示例

```python
def test_end_to_end_analysis():
    """测试端到端分析流程"""
    # 1. 创建测试配置
    config = create_test_config()

    # 2. 运行分析
    analyzer = LogHunter(config_path=config)
    analyzer.run()

    # 3. 验证结果
    assert os.path.exists('output/report.html')
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/unit/test_parser.py

# 显示详细输出
pytest -v

# 显示测试覆盖率
pytest --cov=core --cov-report=html

# 并行运行测试（需要 pytest-xdist）
pytest -n auto

# 标记运行
pytest -m slow  # 运行标记为 slow 的测试
```

### 性能测试

```python
def test_parser_performance(benchmark):
    """测试解析器性能"""
    parser = LogParser(get_test_config())
    test_log = get_sample_log()

    result = benchmark(parser.parse_log_line, test_log)
    assert result is not None
```

## 🐛 调试技巧

### 日志配置

```python
import logging

# 配置开发日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)

# 在代码中使用
logger = logging.getLogger(__name__)
logger.debug("调试信息")
logger.info("一般信息")
logger.warning("警告信息")
logger.error("错误信息")
```

### 性能分析

```python
import cProfile
import pstats

# 性能分析
profiler = cProfile.Profile()
profiler.enable()

# 运行代码
your_function()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative').print_stats(10)
```

### 内存分析

```python
import tracemalloc

# 开始追踪
tracemalloc.start()

# 运行代码
your_function()

# 显示内存使用
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')
for stat in top_stats[:10]:
    print(stat)
```

## ⚡ 性能优化

### 规则引擎优化

```python
# 预编译正则表达式
import re

class RuleEngine:
    def __init__(self):
        # 预编译所有规则
        self.compiled_rules = [
            {
                'pattern': re.compile(rule['pattern']),
                'metadata': rule
            }
            for rule in self.rules
        ]

    def match(self, log_entry):
        # 使用预编译规则
        for rule in self.compiled_rules:
            if rule['pattern'].search(log_entry):
                return rule['metadata']
        return None
```

### 批处理优化

```python
def process_logs(logs, batch_size=1000):
    """批量处理日志"""
    results = []
    for i in range(0, len(logs), batch_size):
        batch = logs[i:i + batch_size]
        batch_results = process_batch(batch)
        results.extend(batch_results)

        # 内存管理
        if i % 10000 == 0:
            gc.collect()

    return results
```

## 🚀 部署流程

### 版本发布

1. 更新版本号
2. 更新 CHANGELOG.md
3. 创建 Git 标签
4. 构建发布包
5. 运行完整测试
6. 推送到远程仓库

### 代码审查清单

- [ ] 代码符合 PEP 8 规范
- [ ] 所有函数都有类型注解
- [ ] 包含适当的文档字符串
- [ ] 有相应的单元测试
- [ ] 测试覆盖率 > 80%
- [ ] 通过所有 lint 检查
- [ ] 性能测试通过
- [ ] 文档已更新

## 🔧 开发工具

### 代码质量工具

```bash
# 代码格式化
black .

# 类型检查
mypy core/

# Lint 检查
flake8 core/

# 安全检查
bandit -r core/
```

### 自动化工具

```bash
# 运行所有质量检查
pre-commit run --all-files

# 安装 pre-commit hooks
pre-commit install
```

## 📚 学习资源

### 推荐阅读

- Python PEP 8 风格指南
- Effective Python (第二版)
- Fluent Python
- Python Cookbook

### 内部文档

- [README.md](README.md) - 项目概述
- [AI_INTEGRATION.md](docs/AI_INTEGRATION.md) - AI 集成文档
- [API.md](API.md) - API 参考

## 💡 开发最佳实践

1. **保持简单**: 优先考虑可读性和可维护性
2. **测试驱动**: 先写测试，再写代码
3. **小步提交**: 频繁提交，每次提交一个功能
4. **代码审查**: 所有代码需要经过审查
5. **文档更新**: 功能变更时同步更新文档
6. **性能考虑**: 关注性能但不提前优化
7. **安全第一**: 始终考虑安全影响

## 🤝 开发流程

1. 从主分支创建功能分支
2. 进行开发和测试
3. 提交代码并推送
4. 创建 Pull Request
5. 代码审查
6. 合并到主分支

---

**Happy Coding!** 🚀
