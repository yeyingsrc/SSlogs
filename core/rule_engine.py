import re
import yaml
import time
import logging
import html
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from urllib.parse import unquote, parse_qs
from collections import defaultdict
from dataclasses import dataclass

@dataclass
class ThreatScore:
    """威胁评分"""
    score: float
    severity: str
    confidence: float
    attack_vectors: List[str]
    risk_factors: List[str]

class RuleEngine:
    def __init__(self, rule_dir: str):
        self.logger = logging.getLogger(__name__)
        self.rules = []
        self.compiled_rules = {}  # 预编译规则缓存
        self.rule_stats = defaultdict(int)  # 规则匹配统计
        self._load_rules(rule_dir)
        self._compile_rules()

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
                            rule_data['source_file'] = file.name
                            rules.append(rule_data)
                        else:
                            self.logger.warning(f"规则文件 {file.name} 缺少必要字段")
                except yaml.YAMLError as e:
                    self.logger.error(f"解析规则文件 {file.name} 失败: {e}")

        self.rules = rules
        return rules

    def _compile_rules(self):
        """预编译所有规则以提升性能"""
        self.logger.info(f"开始预编译 {len(self.rules)} 个规则...")
        start_time = time.time()

        for i, rule in enumerate(self.rules):
            rule_id = f"{rule.get('category', 'unknown')}_{i}"
            try:
                compiled_rule = self._compile_single_rule(rule)
                self.compiled_rules[rule_id] = {
                    'rule': rule,
                    'compiled': compiled_rule,
                    'id': rule_id
                }
            except Exception as e:
                self.logger.error(f"编译规则失败 {rule.get('name', 'unknown')}: {e}")

        compile_time = time.time() - start_time
        self.logger.info(f"规则预编译完成，耗时 {compile_time:.3f}s，成功编译 {len(self.compiled_rules)} 个规则")

    def _compile_single_rule(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """编译单个规则"""
        pattern = rule.get('pattern', {})
        compiled = {}

        if isinstance(pattern, dict):
            for field, pattern_str in pattern.items():
                if field.endswith('_params'):
                    # 特殊处理参数字段（需要解码）
                    compiled[field] = {
                        'regex': re.compile(pattern_str, re.IGNORECASE | re.DOTALL),
                        'needs_decode': True,
                        'field': field.replace('_params', '')
                    }
                else:
                    # 普通字段匹配
                    compiled[field] = {
                        'regex': re.compile(pattern_str, re.IGNORECASE | re.DOTALL),
                        'needs_decode': False,
                        'field': field
                    }
        elif isinstance(pattern, str):
            # 兼容旧版字符串模式
            compiled['legacy'] = {
                'regex': re.compile(pattern, re.IGNORECASE | re.DOTALL),
                'needs_decode': False,
                'field': 'combined'
            }

        return compiled

    def _decode_and_normalize(self, text: str) -> str:
        """解码和标准化文本"""
        if not text:
            return ""

        try:
            # URL解码
            decoded = unquote(text)

            # HTML解码
            decoded = html.unescape(decoded)

            # Base64解码（尝试但失败时忽略）
            try:
                import base64
                if decoded.strip().endswith('=') or len(decoded.strip()) % 4 == 0:
                    try:
                        base64_decoded = base64.b64decode(decoded).decode('utf-8', errors='ignore')
                        # 如果解码结果包含可读文本，则使用它
                        if any(c.isprintable() for c in base64_decoded):
                            decoded = base64_decoded
                    except:
                        pass
            except:
                pass

            return decoded
        except Exception as e:
            self.logger.debug(f"解码失败: {e}")
            return text

    def _extract_attack_context(self, log_entry: Dict[str, str]) -> Dict[str, str]:
        """提取攻击上下文信息"""
        context = {}

        # 提取URL参数
        if 'request_path' in log_entry:
            try:
                parsed = parse_qs(log_entry['request_path'])
                for key, values in parsed.items():
                    if values:
                        context[f'param_{key}'] = values[0]
            except:
                pass

        # 提取请求头
        for field in ['user_agent', 'referer', 'x_forwarded_for']:
            if field in log_entry:
                context[field] = log_entry[field]

        # 提取请求体（如果有）
        if 'request_body' in log_entry:
            context['body'] = log_entry['request_body']

        return context

    def _calculate_threat_score(self, rule: Dict[str, Any], match_details: Dict[str, Any]) -> ThreatScore:
        """计算威胁评分"""
        base_score = 0.0

        # 基于严重级别的基础分数
        severity_scores = {
            'critical': 9.0,
            'high': 7.0,
            'medium': 5.0,
            'low': 3.0
        }
        base_score = severity_scores.get(rule.get('severity', 'medium'), 5.0)

        # 攻击向量分析
        attack_vectors = []
        risk_factors = []
        confidence = 0.8  # 默认置信度

        # 检查匹配的字段类型
        matched_fields = match_details.get('matched_fields', [])
        if 'params' in matched_fields:
            attack_vectors.append('parameter_injection')
            base_score += 1.0
            confidence += 0.1
        if 'user_agent' in matched_fields:
            attack_vectors.append('automated_attack')
            risk_factors.append('tool_detected')
            confidence += 0.15
        if 'request_path' in matched_fields:
            attack_vectors.append('path_injection')

        # 检查是否需要解码
        if match_details.get('required_decode', False):
            attack_vectors.append('encoded_attack')
            base_score += 1.5
            confidence += 0.1

        # 规则类型调整
        category = rule.get('category', '')
        if category in ['injection', 'rce']:
            base_score += 2.0
            attack_vectors.append('remote_code_execution')
        elif category in ['xss', 'ssrf']:
            base_score += 1.5
            attack_vectors.append('client_side_attack')

        # 限制分数范围
        base_score = min(max(base_score, 1.0), 10.0)
        confidence = min(max(confidence, 0.1), 1.0)

        # 确定最终严重级别
        if base_score >= 8.0:
            final_severity = 'critical'
        elif base_score >= 6.0:
            final_severity = 'high'
        elif base_score >= 4.0:
            final_severity = 'medium'
        else:
            final_severity = 'low'

        return ThreatScore(
            score=base_score,
            severity=final_severity,
            confidence=confidence,
            attack_vectors=attack_vectors,
            risk_factors=risk_factors
        )

    def match_log(self, log_entry: Dict[str, str]) -> List[Dict[str, Any]]:
        """多阶段规则匹配"""
        if not log_entry:
            return []

        matched = []

        # 第一阶段：快速匹配
        quick_matches = self._quick_match(log_entry)

        # 第二阶段：上下文分析
        for match in quick_matches:
            context_match = self._context_analysis(match, log_entry)
            if context_match:
                # 第三阶段：威胁评分
                threat_score = self._calculate_threat_score(match['rule'], match)

                match_result = {
                    'rule': match['rule'],
                    'log_entry': log_entry,
                    'threat_score': threat_score,
                    'match_details': match.get('details', {}),
                    'rule_id': match.get('rule_id'),
                    'timestamp': time.time()
                }

                matched.append(match_result)

                # 更新统计
                self.rule_stats[match.get('rule_id', 'unknown')] += 1

        # 按威胁评分排序
        matched.sort(key=lambda x: x['threat_score'].score, reverse=True)

        return matched

    def _quick_match(self, log_entry: Dict[str, str]) -> List[Dict[str, Any]]:
        """快速匹配阶段"""
        matches = []

        # 提取攻击上下文
        context = self._extract_attack_context(log_entry)

        for rule_id, rule_data in self.compiled_rules.items():
            rule = rule_data['rule']
            compiled = rule_data['compiled']
            match_details = {'matched_fields': [], 'required_decode': False}

            # 匹配编译后的规则
            for field_name, pattern_info in compiled.items():
                target_field = pattern_info['field']
                regex = pattern_info['regex']
                needs_decode = pattern_info['needs_decode']

                # 获取目标字段值
                field_value = log_entry.get(target_field) or context.get(target_field, '')
                if not field_value:
                    continue

                # 如果需要解码，先解码再匹配
                original_value = field_value
                if needs_decode:
                    field_value = self._decode_and_normalize(field_value)
                    if field_value != original_value:
                        match_details['required_decode'] = True

                # 执行正则匹配
                if regex.search(field_value):
                    match_details['matched_fields'].append(target_field)

            # 如果有匹配的字段，则添加到结果
            if match_details['matched_fields']:
                matches.append({
                    'rule': rule,
                    'details': match_details,
                    'rule_id': rule_id
                })

        return matches

    def _context_analysis(self, match: Dict[str, Any], log_entry: Dict[str, str]) -> bool:
        """上下文分析阶段"""
        # 这里可以添加更复杂的上下文分析逻辑
        # 例如：检查IP信誉、分析攻击链、检测异常行为等

        # 简单的上下文过滤：检查是否为误报
        user_agent = log_entry.get('user_agent', '').lower()

        # 已知安全工具白名单
        safe_agents = ['googlebot', 'bingbot', 'slurp', 'duckduckbot']
        if any(agent in user_agent for agent in safe_agents):
            # 对于已知的安全爬虫，降低误报
            return False

        return True

    def get_rule_statistics(self) -> Dict[str, Any]:
        """获取规则匹配统计"""
        total_matches = sum(self.rule_stats.values())
        return {
            'total_rules': len(self.rules),
            'total_matches': total_matches,
            'rule_match_counts': dict(self.rule_stats),
            'most_triggered_rules': sorted(
                self.rule_stats.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }