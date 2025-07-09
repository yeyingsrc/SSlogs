import re
import yaml
from pathlib import Path
from typing import List, Dict, Any

class RuleEngine:
    def __init__(self, rule_dir: str):
        import logging
        self.logger = logging.getLogger(__name__)
        self.rules = self._load_rules(rule_dir)

    def _load_rules(self, rule_dir: str) -> List[Dict[str, Any]]:
        """从规则目录加载所有YAML规则文件"""
        rules = []
        rule_path = Path(rule_dir)
        if not rule_path.exists():
            raise FileNotFoundError(f"规则目录不存在: {rule_dir}")

        for file in list(rule_path.glob("*.yaml")) + list(rule_path.glob("*.yml")):
            with open(file, 'r', encoding='utf-8') as f:
                try:
                    rule_data = yaml.safe_load(f)
                    if isinstance(rule_data, dict):
                        # 验证规则必要字段
                        if all(k in rule_data for k in ['name', 'pattern']):
                            rules.append(rule_data)
                        else:
                            print(f"规则文件 {file.name} 缺少必要字段")
                except yaml.YAMLError as e:
                    print(f"解析规则文件 {file.name} 失败: {e}")
        return rules

    def match_log(self, log_entry: Dict[str, str]) -> List[Dict[str, Any]]:
        """检查日志条目是否匹配任何规则"""
        matched = []
        if not log_entry or 'request_line' not in log_entry:
            self.logger.debug(f"日志条目不完整: {log_entry}")
            return matched
        self.logger.debug(f"解析后的日志条目 - 请求: {log_entry.get('request')}, 用户代理: {log_entry.get('user_agent')}")

        for rule in self.rules:
            pattern = rule.get('pattern')
            if isinstance(pattern, dict):
                # 字段级模式匹配
                match = True
                for field, pattern_str in pattern.items():
                    if field not in log_entry or not re.search(pattern_str, log_entry[field], re.IGNORECASE):
                        match = False
                        break
                if match:
                    matched.append({'rule': rule, 'log_entry': log_entry})
            elif isinstance(pattern, str) and 'request_line' in log_entry:
                # 兼容旧版字符串模式
                search_text = log_entry['request_line'] + ' ' + log_entry.get('user_agent', '')
                if re.search(pattern, search_text, re.IGNORECASE):
                    matched.append({'rule': rule, 'log_entry': log_entry})
        return matched