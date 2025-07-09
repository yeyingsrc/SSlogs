#!/usr/bin/env python3
"""
日志分析工具测试脚本
用于验证各个模块的功能
"""

import os
import sys
import logging
from typing import List, Dict

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.parser import LogParser
from core.rule_engine import RuleEngine
from core.ai_analyzer import AIAnalyzer
from core.reporter import ReportGenerator

def setup_logging():
    """配置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def test_log_parser():
    """测试日志解析器"""
    print("=" * 50)
    print("测试日志解析器")
    print("=" * 50)
    
    # 示例日志格式配置
    log_format_config = {
        'fields': [
            {'name': 'src_ip', 'regex': r'(\d+\.\d+\.\d+\.\d+)'},
            {'name': 'timestamp', 'regex': r'\[(.*?)\]'},
            {'name': 'request_line', 'regex': r'"([^"]*)"'},
            {'name': 'status', 'regex': r' (\d{3}) '},
            {'name': 'size', 'regex': r'(\d+)'},
            {'name': 'user_agent', 'regex': r'"([^"]*)"'}
        ]
    }
    
    parser = LogParser(log_format_config)
    
    # 测试日志行
    test_logs = [
        '192.168.1.100 [10/Oct/2023:13:55:36 +0800] "GET /index.php HTTP/1.1" 200 1234 "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"',
        '10.0.0.1 [10/Oct/2023:14:00:00 +0800] "POST /login.php HTTP/1.1" 200 512 "curl/7.68.0"'
    ]
    
    for i, log_line in enumerate(test_logs, 1):
        print(f"\n测试日志 {i}: {log_line}")
        result = parser.parse_log_line(log_line)
        if result:
            print("解析成功:")
            for key, value in result.items():
                print(f"  {key}: {value}")
        else:
            print("解析失败")

def test_rule_engine():
    """测试规则引擎"""
    print("\n" + "=" * 50)
    print("测试规则引擎")
    print("=" * 50)
    
    try:
        rule_engine = RuleEngine("rules")
        print(f"加载了 {len(rule_engine.rules)} 个规则")
        
        # 测试日志条目
        test_log_entry = {
            'src_ip': '192.168.1.100',
            'request_line': 'GET /admin/config.php?id=1 UNION SELECT * FROM users-- HTTP/1.1',
            'user_agent': 'sqlmap/1.0',
            'url': '/admin/config.php?id=1 UNION SELECT * FROM users--',
            'method': 'GET'
        }
        
        print(f"\n测试日志条目: {test_log_entry}")
        matches = rule_engine.match_log(test_log_entry)
        
        if matches:
            print(f"匹配到 {len(matches)} 个规则:")
            for match in matches:
                rule = match['rule']
                print(f"  - 规则: {rule['name']}")
                print(f"    严重程度: {rule.get('severity', 'unknown')}")
                print(f"    类别: {rule.get('category', 'unknown')}")
        else:
            print("未匹配到任何规则")
            
    except FileNotFoundError as e:
        print(f"规则引擎测试失败: {e}")

def test_ai_analyzer():
    """测试AI分析器"""
    print("\n" + "=" * 50)
    print("测试AI分析器")
    print("=" * 50)
    
    try:
        ai_analyzer = AIAnalyzer("config.yaml")
        
        # 测试日志上下文
        test_context = """
1: 192.168.1.100 [10/Oct/2023:13:55:36 +0800] "GET /index.php HTTP/1.1" 200 1234
2: 192.168.1.100 [10/Oct/2023:13:55:37 +0800] "GET /admin/login.php HTTP/1.1" 200 512
3: 192.168.1.100 [10/Oct/2023:13:55:38 +0800] "POST /admin/login.php HTTP/1.1" 302 0
4: 192.168.1.100 [10/Oct/2023:13:55:39 +0800] "GET /admin/config.php?id=1' UNION SELECT * FROM users-- HTTP/1.1" 200 2048
5: 192.168.1.100 [10/Oct/2023:13:55:40 +0800] "GET /admin/dashboard.php HTTP/1.1" 200 4096
        """
        
        print("测试AI分析（可能需要一些时间...）")
        result = ai_analyzer.analyze_log(test_context)
        print(f"AI分析结果:\n{result}")
        
    except Exception as e:
        print(f"AI分析器测试失败: {e}")

def test_reporter():
    """测试报告生成器"""
    print("\n" + "=" * 50)
    print("测试报告生成器")
    print("=" * 50)
    
    # 创建测试数据
    matched_logs = [
        {
            'rule': {
                'name': 'SQL注入攻击检测',
                'severity': 'high',
                'category': 'injection'
            },
            'log_entry': {
                'src_ip': '192.168.1.100',
                'timestamp': '10/Oct/2023:13:55:39 +0800',
                'method': 'GET',
                'url': '/admin/config.php?id=1\' UNION SELECT * FROM users--',
                'user_agent': 'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)'
            }
        }
    ]
    
    ai_results = [
        "检测到SQL注入攻击尝试。攻击者试图通过UNION SELECT语句获取数据库中的用户信息。建议立即检查数据库日志并加强输入验证。"
    ]
    
    internal_ips = {
        '192.168.1.100': 45,
        '192.168.1.101': 23
    }
    
    external_ip_details = [
        {'ip': '203.208.60.1', 'count': 12, 'location': '中国'}
    ]
    
    reporter = ReportGenerator("test_output")
    
    # 测试HTML报告
    try:
        html_report_path = reporter.generate_report(
            matched_logs, ai_results, "html", 
            internal_ips, external_ip_details, "192.168.1.1"
        )
        print(f"HTML报告生成成功: {html_report_path}")
    except Exception as e:
        print(f"HTML报告生成失败: {e}")
    
    # 测试Markdown报告
    try:
        md_report_path = reporter.generate_report(
            matched_logs, ai_results, "markdown",
            internal_ips, external_ip_details, "192.168.1.1"
        )
        print(f"Markdown报告生成成功: {md_report_path}")
    except Exception as e:
        print(f"Markdown报告生成失败: {e}")
    
    # 测试JSON报告
    try:
        json_report_path = reporter.generate_report(
            matched_logs, ai_results, "json",
            internal_ips, external_ip_details, "192.168.1.1"
        )
        print(f"JSON报告生成成功: {json_report_path}")
    except Exception as e:
        print(f"JSON报告生成失败: {e}")

def main():
    """主测试函数"""
    setup_logging()
    
    print("日志分析工具测试开始")
    print("=" * 80)
    
    # 运行各模块测试
    test_log_parser()
    test_rule_engine()
    test_ai_analyzer()
    test_reporter()
    
    print("\n" + "=" * 80)
    print("所有测试完成")

if __name__ == "__main__":
    main()