"""
性能监控模块
提供系统性能指标收集、健康检查和资源监控功能
"""
import time
import threading
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import psutil
import logging

logger = logging.getLogger(__name__)


@dataclass
class Metric:
    """性能指标数据类"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
            "unit": self.unit,
        }


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    name: str
    status: str  # healthy, degraded, unhealthy
    message: str
    duration_ms: float
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details,
        }


class MetricsCollector:
    """性能指标收集器"""

    def __init__(self, max_metrics: int = 10000):
        """
        初始化指标收集器

        Args:
            max_metrics: 最大存储指标数量
        """
        self._metrics: Dict[str, deque] = {}
        self._max_metrics = max_metrics
        self._lock = threading.Lock()

    def record(self, metric: Metric) -> None:
        """
        记录指标

        Args:
            metric: 指标对象
        """
        with self._lock:
            if metric.name not in self._metrics:
                self._metrics[metric.name] = deque(maxlen=self._max_metrics)
            self._metrics[metric.name].append(metric)

    def increment(self, name: str, value: float = 1.0,
                 tags: Optional[Dict[str, str]] = None) -> None:
        """
        增加计数器

        Args:
            name: 指标名称
            value: 增加值
            tags: 标签
        """
        metric = Metric(
            name=name,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {},
            unit="count"
        )
        self.record(metric)

    def gauge(self, name: str, value: float,
              tags: Optional[Dict[str, str]] = None) -> None:
        """
        记录仪表值

        Args:
            name: 指标名称
            value: 当前值
            tags: 标签
        """
        metric = Metric(
            name=name,
            value=value,
            timestamp=datetime.now(),
            tags=tags or {},
            unit="gauge"
        )
        self.record(metric)

    def timing(self, name: str, duration_ms: float,
               tags: Optional[Dict[str, str]] = None) -> None:
        """
        记录计时

        Args:
            name: 指标名称
            duration_ms: 持续时间（毫秒）
            tags: 标签
        """
        metric = Metric(
            name=name,
            value=duration_ms,
            timestamp=datetime.now(),
            tags=tags or {},
            unit="ms"
        )
        self.record(metric)

    def get_metrics(self, name: Optional[str] = None,
                   since: Optional[datetime] = None) -> List[Metric]:
        """
        获取指标

        Args:
            name: 指标名称（None 表示获取所有）
            since: 起始时间

        Returns:
            指标列表
        """
        with self._lock:
            if name:
                metrics = list(self._metrics.get(name, []))
            else:
                metrics = []
                for metric_queue in self._metrics.values():
                    metrics.extend(list(metric_queue))

            if since:
                metrics = [m for m in metrics if m.timestamp >= since]

            return metrics

    def get_aggregated(self, name: str,
                      aggregation: str = "avg") -> Optional[float]:
        """
        获取聚合值

        Args:
            name: 指标名称
            aggregation: 聚合类型 (avg, sum, min, max, count)

        Returns:
            聚合值
        """
        metrics = self.get_metrics(name)
        if not metrics:
            return None

        values = [m.value for m in metrics]

        if aggregation == "avg":
            return sum(values) / len(values)
        elif aggregation == "sum":
            return sum(values)
        elif aggregation == "min":
            return min(values)
        elif aggregation == "max":
            return max(values)
        elif aggregation == "count":
            return len(values)
        else:
            return None

    def clear(self, name: Optional[str] = None) -> None:
        """
        清除指标

        Args:
            name: 指标名称（None 表示清除所有）
        """
        with self._lock:
            if name:
                if name in self._metrics:
                    self._metrics[name].clear()
            else:
                self._metrics.clear()


class SystemMonitor:
    """系统资源监控"""

    def __init__(self, metrics_collector: MetricsCollector):
        """
        初始化系统监控

        Args:
            metrics_collector: 指标收集器
        """
        self.metrics_collector = metrics_collector
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._interval = 5  # 采集间隔（秒）

    def start(self, interval: int = 5) -> None:
        """
        启动监控

        Args:
            interval: 采集间隔（秒）
        """
        if self._running:
            return

        self._interval = interval
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info(f"系统监控已启动，采集间隔: {interval}秒")

    def stop(self) -> None:
        """停止监控"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("系统监控已停止")

    def _monitor_loop(self) -> None:
        """监控循环"""
        while self._running:
            try:
                self._collect_metrics()
            except Exception as e:
                logger.error(f"系统监控采集失败: {e}")

            time.sleep(self._interval)

    def _collect_metrics(self) -> None:
        """采集系统指标"""
        # CPU 使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        self.metrics_collector.gauge("system.cpu.percent", cpu_percent)

        # 内存使用
        memory = psutil.virtual_memory()
        self.metrics_collector.gauge("system.memory.percent", memory.percent)
        self.metrics_collector.gauge("system.memory.used_mb", memory.used / 1024 / 1024)
        self.metrics_collector.gauge("system.memory.available_mb", memory.available / 1024 / 1024)

        # 磁盘使用
        disk = psutil.disk_usage('/')
        self.metrics_collector.gauge("system.disk.percent", disk.percent)
        self.metrics_collector.gauge("system.disk.used_gb", disk.used / 1024 / 1024 / 1024)

        # 网络IO
        net_io = psutil.net_io_counters()
        self.metrics_collector.gauge("system.network.bytes_sent", net_io.bytes_sent)
        self.metrics_collector.gauge("system.network.bytes_recv", net_io.bytes_recv)

        # 进程信息
        process = psutil.Process()
        self.metrics_collector.gauge("process.memory_mb", process.memory_info().rss / 1024 / 1024)
        self.metrics_collector.gauge("process.cpu_percent", process.cpu_percent())

    def get_current_stats(self) -> Dict[str, Any]:
        """
        获取当前系统状态

        Returns:
            系统状态字典
        """
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        process = psutil.Process()

        return {
            "cpu": {
                "percent": cpu_percent,
                "count": psutil.cpu_count(),
            },
            "memory": {
                "percent": memory.percent,
                "used_gb": memory.used / 1024 / 1024 / 1024,
                "total_gb": memory.total / 1024 / 1024 / 1024,
                "available_gb": memory.available / 1024 / 1024 / 1024,
            },
            "disk": {
                "percent": disk.percent,
                "used_gb": disk.used / 1024 / 1024 / 1024,
                "total_gb": disk.total / 1024 / 1024 / 1024,
            },
            "process": {
                "memory_mb": process.memory_info().rss / 1024 / 1024,
                "cpu_percent": process.cpu_percent(),
                "num_threads": process.num_threads(),
                "num_fds": process.num_fds() if hasattr(process, 'num_fds') else 0,
            }
        }


class HealthChecker:
    """健康检查器"""

    def __init__(self):
        """初始化健康检查器"""
        self._checks: Dict[str, Callable[[], HealthCheckResult]] = {}
        self._results: Dict[str, HealthCheckResult] = {}

    def register(self, name: str,
                 check_func: Callable[[], HealthCheckResult]) -> None:
        """
        注册健康检查

        Args:
            name: 检查名称
            check_func: 检查函数
        """
        self._checks[name] = check_func
        logger.info(f"注册健康检查: {name}")

    def unregister(self, name: str) -> None:
        """
        取消注册健康检查

        Args:
            name: 检查名称
        """
        if name in self._checks:
            del self._checks[name]
            logger.info(f"取消注册健康检查: {name}")

    def check(self, name: Optional[str] = None) -> Dict[str, HealthCheckResult]:
        """
        执行健康检查

        Args:
            name: 检查名称（None 表示执行所有）

        Returns:
            检查结果字典
        """
        if name:
            checks = {name: self._checks.get(name)}
        else:
            checks = self._checks

        results = {}
        for check_name, check_func in checks.items():
            if check_func is None:
                continue

            try:
                start_time = time.time()
                result = check_func()
                duration_ms = (time.time() - start_time) * 1000
                result.duration_ms = duration_ms
                results[check_name] = result
            except Exception as e:
                logger.error(f"健康检查失败: {check_name}, 错误: {e}")
                results[check_name] = HealthCheckResult(
                    name=check_name,
                    status="unhealthy",
                    message=f"检查失败: {str(e)}",
                    duration_ms=0,
                    timestamp=datetime.now()
                )

        self._results.update(results)
        return results

    def get_overall_status(self) -> str:
        """
        获取整体健康状态

        Returns:
            状态: healthy, degraded, unhealthy
        """
        if not self._results:
            return "unknown"

        statuses = [r.status for r in self._results.values()]

        if all(s == "healthy" for s in statuses):
            return "healthy"
        elif any(s == "unhealthy" for s in statuses):
            return "unhealthy"
        else:
            return "degraded"

    def get_results(self) -> Dict[str, HealthCheckResult]:
        """
        获取所有检查结果

        Returns:
            检查结果字典
        """
        return self._results.copy()


class PerformanceMonitor:
    """性能监控主类"""

    def __init__(self):
        """初始化性能监控"""
        self.metrics = MetricsCollector()
        self.system_monitor = SystemMonitor(self.metrics)
        self.health_checker = HealthChecker()

        # 注册默认的健康检查
        self._register_default_checks()

    def _register_default_checks(self) -> None:
        """注册默认健康检查"""
        def check_system_resources() -> HealthCheckResult:
            stats = self.system_monitor.get_current_stats()

            # 检查资源使用是否正常
            if stats["cpu"]["percent"] > 90:
                status = "unhealthy"
                message = f"CPU使用率过高: {stats['cpu']['percent']:.1f}%"
            elif stats["memory"]["percent"] > 90:
                status = "unhealthy"
                message = f"内存使用率过高: {stats['memory']['percent']:.1f}%"
            elif stats["disk"]["percent"] > 90:
                status = "degraded"
                message = f"磁盘使用率过高: {stats['disk']['percent']:.1f}%"
            else:
                status = "healthy"
                message = "系统资源正常"

            return HealthCheckResult(
                name="system_resources",
                status=status,
                message=message,
                duration_ms=0,
                timestamp=datetime.now(),
                details=stats
            )

        self.health_checker.register("system_resources", check_system_resources)

    def start(self, monitor_interval: int = 5) -> None:
        """
        启动性能监控

        Args:
            monitor_interval: 监控间隔（秒）
        """
        self.system_monitor.start(monitor_interval)
        logger.info("性能监控已启动")

    def stop(self) -> None:
        """停止性能监控"""
        self.system_monitor.stop()
        logger.info("性能监控已停止")

    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        获取监控面板数据

        Returns:
            面板数据字典
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "health": {
                "status": self.health_checker.get_overall_status(),
                "checks": {
                    name: result.to_dict()
                    for name, result in self.health_checker.get_results().items()
                }
            },
            "metrics": {
                "cpu_percent": self.metrics.get_aggregated("system.cpu.percent", "avg") or 0,
                "memory_percent": self.metrics.get_aggregated("system.memory.percent", "avg") or 0,
                "disk_percent": self.metrics.get_aggregated("system.disk.percent", "avg") or 0,
            },
            "system": self.system_monitor.get_current_stats(),
        }

    def export_metrics(self, format: str = "json") -> str:
        """
        导出指标

        Args:
            format: 格式 (json, prometheus)

        Returns:
            格式化后的指标字符串
        """
        if format == "json":
            import json
            metrics = self.metrics.get_metrics()
            return json.dumps([m.to_dict() for m in metrics], indent=2)
        elif format == "prometheus":
            # Prometheus 格式导出
            lines = []
            for metric in self.metrics.get_metrics():
                tags_str = ",".join([f'{k}="{v}"' for k, v in metric.tags.items()])
                lines.append(f"{metric.name}{{{tags_str}}} {metric.value}")
            return "\n".join(lines)
        else:
            raise ValueError(f"不支持的格式: {format}")


# 上下文管理器用于性能计时
class Timer:
    """性能计时上下文管理器"""

    def __init__(self, metrics_collector: MetricsCollector,
                 metric_name: str, tags: Optional[Dict[str, str]] = None):
        """
        初始化计时器

        Args:
            metrics_collector: 指标收集器
            metric_name: 指标名称
            tags: 标签
        """
        self.metrics_collector = metrics_collector
        self.metric_name = metric_name
        self.tags = tags
        self.start_time = None

    def __enter__(self):
        """进入上下文"""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出上下文"""
        duration_ms = (time.time() - self.start_time) * 1000
        self.metrics_collector.timing(self.metric_name, duration_ms, self.tags)


# 全局性能监控实例
_global_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """
    获取全局性能监控实例

    Returns:
        性能监控实例
    """
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor
