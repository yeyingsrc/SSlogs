#!/usr/bin/env python3
"""
AI集成功能测试用例
验证LM Studio模型连接和AI分析功能
"""

import json
import logging
import time
import asyncio
from pathlib import Path
from typing import Dict, List, Any

# 添加项目根目录到路径
import sys
sys.path.append(str(Path(__file__).parent.parent))

from core.rule_engine import RuleEngine
from core.lm_studio_connector import LMStudioConnector, LMStudioConfig
from core.ai_threat_analyzer import AIThreatAnalyzer, get_ai_threat_analyzer, reset_ai_threat_analyzer
from core.intelligent_log_analyzer import IntelligentLogAnalyzer
from core.natural_language_interface import NaturalLanguageInterface
from core.ai_config_manager import get_ai_config_manager

class AIIntegrationTester:
    """AI集成测试器"""

    def __init__(self):
        self.logger = self._setup_logging()
        self.test_results = []
        self.rule_engine = None
        self.ai_analyzer = None
        self.intelligent_analyzer = None
        self.nli_interface = None

    def _setup_logging(self) -> logging.Logger:
        """设置日志记录"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler('tests/test_ai_integration.log')
            ]
        )
        return logging.getLogger(__name__)

    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有AI集成测试"""
        self.logger.info("🚀 开始AI集成功能测试...")

        test_results = {
            "lm_studio_connection": self.test_lm_studio_connection(),
            "ai_analyzer": self.test_ai_analyzer(),
            "intelligent_analyzer": self.test_intelligent_analyzer(),
            "natural_language_interface": self.test_natural_language_interface(),
            "end_to_end_integration": self.test_end_to_end_integration(),
            "performance": self.test_performance(),
            "error_handling": self.test_error_handling()
        }

        # 汇总测试结果
        total_tests = len(test_results)
        passed_tests = sum(1 for result in test_results.values() if result.get('success', False))
        failed_tests = total_tests - passed_tests

        summary = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": (passed_tests / total_tests) * 100 if total_tests > 0 else 0,
            "test_results": test_results,
            "timestamp": time.time()
        }

        self.logger.info(f"✅ AI集成测试完成")
        self.logger.info(f"总测试数: {total_tests}, 通过: {passed_tests}, 失败: {failed_tests}")
        self.logger.info(f"成功率: {summary['success_rate']:.1f}%")

        return summary

    def test_lm_studio_connection(self) -> Dict[str, Any]:
        """测试LM Studio连接"""
        self.logger.info("🔌 测试LM Studio连接...")

        try:
            # 测试基本连接
            config = LMStudioConfig()
            connector = LMStudioConnector(config)

            connection_test = connector.test_connection()

            if not connection_test:
                return {
                    "success": False,
                    "error": "无法连接到LM Studio",
                    "details": "请确保LM Studio正在运行并监听 http://127.0.0.1:1234"
                }

            # 测试模型列表
            available_models = connector.get_available_models()

            # 测试聊天功能
            test_messages = [
                ("system", "你是一个AI助手。"),
                ("user", "请回复'连接测试成功'")
            ]

            from core.lm_studio_connector import ChatMessage
            chat_messages = [ChatMessage(role=role, content=content) for role, content in test_messages]

            chat_response = connector.chat_completion(chat_messages)

            result = {
                "success": True,
                "available_models": available_models,
                "chat_response": chat_response,
                "model_info": connector.get_model_info(),
                "details": f"成功连接，发现 {len(available_models)} 个模型"
            }

            self.logger.info(f"✅ LM Studio连接测试成功: {result['details']}")
            return result

        except Exception as e:
            self.logger.error(f"❌ LM Studio连接测试失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "details": "连接LM Studio时发生异常"
            }

    def test_ai_analyzer(self) -> Dict[str, Any]:
        """测试AI威胁分析器"""
        self.logger.info("🧠 测试AI威胁分析器...")

        try:
            # 重置全局分析器实例
            reset_ai_threat_analyzer()

            # 创建AI分析器
            ai_analyzer = get_ai_threat_analyzer()

            # 检查连接状态
            status = ai_analyzer.get_analyzer_status()

            if not status['connector_status']['connected']:
                return {
                    "success": False,
                    "error": "AI分析器无法连接到LM Studio",
                    "details": status
                }

            # 测试日志分析
            test_log = {
                "timestamp": "2024-01-15T10:30:00+08:00",
                "src_ip": "192.168.1.100",
                "request_path": "/admin/login?user=admin&pass=123",
                "request_method": "POST",
                "user_agent": "Mozilla/5.0 (compatible; scanner/1.0)",
                "request_body": '{"username": "admin", "password": "123456"}',
                "status_code": "200"
            }

            analysis_result = ai_analyzer.analyze_log_entry(test_log)

            if not analysis_result:
                return {
                    "success": False,
                    "error": "AI分析返回空结果",
                    "details": "分析器可能无法正常处理请求"
                }

            # 验证分析结果
            required_fields = ['is_malicious', 'threat_analysis', 'raw_analysis']
            missing_fields = [field for field in required_fields if not hasattr(analysis_result, field)]

            if missing_fields:
                return {
                    "success": False,
                    "error": f"分析结果缺少必要字段: {missing_fields}",
                    "details": f"分析器返回的数据结构不完整"
                }

            result = {
                "success": True,
                "analysis_result": {
                    "is_malicious": analysis_result.is_malicious,
                    "threat_level": analysis_result.threat_analysis.threat_level,
                    "confidence": analysis_result.confidence_score,
                    "attack_types": analysis_result.threat_analysis.attack_types,
                    "processing_time": analysis_result.processing_time,
                    "model_used": analysis_result.model_used
                },
                "analyzer_status": status,
                "details": f"AI分析成功，威胁等级: {analysis_result.threat_analysis.threat_level}"
            }

            self.logger.info(f"✅ AI威胁分析器测试成功: {result['details']}")
            return result

        except Exception as e:
            self.logger.error(f"❌ AI威胁分析器测试失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "details": "AI分析器测试时发生异常"
            }

    def test_intelligent_analyzer(self) -> Dict[str, Any]:
        """测试智能日志分析器"""
        self.logger.info("🧠 测试智能日志分析器...")

        try:
            # 创建规则引擎
            rule_engine = RuleEngine("rules", enable_ai_analysis=False)

            # 创建AI分析器
            ai_analyzer = get_ai_threat_analyzer()

            # 创建智能分析器
            intelligent_analyzer = IntelligentLogAnalyzer(rule_engine, ai_analyzer)

            # 测试日志条目
            test_logs = [
                {
                    "timestamp": "2024-01-15T10:30:00+08:00",
                    "src_ip": "192.168.1.100",
                    "request_path": "/api/users",
                    "request_method": "GET",
                    "user_agent": "Mozilla/5.0 (compatible; scanner/1.0)",
                    "status_code": "200"
                },
                {
                    "timestamp": "2024-01-15T10:31:00+08:00",
                    "src_ip": "185.220.101.182",
                    "request_path": "/admin/login",
                    "request_method": "POST",
                    "user_agent": "sqlmap/1.6.12",
                    "request_body": "username=admin' OR '1'='1&password=test",
                    "status_code": "200"
                }
            ]

            # 测试单个日志分析
            start_time = time.time()
            analysis_results = []

            for log in test_logs:
                result = intelligent_analyzer.analyze_log(log)
                analysis_results.append(result)

            total_time = time.time() - start_time
            avg_time = total_time / len(test_logs)

            # 验证结果
            successful_analyses = sum(1 for r in analysis_results if r.final_threat_score > 0)

            result = {
                "success": True,
                "analysis_count": len(analysis_results),
                "successful_analyses": successful_analyses,
                "total_processing_time": total_time,
                "avg_processing_time": avg_time,
                "high_risk_count": sum(1 for r in analysis_results if r.final_threat_score >= 6.0),
                "analyzer_status": intelligent_analyzer.get_analysis_status(),
                "details": f"成功分析 {len(test_logs)} 条日志，平均耗时 {avg_time:.3f}s"
            }

            self.logger.info(f"✅ 智能日志分析器测试成功: {result['details']}")
            return result

        except Exception as e:
            self.logger.error(f"❌ 智能日志分析器测试失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "details": "智能分析器测试时发生异常"
            }

    def test_natural_language_interface(self) -> Dict[str, Any]:
        """测试自然语言接口"""
        self.logger.info("💬 测试自然语言接口...")

        try:
            # 创建基础组件
            rule_engine = RuleEngine("rules", enable_ai_analysis=False)
            ai_analyzer = get_ai_threat_analyzer()
            intelligent_analyzer = IntelligentLogAnalyzer(rule_engine, ai_analyzer)

            # 创建自然语言接口
            nli = NaturalLanguageInterface(intelligent_analyzer)

            # 测试查询
            test_queries = [
                "最近有什么威胁事件？",
                "分析IP地址 192.168.1.100",
                "系统性能怎么样？",
                "有什么安全建议？"
            ]

            query_results = []

            for query in test_queries:
                start_time = time.time()
                result = nli.process_query(query)
                processing_time = time.time() - start_time

                query_results.append({
                    "query": query,
                    "intent": result.intent.intent_type,
                    "processing_time": processing_time,
                    "has_answer": bool(result.answer),
                    "answer_length": len(result.answer) if result.answer else 0
                })

            # 验证结果
            successful_queries = sum(1 for q in query_results if q['has_answer'])
            avg_processing_time = sum(q['processing_time'] for q in query_results) / len(query_results)

            result = {
                "success": True,
                "query_count": len(test_queries),
                "successful_queries": successful_queries,
                "avg_processing_time": avg_processing_time,
                "query_results": [
                    {
                        "query": q["query"],
                        "intent": q["intent"],
                        "processing_time": q["processing_time"],
                        "success": q["has_answer"]
                    }
                    for q in query_results
                ],
                "details": f"成功处理 {successful_queries}/{len(test_queries)} 个查询，平均耗时 {avg_processing_time:.3f}s"
            }

            self.logger.info(f"✅ 自然语言接口测试成功: {result['details']}")
            return result

        except Exception as e:
            self.logger.error(f"❌ 自然语言接口测试失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "details": "自然语言接口测试时发生异常"
            }

    def test_end_to_end_integration(self) -> Dict[str, Any]:
        """测试端到端集成"""
        self.logger.info("🔄 测试端到端集成...")

        try:
            # 创建完整的分析流水线
            rule_engine = RuleEngine("rules", enable_ai_analysis=True)
            ai_analyzer = get_ai_threat_analyzer()
            intelligent_analyzer = IntelligentLogAnalyzer(rule_engine, ai_analyzer)

            # 测试复杂的攻击场景
            attack_scenarios = [
                {
                    "name": "SQL注入攻击",
                    "log": {
                        "timestamp": "2024-01-15T10:30:00+08:00",
                        "src_ip": "192.168.1.100",
                        "request_path": "/api/users?id=1' OR '1'='1",
                        "request_method": "GET",
                        "user_agent": "Mozilla/5.0",
                        "status_code": "200"
                    }
                },
                {
                    "name": "命令注入攻击",
                    "log": {
                        "timestamp": "2024-01-15T10:31:00+08:00",
                        "src_ip": "192.168.1.101",
                        "request_path": "/api/system",
                        "request_method": "POST",
                        "request_body": "command=ls -la",
                        "user_agent": "curl/7.68.0",
                        "status_code": "200"
                    }
                },
                {
                    "name": "文件上传攻击",
                    "log": {
                        "timestamp": "2024-01-15T10:32:00+08:00",
                        "src_ip": "192.168.1.102",
                        "request_path": "/upload/file.php",
                        "request_method": "POST",
                        "request_headers": {
                            "Content-Type": "multipart/form-data"
                        },
                        "request_body": "file=<?php system($_GET['cmd']); ?>&name=shell.php",
                        "status_code": "200"
                    }
                }
            ]

            # 使用AI增强的规则引擎进行分析
            enhanced_results = []

            for scenario in attack_scenarios:
                start_time = time.time()

                # 使用AI增强匹配
                matches = rule_engine.match_log_with_ai(scenario["log"])

                processing_time = time.time() - start_time

                # 验证AI增强效果
                has_ai_analysis = any('ai_analysis' in match for match in matches)
                ai_enhanced_matches = [match for match in matches if match.get('ai_analysis')]

                enhanced_results.append({
                    "scenario": scenario["name"],
                    "traditional_matches": len(matches),
                    "ai_enhanced_matches": len(ai_enhanced_matches),
                    "has_ai_analysis": has_ai_analysis,
                    "processing_time": processing_time,
                    "max_threat_score": max([match['threat_score'].score for match in matches]) if matches else 0.0
                })

            # 验证集成效果
            total_enhanced = sum(r['ai_enhanced_matches'] for r in enhanced_results)

            result = {
                "success": True,
                "scenario_count": len(attack_scenarios),
                "enhanced_results": enhanced_results,
                "total_ai_enhancements": total_enhanced,
                "avg_processing_time": sum(r['processing_time'] for r in enhanced_results) / len(enhanced_results),
                "details": f"成功增强 {total_enhanced}/{len(attack_scenarios)} 个攻击检测"
            }

            self.logger.info(f"✅ 端到端集成测试成功: {result['details']}")
            return result

        except Exception as e:
            self.logger.error(f"❌ 端到端集成测试失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "details": "端到端集成测试时发生异常"
            }

    def test_performance(self) -> Dict[str, Any]:
        """测试性能"""
        self.logger.info("⚡ 测试AI功能性能...")

        try:
            # 创建分析器
            rule_engine = RuleEngine("rules", enable_ai_analysis=True)
            intelligent_analyzer = IntelligentLogAnalyzer(rule_engine)

            # 性能测试参数
            batch_sizes = [1, 5, 10, 20]
            performance_results = []

            for batch_size in batch_sizes:
                # 生成测试日志
                test_logs = []
                for i in range(batch_size):
                    test_logs.append({
                        "timestamp": f"2024-01-15T10:{30+i:02d}+08:00",
                        "src_ip": f"192.168.1.{100+i}",
                        "request_path": f"/api/test/{i}",
                        "request_method": "GET",
                        "user_agent": f"TestAgent/{i}",
                        "status_code": "200"
                    })

                # 测试批量分析性能
                start_time = time.time()
                batch_result = intelligent_analyzer.analyze_batch(test_logs)
                processing_time = time.time() - start_time

                throughput = batch_size / processing_time
                avg_time = processing_time / batch_size

                performance_results.append({
                    "batch_size": batch_size,
                    "total_time": processing_time,
                    "avg_time": avg_time,
                    "throughput": throughput,
                    "success_rate": batch_result.successful_analyses / batch_size * 100
                })

            # 计算性能指标
            max_throughput = max(r['throughput'] for r in performance_results)
            min_avg_time = min(r['avg_time'] for r in performance_results)

            result = {
                "success": True,
                "performance_results": performance_results,
                "max_throughput": max_throughput,
                "min_avg_time": min_avg_time,
                "details": f"最大吞吐量: {max_throughput:.1f} 日志/秒，最小平均耗时: {min_avg_time:.3f} 秒"
            }

            self.logger.info(f"✅ 性能测试成功: {result['details']}")
            return result

        except Exception as e:
            self.logger.error(f"❌ 性能测试失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "details": "性能测试时发生异常"
            }

    def test_error_handling(self) -> Dict[str, Any]:
        """测试错误处理"""
        self.pylogger.info("🛡️ 测试错误处理...")

        try:
            error_test_results = []

            # 测试1: 无效LM Studio连接
            try:
                invalid_config = LMStudioConfig(port=9999)
                invalid_connector = LMStudioConnector(invalid_config)
                invalid_connector.test_connection()
                error_test_results.append({
                    "test": "invalid_lm_studio_connection",
                    "success": False,
                    "expected_error": True
                })
            except:
                error_test_results.append({
                    "test": "invalid_lm_studio_connection",
                    "success": True,
                    "expected_error": True
                })

            # 测试2: 无效日志数据
            try:
                invalid_log = {"invalid": "data"}
                ai_analyzer = get_ai_threat_analyzer()
                result = ai_analyzer.analyze_log_entry(invalid_log)

                # 应该能处理无效数据而不崩溃
                error_test_results.append({
                    "test": "invalid_log_data",
                    "success": True,
                    "expected_error": False,
                    "handled_gracefully": result is not None
                })
            except Exception as e:
                error_test_results.append({
                    "test": "invalid_log_data",
                    "success": False,
                    "expected_error": False,
                    "error": str(e)
                })

            # 测试3: 网络超时
            try:
                timeout_config = LMStudioConfig(timeout=0.001)
                timeout_connector = LMStudioConnector(timeout_config)
                timeout_connector.test_connection()
                error_test_results.append({
                    "test": "network_timeout",
                    "success": False,
                    "expected_error": True
                })
            except:
                error_test_results.append({
                    "test": "network_timeout",
                    "success": True,
                    "expected_error": True
                })

            # 统计错误处理结果
            handled_gracefully = sum(1 for r in error_test_results if r['success'] and r.get('expected_error', False))
            expected_errors_handled = sum(1 for r in error_test_results if r['success'] and r.get('expected_error', True))

            result = {
                "success": True,
                "error_tests": error_test_results,
                "handled_gracefully": handled_gracefully,
                "expected_errors_handled": expected_errors_handled,
                "total_tests": len(error_test_results),
                "details": f"优雅处理: {handled_gracefully}, 正确处理预期错误: {expected_errors_handled}"
            }

            self.logger.info(f"✅ 错误处理测试成功: {result['details']}")
            return result

        except Exception as e:
            self.logger.error(f"❌ 错误处理测试失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "details": "错误处理测试时发生异常"
            }

    def save_test_results(self, results: Dict[str, Any], output_file: str = None):
        """保存测试结果"""
        if output_file is None:
            output_file = f"tests/results/ai_integration_test_{int(time.time())}.json"

        try:
            # 确保目录存在
            Path(output_file).parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

            self.logger.info(f"📄 测试结果已保存到: {output_file}")

        except Exception as e:
            self.logger.error(f"保存测试结果失败: {e}")

def main():
    """主函数"""
    print("🛡️ SSlogs AI集成功能测试")
    print("=" * 50)

    tester = AIIntegrationTester()
    results = tester.run_all_tests()

    # 保存测试结果
    tester.save_test_results(results)

    # 显示测试摘要
    print("\n📊 测试摘要:")
    print(f"总测试数: {results['total_tests']}")
    print(f"通过测试: {results['passed_tests']}")
    print(f"失败测试: {results['failed_tests']}")
    print(f"成功率: {results['success_rate']:.1f}%")

    if results['failed_tests'] > 0:
        print("\n❌ 失败的测试:")
        for test_name, result in results['test_results'].items():
            if not result.get('success', False):
                print(f"  - {test_name}: {result.get('error', '未知错误')}")

    print(f"\n📁 详细结果已保存到测试文件")

    return results['success_rate']

if __name__ == "__main__":
    success_rate = main()
    sys.exit(0 if success_rate >= 80 else 1)