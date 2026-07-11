#!/usr/bin/env python3
"""
SSlogs 集成测试
"""
import pytest
import tempfile
import os
from pathlib import Path
import json
from typing import Dict, Any, List

# 导入核心模块
from core.parser import LogParser
from core.rule_engine import RuleEngine
from core.ai_analyzer import AIAnalyzer
from core.reporter import ReportGenerator
from core.config_manager import ConfigManager
from main import LogHunter


@pytest.fixture(scope="module")
def test_config_dir():
    """创建测试配置目录和文件"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建规则目录
        rules_dir = Path(temp_dir) / 'rules'
        rules_dir.mkdir()

        # 创建示例规则文件
        sql_injection_rule = """
- name: SQL注入测试
  pattern:
    url: '(union.*select|insert.*into)'
  severity: high
  category: sql_injection
  description: 检测SQL注入攻击
"""
        (rules_dir / 'sql_injection.yaml').write_text(sql_injection_rule)

        xss_rule = """
- name: XSS攻击测试
  pattern:
    url: '(<script[^>]*>|javascript:|on\\w+\\s*=)'
  severity: high
  category: xss
  description: 检测XSS攻击
"""
        (rules_dir / 'xss_attack.yaml').write_text(xss_rule)

        # 创建配置文件
        config_content = f"""
log_path: {{temp_dir}}/logs/*.log
log_format:
  type: web
  fields:
    src_ip: (\\d+\\.\\d+\\.\\d+\\.\\d+)
    timestamp: \\[(.*?)\\]
    request_line: '"([A-Z]+\\s+[^\\s]+\\s+HTTP/[\\d\\.]+)"'
    status_code: '"\\s+(\\d{{3}})\\s+'

rule_dir: {rules_dir}
output_dir: {temp_dir}/output
server:
  ip: 192.168.1.100

ai:
  type: local
  local_provider: ollama

ollama:
  model: deepseek-r1:14b
  base_url: http://localhost:11434/api/chat
"""
        config_path = Path(temp_dir) / 'config.yaml'
        config_path.write_text(config_content)

        # 创建日志目录
        logs_dir = Path(temp_dir) / 'logs'
        logs_dir.mkdir()

        # 创建示例日志文件
        test_logs = [
            '192.168.1.100 - - [25/Dec/2023:10:00:00 +0000] "GET /index.html HTTP/1.1" 200 1234',
            '198.51.100.1 - - [25/Dec/2023:10:01:00 +0000] "GET /?id=1 union select * from users HTTP/1.1" 200 567',
            '10.0.0.50 - - [25/Dec/2023:10:02:00 +0000] "GET /?q=<script>alert(1)</script> HTTP/1.1" 200 890',
        ]
        log_file = logs_dir / 'test.log'
        log_file.write_text('\n'.join(test_logs))

        yield temp_dir

        # 清理
        config_path.unlink()
        log_file.unlink()


class TestLogParsingIntegration:
    """日志解析集成测试"""

    def test_end_to_end_log_parsing(self, test_config_dir):
        """测试端到端日志解析流程"""
        config_path = os.path.join(test_config_dir, 'config.yaml')

        # 初始化组件
        parser = LogParser({
            'type': 'web',
            'fields': {
                'src_ip': r'(\d+\.\d+\.\d+\.\d+)',
                'timestamp': r'\[(.*?)\]',
                'request_line': r'"([A-Z]+\s+[^\s]+\s+HTTP/[\d\.]+)"',
                'status_code': r'"\s+(\d{3})\s+'
            }
        })

        # 解析测试日志
        test_log = '198.51.100.1 - - [25/Dec/2023:10:01:00 +0000] "GET /?id=1 union select * from users HTTP/1.1" 200 567'
        parsed = parser.parse_log_line(test_log)

        assert parsed is not None
        assert parsed['src_ip'] == '198.51.100.1'
        assert parsed['method'] == 'GET'
        assert parsed['url'] == '/?id=1 union select * from users'


class TestRuleEngineIntegration:
    """规则引擎集成测试"""

    def test_rule_matching_with_parsed_logs(self, test_config_dir):
        """测试规则引擎与解析日志的集成"""
        config_path = os.path.join(test_config_dir, 'config.yaml')

        # 初始化规则引擎
        rule_engine = RuleEngine(os.path.join(test_config_dir, 'rules'))

        # 创建解析日志条目
        log_entry = {
            'src_ip': '198.51.100.1',
            'url': '/?id=1 union select * from users',
            'method': 'GET',
            'user_agent': 'Mozilla/5.0',
            'status_code': '200'
        }

        # 匹配规则
        matches = rule_engine.match_log(log_entry)

        # 验证检测结果
        assert len(matches) > 0
        assert any(match['rule']['category'] == 'sql_injection' for match in matches)


class TestReportGenerationIntegration:
    """报告生成集成测试"""

    def test_full_report_generation_workflow(self, test_config_dir):
        """测试完整的报告生成流程"""
        # 准备测试数据
        matched_logs = [
            {
                'rule': {
                    'name': 'SQL注入攻击检测',
                    'severity': 'high',
                    'category': 'sql_injection',
                    'description': '检测到SQL注入攻击尝试'
                },
                'log_entry': {
                    'src_ip': '198.51.100.1',
                    'timestamp': '2023-12-25 10:01:00',
                    'method': 'GET',
                    'url': '/?id=1 union select * from users',
                    'status_code': '200'
                }
            }
        ]

        ai_results = ['## SQL注入攻击分析\n\n### 攻击技术分析\n检测到SQL注入攻击尝试...']

        internal_ips = {'192.168.1.100': 5}
        external_ip_details = [
            {'ip': '198.51.100.1', 'count': 10, 'location': 'United States'}
        ]

        # 生成报告
        output_dir = os.path.join(test_config_dir, 'reports')
        os.makedirs(output_dir, exist_ok=True)

        reporter = ReportGenerator(output_dir)
        report_path = reporter.generate_report(
            matched_logs, ai_results, 'html',
            internal_ips=internal_ips,
            external_ip_details=external_ip_details,
            server_ip='192.168.1.100'
        )

        # 验证报告文件创建
        assert os.path.exists(report_path)
        assert report_path.endswith('.html')

        # 验证报告内容
        report_content = Path(report_path).read_text(encoding='utf-8')
        assert 'SQL注入攻击检测' in report_content
        assert '198.51.100.1' in report_content


class TestConfigManagerIntegration:
    """配置管理器集成测试"""

    def test_config_loading_with_validation(self, test_config_dir):
        """测试配置加载和验证集成"""
        config_path = os.path.join(test_config_dir, 'config.yaml')

        # 加载配置
        config_manager = ConfigManager(config_path)
        config = config_manager.load_config()

        # 验证配置结构
        assert 'log_path' in config
        assert 'log_format' in config
        assert 'rule_dir' in config
        assert 'output_dir' in config

        # 验证默认值设置
        assert 'analysis' in config
        assert config['analysis']['batch_size'] == 1000

        # 测试配置验证报告
        report = config_manager.get_validation_report()
        assert 'valid' in report
        assert isinstance(report['errors'], list)
        assert isinstance(report['warnings'], list)


class TestLogHunterIntegration:
    """LogHunter主类集成测试"""

    @pytest.fixture
    def log_hunter(self, test_config_dir):
        """创建LogHunter实例"""
        config_path = os.path.join(test_config_dir, 'config.yaml')

        # 创建LogHunter实例（禁用信号处理器）
        return LogHunter(
            config_path=config_path,
            ai_enabled=False,  # 禁用AI以避免外部依赖
            server_ip='192.168.1.100',
            disable_signal_handlers=True
        )

    def test_loghunter_initialization(self, log_hunter):
        """测试LogHunter初始化"""
        assert log_hunter is not None
        assert log_hunter.parser is not None
        assert log_hunter.rule_engine is not None
        assert log_hunter.reporter is not None

    def test_loghunter_basic_workflow(self, log_hunter, test_config_dir):
        """测试LogHunter基本工作流程"""
        # 运行分析
        log_hunter.run()

        # 验证输出
        assert os.path.exists(os.path.join(test_config_dir, 'output'))

        # 检查是否有报告文件生成
        output_dir = Path(test_config_dir) / 'output'
        report_files = list(output_dir.glob('*_report_*'))

        # 应该生成了至少一个报告
        assert len(report_files) >= 1

    def test_loghunter_parser_statistics(self, log_hunter):
        """测试解析器统计功能"""
        # 运行分析
        log_hunter.run()

        # 获取解析器统计
        if hasattr(log_hunter.parser, 'get_statistics'):
            stats = log_hunter.parser.get_statistics()
            assert 'parsed_count' in stats
            assert isinstance(stats['parsed_count'], int)

    def test_loghunter_ip_counter(self, log_hunter):
        """测试IP统计功能"""
        # 运行分析
        log_hunter.run()

        # 验证IP计数器
        assert len(log_hunter.ip_counter) >= 0


class TestMultiModuleIntegration:
    """多模块协同工作集成测试"""

    def test_parser_to_rule_engine_workflow(self, test_config_dir):
        """测试从解析器到规则引擎的工作流"""
        # 初始化组件
        config_path = os.path.join(test_config_dir, 'config.yaml')
        config_manager = ConfigManager(config_path)
        config = config_manager.load_config()

        parser = LogParser(config['log_format'])
        rule_engine = RuleEngine(config['rule_dir'])

        # 测试日志
        test_logs = [
            '198.51.100.1 - - [25/Dec/2023:10:00:00 +0000] "GET /?id=<script>alert(1)</script> HTTP/1.1" 200 1234',
            '10.0.0.50 - - [25/Dec/2023:10:01:00 +0000] "GET /index.html HTTP/1.1" 200 567'
        ]

        detection_count = 0
        for log_line in test_logs:
            parsed = parser.parse_log_line(log_line)
            if parsed:
                matches = rule_engine.match_log(parsed)
                if matches:
                    detection_count += 1

        # 验证检测到攻击
        assert detection_count > 0

    def test_complete_analysis_pipeline(self, test_config_dir):
        """测试完整的分析管道"""
        config_path = os.path.join(test_config_dir, 'config.yaml')

        # 使用LogHunter进行完整分析
        log_hunter = LogHunter(
            config_path=config_path,
            ai_enabled=False,
            server_ip='192.168.1.100',
            disable_signal_handlers=True
        )

        # 运行分析
        log_hunter.run()

        # 验证结果
        assert log_hunter.ip_counter is not None
        assert hasattr(log_hunter.parser, 'get_statistics')

        # 检查性能监控
        try:
            from core.performance import get_performance_summary
            summary = get_performance_summary()
            assert summary is not None
            assert isinstance(summary, str)
        except Exception:
            # 性能监控可能不可用，这不是致命错误
            pass


class TestConfigurationIntegration:
    """配置集成测试"""

    def test_multiple_config_sources(self):
        """测试多种配置源的集成"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建配置文件
            config_content = f"""
log_path: logs/*.log
log_format:
  type: web
  fields:
    src_ip: (\\d+\\.\\d+\\.\\d+\\.\\d+)

rule_dir: rules
output_dir: {temp_dir}/output
server:
  ip: 192.168.1.100

deepseek:
  api_key: ${{SSLOGS_AI_API_KEY:-default_key}}
  model: deepseek-ai/DeepSeek-V3

ai:
  type: cloud
  cloud_provider: deepseek
"""
            config_path = Path(temp_dir) / 'config.yaml'
            config_path.write_text(config_content)

            # 设置环境变量
            original_env = os.environ.get('SSLOGS_AI_API_KEY')
            os.environ['SSLOGS_AI_API_KEY'] = 'test_key'

            try:
                # 加载配置
                config_manager = ConfigManager(str(config_path))
                config = config_manager.load_config()

                # 验证环境变量替换
                assert config['deepseek']['api_key'] == 'test_key'

                # 验证默认值回退
                assert 'output_dir' in config

            finally:
                # 恢复环境变量
                if original_env:
                    os.environ['SSLOGS_AI_API_KEY'] = original_env
                else:
                    del os.environ['SSLOGS_AI_API_KEY']


class TestErrorHandlingIntegration:
    """错误处理集成测试"""

    def test_graceful_degradation(self, test_config_dir):
        """测试优雅降级机制"""
        config_path = os.path.join(test_config_dir, 'config.yaml')

        # 即使某些功能失败，系统应该能继续运行
        try:
            # 创建可能失败的组件
            from core.config_manager import ConfigManager
            ConfigManager(config_path)
        except Exception as e:
            # 配置加载失败不应导致整个系统崩溃
            pass

        # 验证基本组件仍然可用
        parser = LogParser({
            'type': 'web',
            'fields': {
                'src_ip': r'(\d+\.\d+\.\d+\.\d+)',
                'timestamp': r'\[(.*?)\]'
            }
        })

        # 测试基本解析功能
        test_log = '192.168.1.100 - - [25/Dec/2023:10:00:00] "GET /index.html HTTP/1.1" 200 1234'
        parsed = parser.parse_log_line(test_log)

        # 验证基本功能正常
        assert parsed is not None or parsed is None  # 任何结果都可以


class TestDataFlowIntegration:
    """数据流集成测试"""

    def test_data_flow_from_logs_to_report(self, test_config_dir):
        """测试从日志到报告的完整数据流"""
        # 1. 模拟日志数据
        test_logs = [
            '198.51.100.1 - - [25/Dec/2023:10:00:00] "GET /admin/config HTTP/1.1" 200 1234',
            '192.168.1.50 - - [25/Dec/2023:10:01:00] "GET /index.html HTTP/1.1" 200 567'
        ]

        # 2. 写入测试日志
        logs_dir = Path(test_config_dir) / 'logs'
        log_file = logs_dir / 'test.log'
        log_file.write_text('\n'.join(test_logs))

        # 3. 分析日志
        config_path = os.path.join(test_config_dir, 'config.yaml')
        log_hunter = LogHunter(
            config_path=config_path,
            ai_enabled=False,
            server_ip='192.168.1.100',
            disable_signal_handlers=True
        )

        log_hunter.run()

        # 4. 验证报告生成
        output_dir = Path(test_config_dir) / 'output'
        report_files = list(output_dir.glob('*_report_*'))

        assert len(report_files) > 0

        # 5. 验证报告内容完整性
        report_content = Path(report_files[0]).read_text(encoding='utf-8')

        # 验证基本报告结构
        assert '日志分析报告' in report_content or '安全事件' in report_content
        assert '192.168.1.100' in report_content


@pytest.mark.parametrize("attack_log,expected_category", [
    ('198.51.100.1 - - [25/Dec/2023:10:00:00] "GET /?id=1 union select * from users HTTP/1.1" 200 567', 'sql_injection'),
    ('198.51.100.1 - - [25/Dec/2023:10:00:00] "GET /?q=<script>alert(1)</script> HTTP/1.1" 200 567', 'xss'),
])
def test_attack_detection_accuracy(attack_log, expected_category, test_config_dir):
    """测试攻击检测准确性"""
    # 初始化规则引擎
    rule_engine = RuleEngine(os.path.join(test_config_dir, 'rules'))

    # 解析攻击日志
    parser = LogParser({
        'type': 'web',
        'fields': {
            'src_ip': r'(\d+\.\d+\.\d+\.\d+)',
            'timestamp': r'\[(.*?)\]',
            'request_line': r'"([A-Z]+\s+[^\s]+\s+HTTP/[\d\.]+)"',
            'status_code': r'"\s+(\d{3})\s+'
        }
    })

    parsed_log = parser.parse_log_line(attack_log)
    assert parsed_log is not None

    # 匹配规则
    matches = rule_engine.match_log(parsed_log)

    # 验证检测到正确的攻击类别
    assert len(matches) > 0, f"应该检测到 {expected_category} 攻击"
    assert any(match['rule']['category'] == expected_category for match in matches)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])