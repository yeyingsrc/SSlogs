#!/usr/bin/env python3
"""
AI功能演示脚本
展示SSlogs AI集成功能的实际应用
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.lm_studio_connector import LMStudioConnector, get_lm_studio_connector
from core.ai_threat_analyzer import AIThreatAnalyzer, get_ai_threat_analyzer
from core.ai_config_manager import get_ai_config_manager
from core.intelligent_log_analyzer import IntelligentLogAnalyzer, get_intelligent_log_analyzer
from core.natural_language_interface import NaturalLanguageInterface, get_natural_language_interface
from core.rule_engine import RuleEngine


class AIDemo:
    """AI功能演示类"""

    def __init__(self):
        self.config_manager = get_ai_config_manager()
        self.rule_engine = RuleEngine()

    def print_section(self, title: str):
        """打印章节标题"""
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}")

    def print_subsection(self, title: str):
        """打印子章节标题"""
        print(f"\n--- {title} ---")

    def check_lm_studio_connection(self) -> bool:
        """检查LM Studio连接状态"""
        self.print_section("LM Studio 连接检查")

        try:
            connector = get_lm_studio_connector()
            print("正在连接到LM Studio...")
            print(f"主机: {connector.config.host}")
            print(f"端口: {connector.config.port}")

            # 检查连接
            if connector.check_connection():
                print("✅ LM Studio连接成功!")

                # 获取可用模型
                models = connector.get_available_models()
                if models:
                    print(f"✅ 发现 {len(models)} 个可用模型:")
                    for model in models:
                        print(f"  - {model}")
                else:
                    print("⚠️ 未发现可用模型，请确保LM Studio中已加载模型")
                    return False

                return True
            else:
                print("❌ LM Studio连接失败!")
                print("请确保:")
                print("1. LM Studio正在运行")
                print("2. 服务器地址为 http://127.0.0.1:1234")
                print("3. 已加载一个语言模型")
                return False

        except Exception as e:
            print(f"❌ 连接检查出错: {e}")
            return False

    def demo_ai_threat_analysis(self):
        """演示AI威胁分析功能"""
        self.print_section("AI威胁分析演示")

        # 示例日志条目
        test_logs = [
            {
                "timestamp": "2024-01-15 10:30:45",
                "ip": "192.168.1.100",
                "action": "login",
                "user": "admin",
                "status": "success"
            },
            {
                "timestamp": "2024-01-15 10:31:12",
                "ip": "10.0.0.50",
                "action": "sudo",
                "user": "root",
                "command": "rm -rf /var/log/*"
            },
            {
                "timestamp": "2024-01-15 10:32:08",
                "ip": "203.0.113.10",
                "action": "port_scan",
                "target": "192.168.1.0/24",
                "ports": "22,23,80,443,3389"
            },
            {
                "timestamp": "2024-01-15 10:33:15",
                "ip": "172.16.0.25",
                "action": "file_access",
                "user": "unknown",
                "file": "/etc/passwd",
                "status": "denied"
            }
        ]

        try:
            analyzer = get_ai_threat_analyzer()

            for i, log_entry in enumerate(test_logs, 1):
                self.print_subsection(f"分析日志条目 {i}")
                print(f"原始日志: {json.dumps(log_entry, ensure_ascii=False, indent=2)}")

                # 执行AI分析
                print("\n正在进行AI威胁分析...")
                start_time = time.time()

                analysis = analyzer.analyze_log_entry(log_entry)

                end_time = time.time()
                print(f"分析耗时: {end_time - start_time:.2f}秒")

                # 显示分析结果
                if analysis:
                    print(f"\n🔍 威胁分析结果:")
                    print(f"  威胁等级: {analysis.threat_level}")
                    print(f"  威胁评分: {analysis.threat_score:.1f}/10")
                    print(f"  置信度: {analysis.confidence:.1f}")
                    print(f"  攻击类型: {', '.join(analysis.attack_types)}")
                    print(f"  风险因素: {', '.join(analysis.risk_factors)}")

                    if analysis.description:
                        print(f"  描述: {analysis.description}")
                    if analysis.recommendations:
                        print(f"  建议: {', '.join(analysis.recommendations)}")
                else:
                    print("❌ 分析失败")

                print("\n" + "-"*50)

        except Exception as e:
            print(f"❌ AI威胁分析演示失败: {e}")

    def demo_intelligent_analysis(self):
        """演示智能日志分析功能"""
        self.print_section("智能日志分析演示")

        # 批量日志数据
        batch_logs = [
            {"timestamp": "2024-01-15 10:30:00", "ip": "192.168.1.10", "action": "login", "user": "admin", "status": "success"},
            {"timestamp": "2024-01-15 10:30:15", "ip": "192.168.1.10", "action": "config_change", "user": "admin", "target": "/etc/ssh/sshd_config"},
            {"timestamp": "2024-01-15 10:30:30", "ip": "192.168.1.11", "action": "login", "user": "guest", "status": "failed"},
            {"timestamp": "2024-01-15 10:30:45", "ip": "192.168.1.11", "action": "login", "user": "guest", "status": "failed"},
            {"timestamp": "2024-01-15 10:31:00", "ip": "192.168.1.11", "action": "login", "user": "guest", "status": "failed"},
            {"timestamp": "2024-01-15 10:31:15", "ip": "10.0.0.100", "action": "port_scan", "target": "192.168.1.10", "ports": "22,80,443"},
        ]

        try:
            analyzer = get_intelligent_log_analyzer()

            self.print_subsection("批量分析日志")
            print(f"输入 {len(batch_logs)} 条日志记录")

            start_time = time.time()
            batch_results = analyzer.analyze_batch(batch_logs)
            end_time = time.time()

            print(f"批量分析完成，耗时: {end_time - start_time:.2f}秒")

            # 统计结果
            threats = [r for r in batch_results if r.is_threat]
            print(f"\n📊 分析统计:")
            print(f"  总日志数: {len(batch_results)}")
            print(f"  检测到威胁: {len(threats)}")
            print(f"  威胁率: {len(threats)/len(batch_results)*100:.1f}%")

            # 显示威胁详情
            if threats:
                self.print_subsection("检测到的威胁")
                for i, threat in enumerate(threats[:3], 1):  # 只显示前3个
                    print(f"\n威胁 {i}:")
                    print(f"  IP: {threat.log_entry.get('ip')}")
                    print(f"  动作: {threat.log_entry.get('action')}")
                    print(f"  评分: {threat.threat_score:.1f}/10")
                    print(f"  等级: {threat.threat_level}")
                    print(f"  攻击类型: {', '.join(threat.attack_types)}")

                    # 显示关键发现
                    key_findings = []
                    if threat.threat_score >= 7.0:
                        key_findings.append("高危威胁")
                    if threat.log_entry.get('ip') in analyzer.ip_reputation:
                        key_findings.append("已知恶意IP")
                    if len(threat.attack_types) > 1:
                        key_findings.append("复合攻击")

                    if key_findings:
                        print(f"  关键发现: {', '.join(key_findings)}")

        except Exception as e:
            print(f"❌ 智能分析演示失败: {e}")

    def demo_natural_language_query(self):
        """演示自然语言查询功能"""
        self.print_section("自然语言查询演示")

        # 示例查询
        test_queries = [
            "显示所有失败的登录尝试",
            "查找来自IP 192.168.1.100的可疑活动",
            "统计今天的安全事件数量",
            "检测到哪些端口扫描行为？",
            "显示高风险威胁事件"
        ]

        # 模拟日志数据
        sample_logs = [
            {"timestamp": "2024-01-15 10:30:00", "ip": "192.168.1.100", "action": "login", "user": "admin", "status": "success"},
            {"timestamp": "2024-01-15 10:31:00", "ip": "192.168.1.100", "action": "login", "user": "guest", "status": "failed"},
            {"timestamp": "2024-01-15 10:32:00", "ip": "10.0.0.50", "action": "port_scan", "target": "192.168.1.0/24", "ports": "22,80,443"},
            {"timestamp": "2024-01-15 10:33:00", "ip": "172.16.0.25", "action": "file_access", "user": "root", "file": "/etc/shadow", "status": "denied"},
        ]

        try:
            nli = get_natural_language_interface()

            for i, query in enumerate(test_queries, 1):
                self.print_subsection(f"查询 {i}: {query}")

                # 处理查询
                start_time = time.time()
                result = nli.process_query(query, sample_logs)
                end_time = time.time()

                print(f"查询耗时: {end_time - start_time:.2f}秒")
                print(f"查询类型: {result.query_type}")
                print(f"置信度: {result.confidence:.1f}")

                if result.answer:
                    print(f"回答: {result.answer}")

                if result.results:
                    print(f"找到 {len(result.results)} 条匹配记录:")
                    for j, log in enumerate(result.results[:3], 1):  # 只显示前3条
                        print(f"  {j}. {log}")

                if result.suggestions:
                    print(f"建议: {', '.join(result.suggestions)}")

                print("\n" + "-"*40)

        except Exception as e:
            print(f"❌ 自然语言查询演示失败: {e}")

    def demo_configuration_management(self):
        """演示配置管理功能"""
        self.print_section("配置管理演示")

        try:
            config = self.config_manager

            self.print_subsection("当前AI配置")

            # LM Studio配置
            lm_config = config.get_lm_studio_config()
            print(f"LM Studio主机: {lm_config.host}:{lm_config.port}")
            print(f"首选模型: {lm_config.model_name or '自动选择'}")
            print(f"最大令牌: {lm_config.max_tokens}")
            print(f"温度参数: {lm_config.temperature}")

            # AI功能开关
            features = config.get_ai_features_config()
            print(f"\nAI功能状态:")
            print(f"  威胁分析: {'✅' if features.threat_analysis else '❌'}")
            print(f"  自然语言查询: {'✅' if features.natural_language_query else '❌'}")
            print(f"  规则解释: {'✅' if features.rule_explanation else '❌'}")
            print(f"  安全建议: {'✅' if features.security_recommendations else '❌'}")
            print(f"  批量分析: {'✅' if features.batch_analysis else '❌'}")

            # 分析配置
            analysis_config = config.get_analysis_config()
            print(f"\n分析配置:")
            print(f"  AI权重: {analysis_config['scoring_weights'].ai_weight}")
            print(f"  规则权重: {analysis_config['scoring_weights'].rule_weight}")
            print(f"  置信度阈值: {analysis_config['thresholds'].confidence_threshold}")
            print(f"  威胁评分阈值: {analysis_config['thresholds'].threat_score_threshold}")

            # 性能配置
            perf_config = config.get_performance_config()
            print(f"\n性能配置:")
            print(f"  最大并发: {perf_config.max_concurrent_requests}")
            print(f"  批处理大小: {perf_config.batch_size}")
            print(f"  请求超时: {perf_config.request_timeout}秒")

            # 验证配置
            self.print_subsection("配置验证")
            issues = config.validate_config()
            if issues:
                print(f"⚠️ 发现 {len(issues)} 个配置问题:")
                for issue in issues:
                    print(f"  - {issue}")
            else:
                print("✅ 配置验证通过")

        except Exception as e:
            print(f"❌ 配置管理演示失败: {e}")

    def run_performance_test(self):
        """运行性能测试"""
        self.print_section("性能测试")

        test_logs = [
            {"timestamp": "2024-01-15 10:30:00", "ip": "192.168.1.100", "action": "login", "user": "admin"},
            {"timestamp": "2024-01-15 10:31:00", "ip": "10.0.0.50", "action": "sudo", "user": "root"},
            {"timestamp": "2024-01-15 10:32:00", "ip": "203.0.113.10", "action": "port_scan", "target": "192.168.1.0/24"},
        ]

        try:
            analyzer = get_ai_threat_analyzer()

            self.print_subsection("单次分析性能")
            times = []
            for i, log in enumerate(test_logs, 1):
                start = time.time()
                result = analyzer.analyze_log_entry(log)
                end = time.time()

                duration = end - start
                times.append(duration)
                print(f"日志 {i}: {duration:.2f}秒")

            avg_time = sum(times) / len(times)
            print(f"\n平均分析时间: {avg_time:.2f}秒")
            print(f"最快分析: {min(times):.2f}秒")
            print(f"最慢分析: {max(times):.2f}秒")

            # 缓存效果测试
            self.print_subsection("缓存效果测试")
            if len(test_logs) > 0:
                log = test_logs[0]

                # 第一次分析（无缓存）
                start = time.time()
                analyzer.analyze_log_entry(log)
                first_time = time.time() - start

                # 第二次分析（有缓存）
                start = time.time()
                analyzer.analyze_log_entry(log)
                cached_time = time.time() - start

                print(f"首次分析: {first_time:.2f}秒")
                print(f"缓存分析: {cached_time:.2f}秒")
                print(f"缓存加速: {(first_time - cached_time) / first_time * 100:.1f}%")

        except Exception as e:
            print(f"❌ 性能测试失败: {e}")

    def run_demo(self):
        """运行完整演示"""
        print("🚀 SSlogs AI功能演示")
        print("本演示将展示AI增强的安全日志分析功能")

        # 检查LM Studio连接
        if not self.check_lm_studio_connection():
            print("\n⚠️ LM Studio未连接，某些演示功能可能无法正常工作")
            print("您仍然可以查看配置管理和演示脚本的功能介绍")
            response = input("\n是否继续演示？(y/n): ")
            if response.lower() != 'y':
                return

        # 配置管理演示
        self.demo_configuration_management()

        # 如果LM Studio可用，运行AI功能演示
        if self.check_lm_studio_connection():
            self.demo_ai_threat_analysis()
            self.demo_intelligent_analysis()
            self.demo_natural_language_query()
            self.run_performance_test()

        self.print_section("演示完成")
        print("✅ 感谢您观看SSlogs AI功能演示!")
        print("\n💡 提示:")
        print("1. 确保LM Studio持续运行以获得最佳AI分析体验")
        print("2. 可以通过 config/ai_config.yaml 调整AI功能配置")
        print("3. 查看日志了解详细的AI分析过程")
        print("4. 根据需要调整威胁评分阈值和AI权重")


def main():
    """主函数"""
    demo = AIDemo()

    try:
        demo.run_demo()
    except KeyboardInterrupt:
        print("\n\n⏹️ 演示被用户中断")
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()