"""
核心模块初始化文件 - 提供类型安全的接口
"""

from typing import TYPE_CHECKING

# 导入现有核心模块
from .parser import LogParser
from .rule_engine import RuleEngine
from .ai_analyzer import AIAnalyzer
from .reporter import ReportGenerator
from .ip_utils import analyze_ip_access, IPGeoLocator

# 导入新增的优化模块
from .async_ai_analyzer import AsyncAIAnalyzer, analyze_logs_concurrently, analyze_log_entry
from .memory_optimized_processor import (
    MemoryOptimizedProcessor,
    MemoryEfficientLogProcessor,
    StreamingDataProcessor,
    StreamingPipeline,
    process_large_logs_async,
    process_large_logs_sync
)
from .event_bus import (
    EventBus,
    Event,
    EventHandler,
    EventPriority,
    get_event_bus,
    init_event_bus,
    event_handler,
    global_event_handler,
    publish_event,
    publish_event_sync
)
from .interfaces import (
    ILogParser,
    ISecurityRuleEngine,
    IAIAnalyzer,
    IThreatScorer,
    IReportGenerator,
    IConfigManager,
    ICache,
    ILogStorage,
    IMetricsCollector,
    IEventPublisher,
    ISecurityLogger,
    INotificationService,
    LogEntry,
    AnalysisResult,
    SecurityRule
)
from .unified_config_manager import (
    UnifiedConfigManager,
    get_config_manager,
    init_config_manager,
    get_config,
    set_config
)
from .exception_handler import (
    ExceptionHandler,
    ErrorContext,
    ErrorReport,
    ErrorSeverity,
    ExceptionClassifier,
    get_exception_handler,
    init_exception_handler,
    handle_exceptions,
    safe_execute,
    log_error,
    create_error_context
)
from .advanced_cache import (
    MemoryCache,
    FileCache,
    RedisCache,
    MultiLevelCache,
    CacheManager,
    CachePolicy,
    CacheEntry,
    get_cache_manager,
    get_cache,
    cache_result,
    async_cache_result
)
from .security_validator import (
    SecurityManager,
    InputValidator,
    ValidationLevel,
    ThreatType,
    ValidationResult,
    SecurityRule,
    get_security_manager,
    init_security_manager,
    validate_input,
    sanitize_input,
    create_session_token,
    validate_session_token
)

# 类型提示和接口定义
if TYPE_CHECKING:
    from typing import Dict, Any, List, Optional, Union, Iterator, AsyncIterator, Callable
    from pathlib import Path

__all__ = [
    # 原有核心模块
    'LogParser',
    'RuleEngine',
    'AIAnalyzer',
    'ReportGenerator',
    'analyze_ip_access',
    'IPGeoLocator',

    # 异步处理模块
    'AsyncAIAnalyzer',
    'analyze_logs_concurrently',
    'analyze_log_entry',

    # 内存优化模块
    'MemoryOptimizedProcessor',
    'MemoryEfficientLogProcessor',
    'StreamingDataProcessor',
    'StreamingPipeline',
    'process_large_logs_async',
    'process_large_logs_sync',

    # 事件总线模块
    'EventBus',
    'Event',
    'EventHandler',
    'EventPriority',
    'get_event_bus',
    'init_event_bus',
    'event_handler',
    'global_event_handler',
    'publish_event',
    'publish_event_sync',

    # 接口定义
    'ILogParser',
    'ISecurityRuleEngine',
    'IAIAnalyzer',
    'IThreatScorer',
    'IReportGenerator',
    'IConfigManager',
    'ICache',
    'ILogStorage',
    'IMetricsCollector',
    'IEventPublisher',
    'ISecurityLogger',
    'INotificationService',
    'LogEntry',
    'AnalysisResult',
    'SecurityRule',

    # 配置管理模块
    'UnifiedConfigManager',
    'get_config_manager',
    'init_config_manager',
    'get_config',
    'set_config',

    # 异常处理模块
    'ExceptionHandler',
    'ErrorContext',
    'ErrorReport',
    'ErrorSeverity',
    'ExceptionClassifier',
    'get_exception_handler',
    'init_exception_handler',
    'handle_exceptions',
    'safe_execute',
    'log_error',
    'create_error_context',

    # 缓存模块
    'MemoryCache',
    'FileCache',
    'RedisCache',
    'MultiLevelCache',
    'CacheManager',
    'CachePolicy',
    'CacheEntry',
    'get_cache_manager',
    'get_cache',
    'cache_result',
    'async_cache_result',

    # 安全验证模块
    'SecurityManager',
    'InputValidator',
    'ValidationLevel',
    'ThreatType',
    'ValidationResult',
    'SecurityRule',
    'get_security_manager',
    'init_security_manager',
    'validate_input',
    'sanitize_input',
    'create_session_token',
    'validate_session_token',
]

# 版本信息
__version__ = "3.1.0"
__author__ = "SSlogs Team"
__description__ = "企业级智能安全日志分析平台"