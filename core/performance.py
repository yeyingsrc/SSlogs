import time
import logging
import psutil
import os
import threading
from functools import wraps
from typing import Dict, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """性能指标数据类"""
    name: str
    value: float
    unit: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

class PerformanceTracker:
    """性能跟踪器"""

    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        self.counters: Dict[str, int] = defaultdict(int)
        self.timers: Dict[str, float] = {}
        self.lock = threading.Lock()

        # 系统资源监控
        self.process = psutil.Process(os.getpid())
        self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB

    def record_metric(self, name: str, value: float, unit: str = "ms", metadata: Dict[str, Any] = None):
        """记录性能指标"""
        with self.lock:
            metric = PerformanceMetric(
                name=name,
                value=value,
                unit=unit,
                metadata=metadata or {}
            )
            self.metrics[name].append(metric)

    def start_timer(self, name: str):
        """开始计时"""
        with self.lock:
            self.timers[name] = time.time()

    def end_timer(self, name: str, unit: str = "ms", metadata: Dict[str, Any] = None) -> float:
        """结束计时并记录"""
        with self.lock:
            if name not in self.timers:
                logger.warning(f"Timer '{name}' was not started")
                return 0.0

            duration = (time.time() - self.timers[name]) * 1000 if unit == "ms" else time.time() - self.timers[name]
            del self.timers[name]

            self.record_metric(name, duration, unit, metadata)
            return duration

    def increment_counter(self, name: str, increment: int = 1):
        """增加计数器"""
        with self.lock:
            self.counters[name] += increment

    def get_system_metrics(self) -> Dict[str, Any]:
        """获取系统性能指标"""
        try:
            memory_info = self.process.memory_info()
            cpu_percent = self.process.cpu_percent()

            return {
                'memory_usage_mb': memory_info.rss / 1024 / 1024,
                'memory_usage_delta_mb': (memory_info.rss / 1024 / 1024) - self.initial_memory,
                'cpu_percent': cpu_percent,
                'num_threads': self.process.num_threads(),
                'open_files': len(self.process.open_files()),
                'connections': len(self.process.connections())
            }
        except Exception as e:
            logger.warning(f"获取系统指标失败: {e}")
            return {}

    def get_metric_stats(self, name: str) -> Dict[str, Any]:
        """获取指定指标的统计信息"""
        with self.lock:
            if name not in self.metrics or not self.metrics[name]:
                return {}

            values = [m.value for m in self.metrics[name]]
            return {
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'avg': sum(values) / len(values),
                'latest': values[-1] if values else 0
            }

    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有性能统计"""
        with self.lock:
            stats = {
                'counters': dict(self.counters),
                'system_metrics': self.get_system_metrics(),
                'metric_stats': {}
            }

            for metric_name in self.metrics:
                stats['metric_stats'][metric_name] = self.get_metric_stats(metric_name)

            return stats

    def reset(self):
        """重置所有统计数据"""
        with self.lock:
            self.metrics.clear()
            self.counters.clear()
            self.timers.clear()

# 全局性能跟踪器实例
global_tracker = PerformanceTracker()

def performance_monitor(name: str = None, unit: str = "ms", track_memory: bool = False):
    """性能监控装饰器"""
    def decorator(func: Callable) -> Callable:
        metric_name = name or f"{func.__module__}.{func.__qualname__}"

        @wraps(func)
        def wrapper(*args, **kwargs):
            # 开始计时
            global_tracker.start_timer(metric_name)

            # 获取开始时的内存使用
            start_memory = None
            if track_memory:
                try:
                    start_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
                except:
                    pass

            try:
                result = func(*args, **kwargs)

                # 记录成功执行
                global_tracker.increment_counter(f"{metric_name}_success")

                return result

            except Exception as e:
                # 记录执行失败
                global_tracker.increment_counter(f"{metric_name}_error")
                logger.error(f"性能监控: {metric_name} 执行失败: {e}")
                raise

            finally:
                # 结束计时
                duration = global_tracker.end_timer(metric_name, unit)

                # 记录内存使用变化
                if track_memory and start_memory:
                    try:
                        end_memory = psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024
                        memory_delta = end_memory - start_memory
                        global_tracker.record_metric(f"{metric_name}_memory_delta", memory_delta, "MB")
                    except:
                        pass

                # 记录详细执行信息
                metadata = {
                    'args_count': len(args),
                    'kwargs_count': len(kwargs),
                    'function_name': func.__name__,
                    'module': func.__module__
                }
                global_tracker.record_metric(f"{metric_name}_metadata", duration, unit, metadata)

        return wrapper
    return decorator

def memory_monitor(threshold_mb: float = 100.0):
    """内存监控装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 获取开始时的内存使用
            try:
                process = psutil.Process(os.getpid())
                start_memory = process.memory_info().rss / 1024 / 1024

                result = func(*args, **kwargs)

                # 检查内存增长
                end_memory = process.memory_info().rss / 1024 / 1024
                memory_delta = end_memory - start_memory

                if memory_delta > threshold_mb:
                    logger.warning(
                        f"内存使用警告: {func.__name__} 执行过程中内存增长了 {memory_delta:.2f}MB"
                    )
                    global_tracker.increment_counter("memory_warnings")

                return result

            except Exception as e:
                logger.error(f"内存监控: {func.__name__} 执行失败: {e}")
                raise

        return wrapper
    return decorator

def error_rate_monitor(window_size: int = 100):
    """错误率监控装饰器"""
    def decorator(func: Callable) -> Callable:
        metric_name = f"error_rate_{func.__name__}"

        @wraps(func)
        def wrapper(*args, **kwargs):
            global_tracker.increment_counter(f"{metric_name}_total")

            try:
                result = func(*args, **kwargs)
                global_tracker.increment_counter(f"{metric_name}_success")
                return result

            except Exception as e:
                global_tracker.increment_counter(f"{metric_name}_error")

                # 计算错误率
                total = global_tracker.counters[f"{metric_name}_total"]
                errors = global_tracker.counters[f"{metric_name}_error"]
                error_rate = (errors / total) * 100 if total > 0 else 0

                if error_rate > 10:  # 错误率超过10%
                    logger.error(
                        f"错误率警告: {func.__name__} 错误率 {error_rate:.2f}% ({errors}/{total})"
                    )

                raise

        return wrapper
    return decorator

def get_performance_summary() -> str:
    """获取性能摘要报告"""
    stats = global_tracker.get_all_stats()

    summary_lines = ["性能监控摘要报告", "=" * 50]

    # 系统指标
    system = stats.get('system_metrics', {})
    if system:
        summary_lines.append(f"内存使用: {system.get('memory_usage_mb', 0):.2f}MB")
        summary_lines.append(f"内存增长: {system.get('memory_usage_delta_mb', 0):.2f}MB")
        summary_lines.append(f"CPU使用率: {system.get('cpu_percent', 0):.2f}%")
        summary_lines.append("")

    # 计数器
    counters = stats.get('counters', {})
    if counters:
        summary_lines.append("计数器统计:")
        for name, count in counters.items():
            summary_lines.append(f"  {name}: {count}")
        summary_lines.append("")

    # 性能指标
    metric_stats = stats.get('metric_stats', {})
    if metric_stats:
        summary_lines.append("性能指标统计:")
        for name, stats in metric_stats.items():
            if not name.endswith('_metadata'):  # 跳过元数据指标
                summary_lines.append(
                    f"  {name}: 平均 {stats.get('avg', 0):.2f}{stats.get('unit', 'ms')} "
                    f"(最大 {stats.get('max', 0):.2f}, 最小 {stats.get('min', 0):.2f}, "
                    f"执行 {stats.get('count', 0)} 次)"
                )

    return "\n".join(summary_lines)