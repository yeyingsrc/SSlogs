#!/usr/bin/env python3
"""
SSlogs 规则测试框架
用于验证新创建的检测规则的可用性和准确性
"""

import json
import yaml
import time
import logging
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
import random
import string

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent))

from core.rule_engine import RuleEngine

class TestFramework:
    """测试框架主类"""

    def __init__(self, rule_dir: str = "rules"):
        self.rule_dir = rule_dir
        self.logger = self._setup_logging()
        self.test_data_dir = Path(__file__).parent / "test_data"
        self.results_dir = Path(__file__).parent / "results"
        self.reports_dir = Path(__file__).parent / "reports"

        # 确保目录存在
        self.test_data_dir.mkdir(exist_ok=True)
        self.results_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)

        # 测试统计
        self.test_stats = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'error_tests': 0,
            'test_results': []
        }

    def _setup_logging(self) -> logging.Logger:
        """设置日志记录"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('tests/test_framework.log')
            ]
        )
        return logging.getLogger(__name__)

    def load_rule_engine(self) -> RuleEngine:
        """加载规则引擎"""
        try:
            rule_engine = RuleEngine(self.rule_dir)
            self.logger.info(f"规则引擎加载成功，共加载 {len(rule_engine.rules)} 个规则")
            return rule_engine
        except Exception as e:
            self.logger.error(f"规则引擎加载失败: {e}")
            raise

    def generate_test_logs(self) -> Dict[str, List[Dict]]:
        """生成测试日志数据"""
        self.logger.info("开始生成测试日志数据...")

        test_logs = {
            'ai_ml_anomaly': self._generate_ai_ml_test_logs(),
            'threat_intelligence': self._generate_threat_intel_test_logs(),
            'zero_trust': self._generate_zero_trust_test_logs(),
            'supply_chain': self._generate_supply_chain_test_logs(),
            'cloud_native': self._generate_cloud_native_test_logs(),
            'privacy_compliance': self._generate_privacy_test_logs(),
            'financial_security': self._generate_financial_test_logs(),
            'user_behavior': self._generate_user_behavior_test_logs(),
            'attack_chain': self._generate_attack_chain_test_logs(),
            'automated_response': self._generate_automated_response_test_logs()
        }

        # 保存测试数据
        for category, logs in test_logs.items():
            test_file = self.test_data_dir / f"{category}_test_logs.json"
            with open(test_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, indent=2, ensure_ascii=False)

        self.logger.info(f"测试日志数据生成完成，共 {sum(len(logs) for logs in test_logs.values())} 条")
        return test_logs

    def _generate_ai_ml_test_logs(self) -> List[Dict]:
        """生成AI/ML异常检测测试日志"""
        logs = []

        # 异常User-Agent
        logs.append({
            'timestamp': '2024-01-15T10:30:00+08:00',
            'src_ip': '192.168.1.100',
            'request_method': 'GET',
            'request_path': '/api/users',
            'http_version': 'HTTP/1.1',
            'status_code': '200',
            'user_agent': 'Mozilla/5.0 (compatible; bot/1.0; +http://example.com/bot)',
            'processing_time': '1.234'
        })

        # 高频访问异常
        for i in range(5):
            logs.append({
                'timestamp': f'2024-01-15T10:30:{i:02d}+08:00',
                'src_ip': '192.168.1.101',
                'request_method': 'GET',
                'request_path': f'/api/data?param1=value1&param2=value2&param3=value3&param4=value4&param5=value5',
                'http_version': 'HTTP/1.1',
                'status_code': '200',
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'processing_time': '2.567'
            })

        # 异常会话行为
        logs.append({
            'timestamp': '2024-01-15T10:35:00+08:00',
            'src_ip': '192.168.1.102',
            'request_method': 'POST',
            'request_path': '/api/session/change',
            'http_version': 'HTTP/1.1',
            'status_code': '200',
            'user_agent': 'curl/7.68.0',
            'request_body': '{"session_token": "abc123", "device_fingerprint": "changed"}',
            'processing_time': '0.876'
        })

        return logs

    def _generate_threat_intel_test_logs(self) -> List[Dict]:
        """生成威胁情报测试日志"""
        logs = []

        # 恶意IP访问
        logs.append({
            'timestamp': '2024-01-15T11:00:00+08:00',
            'src_ip': '185.220.101.182',  # 已知恶意IP
            'request_method': 'GET',
            'request_path': '/admin/login',
            'http_version': 'HTTP/1.1',
            'status_code': '403',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        # 恶意User-Agent
        logs.append({
            'timestamp': '2024-01-15T11:05:00+08:00',
            'src_ip': '192.168.1.200',
            'request_method': 'GET',
            'request_path': '/wp-admin/',
            'http_version': 'HTTP/1.1',
            'status_code': '404',
            'user_agent': 'sqlmap/1.6.12#stable (http://sqlmap.org)'
        })

        # APT工具特征
        logs.append({
            'timestamp': '2024-01-15T11:10:00+08:00',
            'src_ip': '10.0.0.50',
            'request_method': 'POST',
            'request_path': '/api/heartbeat',
            'http_version': 'HTTP/1.1',
            'status_code': '200',
            'user_agent': 'Cobalt Strike/4.5',
            'request_body': '{"beacon_id": "cobalt_strike_beacon", "task": "checkin"}'
        })

        return logs

    def _generate_zero_trust_test_logs(self) -> List[Dict]:
        """生成零信任架构测试日志"""
        logs = []

        # 身份验证绕过 - 使用更明确的模式
        logs.append({
            'timestamp': '2024-01-15T12:00:00+08:00',
            'src_ip': '192.168.1.150',
            'request_method': 'POST',
            'request_path': '/api/login/bypass',
            'http_version': 'HTTP/1.1',
            'status_code': '401',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'request_headers': {
                'X-Auth-Bypass': 'true',
                'X-MFA-Skip': 'true',
                'X-Identity-Bypass': 'authentication'
            }
        })

        # 权限提升尝试 - 增强模式匹配
        logs.append({
            'timestamp': '2024-01-15T12:05:00+08:00',
            'src_ip': '192.168.1.151',
            'request_method': 'POST',
            'request_path': '/api/privilege/escalate',
            'http_version': 'HTTP/1.1',
            'status_code': '403',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'request_body': '{"privilege_escalation": "bypass", "role_upgrade": "admin", "access_control": "override"}',
            'request_headers': {
                'X-Privilege-Escalation': 'attempt',
                'X-Access-Control': 'bypass'
            }
        })

        # 会话劫持和异常访问 - 使用更明确的攻击模式
        logs.append({
            'timestamp': '2024-01-15T12:10:00+08:00',
            'src_ip': '203.0.113.1',
            'request_method': 'GET',
            'request_path': '/api/session/hijack',
            'http_version': 'HTTP/1.1',
            'status_code': '200',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'request_headers': {
                'X-Session-Hijack': 'true',
                'X-Auth-Token': 'stolen_token',
                'X-Unauthorized-Access': 'sensitive_data'
            }
        })

        return logs

    def _generate_supply_chain_test_logs(self) -> List[Dict]:
        """生成供应链安全测试日志"""
        logs = []

        # 恶意依赖包
        logs.append({
            'timestamp': '2024-01-15T13:00:00+08:00',
            'src_ip': '192.168.1.160',
            'request_method': 'POST',
            'request_path': '/api/npm/install',
            'http_version': 'HTTP/1.1',
            'status_code': '200',
            'user_agent': 'npm/8.5.5 node/v18.12.1 darwin x64',
            'request_body': '{"package": "malicious-package", "version": "backdoor"}'
        })

        # 容器镜像攻击
        logs.append({
            'timestamp': '2024-01-15T13:05:00+08:00',
            'src_ip': '10.0.0.100',
            'request_method': 'POST',
            'request_path': '/api/docker/pull',
            'http_version': 'HTTP/1.1',
            'status_code': '200',
            'user_agent': 'docker/20.10.12',
            'request_body': '{"image": "malicious/docker:latest", "backdoor": "true"}'
        })

        # CI/CD管道攻击
        logs.append({
            'timestamp': '2024-01-15T13:10:00+08:00',
            'src_ip': '192.168.1.161',
            'request_method': 'POST',
            'request_path': '/api/jenkins/build',
            'http_version': 'HTTP/1.1',
            'status_code': '200',
            'user_agent': 'Jenkins-CI/2.401.3',
            'request_body': '{"build": "compromise", "backdoor": "inject"}'
        })

        return logs

    def _generate_cloud_native_test_logs(self) -> List[Dict]:
        """生成云原生威胁测试日志"""
        logs = []

        # Kubernetes RBAC权限提升
        logs.append({
            'timestamp': '2024-01-15T14:00:00+08:00',
            'src_ip': '10.244.0.1',
            'request_method': 'POST',
            'request_path': '/apis/rbac.authorization.k8s.io/v1/clusterroles',
            'http_version': 'HTTP/1.1',
            'status_code': '201',
            'user_agent': 'kubectl/v1.26.0',
            'request_body': '{"role": "cluster-admin", "privilege": "escalate"}'
        })

        # 容器逃逸尝试
        logs.append({
            'timestamp': '2024-01-15T14:05:00+08:00',
            'src_ip': '172.17.0.2',
            'request_method': 'POST',
            'request_path': '/api/container/escape',
            'http_version': 'HTTP/1.1',
            'status_code': '403',
            'user_agent': 'curl/7.68.0',
            'request_body': '{"escape": "privileged", "mount": "host"}'
        })

        # 云元数据攻击
        logs.append({
            'timestamp': '2024-01-15T14:10:00+08:00',
            'src_ip': '169.254.169.254',
            'request_method': 'GET',
            'request_path': '/latest/meta-data/iam/security-credentials',
            'http_version': 'HTTP/1.1',
            'status_code': '200',
            'user_agent': 'curl/7.68.0'
        })

        return logs

    def _generate_privacy_test_logs(self) -> List[Dict]:
        """生成隐私合规测试日志"""
        logs = []

        # GDPR数据访问违规
        logs.append({
            'timestamp': '2024-01-15T15:00:00+08:00',
            'src_ip': '192.168.1.170',
            'request_method': 'GET',
            'request_path': '/api/personal_data/export',
            'http_version': 'HTTP/1.1',
            'status_code': '200',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'request_body': '{"personal_data": "unauthorized_access", "gdpr": "violation"}'
        })

        # PII数据泄露
        logs.append({
            'timestamp': '2024-01-15T15:05:00+08:00',
            'src_ip': '192.168.1.171',
            'request_method': 'POST',
            'request_path': '/api/user/profile',
            'http_version': 'HTTP/1.1',
            'status_code': '200',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'request_body': '{"ssn": "123-45-6789", "credit_card": "4111-1111-1111-1111"}'
        })

        # 同意管理违规
        logs.append({
            'timestamp': '2024-01-15T15:10:00+08:00',
            'src_ip': '192.168.1.172',
            'request_method': 'POST',
            'request_path': '/api/consent/bypass',
            'http_version': 'HTTP/1.1',
            'status_code': '200',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'request_headers': {
                'X-Consent': 'bypass'
            }
        })

        return logs

    def _generate_financial_test_logs(self) -> List[Dict]:
        """生成金融安全测试日志"""
        logs = []

        # 支付欺诈
        logs.append({
            'timestamp': '2024-01-15T16:00:00+08:00',
            'src_ip': '192.168.1.180',
            'request_method': 'POST',
            'request_path': '/api/payment/process',
            'http_version': 'HTTP/1.1',
            'status_code': '200',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'request_body': '{"amount": "-100.00", "card_number": "4111111111111111"}'
        })

        # 洗钱检测
        logs.append({
            'timestamp': '2024-01-15T16:05:00+08:00',
            'src_ip': '192.168.1.181',
            'request_method': 'POST',
            'request_path': '/api/transfer/funds',
            'http_version': 'HTTP/1.1',
            'status_code': '200',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'request_body': '{"transaction": "structuring", "amount": "9999.99"}'
        })

        # 加密货币攻击
        logs.append({
            'timestamp': '2024-01-15T16:10:00+08:00',
            'src_ip': '192.168.1.182',
            'request_method': 'POST',
            'request_path': '/api/crypto/wallet/drain',
            'http_version': 'HTTP/1.1',
            'status_code': '200',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'request_body': '{"private_key": "0x1234567890abcdef", "drain": "true"}'
        })

        return logs

    def _generate_user_behavior_test_logs(self) -> List[Dict]:
        """生成用户行为分析测试日志"""
        logs = []

        # 异常访问时间
        logs.append({
            'timestamp': '2024-01-15T03:00:00+08:00',  # 凌晨3点
            'src_ip': '192.168.1.190',
            'request_method': 'GET',
            'request_path': '/api/sensitive_data',
            'http_version': 'HTTP/1.1',
            'status_code': '200',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'request_headers': {
                'X-Time': '03:00:00',
                'X-Access-Time': 'abnormal'
            }
        })

        # 批量数据访问
        logs.append({
            'timestamp': '2024-01-15T10:00:00+08:00',
            'src_ip': '192.168.1.191',
            'request_method': 'GET',
            'request_path': '/api/users/export?all=true',
            'http_version': 'HTTP/1.1',
            'status_code': '200',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'request_body': '{"export": "bulk", "data": "all_users"}'
        })

        # 会话劫持
        logs.append({
            'timestamp': '2024-01-15T10:05:00+08:00',
            'src_ip': '203.0.113.1',
            'request_method': 'POST',
            'request_path': '/api/session/hijack',
            'http_version': 'HTTP/1.1',
            'status_code': '200',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'request_body': '{"session": "hijack", "token": "stolen"}'
        })

        return logs

    def _generate_attack_chain_test_logs(self) -> List[Dict]:
        """生成攻击链关联测试日志"""
        logs = []

        # 攻击链阶段1：初始访问
        logs.append({
            'timestamp': '2024-01-15T17:00:00+08:00',
            'src_ip': '192.168.1.200',
            'request_method': 'POST',
            'request_path': '/api/phishing/login',
            'http_version': 'HTTP/1.1',
            'status_code': '200',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'request_headers': {
                'X-Attack-Stage': 'initial_access',
                'X-Mitre-Tactic': 'TA0001'
            }
        })

        # 攻击链阶段2：执行
        logs.append({
            'timestamp': '2024-01-15T17:05:00+08:00',
            'src_ip': '192.168.1.200',
            'request_method': 'POST',
            'request_path': '/api/execute/payload',
            'http_version': 'HTTP/1.1',
            'status_code': '200',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'request_body': '{"execute": "malicious_payload", "command": "eval"}'
        })

        # 攻击链阶段3：横向移动
        logs.append({
            'timestamp': '2024-01-15T17:10:00+08:00',
            'src_ip': '192.168.1.200',
            'request_method': 'POST',
            'request_path': '/api/lateral/movement',
            'http_version': 'HTTP/1.1',
            'status_code': '200',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'request_body': '{"lateral": "movement", "pass_the_hash": "true"}'
        })

        return logs

    def _generate_automated_response_test_logs(self) -> List[Dict]:
        """生成自动化响应测试日志"""
        logs = []

        # 自动阻断触发 - 增强模式匹配
        logs.append({
            'timestamp': '2024-01-15T18:00:00+08:00',
            'src_ip': '192.168.1.210',
            'request_method': 'POST',
            'request_path': '/api/firewall/block/ip',
            'http_version': 'HTTP/1.1',
            'status_code': '200',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'request_headers': {
                'X-Block': 'true',
                'X-Block-IP': '192.168.1.210',
                'X-Block-Duration': '3600',
                'X-Block-Reason': 'attack'
            }
        })

        # 自动隔离触发 - 增强模式匹配
        logs.append({
            'timestamp': '2024-01-15T18:05:00+08:00',
            'src_ip': '192.168.1.211',
            'request_method': 'POST',
            'request_path': '/api/security/isolate/system',
            'http_version': 'HTTP/1.1',
            'status_code': '200',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'request_body': '{"isolate": "true", "quarantine": "activate", "malware": "detected", "container": "sandbox"}',
            'request_headers': {
                'X-Quarantine-Trigger': 'malware_detected'
            }
        })

        # 告警升级触发 - 增强模式匹配
        logs.append({
            'timestamp': '2024-01-15T18:10:00+08:00',
            'src_ip': '192.168.1.212',
            'request_method': 'POST',
            'request_path': '/api/security/alert/escalate',
            'http_version': 'HTTP/1.1',
            'status_code': '200',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'request_body': '{"incident": "create", "event": "open", "automation": "true"}',
            'request_headers': {
                'X-Alert-Escalate': 'true',
                'X-Severity-Upgrade': 'critical',
                'X-Escalation-Reason': 'APT_attack'
            }
        })

        return logs

    def run_tests(self, rule_engine: RuleEngine, test_logs: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """运行测试"""
        self.logger.info("开始运行规则测试...")

        results = {}

        for category, logs in test_logs.items():
            self.logger.info(f"测试类别: {category}")
            category_results = []

            for i, log_entry in enumerate(logs):
                try:
                    # 使用规则引擎匹配日志
                    matches = rule_engine.match_log(log_entry)

                    result = {
                        'test_id': f"{category}_{i+1}",
                        'timestamp': log_entry.get('timestamp'),
                        'src_ip': log_entry.get('src_ip'),
                        'request_path': log_entry.get('request_path'),
                        'matches': len(matches),
                        'matched_rules': [match['rule']['name'] for match in matches],
                        'threat_scores': [match['threat_score'].score for match in matches],
                        'success': len(matches) > 0
                    }

                    category_results.append(result)

                    if result['success']:
                        self.test_stats['passed_tests'] += 1
                    else:
                        self.test_stats['failed_tests'] += 1

                    self.test_stats['total_tests'] += 1

                except Exception as e:
                    self.logger.error(f"测试失败 {category}_{i+1}: {e}")
                    error_result = {
                        'test_id': f"{category}_{i+1}",
                        'error': str(e),
                        'success': False
                    }
                    category_results.append(error_result)
                    self.test_stats['error_tests'] += 1
                    self.test_stats['total_tests'] += 1

            results[category] = category_results

        # 保存测试结果
        results_file = self.results_dir / f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        self.test_stats['test_results'] = results
        self.logger.info(f"测试完成，总计 {self.test_stats['total_tests']} 个测试")

        return results

    def _generate_html_report(self, results: Dict[str, Any]) -> str:
        """生成HTML测试报告"""
        html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SSlogs 规则测试报告</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; margin-bottom: 40px; }}
        .header h1 {{ color: #2c3e50; margin-bottom: 10px; }}
        .header p {{ color: #7f8c8d; font-size: 16px; }}
        .stats {{ display: flex; justify-content: space-around; margin-bottom: 40px; flex-wrap: wrap; }}
        .stat-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; text-align: center; min-width: 150px; margin: 5px; }}
        .stat-card h3 {{ margin: 0 0 10px 0; font-size: 24px; }}
        .stat-card p {{ margin: 0; font-size: 14px; opacity: 0.9; }}
        .category-section {{ margin-bottom: 30px; border: 1px solid #e0e0e0; border-radius: 8px; overflow: hidden; }}
        .category-header {{ background-color: #34495e; color: white; padding: 15px 20px; font-weight: bold; font-size: 18px; }}
        .category-content {{ padding: 20px; }}
        .test-item {{ margin-bottom: 15px; padding: 15px; border-left: 4px solid #ddd; background-color: #f9f9f9; }}
        .test-item.success {{ border-left-color: #27ae60; background-color: #d5f4e6; }}
        .test-item.failure {{ border-left-color: #e74c3c; background-color: #fdf2f2; }}
        .test-item.error {{ border-left-color: #f39c12; background-color: #fef9e7; }}
        .test-details {{ margin-top: 10px; font-size: 14px; color: #555; }}
        .matched-rules {{ margin-top: 8px; }}
        .rule-badge {{ display: inline-block; background-color: #3498db; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; margin-right: 5px; margin-bottom: 5px; }}
        .threat-score {{ background-color: #e67e22; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; }}
        .summary-table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; }}
        .summary-table th, .summary-table td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        .summary-table th {{ background-color: #34495e; color: white; }}
        .summary-table tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .pass-rate {{ font-weight: bold; }}
        .pass-rate.high {{ color: #27ae60; }}
        .pass-rate.medium {{ color: #f39c12; }}
        .pass-rate.low {{ color: #e74c3c; }}
        .footer {{ text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #e0e0e0; color: #7f8c8d; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ SSlogs 规则测试报告</h1>
            <p>生成时间: {timestamp}</p>
        </div>

        <div class="stats">
            <div class="stat-card">
                <h3>{total_tests}</h3>
                <p>总测试数</p>
            </div>
            <div class="stat-card">
                <h3>{passed_tests}</h3>
                <p>通过测试</p>
            </div>
            <div class="stat-card">
                <h3>{failed_tests}</h3>
                <p>失败测试</p>
            </div>
            <div class="stat-card">
                <h3>{error_tests}</h3>
                <p>错误测试</p>
            </div>
            <div class="stat-card">
                <h3>{success_rate:.1f}%</h3>
                <p>成功率</p>
            </div>
        </div>

        <h2>📊 测试类别概览</h2>
        <table class="summary-table">
            <thead>
                <tr>
                    <th>测试类别</th>
                    <th>总测试数</th>
                    <th>通过数</th>
                    <th>失败数</th>
                    <th>错误数</th>
                    <th>成功率</th>
                </tr>
            </thead>
            <tbody>
                {category_summary}
            </tbody>
        </table>

        {category_details}

        <div class="footer">
            <p>📋 报告由 SSlogs 测试框架自动生成</p>
            <p>🔧 规则引擎版本: v3.1 | 测试框架版本: v1.0</p>
        </div>
    </div>
</body>
</html>
        """

        # 生成类别概览
        category_summary = ""
        for category, category_results in results.items():
            total = len(category_results)
            passed = sum(1 for r in category_results if r.get('success', False))
            failed = sum(1 for r in category_results if not r.get('success', False) and 'error' not in r)
            errors = sum(1 for r in category_results if 'error' in r)
            success_rate = (passed / total * 100) if total > 0 else 0

            success_rate_class = "high" if success_rate >= 80 else "medium" if success_rate >= 60 else "low"

            category_summary += f"""
                <tr>
                    <td>{category}</td>
                    <td>{total}</td>
                    <td>{passed}</td>
                    <td>{failed}</td>
                    <td>{errors}</td>
                    <td class="pass-rate {success_rate_class}">{success_rate:.1f}%</td>
                </tr>
            """

        # 生成类别详情
        category_details = ""
        for category, category_results in results.items():
            category_details += f"""
            <div class="category-section">
                <div class="category-header">
                    📂 {category} ({len(category_results)} 个测试)
                </div>
                <div class="category-content">
            """

            for result in category_results:
                if 'error' in result:
                    status_class = "error"
                    status_icon = "❌"
                    status_text = "错误"
                elif result.get('success', False):
                    status_class = "success"
                    status_icon = "✅"
                    status_text = "通过"
                else:
                    status_class = "failure"
                    status_icon = "❌"
                    status_text = "失败"

                matched_rules_html = ""
                if result.get('matched_rules'):
                    matched_rules_html = '<div class="matched-rules">匹配的规则:'
                    for rule_name in result['matched_rules']:
                        matched_rules_html += f'<span class="rule-badge">{rule_name}</span>'
                    matched_rules_html += '</div>'

                threat_scores_html = ""
                if result.get('threat_scores'):
                    threat_scores_html = '<div class="threat-scores">威胁评分:'
                    for score in result['threat_scores']:
                        threat_scores_html += f'<span class="threat-score">{score:.1f}</span>'
                    threat_scores_html += '</div>'

                category_details += f"""
                <div class="test-item {status_class}">
                    <div>
                        <strong>{status_icon} {result.get('test_id', 'Unknown')}</strong>
                        <span style="float: right;">{status_text}</span>
                    </div>
                    <div class="test-details">
                        <p><strong>IP:</strong> {result.get('src_ip', 'N/A')}</p>
                        <p><strong>路径:</strong> {result.get('request_path', 'N/A')}</p>
                        <p><strong>时间:</strong> {result.get('timestamp', 'N/A')}</p>
                        {matched_rules_html}
                        {threat_scores_html}
                        {'<p><strong>错误:</strong> ' + result['error'] + '</p>' if 'error' in result else ''}
                    </div>
                </div>
                """

            category_details += "</div></div>"

        # 计算统计数据
        total_tests = self.test_stats['total_tests']
        passed_tests = self.test_stats['passed_tests']
        failed_tests = self.test_stats['failed_tests']
        error_tests = self.test_stats['error_tests']
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        return html_template.format(
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            error_tests=error_tests,
            success_rate=success_rate,
            category_summary=category_summary,
            category_details=category_details
        )

    def generate_report(self, results: Dict[str, Any]) -> str:
        """生成测试报告"""
        report_file = self.reports_dir / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

        html_content = self._generate_html_report(results)

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        self.logger.info(f"测试报告已生成: {report_file}")
        return str(report_file)

if __name__ == "__main__":
    framework = TestFramework()

    # 生成测试数据
    test_logs = framework.generate_test_logs()

    # 加载规则引擎
    rule_engine = framework.load_rule_engine()

    # 运行测试
    results = framework.run_tests(rule_engine, test_logs)

    # 生成报告
    report_file = framework.generate_report(results)
    print(f"✅ 测试完成！报告已生成: {report_file}")