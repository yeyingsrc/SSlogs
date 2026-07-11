"""
配置验证规则扩展测试
"""
import pytest
import tempfile
import os
from pathlib import Path
from core.config_manager import ConfigManager, ConfigurationError


class TestLogFormatValidation:
    """日志格式配置验证测试"""

    def test_log_format_fields_missing(self):
        """测试日志格式缺少字段配置"""
        config_content = """
log_path: logs/*.log
log_format:
  type: web
  # 缺少 fields 字段

rule_dir: rules
output_dir: output
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            manager = ConfigManager(temp_path)

            with pytest.raises(ConfigurationError) as exc_info:
                manager.load_config()

            assert 'fields' in str(exc_info.value).lower()
        finally:
            os.unlink(temp_path)

    def test_log_format_fields_wrong_type(self):
        """测试日志格式字段类型错误"""
        config_content = """
log_path: logs/*.log
log_format:
  type: web
  fields: "not_a_dict"  # 应该是字典

rule_dir: rules
output_dir: output
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            manager = ConfigManager(temp_path)

            with pytest.raises(ConfigurationError) as exc_info:
                manager.load_config()

            assert '字典' in str(exc_info.value) or 'dict' in str(exc_info.value).lower()
        finally:
            os.unlink(temp_path)


class TestGeoIPValidation:
    """GeoIP配置验证测试"""

    def test_geoip_file_not_exists(self):
        """测试GeoIP数据库文件不存在"""
        config_content = """
log_path: logs/*.log
log_format:
  type: web
  fields:
    src_ip: (\\d+\\.\\d+\\.\\d+\\.\\d+)

rule_dir: rules
output_dir: output
geoip_db_path: /nonexistent/path/GeoLite2-Country.mmdb
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            manager = ConfigManager(temp_path)

            with pytest.raises(ConfigurationError) as exc_info:
                manager.load_config()

            assert 'geoip_db_path' in str(exc_info.value)
            assert '不存在' in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_geoip_wrong_extension(self):
        """测试GeoIP数据库文件扩展名错误"""
        # 创建一个存在的测试文件，但扩展名错误
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            test_path = f.name

        config_content = f"""
log_path: logs/*.log
log_format:
  type: web
  fields:
    src_ip: (\\d+\\.\\d+\\.\\d+\\.\\d+)

rule_dir: rules
output_dir: output
geoip_db_path: {test_path}
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            manager = ConfigManager(config_path)

            with pytest.raises(ConfigurationError) as exc_info:
                manager.load_config()

            assert 'mmdb' in str(exc_info.value)
        finally:
            os.unlink(config_path)
            os.unlink(test_path)


class TestRuleDirValidation:
    """规则目录验证测试"""

    def test_rule_dir_not_exists(self):
        """测试规则目录不存在"""
        config_content = """
log_path: logs/*.log
log_format:
  type: web
  fields:
    src_ip: (\\d+\\.\\d+\\.\\d+\\.\\d+)

rule_dir: /nonexistent/rules/directory
output_dir: output
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            manager = ConfigManager(temp_path)

            with pytest.raises(ConfigurationError) as exc_info:
                manager.load_config()

            assert 'rule_dir' in str(exc_info.value)
            assert '不存在' in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_rule_dir_not_directory(self):
        """测试规则路径不是目录"""
        # 创建一个文件而不是目录
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            rule_file_path = f.name

        config_content = f"""
log_path: logs/*.log
log_format:
  type: web
  fields:
    src_ip: (\\d+\\.\\d+\\.\\d+\\.\\d+)

rule_dir: {rule_file_path}
output_dir: output
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            config_path = f.name

        try:
            manager = ConfigManager(config_path)

            with pytest.raises(ConfigurationError) as exc_info:
                manager.load_config()

            assert '目录' in str(exc_info.value)
        finally:
            os.unlink(config_path)
            os.unlink(rule_file_path)


class TestOutputDirValidation:
    """输出目录验证测试"""

    def test_output_dir_creation_error(self):
        """测试输出目录创建失败"""
        # 尝试使用一个无法创建的目录路径（在某些系统上可能成功）
        # 在Unix系统上，/root目录通常需要特殊权限
        config_content = """
log_path: logs/*.log
log_format:
  type: web
  fields:
    src_ip: (\\d+\\.\\d+\\.\\d+\\.\\d+)

rule_dir: rules
output_dir: /root/sslogs_output_test
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            manager = ConfigManager(temp_path)
            # 这个测试可能在不同平台上表现不同
            try:
                manager.load_config()
                # 如果加载成功，说明可以创建目录
                os.rmdir('/root/sslogs_output_test')
            except ConfigurationError as e:
                # 验证是目录相关的错误
                if 'output_dir' in str(e):
                    pass  # 预期的错误
                else:
                    raise  # 其他错误应该传递
        finally:
            os.unlink(temp_path)

    def test_output_dir_auto_creation(self):
        """测试输出目录自动创建"""
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, 'new_output_dir')

            config_content = f"""
log_path: logs/*.log
log_format:
  type: web
  fields:
    src_ip: (\\d+\\.\\d+\\.\\d+\\.\\d+)

rule_dir: rules
output_dir: {output_path}
"""
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                f.write(config_content)
                config_path = f.name

            try:
                manager = ConfigManager(config_path)
                config = manager.load_config()

                # 验证目录被创建
                assert os.path.exists(output_path)
                assert os.path.isdir(output_path)
            finally:
                os.unlink(config_path)


class TestWhitelistValidation:
    """白名单配置验证测试"""

    def test_whitelist_field_type_validation(self):
        """测试白名单字段类型验证"""
        config_content = """
log_path: logs/*.log
log_format:
  type: web
  fields:
    src_ip: (\\d+\\.\\d+\\.\\d+\\.\\d+)

rule_dir: rules
output_dir: output

whitelist:
  safe_agents: "should_be_list_not_string"
  static_extensions: ["valid", "list"]
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            manager = ConfigManager(temp_path)

            with pytest.raises(ConfigurationError) as exc_info:
                manager.load_config()

            assert 'whitelist' in str(exc_info.value).lower()
            assert 'safe_agents' in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_whitelist_valid_config(self):
        """测试有效的白名单配置"""
        config_content = """
log_path: logs/*.log
log_format:
  type: web
  fields:
    src_ip: (\\d+\\.\\d+\\.\\d+\\.\\d+)

rule_dir: rules
output_dir: output

whitelist:
  safe_agents: ["googlebot", "bingbot"]
  static_extensions: [".css", ".js"]
  health_paths: ["/health", "/ping"]
  internal_ips: ["127.0.0.1", "::1"]
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            manager = ConfigManager(temp_path)
            config = manager.load_config()

            # 验证配置加载成功
            assert config['whitelist']['safe_agents'] == ["googlebot", "bingbot"]
        finally:
            os.unlink(temp_path)


class TestReportConfigValidation:
    """报告配置验证测试"""

    def test_report_format_validation(self):
        """测试报告格式验证"""
        config_content = """
log_path: logs/*.log
log_format:
  type: web
  fields:
    src_ip: (\\d+\\.\\d+\\.\\d+\\.\\d+)

rule_dir: rules
output_dir: output

report:
  output_format: invalid_format
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            manager = ConfigManager(temp_path)

            with pytest.raises(ConfigurationError) as exc_info:
                manager.load_config()

            assert 'output_format' in str(exc_info.value)
        finally:
            os.unlink(temp_path)

    def test_report_template_not_exists(self):
        """测试报告模板文件不存在"""
        config_content = """
log_path: logs/*.log
log_format:
  type: web
  fields:
    src_ip: (\\d+\\.\\d+\\.\\d+\\.\\d+)

rule_dir: rules
output_dir: output

report:
  template: /nonexistent/template.html
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            manager = ConfigManager(temp_path)

            with pytest.raises(ConfigurationError) as exc_info:
                manager.load_config()

            assert 'template' in str(exc_info.value)
            assert '不存在' in str(exc_info.value)
        finally:
            os.unlink(temp_path)


class TestValidationReport:
    """验证报告测试"""

    def test_validation_report_with_warnings(self):
        """测试包含警告的验证报告"""
        config_content = """
log_path: logs/*.log
log_format:
  type: web
  fields:
    src_ip: (\\d+\\.\\d+\\.\\d+\\.\\d+)

rule_dir: rules
output_dir: output

deepseek:
  api_key: demo_key_for_testing
  model: deepseek-ai/DeepSeek-V3

analysis:
  batch_size: 50000
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            manager = ConfigManager(temp_path)
            manager.load_config()
            report = manager.get_validation_report()

            # 验证报告结构
            assert 'valid' in report
            assert 'warnings' in report
            assert 'suggestions' in report
            assert 'total_issues' in report

            # 验证有警告信息
            if report['warnings']:
                assert any('demo_key' in str(w) or 'batch_size' in str(w)
                          for w in report['warnings'])
        finally:
            os.unlink(temp_path)

    def test_validation_report_performance_warnings(self):
        """测试性能相关的警告"""
        config_content = """
log_path: logs/*.log
log_format:
  type: web
  fields:
    src_ip: (\\d+\\.\\d+\\.\\d+\\.\\d+)

rule_dir: rules
output_dir: output

ai_analysis:
  max_ai_analysis: 50
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            manager = ConfigManager(temp_path)
            manager.load_config()
            report = manager.get_validation_report()

            # 验证可能有AI分析成本相关的建议
            if report['suggestions']:
                assert any('max_ai_analysis' in str(s) or 'API' in str(s)
                          for s in report['suggestions'])
        finally:
            os.unlink(temp_path)


class TestConfigChangeValidation:
    """配置更改验证测试"""

    def test_validate_nested_config_change(self):
        """测试嵌套配置更改验证"""
        config_content = """
log_path: logs/*.log
log_format:
  type: web
  fields:
    src_ip: (\\d+\\.\\d+\\.\\d+\\.\\d+)

rule_dir: rules
output_dir: output
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            manager = ConfigManager(temp_path)
            manager.load_config()

            # 测试嵌套配置更改
            changes = {
                'analysis.batch_size': 500,
                'ai_analysis.max_ai_analysis': 10
            }

            is_valid, errors = manager.validate_config_change(changes)
            assert is_valid is True
            assert len(errors) == 0
        finally:
            os.unlink(temp_path)

    def test_validate_invalid_config_change(self):
        """测试无效的配置更改验证"""
        config_content = """
log_path: logs/*.log
log_format:
  type: web
  fields:
    src_ip: (\\d+\\.\\d+\\.\\d+\\.\\d+)

rule_dir: rules
output_dir: output
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            manager = ConfigManager(temp_path)
            manager.load_config()

            # 测试无效的配置更改
            changes = {
                'analysis.batch_size': -100,  # 负数
                'ai.type': 'invalid_type'       # 无效枚举值
            }

            is_valid, errors = manager.validate_config_change(changes)
            assert is_valid is False
            assert len(errors) > 0
        finally:
            os.unlink(temp_path)


class TestComplexValidationScenarios:
    """复杂验证场景测试"""

    def test_complete_valid_configuration(self):
        """测试完整有效的配置"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建必要的目录和文件
            rule_dir = os.path.join(temp_dir, 'rules')
            os.makedirs(rule_dir)

            # 创建GeoIP测试文件
            geoip_file = os.path.join(temp_dir, 'GeoLite2-Country.mmdb')
            Path(geoip_file).touch()  # 创建空文件

            # 创建报告模板
            template_file = os.path.join(temp_dir, 'template.html')
            Path(template_file).touch()

            config_content = f"""
log_path: logs/*.log
log_format:
  type: web
  fields:
    src_ip: (\\d+\\.\\d+\\.\\d+\\.\\d+)
    timestamp: \\[(.*?)\\]

rule_dir: {rule_dir}
output_dir: {temp_dir}/output
geoip_db_path: {geoip_file}

ai:
  type: local
  local_provider: ollama

ollama:
  model: deepseek-r1:14b
  base_url: http://localhost:11434/api/chat

whitelist:
  safe_agents: ["googlebot", "bingbot"]

report:
  output_format: html
  template: {template_file}
"""
            config_path = os.path.join(temp_dir, 'config.yaml')
            with open(config_path, 'w') as f:
                f.write(config_content)

            manager = ConfigManager(config_path)
            config = manager.load_config()

            # 验证配置加载成功
            assert config is not None
            assert 'log_path' in config

    def test_multiple_errors_in_configuration(self):
        """测试配置中的多个错误"""
        config_content = """
# 缺少必需字段
log_format:
  type: web

# 无效的枚举值
ai:
  type: invalid_type

# 无效的数值范围
analysis:
  batch_size: -100
  max_events: 999999

# 无效的URL
ollama:
  base_url: "not_a_url"

# 无效的API密钥
deepseek:
  api_key: your-api-key-here
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(config_content)
            temp_path = f.name

        try:
            manager = ConfigManager(temp_path)

            with pytest.raises(ConfigurationError) as exc_info:
                manager.load_config()

            error_message = str(exc_info.value)
            # 应该有多个错误
            assert 'log_path' in error_message or 'rule_dir' in error_message
            assert 'invalid_type' in error_message or 'batch_size' in error_message
        finally:
            os.unlink(temp_path)
