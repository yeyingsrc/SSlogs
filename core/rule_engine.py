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
import asyncio

@dataclass
class ThreatScore:
    """威胁评分"""
    score: float
    severity: str
    confidence: float
    attack_vectors: List[str]
    risk_factors: List[str]

class RuleEngine:
    def __init__(self, rule_dir: str, enable_ai_analysis: bool = False):
        self.logger = logging.getLogger(__name__)
        self.rules = []
        self.compiled_rules = {}  # 预编译规则缓存
        self.rule_stats = defaultdict(int)  # 规则匹配统计
        self.enable_ai_analysis = enable_ai_analysis
        self.ai_analyzer = None

        # 延迟导入AI分析器以避免循环依赖
        if enable_ai_analysis:
            try:
                from core.ai_threat_analyzer import get_ai_threat_analyzer
                self.ai_analyzer = get_ai_threat_analyzer()
                self.logger.info("AI威胁分析已启用")
            except Exception as e:
                self.logger.warning(f"AI威胁分析初始化失败: {e}")
                self.enable_ai_analysis = False

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

    def _extract_attack_context(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
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
        headers = {}
        if 'request_headers' in log_entry:
            # 如果是字典形式，直接使用
            if isinstance(log_entry['request_headers'], dict):
                headers.update(log_entry['request_headers'])
            # 如果是字符串形式，解析它
            elif isinstance(log_entry['request_headers'], str):
                try:
                    # 简单的HTTP头解析
                    for line in log_entry['request_headers'].split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            headers[key.strip().lower()] = value.strip()
                except:
                    pass

        # 添加常用的请求头字段
        for field in ['user_agent', 'referer', 'x_forwarded_for', 'x-auth', 'x-block']:
            if field in log_entry:
                headers[field] = log_entry[field]
            # 尝试从headers字典中获取（不区分大小写）
            elif headers:
                for header_key, header_value in headers.items():
                    if header_key.lower() == field.lower():
                        headers[field] = header_value
                        break

        # 将headers合并到context中
        context.update(headers)

        # 提取请求体（如果有）
        if 'request_body' in log_entry:
            body = log_entry['request_body']
            # 如果是字典，转换为字符串
            if isinstance(body, dict):
                context['body'] = str(body)
            # 如果是字符串，直接使用
            elif isinstance(body, str):
                context['body'] = body

        # 处理其他特殊字段
        special_fields = ['status_code', 'response_size', 'processing_time']
        for field in special_fields:
            if field in log_entry:
                context[field] = str(log_entry[field])

        return context

    def _get_field_value(self, data_dict: Dict[str, Any], field_name: str) -> Any:
        """递归获取嵌套字典中的字段值"""
        if not data_dict or not field_name:
            return None

        # 直接查找
        if field_name in data_dict:
            return data_dict[field_name]

        # 递归查找嵌套字典
        for key, value in data_dict.items():
            if isinstance(value, dict):
                result = self._get_field_value(value, field_name)
                if result is not None:
                    return result
            # 如果是列表，检查每个元素
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        result = self._get_field_value(item, field_name)
                        if result is not None:
                            return result

        return None

    def _calculate_threat_score(self, rule: Dict[str, Any], match_details: Dict[str, Any]) -> ThreatScore:
        """计算威胁评分（增强版）"""
        base_score = 0.0
        confidence = 0.5  # 基础置信度
        attack_vectors = []
        risk_factors = []

        # 基于严重级别的基础分数（更精确）
        severity_scores = {
            'critical': 9.5,
            'high': 7.5,
            'medium': 5.5,
            'low': 3.5
        }
        base_score = severity_scores.get(rule.get('severity', 'medium'), 5.5)

        # 匹配字段权重分析
        matched_fields = match_details.get('matched_fields', [])
        field_weights = {
            'request_body': 1.5,    # 请求体攻击更危险
            'params': 1.2,          # 参数注入
            'user_agent': 0.8,      # 工具检测
            'request_path': 1.0,    # 路径注入
            'request_headers': 1.3, # 请求头攻击
            'src_ip': 0.7           # IP相关
        }

        # 计算字段匹配加分
        for field in matched_fields:
            if field in field_weights:
                base_score += field_weights[field]
                confidence += 0.08

                # 特定字段类型的攻击向量
                if field == 'request_body':
                    attack_vectors.append('payload_injection')
                    risk_factors.append('complex_attack')
                elif field == 'params':
                    attack_vectors.append('parameter_pollution')
                elif field == 'user_agent':
                    attack_vectors.append('automated_attack')
                    risk_factors.append('tool_detected')
                elif field == 'request_headers':
                    attack_vectors.append('header_manipulation')
                    risk_factors.append('protocol_abuse')

        # 编码绕过检测（更严格）
        if match_details.get('required_decode', False):
            attack_vectors.append('evasion_technique')
            base_score += 2.0
            confidence += 0.15
            risk_factors.append('obfuscation_attempt')

        # 规则类别威胁分析（更详细）
        category = rule.get('category', '')
        category_threats = {
            'rce': {'score': 2.5, 'vector': 'remote_code_execution', 'risk': 'system_compromise'},
            'injection': {'score': 2.0, 'vector': 'code_injection', 'risk': 'data_manipulation'},
            'sql_injection': {'score': 2.8, 'vector': 'database_compromise', 'risk': 'data_breach'},
            'xss': {'score': 1.8, 'vector': 'client_side_attack', 'risk': 'session_hijack'},
            'ssrf': {'score': 2.2, 'vector': 'server_side_request', 'risk': 'internal_network_access'},
            'file_inclusion': {'score': 2.3, 'vector': 'file_manipulation', 'risk': 'code_execution'},
            'command_injection': {'score': 2.6, 'vector': 'system_command_execution', 'risk': 'privilege_escalation'},
            'log4j_vulnerability': {'score': 3.0, 'vector': 'jndi_injection', 'risk': 'remote_code_execution'},
            'api_security': {'score': 1.9, 'vector': 'api_abuse', 'risk': 'unauthorized_access'},
            'threat_intelligence': {'score': 2.1, 'vector': 'known_threat', 'risk': 'confirmed_attack'},
            'supply_chain': {'score': 2.4, 'vector': 'supply_chain_attack', 'risk': 'wide_impact'},
            'zero_trust': {'score': 1.7, 'vector': 'trust_violation', 'risk': 'policy_breach'},
            'automated_response': {'score': 1.5, 'vector': 'automation_trigger', 'risk': 'mass_attack'},
            'privacy_compliance': {'score': 1.6, 'vector': 'privacy_violation', 'risk': 'compliance_breach'},
            'financial_security': {'score': 2.7, 'vector': 'financial_fraud', 'risk': 'monetary_loss'},
            'user_behavior': {'score': 1.4, 'vector': 'behavioral_anomaly', 'risk': 'insider_threat'},
            'attack_chain': {'score': 2.9, 'vector': 'multi_stage_attack', 'risk': 'advanced_persistent_threat'},
            'ai_ml_anomaly': {'score': 1.3, 'vector': 'anomaly_detection', 'risk': 'unknown_pattern'},
            'cloud_native': {'score': 2.0, 'vector': 'cloud_attack', 'risk': 'container_escape'},
            'file_upload': {'score': 2.5, 'vector': 'malicious_upload', 'risk': 'webshell_implant'}
        }

        if category in category_threats:
            threat_info = category_threats[category]
            base_score += threat_info['score']
            attack_vectors.append(threat_info['vector'])
            risk_factors.append(threat_info['risk'])
            confidence += 0.12

        # 攻击模式严重性分析
        attack_patterns = rule.get('attack_patterns', [])
        if attack_patterns:
            high_risk_patterns = ['remote_code_execution', 'sql注入', '命令注入', '文件包含', 'SSRF', '反序列化']
            medium_risk_patterns = ['XSS', 'CSRF', '路径遍历', '信息泄露', '权限绕过']

            for pattern in attack_patterns:
                if any(high in pattern for high in high_risk_patterns):
                    base_score += 1.0
                    confidence += 0.1
                elif any(medium in pattern for medium in medium_risk_patterns):
                    base_score += 0.5
                    confidence += 0.05

        # 规则复杂度和覆盖范围
        pattern = rule.get('pattern', {})
        if isinstance(pattern, dict):
            pattern_count = len(pattern)
            if pattern_count >= 5:  # 复杂规则
                base_score += 0.3
                confidence += 0.05
            elif pattern_count >= 3:  # 中等复杂度
                base_score += 0.15

        # 威胁等级调整
        threat_level = rule.get('threat_level', '')
        if threat_level == 'critical':
            base_score += 1.0
            confidence += 0.1
        elif threat_level == 'high':
            base_score += 0.5

        # 响应状态码分析
        response_codes = rule.get('response_codes', [])
        dangerous_codes = [200, 201, 202]  # 成功响应表示攻击可能成功
        if any(code in dangerous_codes for code in response_codes):
            base_score += 0.4
            confidence += 0.08

        # 限制分数范围
        base_score = min(max(base_score, 1.0), 10.0)
        confidence = min(max(confidence, 0.1), 1.0)

        # 确定最终严重级别（更精确的阈值）
        if base_score >= 9.0:
            final_severity = 'critical'
        elif base_score >= 7.5:
            final_severity = 'high'
        elif base_score >= 5.0:
            final_severity = 'medium'
        else:
            final_severity = 'low'

        # 去重攻击向量和风险因子
        attack_vectors = list(set(attack_vectors))
        risk_factors = list(set(risk_factors))

        return ThreatScore(
            score=base_score,
            severity=final_severity,
            confidence=confidence,
            attack_vectors=attack_vectors,
            risk_factors=risk_factors
        )

    def match_log(self, log_entry: Dict[str, Any]) -> List[Dict[str, Any]]:
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

    def _quick_match(self, log_entry: Dict[str, Any]) -> List[Dict[str, Any]]:
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

                # 获取目标字段值，支持嵌套字典
                field_value = self._get_field_value(log_entry, target_field) or self._get_field_value(context, target_field)
                if not field_value:
                    continue

                # 如果字段值是复杂数据类型，转换为字符串
                if not isinstance(field_value, str):
                    field_value = str(field_value)

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

    def _context_analysis(self, match: Dict[str, Any], log_entry: Dict[str, Any]) -> bool:
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
        stats = {
            'total_rules': len(self.rules),
            'total_matches': total_matches,
            'rule_match_counts': dict(self.rule_stats),
            'most_triggered_rules': sorted(
                self.rule_stats.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }

        # 添加AI分析状态
        if self.enable_ai_analysis and self.ai_analyzer:
            stats['ai_analysis'] = self.ai_analyzer.get_analyzer_status()

        return stats

    def match_log_with_ai(self, log_entry: Dict[str, Any]) -> List[Dict[str, Any]]:
        """带AI增强的规则匹配"""
        # 首先执行传统规则匹配
        traditional_matches = self.match_log(log_entry)

        # 如果AI分析不可用，直接返回传统匹配结果
        if not self.enable_ai_analysis or not self.ai_analyzer:
            return traditional_matches

        try:
            # 提取匹配的规则名称
            matched_rule_names = [match['rule']['name'] for match in traditional_matches]

            # 执行AI分析
            ai_result = self.ai_analyzer.analyze_log_entry(log_entry, matched_rule_names)

            if ai_result:
                # 将AI分析结果整合到匹配结果中
                enhanced_matches = []

                for match in traditional_matches:
                    enhanced_match = match.copy()

                    # 添加AI分析信息
                    enhanced_match['ai_analysis'] = {
                        'is_malicious': ai_result.is_malicious,
                        'ai_threat_level': ai_result.threat_analysis.threat_level,
                        'ai_attack_types': ai_result.threat_analysis.attack_types,
                        'ai_confidence': ai_result.confidence_score,
                        'ai_recommendations': ai_result.threat_analysis.recommendations,
                        'ai_analysis_summary': ai_result.threat_analysis.analysis_summary,
                        'ai_processing_time': ai_result.processing_time,
                        'model_used': ai_result.model_used
                    }

                    # 如果AI分析认为是恶意的，提高威胁评分
                    if ai_result.is_malicious:
                        # 调整威胁评分，融合AI分析结果
                        original_score = enhanced_match['threat_score'].score
                        ai_score = ai_result.threat_analysis.threat_score

                        # 加权平均：AI权重0.4，规则权重0.6
                        blended_score = original_score * 0.6 + ai_score * 0.4

                        # 更新威胁评分
                        enhanced_match['threat_score'].score = blended_score

                        # 根据AI分析调整严重级别
                        if ai_result.threat_analysis.threat_level == '严重' and enhanced_match['threat_score'].severity != 'critical':
                            enhanced_match['threat_score'].severity = 'critical'
                        elif ai_result.threat_analysis.threat_level == '高' and enhanced_match['threat_score'].severity == 'low':
                            enhanced_match['threat_score'].severity = 'high'

                    enhanced_matches.append(enhanced_match)

                # 如果AI检测到威胁但传统规则没有匹配，创建AI专用匹配项
                if ai_result.is_malicious and not traditional_matches:
                    ai_match = {
                        'rule': {
                            'name': 'AI威胁检测',
                            'category': 'ai_detection',
                            'description': '基于AI模型的智能威胁检测',
                            'severity': ai_result.threat_analysis.threat_level.lower(),
                            'source': 'ai_analysis'
                        },
                        'log_entry': log_entry,
                        'threat_score': ThreatScore(
                            score=ai_result.threat_analysis.threat_score,
                            severity=ai_result.threat_analysis.threat_level.lower(),
                            confidence=ai_result.confidence_score,
                            attack_vectors=ai_result.threat_analysis.attack_types,
                            risk_factors=ai_result.threat_analysis.risk_factors
                        ),
                        'match_details': {
                            'matched_fields': ['ai_analysis'],
                            'ai_detected': True
                        },
                        'rule_id': 'ai_detection',
                        'timestamp': time.time(),
                        'ai_analysis': {
                            'is_malicious': ai_result.is_malicious,
                            'ai_threat_level': ai_result.threat_analysis.threat_level,
                            'ai_attack_types': ai_result.threat_analysis.attack_types,
                            'ai_confidence': ai_result.confidence_score,
                            'ai_recommendations': ai_result.threat_analysis.recommendations,
                            'ai_analysis_summary': ai_result.threat_analysis.analysis_summary,
                            'ai_processing_time': ai_result.processing_time,
                            'model_used': ai_result.model_used,
                            'pure_ai_detection': True
                        }
                    }
                    enhanced_matches.append(ai_match)

                return enhanced_matches
            else:
                # AI分析失败，返回传统匹配结果
                self.logger.warning("AI分析失败，使用传统规则匹配结果")
                return traditional_matches

        except Exception as e:
            self.logger.error(f"AI增强匹配失败: {e}")
            return traditional_matches

    async def match_log_with_ai_async(self, log_entry: Dict[str, Any]) -> List[Dict[str, Any]]:
        """异步AI增强规则匹配"""
        # 首先执行传统规则匹配
        traditional_matches = self.match_log(log_entry)

        # 如果AI分析不可用，直接返回传统匹配结果
        if not self.enable_ai_analysis or not self.ai_analyzer:
            return traditional_matches

        try:
            # 提取匹配的规则名称
            matched_rule_names = [match['rule']['name'] for match in traditional_matches]

            # 执行异步AI分析
            ai_result = await self.ai_analyzer.analyze_log_entry_async(log_entry, matched_rule_names)

            if ai_result:
                # 将AI分析结果整合到匹配结果中（与同步版本相同的逻辑）
                enhanced_matches = []

                for match in traditional_matches:
                    enhanced_match = match.copy()

                    # 添加AI分析信息
                    enhanced_match['ai_analysis'] = {
                        'is_malicious': ai_result.is_malicious,
                        'ai_threat_level': ai_result.threat_analysis.threat_level,
                        'ai_attack_types': ai_result.threat_analysis.attack_types,
                        'ai_confidence': ai_result.confidence_score,
                        'ai_recommendations': ai_result.threat_analysis.recommendations,
                        'ai_analysis_summary': ai_result.threat_analysis.analysis_summary,
                        'ai_processing_time': ai_result.processing_time,
                        'model_used': ai_result.model_used
                    }

                    # 如果AI分析认为是恶意的，提高威胁评分
                    if ai_result.is_malicious:
                        original_score = enhanced_match['threat_score'].score
                        ai_score = ai_result.threat_analysis.threat_score
                        blended_score = original_score * 0.6 + ai_score * 0.4

                        enhanced_match['threat_score'].score = blended_score

                        if ai_result.threat_analysis.threat_level == '严重' and enhanced_match['threat_score'].severity != 'critical':
                            enhanced_match['threat_score'].severity = 'critical'
                        elif ai_result.threat_analysis.threat_level == '高' and enhanced_match['threat_score'].severity == 'low':
                            enhanced_match['threat_score'].severity = 'high'

                    enhanced_matches.append(enhanced_match)

                # 如果AI检测到威胁但传统规则没有匹配，创建AI专用匹配项
                if ai_result.is_malicious and not traditional_matches:
                    ai_match = {
                        'rule': {
                            'name': 'AI威胁检测',
                            'category': 'ai_detection',
                            'description': '基于AI模型的智能威胁检测',
                            'severity': ai_result.threat_analysis.threat_level.lower(),
                            'source': 'ai_analysis'
                        },
                        'log_entry': log_entry,
                        'threat_score': ThreatScore(
                            score=ai_result.threat_analysis.threat_score,
                            severity=ai_result.threat_analysis.threat_level.lower(),
                            confidence=ai_result.confidence_score,
                            attack_vectors=ai_result.threat_analysis.attack_types,
                            risk_factors=ai_result.threat_analysis.risk_factors
                        ),
                        'match_details': {
                            'matched_fields': ['ai_analysis'],
                            'ai_detected': True
                        },
                        'rule_id': 'ai_detection',
                        'timestamp': time.time(),
                        'ai_analysis': {
                            'is_malicious': ai_result.is_malicious,
                            'ai_threat_level': ai_result.threat_analysis.threat_level,
                            'ai_attack_types': ai_result.threat_analysis.attack_types,
                            'ai_confidence': ai_result.confidence_score,
                            'ai_recommendations': ai_result.threat_analysis.recommendations,
                            'ai_analysis_summary': ai_result.threat_analysis.analysis_summary,
                            'ai_processing_time': ai_result.processing_time,
                            'model_used': ai_result.model_used,
                            'pure_ai_detection': True
                        }
                    }
                    enhanced_matches.append(ai_match)

                return enhanced_matches
            else:
                self.logger.warning("异步AI分析失败，使用传统规则匹配结果")
                return traditional_matches

        except Exception as e:
            self.logger.error(f"异步AI增强匹配失败: {e}")
            return traditional_matches

    def analyze_with_ai(self, log_entry: Dict[str, Any], rule_name: str, threat_score: float) -> Optional[str]:
        """使用AI解释规则匹配"""
        if not self.enable_ai_analysis or not self.ai_analyzer:
            return None

        try:
            explanation = self.ai_analyzer.explain_detection(rule_name, log_entry, threat_score)
            return explanation
        except Exception as e:
            self.logger.error(f"AI解释失败: {e}")
            return None

    def natural_language_query(self, query: str, log_data: List[Dict[str, Any]] = None) -> Optional[str]:
        """自然语言查询接口"""
        if not self.enable_ai_analysis or not self.ai_analyzer:
            return "AI分析功能未启用"

        try:
            response = self.ai_analyzer.natural_language_query(query, log_data)
            return response
        except Exception as e:
            self.logger.error(f"自然语言查询失败: {e}")
            return f"查询失败: {str(e)}"

    def get_ai_recommendations(self, log_entry: Dict[str, Any], rule_matches: List[Dict[str, Any]]) -> List[str]:
        """获取AI生成的安全建议"""
        if not self.enable_ai_analysis or not self.ai_analyzer:
            return ["AI分析功能未启用"]

        try:
            # 查找AI分析结果
            ai_analysis = None
            for match in rule_matches:
                if 'ai_analysis' in match:
                    ai_analysis = match['ai_analysis']
                    break

            if ai_analysis and ai_analysis.get('ai_recommendations'):
                return ai_analysis['ai_recommendations']

            # 如果没有找到AI分析结果，执行新的分析
            matched_rule_names = [match['rule']['name'] for match in rule_matches]
            ai_result = self.ai_analyzer.analyze_log_entry(log_entry, matched_rule_names)

            if ai_result:
                return self.ai_analyzer.get_security_recommendations(ai_result)

            return ["无法生成AI建议"]

        except Exception as e:
            self.logger.error(f"获取AI建议失败: {e}")
            return [f"建议生成失败: {str(e)}"]

    def enable_ai_support(self) -> bool:
        """启用AI支持"""
        if self.enable_ai_analysis:
            return True

        try:
            from core.ai_threat_analyzer import get_ai_threat_analyzer
            self.ai_analyzer = get_ai_threat_analyzer()
            self.enable_ai_analysis = True
            self.logger.info("AI威胁分析已启用")
            return True
        except Exception as e:
            self.logger.error(f"启用AI支持失败: {e}")
            return False

    def disable_ai_support(self):
        """禁用AI支持"""
        self.enable_ai_analysis = False
        self.ai_analyzer = None
        self.logger.info("AI威胁分析已禁用")