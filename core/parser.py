import re
import json
import codecs
import logging
from urllib.parse import urlparse, parse_qs
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

class LogParser:
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
        
        self.regex_pattern = self._build_regex_pattern()
        self.regex = re.compile(self.regex_pattern)

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

    def parse_log_line(self, line: str) -> Optional[Dict[str, str]]:
        """解析单条日志行并返回字典格式数据"""
        try:
            match = self.regex.match(line)
            if not match:
                # 如果完整模式匹配失败，尝试逐个匹配字段
                return self._partial_parse(line)

            # 提取匹配组并映射到字段名
            result = {}
            groups = match.groups()
            
            for i, field_name in enumerate(self.field_names):
                if i < len(groups):
                    result[field_name] = groups[i] if groups[i] is not None else ''
            
            # 特殊处理：从request_line或类似字段提取HTTP信息
            self._extract_http_info(result)
            
            # 解析JSON数据字段（如果存在）
            self._parse_json_fields(result)
            
            logger.debug(f"解析结果: {result}")
            return result
            
        except Exception as e:
            logger.error(f"日志行解析失败: {e}")
            return None

    def _partial_parse(self, line: str) -> Optional[Dict[str, str]]:
        """部分解析：逐个匹配字段"""
        result = {}
        remaining_line = line
        
        # 预编译正则表达式以提高性能
        compiled_patterns = []
        for pattern in self.field_patterns:
            # 确保模式有捕获组
            if '(' not in pattern:
                pattern = f'({pattern})'
            compiled_patterns.append(re.compile(pattern))
        
        for field_name, pattern in zip(self.field_names, compiled_patterns):
            try:
                match = pattern.search(remaining_line)
                if match:
                    result[field_name] = match.group(1)
                    # 移除已匹配的部分
                    remaining_line = remaining_line[match.end():]
                else:
                    result[field_name] = ''
            except Exception as e:
                logger.warning(f"字段 {field_name} 解析失败: {e}")
                result[field_name] = ''
        
        return result if any(result.values()) else None

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