"""
统一日志配置模块

提供集中式的日志配置和管理
"""
import logging
import logging.handlers
import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import json


class SSlogsFormatter(logging.Formatter):
    """自定义日志格式化器，支持彩色输出和结构化日志"""

    # ANSI颜色代码
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
        'RESET': '\033[0m'        # 重置
    }

    def __init__(self, use_color: bool = True, use_json: bool = False):
        """初始化格式化器

        Args:
            use_color: 是否使用彩色输出
            use_json: 是否使用JSON格式
        """
        super().__init__()
        self.use_color = use_color and self._supports_color()
        self.use_json = use_json

    def _supports_color(self) -> bool:
        """检测终端是否支持彩色输出"""
        return (
            hasattr(sys.stdout, 'isatty') and sys.stdout.isatty() and
            os.environ.get('TERM') != 'dumb' and
            (os.name == 'posix' or 'WT_SESSION' in os.environ)
        )

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        if self.use_json:
            return self._format_json(record)
        else:
            return self._format_text(record)

    def _format_text(self, record: logging.LogRecord) -> str:
        """格式化为文本"""
        level_name = record.levelname

        # 添加颜色
        if self.use_color and level_name in self.COLORS:
            level_name = f"{self.COLORS[level_name]}{level_name}{self.COLORS['RESET']}"

        # 基础格式
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        base_format = f"[{timestamp}] [{level_name}] [{record.name}] {record.getMessage()}"

        # 添加异常信息
        if record.exc_info:
            base_format += "\n" + self.formatException(record.exc_info)

        return base_format

    def _format_json(self, record: logging.LogRecord) -> str:
        """格式化为JSON"""
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # 添加异常信息
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        # 添加额外字段
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)

        return json.dumps(log_entry, ensure_ascii=False)


class ContextualLogger(logging.LoggerAdapter):
    """上下文日志记录器，支持自动添加上下文信息"""

    def __init__(self, logger: logging.Logger, extra: Optional[Dict[str, Any]] = None):
        """初始化上下文日志记录器

        Args:
            logger: 底层日志记录器
            extra: 额外的上下文信息
        """
        super().__init__(logger, extra or {})

    def process(self, msg: Any, kwargs: Dict[str, Any]) -> tuple:
        """处理消息，添加上下文信息"""
        # 将extra信息合并到kwargs中
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        kwargs['extra'].update(self.extra)
        return msg, kwargs


class LoggingConfig:
    """日志配置管理器"""

    # 日志级别映射
    LOG_LEVELS = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }

    def __init__(self):
        """初始化日志配置管理器"""
        self.configured_loggers: Dict[str, logging.Logger] = {}
        self.log_dir: Optional[Path] = None
        self.use_color: bool = True
        self.use_json: bool = False
        self.level: str = 'INFO'

    def setup_logging(self,
                     level: str = 'INFO',
                     log_dir: Optional[str] = None,
                     log_file: Optional[str] = None,
                     use_color: bool = True,
                     use_json: bool = False,
                     console_output: bool = True,
                     file_max_bytes: int = 10 * 1024 * 1024,  # 10MB
                     file_backup_count: int = 5) -> None:
        """设置日志系统

        Args:
            level: 日志级别
            log_dir: 日志目录
            log_file: 日志文件名
            use_color: 是否使用彩色输出
            use_json: 是否使用JSON格式
            console_output: 是否输出到控制台
            file_max_bytes: 单个日志文件最大大小
            file_backup_count: 保留的日志文件数量
        """
        self.level = level
        self.use_color = use_color
        self.use_json = use_json

        # 设置日志目录
        if log_dir:
            self.log_dir = Path(log_dir)
            self.log_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.log_dir = Path('logs')

        # 配置根日志记录器
        root_logger = logging.getLogger()
        root_logger.setLevel(self.LOG_LEVELS.get(level.upper(), logging.INFO))

        # 清除现有处理器
        root_logger.handlers.clear()

        # 创建格式化器
        formatter = SSlogsFormatter(use_color=use_color, use_json=use_json)

        # 控制台处理器
        if console_output:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            console_handler.setLevel(self.LOG_LEVELS.get(level.upper(), logging.INFO))
            root_logger.addHandler(console_handler)

        # 文件处理器
        if log_file:
            file_path = self.log_dir / log_file

            # 创建滚动文件处理器
            file_handler = logging.handlers.RotatingFileHandler(
                file_path,
                maxBytes=file_max_bytes,
                backupCount=file_backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(SSlogsFormatter(use_color=False, use_json=use_json))
            file_handler.setLevel(self.LOG_LEVELS.get(level.upper(), logging.INFO))
            root_logger.addHandler(file_handler)

        # 错误日志文件处理器
        if log_file:
            error_file_path = self.log_dir / f"{log_file}.error"
            error_handler = logging.handlers.RotatingFileHandler(
                error_file_path,
                maxBytes=file_max_bytes,
                backupCount=file_backup_count,
                encoding='utf-8'
            )
            error_handler.setFormatter(SSlogsFormatter(use_color=False, use_json=use_json))
            error_handler.setLevel(logging.ERROR)
            root_logger.addHandler(error_handler)

        # 配置第三方库的日志级别
        self._configure_third_party_loggers()

    def _configure_third_party_loggers(self) -> None:
        """配置第三方库的日志级别"""
        # 降低噪音库的日志级别
        noisy_loggers = [
            'urllib3',
            'requests',
            'charset_normalizer',
            'aiohttp',
            'asyncio'
        ]

        for logger_name in noisy_loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.WARNING)

    def get_logger(self, name: str, context: Optional[Dict[str, Any]] = None) -> logging.Logger:
        """获取日志记录器

        Args:
            name: 日志记录器名称
            context: 上下文信息

        Returns:
            日志记录器实例
        """
        if name in self.configured_loggers:
            logger = self.configured_loggers[name]
        else:
            logger = logging.getLogger(name)
            self.configured_loggers[name] = logger

        # 如果提供了上下文，返回上下文日志记录器
        if context:
            return ContextualLogger(logger, context)

        return logger

    def add_file_handler(self,
                         logger_name: str,
                         file_path: str,
                         level: str = 'INFO',
                         use_json: bool = False) -> None:
        """为指定日志记录器添加文件处理器

        Args:
            logger_name: 日志记录器名称
            file_path: 文件路径
            level: 日志级别
            use_json: 是否使用JSON格式
        """
        logger = logging.getLogger(logger_name)

        # 确保日志目录存在
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # 创建文件处理器
        handler = logging.FileHandler(file_path, encoding='utf-8')
        handler.setFormatter(SSlogsFormatter(use_color=False, use_json=use_json))
        handler.setLevel(self.LOG_LEVELS.get(level.upper(), logging.INFO))

        logger.addHandler(handler)

    def set_level(self, logger_name: str, level: str) -> None:
        """设置日志记录器的日志级别

        Args:
            logger_name: 日志记录器名称
            level: 日志级别
        """
        logger = logging.getLogger(logger_name)
        logger.setLevel(self.LOG_LEVELS.get(level.upper(), logging.INFO))

    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要

        Returns:
            配置摘要字典
        """
        return {
            'level': self.level,
            'log_dir': str(self.log_dir) if self.log_dir else None,
            'use_color': self.use_color,
            'use_json': self.use_json,
            'configured_loggers': list(self.configured_loggers.keys())
        }


# 全局日志配置实例
_global_logging_config: Optional[LoggingConfig] = None


def get_logging_config() -> LoggingConfig:
    """获取全局日志配置实例"""
    global _global_logging_config
    if _global_logging_config is None:
        _global_logging_config = LoggingConfig()
    return _global_logging_config


def setup_logging(**kwargs) -> None:
    """设置日志系统的便捷函数"""
    config = get_logging_config()
    config.setup_logging(**kwargs)


def get_logger(name: str, context: Optional[Dict[str, Any]] = None) -> logging.Logger:
    """获取日志记录器的便捷函数"""
    config = get_logging_config()
    return config.get_logger(name, context)


# 便捷函数
def log_performance(func: callable) -> callable:
    """性能日志装饰器"""
    import functools
    import time

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.debug(f"{func.__name__} 执行完成，耗时: {elapsed:.4f}秒")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"{func.__name__} 执行失败，耗时: {elapsed:.4f}秒，错误: {e}")
            raise

    return wrapper


def log_context(context_name: str, **context_values) -> callable:
    """上下文日志装饰器"""
    def decorator(func: callable) -> callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            context = {'context_name': context_name, **context_values}
            logger = get_logger(func.__module__, context)
            return func(*args, **kwargs)
        return wrapper
    return decorator


# 默认配置
def init_default_logging() -> None:
    """初始化默认日志配置"""
    setup_logging(
        level='INFO',
        log_dir='logs',
        log_file='sslogs.log',
        use_color=True,
        use_json=False,
        console_output=True
    )
