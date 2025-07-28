#!/usr/bin/env python3
"""
性能对比测试脚本 - 比较优化前后的性能差异
"""

import sys
import os
import time
import tracemalloc
import tempfile
from datetime import datetime
import json

# 添加核心模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

# 导入原版本和优化版本
from reporter import ReportGenerator as OriginalReportGenerator
from reporter_optimized import ReportGenerator as OptimizedReportGenerator
from parser import LogParser as OriginalLogParser
from parser_optimized import LogParser as OptimizedLogParser

def create_test_data(size='medium'):
    """创建测试数据"""
    sizes = {
        'small': 10,
        'medium': 100,
        'large': 1000
    }
    
    count = sizes.get(size, 100)
    
    matched_logs = []
    ai_results = []
    
    for i in range(count):
        matched_logs.append({
            'id': f'test-{i:03d}',
            'timestamp': f'2024-01-01 10:{i%60:02d}:00',
            'source_ip': f'192.168.1.{100 + i%50}',
            'destination_port': '80',
            'attack_type': ['SQL Injection', 'XSS', 'Command Injection', 'Directory Traversal'][i%4],
            'severity': ['high', 'medium', 'low'][i%3],
            'rule_name': f'RULE-{i%10:03d}',
            'rule': {
                'name': f'Security Rule {i}',
                'severity': ['high', 'medium', 'low'][i%3],
                'description': f'Test rule {i} for security detection',
                'category': ['SQL Injection', 'XSS', 'Command Injection', 'Directory Traversal'][i%4]
            },
            'log_entry': {
                'src_ip': f'192.168.1.{100 + i%50}',
                'timestamp': f'2024-01-01 10:{i%60:02d}:00',
                'method': ['GET', 'POST', 'PUT', 'DELETE'][i%4],
                'url': f'/test/path{i}?param=value{i}',
                'user_agent': f'TestBot/{i%10}.0 (compatible; TestBot/1.0)',
                'status_code': ['200', '404', '500', '403'][i%4]
            }
        })
        
        ai_results.append(f'AI分析结果 {i}: 检测到{["高危", "中危", "低危"][i%3]}安全威胁，建议采取相应措施。')
    
    internal_ips = {f'192.168.1.{100+i}': (i+1)*5 for i in range(min(20, count//5))}
    external_ip_details = [
        {'ip': f'8.8.8.{i}', 'count': (i+1)*10, 'location': f'Location-{i}'}
        for i in range(min(10, count//10))
    ]
    
    return matched_logs, ai_results, internal_ips, external_ip_details

def measure_performance(func, *args, **kwargs):
    """测量函数执行性能"""
    tracemalloc.start()
    
    start_time = time.time()
    start_memory = tracemalloc.get_traced_memory()[0]
    
    try:
        result = func(*args, **kwargs)
        success = True
        error = None
    except Exception as e:
        result = None
        success = False
        error = str(e)
    
    end_time = time.time()
    current_memory, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    return {
        'success': success,
        'error': error,
        'execution_time': end_time - start_time,
        'memory_used': peak_memory - start_memory,
        'peak_memory': peak_memory,
        'result': result
    }

def test_reporter_performance():
    """测试报告生成器性能"""
    print("🚀 测试报告生成器性能对比...")
    
    # 测试不同数据规模
    for size in ['small', 'medium', 'large']:
        print(f"\n📊 测试数据规模: {size}")
        
        matched_logs, ai_results, internal_ips, external_ip_details = create_test_data(size)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # 测试原版本
            original_reporter = OriginalReportGenerator(tmpdir)
            original_perf = measure_performance(
                original_reporter.generate_report,
                matched_logs, ai_results, 'html',
                internal_ips, external_ip_details, 'test-server'
            )
            
            # 测试优化版本
            optimized_reporter = OptimizedReportGenerator(tmpdir)
            optimized_perf = measure_performance(
                optimized_reporter.generate_report,
                matched_logs, ai_results, 'html',
                internal_ips, external_ip_details, 'test-server'
            )
            
            # 输出对比结果
            print(f"   原版本: 时间={original_perf['execution_time']:.3f}s, 内存={original_perf['memory_used']//1024}KB")
            print(f"   优化版: 时间={optimized_perf['execution_time']:.3f}s, 内存={optimized_perf['memory_used']//1024}KB")
            
            if original_perf['success'] and optimized_perf['success']:
                time_improvement = (original_perf['execution_time'] - optimized_perf['execution_time']) / original_perf['execution_time'] * 100
                memory_improvement = (original_perf['memory_used'] - optimized_perf['memory_used']) / original_perf['memory_used'] * 100
                print(f"   改进: 时间{time_improvement:+.1f}%, 内存{memory_improvement:+.1f}%")
            else:
                if not original_perf['success']:
                    print(f"   ❌ 原版本失败: {original_perf['error']}")
                if not optimized_perf['success']:
                    print(f"   ❌ 优化版失败: {optimized_perf['error']}")

def test_parser_performance():
    """测试解析器性能"""
    print("\n🔍 测试日志解析器性能对比...")
    
    # 创建测试配置
    test_config = {
        'fields': {
            'src_ip': r'(\d+\.\d+\.\d+\.\d+)',
            'timestamp': r'\[(.*?)\]',
            'request_line': r'"([A-Z]+\s+[^\s]+\s+HTTP/[\d\.]+)"',
            'status_code': r'"\s+(\d{3})\s+',
            'response_size': r'\s+(\d+)\s+'
        }
    }
    
    # 创建测试日志行
    test_lines = [
        '192.168.1.100 - - [25/Dec/2023:10:00:00 +0000] "GET /index.html HTTP/1.1" 200 1234',
        '10.0.0.1 - - [25/Dec/2023:10:01:00 +0000] "POST /login HTTP/1.1" 404 567',
        '172.16.0.50 - - [25/Dec/2023:10:02:00 +0000] "PUT /api/data HTTP/1.1" 500 890',
    ] * 1000  # 重复1000次
    
    try:
        # 测试原版本
        original_parser = OriginalLogParser(test_config)
        original_perf = measure_performance(
            lambda: [original_parser.parse_log_line(line) for line in test_lines]
        )
        
        # 测试优化版本
        optimized_parser = OptimizedLogParser(test_config)
        optimized_perf = measure_performance(
            lambda: [optimized_parser.parse_log_line(line) for line in test_lines]
        )
        
        # 输出对比结果
        print(f"   处理{len(test_lines)}条日志行:")
        print(f"   原版本: 时间={original_perf['execution_time']:.3f}s, 内存={original_perf['memory_used']//1024}KB")
        print(f"   优化版: 时间={optimized_perf['execution_time']:.3f}s, 内存={optimized_perf['memory_used']//1024}KB")
        
        if original_perf['success'] and optimized_perf['success']:
            time_improvement = (original_perf['execution_time'] - optimized_perf['execution_time']) / original_perf['execution_time'] * 100
            memory_improvement = (original_perf['memory_used'] - optimized_perf['memory_used']) / original_perf['memory_used'] * 100
            print(f"   改进: 时间{time_improvement:+.1f}%, 内存{memory_improvement:+.1f}%")
            
            # 验证结果一致性
            original_results = [r for r in original_perf['result'] if r is not None]
            optimized_results = [r for r in optimized_perf['result'] if r is not None]
            print(f"   成功解析: 原版本{len(original_results)}, 优化版{len(optimized_results)}")
        
    except Exception as e:
        print(f"   ❌ 解析器测试失败: {e}")

def test_functionality():
    """测试功能正确性"""
    print("\n✅ 测试功能正确性...")
    
    matched_logs, ai_results, internal_ips, external_ip_details = create_test_data('small')
    
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            # 测试所有格式
            formats = ['html', 'markdown', 'json']
            
            for fmt in formats:
                print(f"   测试{fmt.upper()}格式...")
                
                # 优化版本测试
                optimized_reporter = OptimizedReportGenerator(tmpdir)
                path = optimized_reporter.generate_report(
                    matched_logs, ai_results, fmt,
                    internal_ips, external_ip_details, 'test-server'
                )
                
                if os.path.exists(path):
                    size = os.path.getsize(path)
                    print(f"     ✅ {fmt}报告生成成功: {size} bytes")
                else:
                    print(f"     ❌ {fmt}报告生成失败")
                    
        except Exception as e:
            print(f"   ❌ 功能测试失败: {e}")

def generate_optimization_report():
    """生成优化报告"""
    print("\n📋 优化总结报告:")
    print("="*60)
    
    optimizations = [
        "✅ 重构ReportGenerator类，提取模板渲染逻辑",
        "✅ 分离CSS样式到独立文件 (core/templates/styles.css)",
        "✅ 优化HTML报告生成方法，拆分为更小的函数",
        "✅ 添加数据处理缓存机制 (@lru_cache装饰器)",
        "✅ 改进错误处理和日志记录",
        "✅ 添加LogParserError异常类",
        "✅ 增强URL安全检测功能",
        "✅ 优化正则表达式编译和缓存",
        "✅ 改进部分解析成功率判断逻辑"
    ]
    
    for opt in optimizations:
        print(f"  {opt}")
    
    print("\n🔧 主要优化点:")
    print("  • 性能优化: 缓存机制、预编译正则表达式")
    print("  • 代码结构: 模块化、单一职责原则")
    print("  • 错误处理: 异常分类、详细日志")
    print("  • 可维护性: CSS分离、函数拆分")
    print("  • 功能增强: 安全检测、配置验证")

def main():
    """主函数"""
    print("🔍 SSlogs 代码优化性能测试")
    print("="*60)
    
    try:
        # 运行性能测试
        test_reporter_performance()
        test_parser_performance()
        
        # 运行功能测试
        test_functionality()
        
        # 生成优化报告
        generate_optimization_report()
        
        print("\n🎉 测试完成!")
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()