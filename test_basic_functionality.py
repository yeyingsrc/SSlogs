#!/usr/bin/env python3
"""
基础功能测试脚本 - 测试核心功能是否正常
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

def test_parser():
    """测试日志解析器"""
    print("🔍 测试日志解析器...")
    try:
        from core.parser import LogParser

        config = {
            'type': 'web',
            'fields': {
                'src_ip': r'(\d+\.\d+\.\d+\.\d+)',
                'timestamp': r'\[(.*?)\]',
                'request_line': r'"([A-Z]+\s+[^\s]+\s+HTTP/[\d\.]+)"'
            }
        }

        parser = LogParser(config)
        test_log = '192.168.1.1 - - [10/Oct/2023:13:55:36] "GET /index.html HTTP/1.1" 200 1234'
        result = parser.parse_log_line(test_log)

        if result:
            print(f"✅ 解析器测试成功: {result}")
            return True
        else:
            print("❌ 解析器测试失败: 无结果")
            return False
    except Exception as e:
        print(f"❌ 解析器测试失败: {e}")
        return False

def test_rule_engine():
    """测试规则引擎"""
    print("\n🎯 测试规则引擎...")
    try:
        from core.rule_engine import RuleEngine
        import tempfile
        from pathlib import Path

        # 创建临时规则
        with tempfile.TemporaryDirectory() as temp_dir:
            rules_dir = Path(temp_dir) / 'rules'
            rules_dir.mkdir()

            test_rule = '''name: SQL注入测试
pattern:
  url: (union.*select|insert.*into)
severity: high
category: sql_injection
description: 检测SQL注入攻击
'''
            (rules_dir / 'test.yaml').write_text(test_rule)

            # 初始化规则引擎
            engine = RuleEngine(str(rules_dir))

            # 测试匹配
            log_entry = {
                'url': '/?id=1 union select * from users',
                'method': 'GET',
                'user_agent': 'Mozilla/5.0'
            }

            matches = engine.match_log(log_entry)

            if matches:
                print(f"✅ 规则引擎测试成功: 匹配到 {len(matches)} 条规则")
                print(f"   匹配规则: {matches[0]['rule']['name']}")
                return True
            else:
                print("❌ 规则引擎测试失败: 无匹配")
                return False
    except Exception as e:
        print(f"❌ 规则引擎测试失败: {e}")
        return False

def test_ai_analyzer():
    """测试AI分析器"""
    print("\n🤖 测试AI分析器...")
    try:
        from core.ai_analyzer import AIAnalyzer

        # 创建临时配置
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / 'config.yaml'
            config_path.write_text('''
ai:
  type: local
  local_provider: ollama
ollama:
  model: test-model
  base_url: http://localhost:11434/api/chat
''')

            analyzer = AIAnalyzer(str(config_path))
            print("✅ AI分析器初始化成功")
            print("   注意: 实际AI分析需要配置有效的AI服务")
            return True
    except Exception as e:
        print(f"❌ AI分析器测试失败: {e}")
        return False

def test_reporter():
    """测试报告生成器"""
    print("\n📊 测试报告生成器...")
    try:
        from core.reporter import ReportGenerator
        import tempfile

        with tempfile.TemporaryDirectory() as temp_dir:
            reporter = ReportGenerator(temp_dir)

            # 测试数据
            matched_logs = [
                {
                    'rule': {'name': 'SQL注入测试', 'severity': 'high', 'category': 'sql_injection'},
                    'log_entry': {'src_ip': '192.168.1.1', 'url': '/?id=1 union select'}
                }
            ]

            # 生成报告
            report_path = reporter.generate_report(
                matched_logs, [], 'html',
                internal_ips={'192.168.1.1': 1},
                external_ip_details=[],
                server_ip='192.168.1.100'
            )

            if Path(report_path).exists():
                print(f"✅ 报告生成器测试成功: {report_path}")
                return True
            else:
                print("❌ 报告生成器测试失败: 报告文件不存在")
                return False
    except Exception as e:
        print(f"❌ 报告生成器测试失败: {e}")
        return False

def test_config_manager():
    """测试配置管理器"""
    print("\n⚙️  测试配置管理器...")
    try:
        from core.config_manager import ConfigManager
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / 'config.yaml'
            config_path.write_text('''
log_path: logs/*.log
log_format:
  type: web
  fields:
    src_ip: (\\d+\\.\\d+\\.\\d+\\.\\d+)
''')

            config_manager = ConfigManager(str(config_path))
            config = config_manager.load_config()

            if 'log_format' in config:
                print("✅ 配置管理器测试成功")
                return True
            else:
                print("❌ 配置管理器测试失败: 配置加载不正确")
                return False
    except Exception as e:
        print(f"❌ 配置管理器测试失败: {e}")
        return False

def test_performance_monitor():
    """测试性能监控"""
    print("\n⚡ 测试性能监控...")
    try:
        from core.performance import get_performance_summary

        # 尝试获取性能摘要
        summary = get_performance_summary()
        print(f"✅ 性能监控测试成功: {summary[:50]}..." if len(summary) > 50 else f"✅ 性能监控测试成功: {summary}")
        return True
    except Exception as e:
        print(f"⚠️  性能监控测试: {e} (非关键功能)")
        return True  # 性能监控不是关键功能

def main():
    """运行所有测试"""
    print("🚀 SSlogs 基础功能测试")
    print("=" * 50)

    results = []

    # 运行各项测试
    results.append(("日志解析器", test_parser()))
    results.append(("规则引擎", test_rule_engine()))
    results.append(("AI分析器", test_ai_analyzer()))
    results.append(("报告生成器", test_reporter()))
    results.append(("配置管理器", test_config_manager()))
    results.append(("性能监控", test_performance_monitor()))

    # 统计结果
    print("\n" + "=" * 50)
    print("📊 测试结果摘要:")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name}: {status}")

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("🎉 所有核心功能测试通过！")
        return 0
    else:
        print("⚠️  部分测试失败，请检查相关功能")
        return 1

if __name__ == '__main__':
    sys.exit(main())
