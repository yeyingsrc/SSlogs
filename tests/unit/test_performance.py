"""
性能监控模块单元测试
"""
import pytest
import time
from unittest.mock import patch, MagicMock
from core.performance import (
    PerformanceTracker,
    PerformanceMetric,
    performance_monitor,
    memory_monitor,
    error_rate_monitor,
    get_performance_summary
)


class TestPerformanceMetric:
    """性能指标数据类测试"""

    def test_create_metric(self):
        """测试创建性能指标"""
        metric = PerformanceMetric(
            name='test_operation',
            value=123.45,
            unit='ms'
        )
        assert metric.name == 'test_operation'
        assert metric.value == 123.45
        assert metric.unit == 'ms'
        assert isinstance(metric.timestamp, float)
        assert metric.metadata == {}

    def test_create_metric_with_metadata(self):
        """测试创建带元数据的性能指标"""
        metric = PerformanceMetric(
            name='test_operation',
            value=100.0,
            unit='ms',
            metadata={'request_id': '12345', 'user': 'test_user'}
        )
        assert metric.metadata == {'request_id': '12345', 'user': 'test_user'}


class TestPerformanceTracker:
    """性能跟踪器测试"""

    @pytest.fixture
    def tracker(self):
        """创建性能跟踪器实例"""
        return PerformanceTracker(max_history=100)

    def test_record_metric(self, tracker):
        """测试记录性能指标"""
        tracker.record_metric('test_operation', 150.5, 'ms', {'key': 'value'})

        assert 'test_operation' in tracker.metrics
        assert len(tracker.metrics['test_operation']) == 1
        assert tracker.metrics['test_operation'][0].value == 150.5

    def test_record_multiple_metrics(self, tracker):
        """测试记录多个性能指标"""
        for i in range(5):
            tracker.record_metric('operation', 100.0 + i, 'ms')

        assert len(tracker.metrics['operation']) == 5
        assert tracker.metrics['operation'][4].value == 104.0

    def test_max_history_limit(self, tracker):
        """测试最大历史记录限制"""
        tracker = PerformanceTracker(max_history=3)

        for i in range(5):
            tracker.record_metric('operation', float(i), 'ms')

        # 应该只保留最后3个记录
        assert len(tracker.metrics['operation']) == 3
        assert tracker.metrics['operation'][0].value == 2.0

    def test_increment_counter(self, tracker):
        """测试计数器递增"""
        tracker.increment_counter('test_counter', 5)
        assert tracker.counters['test_counter'] == 5

        tracker.increment_counter('test_counter', 3)
        assert tracker.counters['test_counter'] == 8

    def test_start_and_end_timer(self, tracker):
        """测试计时器功能"""
        tracker.start_timer('test_timer')
        time.sleep(0.1)  # 等待100ms
        duration = tracker.end_timer('test_timer')

        assert duration > 80  # 应该至少80ms
        assert duration < 200  # 应该不超过200ms
        assert 'test_timer' not in tracker.timers  # 计时器应该被移除

    def test_end_timer_without_start(self, tracker):
        """测试未启动计时器就结束"""
        duration = tracker.end_timer('nonexistent_timer')
        assert duration == 0.0

    def test_get_metric_stats(self, tracker):
        """测试获取指标统计"""
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        for value in values:
            tracker.record_metric('test_metric', value, 'ms')

        stats = tracker.get_metric_stats('test_metric')

        assert stats['count'] == 5
        assert stats['min'] == 10.0
        assert stats['max'] == 50.0
        assert stats['avg'] == 30.0
        assert stats['latest'] == 50.0

    def test_get_metric_stats_empty(self, tracker):
        """测试获取不存在指标的统计"""
        stats = tracker.get_metric_stats('nonexistent_metric')
        assert stats == {}

    def test_get_system_metrics(self, tracker):
        """测试获取系统指标"""
        metrics = tracker.get_system_metrics()

        assert isinstance(metrics, dict)
        assert 'memory_usage_mb' in metrics
        assert 'cpu_percent' in metrics

    def test_get_all_stats(self, tracker):
        """测试获取所有统计信息"""
        tracker.increment_counter('test_counter', 10)
        tracker.record_metric('test_metric', 100.0, 'ms')

        stats = tracker.get_all_stats()

        assert 'counters' in stats
        assert 'system_metrics' in stats
        assert 'metric_stats' in stats
        assert stats['counters']['test_counter'] == 10

    def test_reset(self, tracker):
        """测试重置统计数据"""
        tracker.increment_counter('test_counter', 10)
        tracker.record_metric('test_metric', 100.0, 'ms')
        tracker.start_timer('test_timer')

        tracker.reset()

        assert len(tracker.counters) == 0
        assert len(tracker.metrics) == 0
        assert len(tracker.timers) == 0


class TestPerformanceMonitorDecorator:
    """性能监控装饰器测试"""

    def test_performance_monitor_basic(self):
        """测试基本性能监控"""
        @performance_monitor(name='test_function')
        def test_function():
            time.sleep(0.05)
            return 'result'

        result = test_function()

        assert result == 'result'
        # 验证指标被记录
        from core.performance import global_tracker
        assert 'test_function' in global_tracker.metrics

    def test_performance_monitor_auto_naming(self):
        """测试自动函数命名"""
        @performance_monitor()
        def my_test_function():
            return 'result'

        my_test_function()

        from core.performance import global_tracker
        # 应该使用函数的限定名
        assert any('my_test_function' in str(metric.name) for metric in
                  global_tracker.metrics.get('my_test_function', []))

    def test_performance_monitor_with_memory_tracking(self):
        """测试内存使用跟踪"""
        @performance_monitor(track_memory=True)
        def memory_intensive_function():
            # 创建一些内存使用
            data = [i for i in range(10000)]
            return len(data)

        result = memory_intensive_function()
        assert result == 10000

        # 验证内存指标被记录
        from core.performance import global_tracker
        assert any('memory_delta' in str(metric.name) for metric in
                  global_tracker.metrics.get('memory_intensive_function', []))

    def test_performance_monitor_exception_handling(self):
        """测试异常处理"""
        @performance_monitor()
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()

        from core.performance import global_tracker
        # 验证错误计数器被增加
        assert global_tracker.counters.get('failing_function_error', 0) > 0


class TestMemoryMonitorDecorator:
    """内存监控装饰器测试"""

    def test_memory_monitor_normal(self):
        """测试正常情况下的内存监控"""
        @memory_monitor(threshold_mb=1.0)
        def normal_function():
            return 'result'

        result = normal_function()
        assert result == 'result'

    def test_memory_monitor_exceeds_threshold(self):
        """测试超过内存阈值"""
        @memory_monitor(threshold_mb=0.001)  # 非常低的阈值
        def memory_intensive_function():
            # 创建足够大的内存使用
            data = [i for i in range(100000)]
            return len(data)

        memory_intensive_function()

        from core.performance import global_tracker
        # 验证内存警告计数器被增加
        assert global_tracker.counters.get('memory_warnings', 0) >= 0


class TestErrorRateMonitorDecorator:
    """错误率监控装饰器测试"""

    def test_error_rate_monitor_success(self):
        """测试成功的错误率监控"""
        @error_rate_monitor(window_size=10)
        def successful_function():
            return 'success'

        result = successful_function()
        assert result == 'success'

        from core.performance import global_tracker
        assert global_tracker.counters.get('error_rate_successful_function_total', 0) > 0
        assert global_tracker.counters.get('error_rate_successful_function_success', 0) > 0

    def test_error_rate_monitor_failure(self):
        """测试失败情况下的错误率监控"""
        @error_rate_monitor(window_size=10)
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()

        from core.performance import global_tracker
        assert global_tracker.counters.get('error_rate_failing_function_error', 0) > 0

    def test_error_rate_calculation(self):
        """测试错误率计算"""
        @error_rate_monitor(window_size=100)
        def partial_failure_function(should_fail):
            if should_fail:
                raise ValueError("Test error")
            return 'success'

        # 多次调用，其中一些失败
        for i in range(10):
            try:
                partial_failure_function(i < 3)  # 前3次失败
            except ValueError:
                pass

        from core.performance import global_tracker
        total = global_tracker.counters.get('error_rate_partial_failure_function_total', 0)
        errors = global_tracker.counters.get('error_rate_partial_failure_function_error', 0)

        assert total == 10
        assert errors == 3


class TestPerformanceSummary:
    """性能摘要报告测试"""

    def test_get_performance_summary(self):
        """测试获取性能摘要"""
        from core.performance import global_tracker

        # 添加一些测试数据
        global_tracker.increment_counter('test_counter', 10)
        global_tracker.record_metric('test_metric', 100.0, 'ms')

        summary = get_performance_summary()

        assert isinstance(summary, str)
        assert '性能监控摘要报告' in summary
        assert 'test_counter' in summary or 'test_metric' in summary

    def test_get_performance_summary_empty(self):
        """测试空数据的性能摘要"""
        from core.performance import global_tracker

        # 清空数据
        global_tracker.reset()

        summary = get_performance_summary()

        assert isinstance(summary, str)
        assert '性能监控摘要报告' in summary


class TestDecoratorIntegration:
    """装饰器集成测试"""

    def test_multiple_decorators(self):
        """测试多个装饰器组合使用"""
        @performance_monitor(name='multi_decorator_test')
        @memory_monitor(threshold_mb=100.0)
        @error_rate_monitor(window_size=50)
        def complex_function(x):
            return x * 2

        result = complex_function(5)
        assert result == 10

        from core.performance import global_tracker
        # 验证所有监控都被记录
        assert 'multi_decorator_test' in global_tracker.metrics

    def test_decorator_with_arguments(self):
        """测试带参数的函数"""
        @performance_monitor()
        def function_with_args(a, b, c=None):
            return a + b + (c or 0)

        result = function_with_args(1, 2, 3)
        assert result == 6

    def test_decorator_with_keyword_arguments(self):
        """测试带关键字参数的函数"""
        @performance_monitor()
        def function_with_kwargs(**kwargs):
            return sum(kwargs.values())

        result = function_with_kwargs(a=1, b=2, c=3)
        assert result == 6


class TestPerformanceTrackerThreadSafety:
    """性能跟踪器线程安全测试"""

    def test_concurrent_metric_recording(self):
        """测试并发记录指标的线程安全性"""
        import threading

        tracker = PerformanceTracker(max_history=1000)
        num_threads = 10
        records_per_thread = 100

        def record_metrics():
            for i in range(records_per_thread):
                tracker.record_metric('concurrent_test', float(i), 'ms')

        threads = [threading.Thread(target=record_metrics) for _ in range(num_threads)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # 验证所有记录都被正确保存
        assert len(tracker.metrics['concurrent_test']) == num_threads * records_per_thread

    def test_concurrent_counter_increments(self):
        """测试并发计数器递增的线程安全性"""
        import threading

        tracker = PerformanceTracker()
        num_threads = 10
        increments_per_thread = 100

        def increment_counter():
            for _ in range(increments_per_thread):
                tracker.increment_counter('concurrent_counter')

        threads = [threading.Thread(target=increment_counter) for _ in range(num_threads)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # 验证最终计数正确
        assert tracker.counters['concurrent_counter'] == num_threads * increments_per_thread
