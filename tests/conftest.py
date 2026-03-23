"""
pytest 配置文件 - 定义共享的 fixtures 和测试工具
"""
import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Generator, Dict, Any

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def project_root_path() -> Path:
    """项目根目录路径"""
    return project_root


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """测试数据目录"""
    return project_root / "tests" / "test_data"


@pytest.fixture(scope="session")
def test_output_dir() -> Path:
    """测试输出目录"""
    output_dir = project_root / "tests" / "test_output"
    output_dir.mkdir(exist_ok=True)
    return output_dir


@pytest.fixture(scope="function")
def temp_dir() -> Generator[Path, None, None]:
    """临时目录 fixture，测试后自动清理"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    # 清理临时目录
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture(scope="session")
def sample_config() -> Dict[str, Any]:
    """示例配置"""
    return {
        "log_parser": {
            "timestamp_format": "%Y-%m-%d %H:%M:%S",
            "field_separator": ",",
        },
        "rule_engine": {
            "rules_dir": "rules",
            "threat_threshold": 7.0,
        },
        "ai_analyzer": {
            "enabled": True,
            "provider": "deepseek",
            "api_timeout": 30,
        },
        "performance": {
            "batch_size": 100,
            "max_workers": 4,
        },
    }


@pytest.fixture(scope="function")
def sample_log_entries() -> list:
    """示例日志条目"""
    return [
        {
            "timestamp": "2024-01-15 10:30:45",
            "ip": "192.168.1.100",
            "method": "GET",
            "url": "/api/users",
            "status": 200,
            "user_agent": "Mozilla/5.0",
        },
        {
            "timestamp": "2024-01-15 10:31:12",
            "ip": "192.168.1.101",
            "method": "POST",
            "url": "/api/login",
            "status": 401,
            "user_agent": "curl/7.68.0",
        },
        {
            "timestamp": "2024-01-15 10:32:33",
            "ip": "192.168.1.102",
            "method": "GET",
            "url": "/admin/config",
            "status": 403,
            "user_agent": "Python/3.9",
        },
    ]


@pytest.fixture(scope="function")
def sample_malicious_log_entries() -> list:
    """示例恶意日志条目（用于安全测试）"""
    return [
        {
            "timestamp": "2024-01-15 10:30:45",
            "ip": "192.168.1.100",
            "method": "POST",
            "url": "/api/users?id=1' OR '1'='1",
            "status": 500,
            "user_agent": "sqlmap/1.6",
        },
        {
            "timestamp": "2024-01-15 10:31:12",
            "ip": "192.168.1.101",
            "method": "GET",
            "url": "/search?q=<script>alert('XSS')</script>",
            "status": 200,
            "user_agent": "Mozilla/5.0",
        },
        {
            "timestamp": "2024-01-15 10:32:33",
            "ip": "192.168.1.102",
            "method": "GET",
            "url": "/../../etc/passwd",
            "status": 403,
            "user_agent": "curl/7.68.0",
        },
    ]


@pytest.fixture(scope="session")
def mock_ai_response() -> Dict[str, Any]:
    """模拟 AI 响应"""
    return {
        "threat_level": "high",
        "confidence": 0.85,
        "analysis": "检测到潜在的 SQL 注入攻击",
        "recommendation": "建议立即封禁该 IP 地址",
        "attack_type": "sql_injection",
    }


@pytest.fixture(scope="function")
def config_file(temp_dir: Path, sample_config: Dict[str, Any]) -> Path:
    """创建临时配置文件"""
    import yaml

    config_path = temp_dir / "config.yaml"
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(sample_config, f, allow_unicode=True)
    return config_path


@pytest.fixture(scope="function")
def sample_log_file(temp_dir: Path, sample_log_entries: list) -> Path:
    """创建临时日志文件"""
    import csv

    log_path = temp_dir / "test.log"
    with open(log_path, "w", newline="", encoding="utf-8") as f:
        if sample_log_entries:
            writer = csv.DictWriter(f, fieldnames=sample_log_entries[0].keys())
            writer.writeheader()
            writer.writerows(sample_log_entries)
    return log_path


# 跳过某些测试的条件
def pytest_configure(config):
    """pytest 配置钩子"""
    config.addinivalue_line(
        "markers", "slow: 标记为慢速测试（使用 -m 'not slow' 跳过）"
    )
    config.addinivalue_line(
        "markers", "integration: 标记为集成测试"
    )
    config.addinivalue_line(
        "markers", "ai: 标记为需要 AI 服务的测试"
    )


@pytest.fixture(scope="session")
def is_ci() -> bool:
    """检测是否在 CI 环境中运行"""
    return os.getenv("CI", "false").lower() == "true"


@pytest.fixture(scope="session")
def skip_slow_tests(is_ci: bool) -> bool:
    """CI 环境中跳过慢速测试"""
    return is_ci


@pytest.fixture(scope="function")
def mock_logger(temp_dir: Path) -> Any:
    """创建模拟日志记录器"""
    import logging
    from pathlib import Path

    log_path = temp_dir / "test.log"
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.DEBUG)

    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    yield logger

    logger.removeHandler(handler)
    handler.close()
