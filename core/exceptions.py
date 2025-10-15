"""自定义异常类定义"""

class LogAnalysisError(Exception):
    """日志分析基础异常"""
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}

class ConfigurationError(LogAnalysisError):
    """配置相关错误"""
    pass

class ParsingError(LogAnalysisError):
    """日志解析错误"""
    pass

class RuleEngineError(LogAnalysisError):
    """规则引擎错误"""
    pass

class AIServiceError(LogAnalysisError):
    """AI服务相关错误"""
    pass

class AIServiceUnavailableError(AIServiceError):
    """AI服务不可用错误"""
    pass

class AIAuthenticationError(AIServiceError):
    """AI认证错误"""
    pass

class AIRateLimitError(AIServiceError):
    """AI服务频率限制错误"""
    pass

class ReportGenerationError(LogAnalysisError):
    """报告生成错误"""
    pass

class GeoIPError(LogAnalysisError):
    """地理位置服务错误"""
    pass

class SecurityValidationError(LogAnalysisError):
    """安全验证错误"""
    pass

class PerformanceError(LogAnalysisError):
    """性能相关错误"""
    pass

class ResourceExhaustionError(PerformanceError):
    """资源耗尽错误"""
    pass