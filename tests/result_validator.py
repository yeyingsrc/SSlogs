#!/usr/bin/env python3
"""
SSlogs 测试结果验证器
验证测试结果的准确性和完整性
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Set
from datetime import datetime

class ResultValidator:
    """测试结果验证器"""

    def __init__(self, results_dir: str = "tests/results"):
        self.results_dir = Path(results_dir)
        self.logger = self._setup_logging()

        # 预期结果映射
        self.expected_matches = {
            'ai_ml_anomaly': ['AI/ML驱动的异常行为检测'],
            'threat_intelligence': ['威胁情报自动检测与IOC匹配'],
            'zero_trust': ['零信任架构安全检测'],
            'supply_chain': ['软件供应链安全威胁检测'],
            'cloud_native': ['云原生高级威胁检测'],
            'privacy_compliance': ['隐私合规性检测规则'],
            'financial_security': ['金融行业安全威胁检测'],
            'user_behavior': ['用户实体行为分析(UEBA)检测'],
            'attack_chain': ['攻击链关联检测规则'],
            'automated_response': ['自动化响应触发规则']
        }

        # 验证结果
        self.validation_results = {
            'total_categories': 0,
            'validated_categories': 0,
            'failed_validations': [],
            'validation_details': {}
        }

    def _setup_logging(self) -> logging.Logger:
        """设置日志记录"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)

    def load_latest_results(self) -> Dict[str, Any]:
        """加载最新的测试结果"""
        result_files = list(self.results_dir.glob("test_results_*.json"))
        if not result_files:
            raise FileNotFoundError("没有找到测试结果文件")

        latest_file = max(result_files, key=lambda x: x.stat().st_mtime)
        self.logger.info(f"加载测试结果: {latest_file}")

        with open(latest_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def validate_rule_coverage(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """验证规则覆盖率"""
        self.logger.info("开始验证规则覆盖率...")

        coverage_results = {}

        for category, category_results in results.items():
            self.logger.info(f"验证类别: {category}")

            # 统计匹配到的规则
            matched_rules = set()
            total_tests = len(category_results)

            for result in category_results:
                if result.get('success', False) and 'matched_rules' in result:
                    matched_rules.update(result['matched_rules'])

            # 计算覆盖率
            expected_rules = set(self.expected_matches.get(category, []))
            coverage_rate = len(matched_rules) / len(expected_rules) if expected_rules else 0

            coverage_results[category] = {
                'total_tests': total_tests,
                'successful_tests': sum(1 for r in category_results if r.get('success', False)),
                'matched_rules': list(matched_rules),
                'expected_rules': list(expected_rules),
                'coverage_rate': coverage_rate,
                'is_fully_covered': matched_rules >= expected_rules
            }

            self.logger.info(f"  测试数: {total_tests}, 成功: {coverage_results[category]['successful_tests']}")
            self.logger.info(f"  规则覆盖率: {coverage_rate:.2%}")

        return coverage_results

    def validate_threat_scoring(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """验证威胁评分"""
        self.logger.info("开始验证威胁评分...")

        scoring_results = {}

        for category, category_results in results.items():
            scores = []
            high_score_tests = 0

            for result in category_results:
                if result.get('success', False) and 'threat_scores' in result:
                    scores.extend(result['threat_scores'])
                    if any(score >= 7.0 for score in result['threat_scores']):
                        high_score_tests += 1

            # 计算评分统计
            if scores:
                avg_score = sum(scores) / len(scores)
                max_score = max(scores)
                min_score = min(scores)
            else:
                avg_score = max_score = min_score = 0

            scoring_results[category] = {
                'total_scores': len(scores),
                'average_score': avg_score,
                'max_score': max_score,
                'min_score': min_score,
                'high_score_tests': high_score_tests,
                'scoring_effective': avg_score >= 5.0  # 平均分应该超过5.0
            }

            self.logger.info(f"  平均威胁评分: {avg_score:.2f}, 最高: {max_score:.2f}")

        return scoring_results

    def validate_false_positives(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """验证误报情况"""
        self.logger.info("开始验证误报情况...")

        false_positive_results = {}

        for category, category_results in results.items():
            successful_tests = 0
            false_positive_tests = 0

            for result in category_results:
                if result.get('success', False):
                    successful_tests += 1
                    # 检查是否为合理的威胁评分
                    if 'threat_scores' in result:
                        if any(score < 3.0 for score in result['threat_scores']):
                            false_positive_tests += 1

            false_positive_rate = false_positive_tests / successful_tests if successful_tests > 0 else 0

            false_positive_results[category] = {
                'successful_tests': successful_tests,
                'false_positive_tests': false_positive_tests,
                'false_positive_rate': false_positive_rate,
                'acceptable': false_positive_rate <= 0.2  # 误报率应该低于20%
            }

            self.logger.info(f"  误报率: {false_positive_rate:.2%}")

        return false_positive_results

    def validate_attack_patterns(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """验证攻击模式检测"""
        self.logger.info("开始验证攻击模式检测...")

        pattern_results = {}

        # 定义预期的攻击模式
        expected_patterns = {
            'ai_ml_anomaly': ['异常行为攻击', '绕过行为检测'],
            'threat_intelligence': ['恶意软件传播', 'C2通信'],
            'zero_trust': ['身份验证绕过', '权限提升'],
            'supply_chain': ['依赖混淆攻击', 'CI/CD管道攻击'],
            'cloud_native': ['容器逃逸攻击', 'Kubernetes权限提升'],
            'privacy_compliance': ['隐私数据泄露', '同意管理绕过'],
            'financial_security': ['支付系统攻击', '金融数据泄露'],
            'user_behavior': ['内部威胁', '账户劫持'],
            'attack_chain': ['多阶段攻击', 'APT攻击'],
            'automated_response': ['自动化攻击', '大规模攻击']
        }

        for category, category_results in results.items():
            detected_patterns = set()

            for result in category_results:
                if result.get('success', False) and 'matched_rules' in result:
                    # 这里可以根据规则名称推断攻击模式
                    for rule_name in result['matched_rules']:
                        if '异常' in rule_name:
                            detected_patterns.add('异常行为攻击')
                        if '绕过' in rule_name:
                            detected_patterns.add('绕过行为检测')
                        if '恶意' in rule_name:
                            detected_patterns.add('恶意软件传播')
                        if 'C2' in rule_name or '控制' in rule_name:
                            detected_patterns.add('C2通信')
                        if '身份' in rule_name:
                            detected_patterns.add('身份验证绕过')
                        if '权限' in rule_name:
                            detected_patterns.add('权限提升')
                        if '容器' in rule_name:
                            detected_patterns.add('容器逃逸攻击')
                        if '隐私' in rule_name:
                            detected_patterns.add('隐私数据泄露')
                        if '支付' in rule_name:
                            detected_patterns.add('支付系统攻击')
                        if '劫持' in rule_name:
                            detected_patterns.add('账户劫持')
                        if '多阶段' in rule_name or 'APT' in rule_name:
                            detected_patterns.add('APT攻击')

            expected = set(expected_patterns.get(category, []))
            pattern_coverage = len(detected_patterns & expected) / len(expected) if expected else 0

            pattern_results[category] = {
                'detected_patterns': list(detected_patterns),
                'expected_patterns': list(expected),
                'pattern_coverage': pattern_coverage,
                'patterns_detected': len(detected_patterns & expected),
                'total_expected_patterns': len(expected)
            }

            self.logger.info(f"  攻击模式覆盖率: {pattern_coverage:.2%}")

        return pattern_results

    def validate_performance(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """验证性能指标"""
        self.logger.info("开始验证性能指标...")

        performance_results = {}

        for category, category_results in results.items():
            successful_tests = sum(1 for r in category_results if r.get('success', False))
            total_tests = len(category_results)

            success_rate = successful_tests / total_tests if total_tests > 0 else 0

            performance_results[category] = {
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'success_rate': success_rate,
                'performance_acceptable': success_rate >= 0.8  # 成功率应该超过80%
            }

            self.logger.info(f"  成功率: {success_rate:.2%}")

        return performance_results

    def run_full_validation(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """运行完整验证"""
        self.logger.info("开始完整验证流程...")

        validation_results = {
            'validation_timestamp': datetime.now().isoformat(),
            'rule_coverage': self.validate_rule_coverage(results),
            'threat_scoring': self.validate_threat_scoring(results),
            'false_positives': self.validate_false_positives(results),
            'attack_patterns': self.validate_attack_patterns(results),
            'performance': self.validate_performance(results)
        }

        # 计算总体评分
        overall_score = self._calculate_overall_score(validation_results)
        validation_results['overall_score'] = overall_score
        validation_results['validation_passed'] = overall_score >= 80.0

        return validation_results

    def _calculate_overall_score(self, validation_results: Dict[str, Any]) -> float:
        """计算总体评分"""
        scores = []

        # 规则覆盖率评分 (30%)
        coverage_rates = [v['coverage_rate'] for v in validation_results['rule_coverage'].values()]
        if coverage_rates:
            scores.append(sum(coverage_rates) / len(coverage_rates) * 30)

        # 威胁评分有效性 (20%)
        scoring_effectiveness = sum(1 for v in validation_results['threat_scoring'].values() if v['scoring_effective'])
        total_categories = len(validation_results['threat_scoring'])
        if total_categories > 0:
            scores.append((scoring_effectiveness / total_categories) * 20)

        # 误报率评分 (20%)
        acceptable_false_positives = sum(1 for v in validation_results['false_positives'].values() if v['acceptable'])
        if total_categories > 0:
            scores.append((acceptable_false_positives / total_categories) * 20)

        # 性能评分 (30%)
        success_rates = [v['success_rate'] for v in validation_results['performance'].values()]
        if success_rates:
            scores.append(sum(success_rates) / len(success_rates) * 30)

        return sum(scores)

    def save_validation_report(self, validation_results: Dict[str, Any]) -> str:
        """保存验证报告"""
        report_file = self.results_dir / f"validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(validation_results, f, indent=2, ensure_ascii=False)

        self.logger.info(f"验证报告已保存: {report_file}")
        return str(report_file)

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='SSlogs 测试结果验证器')
    parser.add_argument('--results-dir', default='tests/results', help='测试结果目录')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')

    args = parser.parse_args()

    try:
        validator = ResultValidator(args.results_dir)

        # 加载测试结果
        results = validator.load_latest_results()

        # 运行验证
        validation_results = validator.run_full_validation(results)

        # 保存验证报告
        report_file = validator.save_validation_report(validation_results)

        # 输出验证结果
        print(f"📊 验证完成！总体评分: {validation_results['overall_score']:.1f}/100")
        print(f"✅ 验证状态: {'通过' if validation_results['validation_passed'] else '未通过'}")
        print(f"📄 详细报告: {report_file}")

        if args.verbose:
            print("\n📋 详细验证结果:")
            for category in results.keys():
                print(f"\n🔸 {category}:")
                print(f"  规则覆盖率: {validation_results['rule_coverage'][category]['coverage_rate']:.2%}")
                print(f"  平均威胁评分: {validation_results['threat_scoring'][category]['average_score']:.2f}")
                print(f"  误报率: {validation_results['false_positives'][category]['false_positive_rate']:.2%}")
                print(f"  成功率: {validation_results['performance'][category]['success_rate']:.2%}")

        return 0 if validation_results['validation_passed'] else 1

    except Exception as e:
        print(f"❌ 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())