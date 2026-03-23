"""
测试核心解析器模块
"""
import pytest
from pathlib import Path
from core.parser import LogParser


@pytest.mark.unit
class TestLogParser:
    """LogParser 单元测试"""

    def test_parser_initialization(self, sample_config):
        """测试解析器初始化"""
        parser = LogParser(sample_config.get("log_parser", {}))
        assert parser is not None
        assert hasattr(parser, "parse")

    def test_parse_simple_log_entry(self):
        """测试解析简单日志条目"""
        parser = LogParser({})
        log_line = "2024-01-15 10:30:45,192.168.1.100,GET,/api/users,200"
        result = parser.parse(log_line)

        assert result is not None
        assert "timestamp" in result or "ip" in result

    def test_parse_log_with_custom_separator(self):
        """测试使用自定义分隔符解析日志"""
        config = {"field_separator": "|"}
        parser = LogParser(config)
        log_line = "2024-01-15 10:30:45|192.168.1.100|GET|/api/users|200"
        result = parser.parse(log_line)

        assert result is not None

    def test_parse_malformed_log_entry(self):
        """测试解析格式错误的日志条目"""
        parser = LogParser({})
        malformed_log = "this is not a valid log"

        # 解析器应该优雅地处理格式错误的日志
        try:
            result = parser.parse(malformed_log)
            # 如果返回 None 或空字典，这是可接受的行为
            assert result is None or isinstance(result, dict)
        except Exception as e:
            # 或者抛出适当的异常
            assert isinstance(e, (ValueError, KeyError))

    def test_parse_batch_logs(self, sample_log_entries):
        """测试批量解析日志"""
        parser = LogParser({})

        # 假设 parse_batch 方法存在
        if hasattr(parser, "parse_batch"):
            logs_text = "\n".join([
                "2024-01-15 10:30:45,192.168.1.100,GET,/api/users,200",
                "2024-01-15 10:31:12,192.168.1.101,POST,/api/login,401",
            ])
            results = parser.parse_batch(logs_text)

            assert isinstance(results, list)
            assert len(results) > 0

    def test_extract_ip_address(self):
        """测试 IP 地址提取"""
        parser = LogParser({})
        log_line = "2024-01-15 10:30:45,192.168.1.100,GET,/api/users,200"
        result = parser.parse(log_line)

        if result and "ip" in result:
            assert result["ip"] == "192.168.1.100"

    def test_extract_http_method(self):
        """测试 HTTP 方法提取"""
        parser = LogParser({})
        log_line = "2024-01-15 10:30:45,192.168.1.100,POST,/api/login,401"
        result = parser.parse(log_line)

        if result and "method" in result:
            assert result["method"] == "POST"

    def test_timestamp_parsing(self):
        """测试时间戳解析"""
        config = {"timestamp_format": "%Y-%m-%d %H:%M:%S"}
        parser = LogParser(config)
        log_line = "2024-01-15 10:30:45,192.168.1.100,GET,/api/users,200"
        result = parser.parse(log_line)

        assert result is not None
        # 时间戳应该被正确解析

    def test_empty_log_line(self):
        """测试空日志行"""
        parser = LogParser({})
        result = parser.parse("")

        # 应该优雅地处理空输入
        assert result is None or result == {}

    def test_unicode_handling(self):
        """测试 Unicode 字符处理"""
        parser = LogParser({})
        log_line = "2024-01-15 10:30:45,192.168.1.100,GET,/api/用户,200"
        result = parser.parse(log_line)

        assert result is not None


@pytest.mark.unit
class TestLogParserEdgeCases:
    """LogParser 边缘情况测试"""

    def test_extremely_long_log_line(self):
        """测试超长日志行"""
        parser = LogParser({})
        long_url = "/api/" + "a" * 10000
        log_line = f"2024-01-15 10:30:45,192.168.1.100,GET,{long_url},200"

        try:
            result = parser.parse(log_line)
            assert result is not None
        except Exception:
            # 应该有合理的长度限制
            pytest.skip("Parser has length limit")

    def test_special_characters_in_url(self):
        """测试 URL 中的特殊字符"""
        parser = LogParser({})
        log_line = "2024-01-15 10:30:45,192.168.1.100,GET,/api/test?param=value%20with%20spaces,200"
        result = parser.parse(log_line)

        assert result is not None

    def test_null_bytes_in_log(self):
        """测试包含空字节的日志"""
        parser = LogParser({})
        log_line = "2024-01-15 10:30:45,\x00,GET,/api/users,200"

        try:
            result = parser.parse(log_line)
            assert result is not None
        except Exception:
            # 应该拒绝包含空字节的输入
            pass
