import re
import json
import codecs
import logging
import hashlib
from urllib.parse import urlparse, parse_qs
from typing import Dict, Optional, List
from functools import lru_cache

logger = logging.getLogger(__name__)

class LogValidationError(Exception):
    """日志验证错误"""
    pass

class LogParser:
    # 安全配置
    MAX_LINE_LENGTH = 10000  # 最大日志行长度
    MAX_FIELD_VALUE_LENGTH = 1000  # 字段最大值长度
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # XSS
        r'javascript:',  # JavaScript协议
        r'on\w+\s*=',  # 事件处理器
        r'expression\s*\(',  # CSS表达式
    ]

    def __init__(self, log_format_config):
        self.log_format_config = log_format_config
        self.fields = log_format_config.get('fields', {})

        # 支持两种配置格式：字典和列表
        if isinstance(self.fields, dict):
            # 新格式：字典形式
            self.field_names = list(self.fields.keys())
            self.field_patterns = list(self.fields.values())
        else:
            # 旧格式：列表形式
            self.field_names = [field['name'] for field in self.fields]
            self.field_patterns = [field['regex'] for field in self.fields]

        # 正则表达式缓存
        self._regex_cache = {}
        self._field_pattern_cache = {}

        # 预编译危险模式检测
        self.dangerous_regexes = [re.compile(pattern, re.IGNORECASE) for pattern in self.DANGEROUS_PATTERNS]

        self.regex_pattern = self._build_regex_pattern()
        self.regex = re.compile(self.regex_pattern)

        # 统计信息
        self.parsed_count = 0
        self.failed_count = 0
        self.blocked_count = 0
        self.cache_hits = 0
        self.cache_misses = 0

    def _build_regex_pattern(self) -> str:
        """基于字段定义构建完整的正则表达式模式"""
        if not self.field_patterns:
            raise ValueError("日志格式配置中未定义字段")
        
        # 拼接所有字段的正则表达式
        regex_parts = []
        for pattern in self.field_patterns:
            # 确保模式有捕获组
            if '(' not in pattern:
                pattern = f'({pattern})'
            regex_parts.append(pattern)
        
        # 组合成完整的正则表达式，添加适当的分隔符
        full_pattern = '\\s*'.join(regex_parts)
        return '^' + full_pattern + '\\s*$'

    def validate_log_input(self, line: str) -> bool:
        """验证日志输入的安全性"""
        if not line or not isinstance(line, str):
            return False

        # 长度检查
        if len(line) > self.MAX_LINE_LENGTH:
            self.blocked_count += 1
            logger.warning(f"日志行过长被拒绝: {len(line)} 字符")
            return False

        # 危险内容检查
        for dangerous_regex in self.dangerous_regexes:
            if dangerous_regex.search(line):
                self.blocked_count += 1
                logger.warning(f"检测到危险内容被拒绝: {dangerous_regex.pattern}")
                return False

        # 基本格式检查（至少包含基本的时间戳和IP）
        if not re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', line):
            # 如果没有IP地址，至少应该有日期时间模式
            if not re.search(r'\d{4}-\d{2}-\d{2}|\d{2}/\w{3}/\d{4}', line):
                self.blocked_count += 1
                logger.debug("日志格式无效被拒绝")
                return False

        return True

    def sanitize_field_value(self, value: str) -> str:
        """清理字段值，移除潜在危险内容"""
        if not value:
            return ''

        # 长度限制
        if len(value) > self.MAX_FIELD_VALUE_LENGTH:
            value = value[:self.MAX_FIELD_VALUE_LENGTH] + '...[截断]'

        # 移除HTML标签
        value = re.sub(r'<[^>]+>', '', value)

        # 转义特殊字符
        value = value.replace('<', '&lt;').replace('>', '&gt;')

        return value.strip()

    def parse_log_line(self, line: str) -> Optional[Dict[str, str]]:
        """解析单条日志行并返回字典格式数据"""
        try:
            # 输入验证
            if not self.validate_log_input(line):
                return None

            match = self.regex.match(line)
            if not match:
                # 如果完整模式匹配失败，尝试逐个匹配字段
                return self._partial_parse(line)

            # 提取匹配组并映射到字段名
            result = {}
            groups = match.groups()

            for i, field_name in enumerate(self.field_names):
                if i < len(groups):
                    value = groups[i] if groups[i] is not None else ''
                    # 清理和验证字段值
                    result[field_name] = self.sanitize_field_value(value)

            # 特殊处理：从request_line或类似字段提取HTTP信息
            self._extract_http_info(result)

            # 解析JSON数据字段（如果存在）
            self._parse_json_fields(result)

            # 验证解析结果
            if not self._validate_parsed_result(result):
                self.failed_count += 1
                return None

            self.parsed_count += 1
            logger.debug(f"解析结果: {result}")
            return result

        except LogValidationError as e:
            logger.warning(f"日志验证失败: {e}")
            self.failed_count += 1
            return None
        except Exception as e:
            logger.error(f"日志行解析失败: {e}")
            self.failed_count += 1
            return None

    def _validate_parsed_result(self, result: Dict[str, str]) -> bool:
        """验证解析结果的基本完整性"""
        if not result:
            return False

        # 检查关键字段是否存在
        required_fields = ['src_ip']  # 至少需要IP地址
        for field in required_fields:
            if field not in result or not result[field]:
                logger.debug(f"缺少必需字段: {field}")
                return False

        # IP地址格式验证
        ip = result.get('src_ip', '')
        if not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
            logger.debug(f"无效的IP地址格式: {ip}")
            return False

        # 检查IP地址范围是否合理
        try:
            octets = list(map(int, ip.split('.')))
            if not all(0 <= octet <= 255 for octet in octets):
                logger.debug(f"IP地址超出有效范围: {ip}")
                return False
        except ValueError:
            logger.debug(f"IP地址格式错误: {ip}")
            return False

        return True

    def get_statistics(self) -> Dict[str, int]:
        """获取解析统计信息"""
        return {
            'parsed_count': self.parsed_count,
            'failed_count': self.failed_count,
            'blocked_count': self.blocked_count,
            'total_processed': self.parsed_count + self.failed_count + self.blocked_count
        }

    @lru_cache(maxsize=128)
    def _compile_field_pattern(self, pattern: str) -> re.Pattern:
        """缓存编译后的字段正则表达式"""
        # 确保模式有捕获组
        if '(' not in pattern:
            pattern = f'({pattern})'
        return re.compile(pattern)

    def _partial_parse(self, line: str) -> Optional[Dict[str, str]]:
        """部分解析：逐个匹配字段"""
        result = {}
        remaining_line = line

        # 使用缓存的编译正则表达式
        for field_name, pattern in zip(self.field_names, self.field_patterns):
            try:
                # 尝试从缓存获取编译后的正则表达式
                if pattern in self._field_pattern_cache:
                    compiled_pattern = self._field_pattern_cache[pattern]
                    self.cache_hits += 1
                else:
                    compiled_pattern = self._compile_field_pattern(pattern)
                    self._field_pattern_cache[pattern] = compiled_pattern
                    self.cache_misses += 1

                match = compiled_pattern.search(remaining_line)
                if match:
                    result[field_name] = self.sanitize_field_value(match.group(1))
                    # 移除已匹配的部分
                    remaining_line = remaining_line[match.end():]
                else:
                    result[field_name] = ''
            except Exception as e:
                logger.warning(f"字段 {field_name} 解析失败: {e}")
                result[field_name] = ''

        # 如果没有匹配到任何字段，返回None
        return result if any(result.values()) else None

    def get_cache_statistics(self) -> Dict[str, int]:
        """获取缓存统计信息"""
        return {
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_size': len(self._field_pattern_cache),
            'hit_rate': self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0
        }

    def clear_cache(self):
        """清理缓存"""
        self._field_pattern_cache.clear()
        self._compile_field_pattern.cache_clear()
        self.cache_hits = 0
        self.cache_misses = 0

    def _extract_http_info(self, result: Dict[str, str]):
        """从请求行提取HTTP信息"""
        # 尝试多个可能的字段名
        request_fields = ['request_line', 'request_method', 'request']
        
        for field in request_fields:
            if field in result and result[field]:
                try:
                    if field == 'request_line':
                        # 完整请求行: "GET /path HTTP/1.1"
                        parts = result[field].split()
                        if len(parts) >= 3:
                            result['method'] = parts[0]
                            result['url'] = parts[1]
                            result['protocol'] = parts[2]
                        elif len(parts) >= 2:
                            result['method'] = parts[0]
                            result['url'] = parts[1]
                            result['protocol'] = 'HTTP/1.1'
                    elif field == 'request_method':
                        result['method'] = result[field]
                    
                    # 解析URL参数
                    if 'url' in result:
                        self._parse_url_params(result)
                    
                    break
                except Exception as e:
                    logger.warning(f"HTTP信息提取失败: {e}")

    def _parse_url_params(self, result: Dict[str, str]):
        """解析URL参数"""
        try:
            url = result.get('url', '')
            if url:
                parsed_url = urlparse(url)
                result['query_params'] = parse_qs(parsed_url.query)
                result['path'] = parsed_url.path
        except ValueError as e:
            logger.warning(f"URL格式无效: {e}")
            result['query_params'] = {}
        except Exception as e:
            logger.warning(f"URL参数解析失败: {e}")
            result['query_params'] = {}

    def _parse_json_fields(self, result: Dict[str, str]):
        """解析JSON数据字段"""
        json_fields = ['json_data', 'data', 'payload']
        
        for field in json_fields:
            if field in result and result[field]:
                try:
                    # 解码Unicode转义字符
                    decoded_json = codecs.decode(result[field], 'unicode_escape')
                    # 解析JSON
                    json_data = json.loads(decoded_json)
                    # 合并JSON数据到结果中
                    for key, value in json_data.items():
                        if key not in result:  # 避免覆盖现有字段
                            result[key] = str(value)
                    # 移除原始json字段以避免重复
                    del result[field]
                    break
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    logger.warning(f"JSON解析失败: {e}")
                except Exception as e:
                    logger.warning(f"处理JSON数据时出错: {e}")