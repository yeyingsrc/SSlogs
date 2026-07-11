#!/usr/bin/env python3
"""
SSlogs 基本使用示例
"""
import yaml
from core.parser import LogParser
from core.rule_engine import RuleEngine
from core.reporter import ReportGenerator


def basic_log_analysis():
    """基本日志分析示例"""
    # 1. 创建配置
    config = {
        'log_path': 'logs/*.log',
        'log_format': {
            'type': 'web',
            'fields': {
                'src_ip': r'(\d+\.\d+\.\d+\.\d+)',
                'timestamp': r'\[(.*?)\]',
                'request_line': r'"([A-Z]+\s+[^\s]+\s+HTTP/[\d\.]+)"',
                'status_code': r'"\s+(\d{3})\s+',
                'response_size': r'\s+(\d+)\s+'
            }
        },
        'rule_dir': 'rules',
        'output_dir': 'output',
        'server': {'ip': '192.168.1.100'}
    }

    # 2. 初始化日志解析器
    parser = LogParser(config['log_format'])
    print("✅ 日志解析器初始化成功")

    # 3. 示例日志解析
    sample_log = '192.168.1.100 - - [25/Dec/2023:10:00:00 +0000] "GET /index.html HTTP/1.1" 200 1234'
    parsed_log = parser.parse_log_line(sample_log)

    if parsed_log:
        print("📊 日志解析结果:")
        print(f"  源IP: {parsed_log.get('src_ip')}")
        print(f"  时间戳: {parsed_log.get('timestamp')}")
        print(f"  方法: {parsed_log.get('method')}")
        print(f"  URL: {parsed_log.get('url')}")

    # 4. 初始化规则引擎
    rule_engine = RuleEngine(config['rule_dir'])
    print("✅ 规则引擎初始化成功")

    # 5. 检查日志条目
    if parsed_log:
        matches = rule_engine.match_log(parsed_log)
        if matches:
            print(f"⚠️  检测到 {len(matches)} 个安全事件")
            for match in matches:
                print(f"  - {match['rule']['name']} ({match['rule']['severity']})")
        else:
            print("✅ 未检测到安全问题")

    # 6. 获取解析统计信息
    stats = parser.get_statistics()
    print("📈 解析统计:")
    print(f"  成功解析: {stats['parsed_count']}")
    print(f"  解析失败: {stats['failed_count']}")
    print(f"  拒绝处理: {stats['blocked_count']}")

    # 7. 获取缓存统计
    cache_stats = parser.get_cache_statistics()
    print("💾 缓存统计:")
    print(f"  缓存命中率: {cache_stats['hit_rate']:.1%}")
    print(f"  缓存大小: {cache_stats['cache_size']}")

    return parsed_log, matches if matches else []


def batch_log_analysis():
    """批量日志分析示例"""
    config = {
        'log_path': 'logs/*.log',
        'log_format': {
            'type': 'web',
            'fields': {
                'src_ip': r'(\d+\.\d+\.\d+\.\d+)',
                'timestamp': r'\[(.*?)\]',
                'request_line': r'"([A-Z]+\s+[^\s]+\s+HTTP/[\d\.]+)"',
                'status_code': r'"\s+(\d{3})\s+',
                'response_size': r'\s+(\d+)\s+'
            }
        },
        'rule_dir': 'rules',
        'output_dir': 'output'
    }

    # 示例日志数据
    sample_logs = [
        '192.168.1.100 - - [25/Dec/2023:10:00:00 +0000] "GET /index.html HTTP/1.1" 200 1234',
        '198.51.100.1 - - [25/Dec/2023:10:01:00 +0000] "GET /?id=1 union select * from users HTTP/1.1" 200 567',
        '10.0.0.50 - - [25/Dec/2023:10:02:00 +0000] "POST /admin/login HTTP/1.1" 403 890',
        '172.16.0.75 - - [25/Dec/2023:10:03:00 +0000] "GET /config.php HTTP/1.1" 200 234'
    ]

    parser = LogParser(config['log_format'])
    rule_engine = RuleEngine(config['rule_dir'])

    print("🔍 批量日志分析开始...")
    all_matches = []

    for i, log_line in enumerate(sample_logs, 1):
        parsed = parser.parse_log_line(log_line)
        if parsed:
            matches = rule_engine.match_log(parsed)
            if matches:
                print(f"🚨 事件 #{i}: {matches[0]['rule']['name']}")
                all_matches.extend(matches)

    print(f"\n📊 分析完成，共发现 {len(all_matches)} 个安全事件")

    return all_matches


def generate_report_example():
    """报告生成示例"""
    from core.reporter import ReportGenerator

    # 创建示例数据
    matched_logs = [
        {
            'rule': {
                'name': 'SQL注入攻击检测',
                'severity': 'high',
                'category': 'sql_injection',
                'description': '检测到SQL注入攻击尝试'
            },
            'log_entry': {
                'src_ip': '198.51.100.1',
                'timestamp': '2023-12-25 10:01:00',
                'method': 'GET',
                'url': '/?id=1 union select * from users',
                'status_code': '200'
            }
        }
    ]

    ai_results = [
        '## SQL注入攻击分析\n\n### 攻击技术分析\n检测到SQL注入攻击尝试...'
    ]

    internal_ips = {'192.168.1.100': 5, '192.168.1.101': 3}
    external_ip_details = [
        {'ip': '198.51.100.1', 'count': 10, 'location': 'United States'}
    ]

    # 生成HTML报告
    reporter = ReportGenerator('output')
    report_path = reporter.generate_report(
        matched_logs, ai_results, 'html',
        internal_ips=internal_ips,
        external_ip_details=external_ip_details,
        server_ip='192.168.1.100'
    )

    print(f"📋 报告已生成: {report_path}")
    return report_path


if __name__ == '__main__':
    print("🚀 SSlogs 基本使用示例")
    print("=" * 50)

    try:
        # 运行基本分析示例
        print("\n1️⃣  基本日志分析:")
        basic_log_analysis()

        # 运行批量分析示例
        print("\n2️⃣  批量日志分析:")
        batch_log_analysis()

        # 运行报告生成示例
        print("\n3️⃣  报告生成:")
        generate_report_example()

        print("\n✅ 所有示例运行完成")

    except Exception as e:
        print(f"\n❌ 示例运行失败: {e}")
        import traceback
        traceback.print_exc()