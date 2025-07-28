#!/usr/bin/env python3
"""
测试reporter.py功能的简单脚本
"""

import sys
import os
import tempfile
from datetime import datetime

# 添加核心模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

from reporter import ReportGenerator

def test_reporter():
    """测试报告生成功能"""
    print("🧪 开始测试Reporter模块...")
    
    # 创建测试数据
    matched_logs = [
        {
            'id': 'test-001',
            'timestamp': '2024-01-01 10:00:00',
            'source_ip': '192.168.1.100',
            'destination_port': '80',
            'attack_type': 'SQL Injection',
            'severity': 'high',
            'rule_name': 'SQL-001',
            'rule': {
                'name': 'SQL Injection Detection',
                'severity': 'high',
                'description': 'Detects SQL injection attempts',
                'category': 'SQL Injection'
            },
            'log_entry': {
                'src_ip': '192.168.1.100',
                'timestamp': '2024-01-01 10:00:00',
                'method': 'GET',
                'url': '/test?id=1 UNION SELECT * FROM users',
                'user_agent': 'Mozilla/5.0 (compatible; Bot/1.0)'
            }
        },
        {
            'id': 'test-002',
            'timestamp': '2024-01-01 10:05:00',
            'source_ip': '8.8.8.8',
            'destination_port': '443',
            'attack_type': 'Brute Force',
            'severity': 'medium',
            'rule_name': 'BRUTE-001',
            'rule': {
                'name': 'Brute Force Attack',
                'severity': 'medium',
                'description': 'Detects brute force login attempts',
                'category': 'Brute Force'
            },
            'log_entry': {
                'src_ip': '8.8.8.8',
                'timestamp': '2024-01-01 10:05:00',
                'method': 'POST',
                'url': '/login',
                'user_agent': 'curl/7.68.0'
            }
        }
    ]
    
    ai_results = [
        '检测到可疑的SQL注入攻击模式，建议立即检查数据库日志',
        '发现暴力破解攻击，建议启用IP限制策略'
    ]
    
    internal_ips = {'192.168.1.100': 5, '192.168.1.101': 3}
    external_ip_details = [
        {'ip': '8.8.8.8', 'count': 10, 'location': 'Google DNS'},
        {'ip': '1.1.1.1', 'count': 5, 'location': 'Cloudflare DNS'}
    ]
    
    # 使用临时目录测试
    with tempfile.TemporaryDirectory() as tmpdir:
        reporter = ReportGenerator(tmpdir)
        
        print(f"📁 输出目录: {tmpdir}")
        
        # 测试所有格式
        formats = ['html', 'markdown', 'json']
        results = {}
        
        for fmt in formats:
            try:
                path = reporter.generate_report(
                    matched_logs, ai_results, fmt,
                    internal_ips, external_ip_details, 'test-server'
                )
                
                if os.path.exists(path):
                    size = os.path.getsize(path)
                    results[fmt] = {'path': path, 'size': size, 'status': 'success'}
                    print(f"✅ {fmt.upper()}报告: {os.path.basename(path)} ({size} bytes)")
                else:
                    results[fmt] = {'status': 'failed', 'error': '文件未创建'}
                    print(f"❌ {fmt}格式: 文件未创建")
                    
            except Exception as e:
                results[fmt] = {'status': 'failed', 'error': str(e)}
                print(f"❌ {fmt}格式失败: {e}")
        
        # 验证结果
        success_count = sum(1 for r in results.values() if r['status'] == 'success')
        print(f"\n📊 测试结果: {success_count}/3 成功")
        
        if success_count == 3:
            print("🎉 所有测试通过！Reporter模块工作正常")
            return True
        else:
            print("⚠️  部分测试失败")
            return False

if __name__ == '__main__':
    test_reporter()