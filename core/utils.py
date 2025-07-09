import os
import re
from datetime import datetime
from typing import Optional, Dict, Any

def ensure_dir(path: str) -> None:
    """确保目录存在，如果不存在则创建"""
    if not os.path.exists(path):
        os.makedirs(path)

def parse_timestamp(timestamp_str: str, format_str: str = "[%d/%b/%Y:%H:%M:%S %z]") -> Optional[datetime]:
    """解析日志时间戳字符串为datetime对象"""
    try:
        return datetime.strptime(timestamp_str, format_str)
    except ValueError:
        return None

def clean_string(s: str) -> str:
    """清理字符串中的特殊字符"""
    return re.sub(r'[\x00-\x1F\x7F]', '', s)

def convert_size(size_str: str) -> int:
    """将日志中的大小字符串转换为整数"""
    if size_str == '-':
        return 0
    try:
        return int(size_str)
    except ValueError:
        return 0

def severity_to_level(severity: str) -> int:
    """将严重程度字符串转换为数值级别"""
    severity_map = {
        'low': 1,
        'medium': 2,
        'high': 3,
        'critical': 4
    }
    return severity_map.get(severity.lower(), 2)

def extract_ip_from_log(log_line: str) -> Optional[str]:
    """从日志行中提取IP地址"""
    ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    match = re.search(ip_pattern, log_line)
    return match.group(0) if match else None

def get_file_extension(file_path: str) -> str:
    """获取文件扩展名"""
    return os.path.splitext(file_path)[1].lower()

def merge_dicts(*dicts: Dict[str, Any]) -> Dict[str, Any]:
    """合并多个字典"""
    result = {}
    for d in dicts:
        result.update(d)
    return result