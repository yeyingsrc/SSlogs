import logging
import traceback
import time
import sys
import functools
import asyncio
import inspect
from typing import Dict, Any, Optional, Callable, Type, Union, List, Tuple
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path

from .exceptions import (
    LogAnalysisError, ConfigurationError, ParsingError, RuleEngineError,
    AIServiceError, AIServiceUnavailableError, AIAuthenticationError, AIRateLimitError,
    ReportGenerationError, GeoIPError, SecurityValidationError, PerformanceError,
    ResourceExhaustionError
)


class ErrorSeverity(Enum):
    """错误严重程度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """错误上下文信息"""
    component: str
    operation: str
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'component': self.component,
            'operation': self.operation,
            'user_id': self.user_id,
            'request_id': self.request_id,
            'session_id': self.session_id,
            'ip_address': self.ip_address,
            'additional_data': self.additional_data
        }


@dataclass
class ErrorReport:
    """错误报告"""
    exception_type: str
    message: str
    severity: ErrorSeverity
    context: ErrorContext
    traceback: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    error_code: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'exception_type': self.exception_type,
            'message': self.message,
            'severity': self.severity.value,
            'context': self.context.to_dict(),
            'traceback': self.traceback,
            'timestamp': self.timestamp,
            'error_code': self.error_code,
            'details': self.details
        }


class ExceptionClassifier:
    """异常分类器"""

    def __init__(self):
        self.classification_rules = {
            ConfigurationError: (ErrorSeverity.HIGH, "config_error"),
            ParsingError: (ErrorSeverity.MEDIUM, "parsing_error"),
            RuleEngineError: (ErrorSeverity.HIGH, "rule_engine_error"),
            AIServiceError: (ErrorSeverity.MEDIUM, "ai_service_error"),
            AIServiceUnavailableError: (ErrorSeverity.HIGH, "ai_unavailable"),
            AIAuthenticationError: (ErrorSeverity.CRITICAL, "ai_auth_error"),
            AIRateLimitError: (ErrorSeverity.MEDIUM, "ai_rate_limit"),
            ReportGenerationError: (ErrorSeverity.LOW, "report_error"),
            GeoIPError: (ErrorSeverity.LOW, "geoip_error"),
            SecurityValidationError: (ErrorSeverity.CRITICAL, "security_error"),
            PerformanceError: (ErrorSeverity.MEDIUM, "performance_error"),
            ResourceExhaustionError: (ErrorSeverity.HIGH, "resource_exhausted"),
            MemoryError: (ErrorSeverity.HIGH, "memory_error"),
            FileNotFoundError: (ErrorSeverity.MEDIUM, "file_not_found"),
            PermissionError: (ErrorSeverity.HIGH, "permission_error"),
            TimeoutError: (ErrorSeverity.MEDIUM, "timeout_error"),
            ConnectionError: (ErrorSeverity.HIGH, "connection_error"),
            ValueError: (ErrorSeverity.LOW, "value_error"),
            KeyError: (ErrorSeverity.LOW, "key_error"),
        }

    def classify(self, exception: Exception) -> Tuple[ErrorSeverity, str]:
        """分类异常"""
        exception_type = type(exception)

        # 精确匹配
        if exception_type in self.classification_rules:
            return self.classification_rules[exception_type]

        # 继承关系匹配
        for exc_type, (severity, category) in self.classification_rules.items():
            if issubclass(exception_type, exc_type):
                return (severity, category)

        # 默认分类
        return (ErrorSeverity.MEDIUM, "unknown_error")


class ExceptionHandler:
    """统一异常处理器"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.classifier = ExceptionClassifier()
        self.error_handlers: Dict[str, List[Callable]] = {}
        self.error_reports: List[ErrorReport] = []
        self.max_reports = 1000
        self.global_handlers: List[Callable] = []

    def register_handler(self, exception_type: Type[Exception],
                        handler: Callable[[Exception, ErrorContext], Any]) -> None:
        """注册异常处理器"""
        type_name = exception_type.__name__
        if type_name not in self.error_handlers:
            self.error_handlers[type_name] = []
        self.error_handlers[type_name].append(handler)
        self.logger.debug(f"注册异常处理器: {type_name}")

    def register_global_handler(self, handler: Callable[[Exception, ErrorContext], Any]) -> None:
        """注册全局异常处理器"""
        self.global_handlers.append(handler)
        self.logger.debug("注册全局异常处理器")

    def handle_exception(self, exception: Exception, context: ErrorContext) -> Any:
        """处理异常"""
        # 分类异常
        severity, category = self.classifier.classify(exception)

        # 创建错误报告
        error_report = ErrorReport(
            exception_type=type(exception).__name__,
            message=str(exception),
            severity=severity,
            context=context,
            traceback=traceback.format_exc(),
            error_code=getattr(exception, 'error_code', None),
            details=getattr(exception, 'details', {})
        )

        # 记录错误报告
        self._add_error_report(error_report)

        # 记录日志
        self._log_error(error_report)

        # 执行异常处理器
        result = self._execute_handlers(exception, context, error_report)

        # 根据严重程度决定是否继续
        if severity == ErrorSeverity.CRITICAL:
            self.logger.critical("严重错误，程序即将退出")
            sys.exit(1)

        return result

    def _add_error_report(self, report: ErrorReport) -> None:
        """添加错误报告"""
        self.error_reports.append(report)
        if len(self.error_reports) > self.max_reports:
            self.error_reports = self.error_reports[-self.max_reports:]

    def _log_error(self, report: ErrorReport) -> None:
        """记录错误日志"""
        log_message = f"[{report.context.component}:{report.context.operation}] {report.message}"

        if report.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message, exc_info=True)
        elif report.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message, exc_info=True)
        elif report.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.info(log_message)

    def _execute_handlers(self, exception: Exception, context: ErrorContext,
                         report: ErrorReport) -> Any:
        """执行异常处理器"""
        exception_type = type(exception).__name__
        result = None

        # 执行特定类型的处理器
        if exception_type in self.error_handlers:
            for handler in self.error_handlers[exception_type]:
                try:
                    handler_result = handler(exception, context)
                    if handler_result is not None:
                        result = handler_result
                except Exception as e:
                    self.logger.error(f"异常处理器执行失败: {e}")

        # 执行全局处理器
        for handler in self.global_handlers:
            try:
                handler_result = handler(exception, context)
                if handler_result is not None:
                    result = handler_result
            except Exception as e:
                self.logger.error(f"全局异常处理器执行失败: {e}")

        return result

    def get_error_reports(self, severity: Optional[ErrorSeverity] = None,
                         limit: int = 100) -> List[ErrorReport]:
        """获取错误报告"""
        reports = self.error_reports
        if severity:
            reports = [r for r in reports if r.severity == severity]
        return reports[-limit:]

    def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计信息"""
        total_errors = len(self.error_reports)
        if total_errors == 0:
            return {'total_errors': 0}

        severity_counts = {}
        type_counts = {}
        component_counts = {}

        for report in self.error_reports:
            # 按严重程度统计
            severity = report.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

            # 按异常类型统计
            exc_type = report.exception_type
            type_counts[exc_type] = type_counts.get(exc_type, 0) + 1

            # 按组件统计
            component = report.context.component
            component_counts[component] = component_counts.get(component, 0) + 1

        return {
            'total_errors': total_errors,
            'severity_distribution': severity_counts,
            'type_distribution': type_counts,
            'component_distribution': component_counts,
            'recent_errors': [r.to_dict() for r in self.error_reports[-10:]]
        }

    def export_error_logs(self, file_path: str) -> bool:
        """导出错误日志"""
        try:
            export_data = {
                'export_time': time.time(),
                'statistics': self.get_error_statistics(),
                'error_reports': [report.to_dict() for report in self.error_reports]
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                import json
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"错误日志已导出: {file_path}")
            return True

        except Exception as e:
            self.logger.error(f"导出错误日志失败: {e}")
            return False

    def clear_reports(self) -> None:
        """清空错误报告"""
        self.error_reports.clear()
        self.logger.info("错误报告已清空")


# 全局异常处理器
_global_exception_handler: Optional[ExceptionHandler] = None


def get_exception_handler() -> ExceptionHandler:
    """获取全局异常处理器"""
    global _global_exception_handler
    if _global_exception_handler is None:
        _global_exception_handler = ExceptionHandler()
    return _global_exception_handler


def init_exception_handler(logger: Optional[logging.Logger] = None) -> ExceptionHandler:
    """初始化全局异常处理器"""
    global _global_exception_handler
    _global_exception_handler = ExceptionHandler(logger)
    return _global_exception_handler


def handle_exceptions(component: str, operation: str = "",
                     severity_map: Optional[Dict[Type[Exception], ErrorSeverity]] = None,
                     return_on_error: Any = None):
    """异常处理装饰器"""
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                context = ErrorContext(
                    component=component,
                    operation=operation or func.__name__,
                    additional_data={'args_count': len(args), 'kwargs_count': len(kwargs)}
                )

                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    handler = get_exception_handler()
                    result = handler.handle_exception(e, context)
                    return return_on_error if result is None else result

            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                context = ErrorContext(
                    component=component,
                    operation=operation or func.__name__,
                    additional_data={'args_count': len(args), 'kwargs_count': len(kwargs)}
                )

                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    handler = get_exception_handler()
                    result = handler.handle_exception(e, context)
                    return return_on_error if result is None else result

            return sync_wrapper

    return decorator


def safe_execute(func: Callable, *args, default_return: Any = None,
                context: Optional[ErrorContext] = None, **kwargs) -> Any:
    """安全执行函数"""
    if context is None:
        context = ErrorContext(
            component="safe_execute",
            operation=func.__name__
        )

    try:
        if asyncio.iscoroutinefunction(func):
            # 异步函数需要在事件循环中执行
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果已经在事件循环中，创建任务
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(lambda: asyncio.run(func(*args, **kwargs)))
                        return future.result()
                else:
                    return loop.run_until_complete(func(*args, **kwargs))
            except RuntimeError:
                # 没有事件循环，创建新的
                return asyncio.run(func(*args, **kwargs))
        else:
            return func(*args, **kwargs)
    except Exception as e:
        handler = get_exception_handler()
        result = handler.handle_exception(e, context)
        return default_return if result is None else result


# 便捷函数
def log_error(component: str, operation: str, exception: Exception,
              severity: ErrorSeverity = ErrorSeverity.MEDIUM,
              additional_data: Optional[Dict[str, Any]] = None) -> None:
    """记录错误的便捷函数"""
    context = ErrorContext(
        component=component,
        operation=operation,
        additional_data=additional_data or {}
    )

    handler = get_exception_handler()
    handler.handle_exception(exception, context)


def create_error_context(component: str, operation: str, **kwargs) -> ErrorContext:
    """创建错误上下文的便捷函数"""
    return ErrorContext(
        component=component,
        operation=operation,
        **kwargs
    )


# 默认错误处理器
def default_ai_error_handler(exception: Exception, context: ErrorContext) -> Dict[str, Any]:
    """默认AI错误处理器"""
    if isinstance(exception, (AIServiceUnavailableError, AIRateLimitError)):
        return {
            'success': False,
            'fallback_used': True,
            'error_type': 'ai_service_error',
            'message': 'AI服务不可用，使用备用分析'
        }
    return None


def default_file_error_handler(exception: Exception, context: ErrorContext) -> Dict[str, Any]:
    """默认文件错误处理器"""
    if isinstance(exception, FileNotFoundError):
        return {
            'success': False,
            'error_type': 'file_not_found',
            'message': f'文件不存在: {exception}'
        }
    elif isinstance(exception, PermissionError):
        return {
            'success': False,
            'error_type': 'permission_error',
            'message': f'权限不足: {exception}'
        }
    return None


# 注册默认处理器
def register_default_handlers():
    """注册默认异常处理器"""
    handler = get_exception_handler()
    handler.register_handler(AIServiceError, default_ai_error_handler)
    handler.register_handler(FileNotFoundError, default_file_error_handler)
    handler.register_handler(PermissionError, default_file_error_handler)