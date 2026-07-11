# 贡献指南 - SSlogs

感谢您对 SSlogs 项目的关注！我们欢迎所有形式的贡献。

## 🤝 如何贡献

### 报告问题

如果您发现了 bug 或有功能建议：

1. 检查 [Issues](../../issues) 确认问题未被报告
2. 创建新 Issue，包含：
   - 清晰的标题和描述
   - 复现步骤（针对 bug）
   - 预期行为和实际行为
   - 环境信息（Python 版本、操作系统等）
   - 相关日志或截图

### 提交代码

#### 1. Fork 和克隆

```bash
# Fork 项目到您的 GitHub 账号
# 然后克隆您的 fork
git clone https://github.com/YOUR_USERNAME/SSlogs.git
cd SSlogs
```

#### 2. 创建分支

```bash
# 从 main 分支创建功能分支
git checkout -b feature/your-feature-name

# 或修复分支
git checkout -b fix/your-bug-fix
```

分支命名规范：
- `feature/` - 新功能
- `fix/` - bug 修复
- `docs/` - 文档更新
- `test/` - 测试相关
- `refactor/` - 代码重构
- `perf/` - 性能优化

#### 3. 进行开发

```bash
# 进行您的更改
# 确保遵循代码规范

# 运行测试
pytest tests/

# 运行代码检查
black .
flake8 core/
mypy core/
```

#### 4. 提交更改

```bash
git add .
git commit -m "feat: add SQL injection detection rule"
```

提交信息格式：
- `feat:` - 新功能
- `fix:` - bug 修复
- `docs:` - 文档更新
- `style:` - 代码格式（不影响功能）
- `refactor:` - 重构
- `test:` - 测试相关
- `chore:` - 构建/工具相关

#### 5. 推送和创建 PR

```bash
# 推送到您的 fork
git push origin feature/your-feature-name

# 在 GitHub 上创建 Pull Request
```

## 📝 代码规范

### Python 风格指南

我们遵循 [PEP 8](https://www.python.org/dev/peps/pep-0008/) 风格指南：

```python
# 好的示例 ✅
class SecurityAnalyzer:
    """安全分析器类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def analyze(self, log_entry: Dict) -> Optional[ThreatResult]:
        """分析日志条目"""
        if not self._validate(log_entry):
            return None
        return self._process(log_entry)

# 不好的示例 ❌
class securityanalyzer:  # 类名应该使用 PascalCase
    def __init__(self,c):  # 缺少类型注解，参数命名不清晰
        self.c=c
```

### 文档字符串

使用 Google 风格的文档字符串：

```python
def analyze_security_log(log_entry: Dict[str, Any]) -> Optional[ThreatResult]:
    """分析安全日志条目

    Args:
        log_entry: 包含日志信息的字典

    Returns:
        威胁分析结果，如果无法分析则返回 None

    Raises:
        ValueError: 当日志格式无效时
        ParserError: 当解析失败时

    Examples:
        >>> analyze_security_log({'ip': '192.168.1.1'})
        ThreatResult(severity='high', confidence=0.95)
    """
    pass
```

### 类型注解

所有公共函数和方法都应该有类型注解：

```python
from typing import Dict, List, Optional, Any, Callable

def process_logs(
    logs: List[Dict[str, Any]],
    rules: List[Dict[str, Any]],
    callback: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """处理日志条目"""
    pass
```

## 🧪 测试要求

### 测试覆盖率

新功能需要包含测试，覆盖率目标：

- 单元测试覆盖率 > 80%
- 关键路径覆盖率 = 100%

### 编写测试

```python
import pytest
from core.analyzer import SecurityAnalyzer

class TestSecurityAnalyzer:
    """安全分析器测试"""

    @pytest.fixture
    def analyzer(self):
        """创建测试实例"""
        return SecurityAnalyzer(test_config)

    def test_sql_injection_detection(self, analyzer):
        """测试 SQL 注入检测"""
        log = {'url': '/?id=1 OR 1=1'}
        result = analyzer.analyze(log)

        assert result is not None
        assert result.threat_type == 'sql_injection'
        assert result.severity == 'high'

    def test_xss_detection(self, analyzer):
        """测试 XSS 检测"""
        log = {'url': '/?q=<script>alert(1)</script>'}
        result = analyzer.analyze(log)

        assert result is not None
        assert 'xss' in result.threat_type.lower()
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/unit/test_analyzer.py

# 查看覆盖率
pytest --cov=core --cov-report=html
```

## 📋 PR 检查清单

提交 PR 前确认：

- [ ] 代码符合项目的代码规范
- [ ] 包含适当的文档字符串
- [ ] 有相应的测试用例
- [ ] 所有测试通过 (`pytest`)
- [ ] 代码格式正确 (`black --check`)
- [ ] 通过 lint 检查 (`flake8`)
- [ ] 无类型错误 (`mypy`)
- [ ] 更新了相关文档
- [ ] 提交信息清晰明确

## 🎨 设计指南

### 规则编写

编写新的安全检测规则时：

1. **规则命名**
   - 使用描述性名称
   - 格式：`动作_对象_类型`

2. **模式编写**
   - 使用精确的正则表达式
   - 避免过于宽泛的模式
   - 考虑编码绕过

3. **严重级别**
   - `critical`: 立即威胁（RCE、SQL注入）
   - `high`: 严重威胁（XSS、CSRF）
   - `medium`: 中等威胁（扫描、探测）
   - `low`: 低威胁（信息收集）

示例规则：

```yaml
- name: detect_sql_injection_union
  pattern:
    url: '(union.*select|insert.*into|delete.*from)'
  severity: high
  category: injection
  description: 检测SQL注入攻击尝试
  examples:
    - '/?id=1 union select * from users'
    - '/user?id=1 insert into users'
  mitigation: 使用参数化查询
```

### API 设计

添加新的公共 API 时：

1. 保持向后兼容
2. 使用类型注解
3. 提供完整文档
4. 包含使用示例
5. 考虑错误处理

## 🚀 发布流程

### 版本号规范

我们遵循 [语义化版本](https://semver.org/)：
- `MAJOR.MINOR.PATCH`
- 主版本：不兼容的 API 变更
- 次版本：向后兼容的新功能
- 修订号：向后兼容的问题修复

### 发布步骤

1. 更新版本号
2. 更新 CHANGELOG.md
3. 创建 Git 标签
4. 构建和发布

## 📖 资源

### 学习材料

- [开发指南](DEVELOPMENT.md)
- [API 文档](docs/API_REFERENCE.md)
- [架构文档](docs/ARCHITECTURE.md)

### 获取帮助

- [GitHub Issues](../../issues)
- [GitHub Discussions](../../discussions)
- [项目 Wiki](../../wiki)

## 🌟 贡献者

感谢所有贡献者！

### 成为贡献者

提交您的第一个 PR 后，您的名字将被添加到贡献者列表。

## 📜 行为准则

### 我们的承诺

为了营造开放和友好的环境，我们承诺：
- 尊重不同的观点和经验
- 使用包容性语言
- 建设性地接受反馈
- 关注对社区最有利的事情

### 不可接受的行为

- 使用性化的语言或图像
- 人身攻击或政治攻击
- 公开或私下骚扰
- 未经许可发布他人私人信息

## 🎉 致谢

再次感谢您的贡献！

---

有问题？请查看 [常见问题](FAQ.md) 或创建 [Issue](../../issues)。
