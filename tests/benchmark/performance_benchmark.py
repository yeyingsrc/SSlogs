#!/usr/bin/env python3
"""
性能基准测试 - 用于验证优化后的代码性能并防止性能回归
"""
import time
import tracemalloc
import statistics
from typing import Callable, List, Dict, Any
from dataclasses import dataclass
from pathlib import Path
import tempfile
import sys

# 添加核心模块路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.parser import LogParser
from core.rule_engine import RuleEngine
from core.reporter import ReportGenerator
from core.performance import PerformanceTracker


@dataclass
class BenchmarkResult:
    """基准测试结果"""
    name: str
    execution_time: float
    memory_used: float
    operations_per_second: float
    success: bool
    metadata: Dict[str, Any] = None

    def __str__(self):
        return f"{self.name}: {self.execution_time:.3f}s, {self.memory_used:.1f}KB, {self.operations_per_second:.1f} ops/s"


class PerformanceBenchmark:
    """性能基准测试框架"""

    def __init__(self):
        self.results: List[BenchmarkResult] = []

    def run_benchmark(self, func: Callable, name: str, iterations: int = 100, **kwargs) -> BenchmarkResult:
        """运行单个基准测试

        Args:
            func: 要测试的函数
            name: 测试名称
            iterations: 迭代次数
            **kwargs: 传递给函数的额外参数

        Returns:
            BenchmarkResult: 测试结果
        """
        tracemalloc.start()
        start_time = time.time()
        start_memory = tracemalloc.get_traced_memory()[0]

        success = True
        operations_completed = 0

        try:
            for i in range(iterations):
                result = func(**kwargs)
                if result is not None:
                    operations_completed += 1
        except Exception as e:
            success = False
            print(f"基准测试失败 {name}: {e}")

        end_time = time.time()
        current_memory, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        execution_time = end_time - start_time
        memory_used = (peak_memory - start_memory) / 1024  # KB
        ops_per_second = operations_completed / execution_time if execution_time > 0 else 0

        result = BenchmarkResult(
            name=name,
            execution_time=execution_time,
            memory_used=memory_used,
            operations_per_second=ops_per_second,
            success=success,
            metadata={
                'iterations': iterations,
                'operations_completed': operations_completed
            }
        )

        self.results.append(result)
        return result

    def run_parser_benchmark(self):
        """运行解析器性能基准测试"""
        print("🔍 解析器性能基准测试...")

        # 创建测试配置
        config = {
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
        ] * 1000  # 3000行

        def parse_single_line(parser, line):
            return parser.parse_log_line(line)

        parser = LogParser(config)

        # 测试单行解析性能
        result = self.run_benchmark(
            lambda: parse_single_line(parser, test_lines[0]),
            name="解析器-单行解析",
            iterations=1000
        )
        print(f"  {result}")

        # 测试批量解析性能
        def parse_batch():
            return [parser.parse_log_line(line) for line in test_lines]

        batch_result = self.run_benchmark(
            parse_batch,
            name="解析器-批量解析3000行",
            iterations=10
        )
        print(f"  {batch_result}")

        # 测试缓存性能
        def parse_with_cache():
            # 重复解析相同内容，测试缓存效果
            return [parser.parse_log_line(test_lines[0]) for _ in range(1000)]

        cache_result = self.run_benchmark(
            parse_with_cache,
            name="解析器-缓存命中1000次",
            iterations=10
        )
        print(f"  {cache_result}")

        # 获取缓存统计
        cache_stats = parser.get_cache_statistics()
        print(f"  缓存命中率: {cache_stats['hit_rate']:.1%}")

    def run_rule_engine_benchmark(self):
        """运行规则引擎性能基准测试"""
        print("\n🎯 规则引擎性能基准测试...")

        # 加载规则引擎
        try:
            rule_engine = RuleEngine('rules', enable_ai_analysis=False)
        except Exception as e:
            print(f"  跳过规则引擎测试: {e}")
            return

        # 创建测试日志条目
        normal_log = {
            'src_ip': '192.168.1.50',
            'request_path': '/index.html',
            'method': 'GET',
            'user_agent': 'Mozilla/5.0',
            'status_code': '200',
        }

        attack_log = {
            'src_ip': '198.51.100.1',
            'request_path': '/?id=1 union select * from users',
            'method': 'GET',
            'user_agent': 'Mozilla/5.0',
            'status_code': '200',
        }

        # 测试正常流量处理性能
        def match_normal_traffic():
            return rule_engine.match_log(normal_log)

        result = self.run_benchmark(
            match_normal_traffic,
            name="规则引擎-正常流量匹配",
            iterations=1000
        )
        print(f"  {result}")

        # 测试攻击流量检测性能
        def match_attack_traffic():
            return rule_engine.match_log(attack_log)

        attack_result = self.run_benchmark(
            match_attack_traffic,
            name="规则引擎-攻击流量匹配",
            iterations=1000
        )
        print(f"  {attack_result}")

    def run_reporter_benchmark(self):
        """运行报告生成器性能基准测试"""
        print("\n📊 报告生成器性能基准测试...")

        # 创建测试数据
        matched_logs = []
        ai_results = []
        for i in range(100):
            matched_logs.append({
                'id': f'test-{i:03d}',
                'timestamp': f'2024-01-01 10:{i%60:02d}:00',
                'rule': {
                    'name': f'Security Rule {i}',
                    'severity': ['high', 'medium', 'low'][i%3],
                    'category': ['SQL Injection', 'XSS', 'Command Injection'][i%3],
                    'description': f'Test rule {i} for security detection'
                },
                'log_entry': {
                    'src_ip': f'192.168.1.{100 + i%50}',
                    'timestamp': f'2024-01-01 10:{i%60:02d}:00',
                    'method': ['GET', 'POST'][i%2],
                    'url': f'/test/path{i}?param=value{i}',
                    'status_code': '200'
                }
            })
            ai_results.append(f'AI分析结果 {i}: 检测到{["高危", "中危"][i%2]}安全威胁')

        internal_ips = {f'192.168.1.{100+i}': (i+1)*5 for i in range(20)}
        external_ip_details = [
            {'ip': f'8.8.8.{i}', 'count': (i+1)*10, 'location': f'Location-{i}'}
            for i in range(10)
        ]

        def generate_html_report():
            with tempfile.TemporaryDirectory() as tmpdir:
                reporter = ReportGenerator(tmpdir)
                return reporter.generate_report(
                    matched_logs, ai_results, 'html',
                    internal_ips, external_ip_details, 'test-server'
                )

        result = self.run_benchmark(
            generate_html_report,
            name="报告生成器-HTML报告100条事件",
            iterations=10
        )
        print(f"  {result}")

    def run_performance_tracker_benchmark(self):
        """运行性能跟踪器性能基准测试"""
        print("\n⚡ 性能跟踪器基准测试...")

        tracker = PerformanceTracker()

        # 测试指标记录性能
        def record_metrics():
            for i in range(100):
                tracker.record_metric(f'metric_{i%10}', 100.0 + i, 'ms')

        result = self.run_benchmark(
            record_metrics,
            name="性能跟踪器-记录100个指标",
            iterations=100
        )
        print(f"  {result}")

        # 测试计时器性能
        def timer_operations():
            for i in range(100):
                tracker.start_timer(f'timer_{i%10}')
                tracker.end_timer(f'timer_{i%10}')

        timer_result = self.run_benchmark(
            timer_operations,
            name="性能跟踪器-100次计时操作",
            iterations=100
        )
        print(f"  {timer_result}")

    def generate_performance_report(self):
        """生成性能测试报告"""
        print("\n📋 性能基准测试报告")
        print("=" * 70)

        if not self.results:
            print("没有测试结果")
            return

        # 按类别分组结果
        categories = {}
        for result in self.results:
            category = result.name.split('-')[0]
            if category not in categories:
                categories[category] = []
            categories[category].append(result)

        for category, results in categories.items():
            print(f"\n{category.upper()} 类测试结果:")
            print("-" * 70)

            for result in results:
                status = "✅" if result.success else "❌"
                print(f"{status} {result}")

            # 计算统计数据
            if len(results) > 1:
                times = [r.execution_time for r in results if r.success]
                if times:
                    print(f"\n  统计信息:")
                    print(f"  平均执行时间: {statistics.mean(times):.3f}s")
                    print(f"  最快执行时间: {min(times):.3f}s")
                    print(f"  最慢执行时间: {max(times):.3f}s")

    def save_baseline(self, filename: str = "performance_baseline.json"):
        """保存性能基线到文件

        Args:
            filename: 基线文件名
        """
        import json
        from pathlib import Path

        baseline_data = []
        for result in self.results:
            baseline_data.append({
                'name': result.name,
                'execution_time': result.execution_time,
                'memory_used': result.memory_used,
                'operations_per_second': result.operations_per_second,
                'metadata': result.metadata
            })

        baseline_path = Path(__file__).parent / filename
        with open(baseline_path, 'w') as f:
            json.dump(baseline_data, f, indent=2)

        print(f"\n💾 性能基线已保存到: {baseline_path}")

    def compare_with_baseline(self, filename: str = "performance_baseline.json") -> bool:
        """与保存的基线进行比较

        Args:
            filename: 基线文件名

        Returns:
            bool: 如果性能在可接受范围内返回True，否则返回False
        """
        import json
        from pathlib import Path

        baseline_path = Path(__file__).parent / filename
        if not baseline_path.exists():
            print(f"⚠️  基线文件不存在: {baseline_path}")
            return False

        with open(baseline_path, 'r') as f:
            baseline_data = json.load(f)

        print("\n📈 性能回归分析:")
        print("-" * 70)

        all_passed = True
        tolerance = 0.1  # 10%的容差

        for baseline in baseline_data:
            current = next((r for r in self.results if r.name == baseline['name']), None)
            if not current:
                continue

            baseline_time = baseline['execution_time']
            current_time = current.execution_time

            if current_time > 0:
                change_percent = ((current_time - baseline_time) / baseline_time) * 100
            else:
                change_percent = 0

            status = "✅" if abs(change_percent) < tolerance * 100 else "⚠️"
            if abs(change_percent) >= tolerance * 100:
                all_passed = False

            print(f"{status} {current.name}:")
            print(f"    基线: {baseline_time:.3f}s")
            print(f"    当前: {current_time:.3f}s")
            print(f"    变化: {change_percent:+.1f}%")

        return all_passed


def main():
    """主测试函数"""
    print("🚀 SSlogs 性能基准测试")
    print("=" * 70)

    benchmark = PerformanceBenchmark()

    try:
        # 运行各项基准测试
        benchmark.run_parser_benchmark()
        benchmark.run_rule_engine_benchmark()
        benchmark.run_reporter_benchmark()
        benchmark.run_performance_tracker_benchmark()

        # 生成报告
        benchmark.generate_performance_report()

        # 保存基线
        benchmark.save_baseline()

        print("\n✅ 性能基准测试完成")

    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()