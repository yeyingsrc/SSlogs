"""
核心接口定义 - 定义系统的抽象接口，实现模块解耦
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Iterator, AsyncIterator
from dataclasses import dataclass
import asyncio


@dataclass
class LogEntry:
    """日志条目数据类"""
    raw: str
    timestamp: Optional[str] = None
    level: Optional[str] = None
    source: Optional[str] = None
    message: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class AnalysisResult:
    """分析结果数据类"""
    log_entry: LogEntry
    threat_score: float
    threat_level: str
    attack_category: Optional[str] = None
    attack_patterns: List[str] = None
    confidence: float = 0.0
    ai_analysis: Optional[str] = None
    recommendations: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.attack_patterns is None:
            self.attack_patterns = []
        if self.recommendations is None:
            self.recommendations = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class SecurityRule:
    """安全规则数据类"""
    name: str
    pattern: str
    category: str
    severity: str
    description: str = ""
    cwe_id: Optional[str] = None
    attack_patterns: List[str] = None
    mitigation: str = ""

    def __post_init__(self):
        if self.attack_patterns is None:
            self.attack_patterns = []


class ILogParser(ABC):
    """日志解析器接口"""

    @abstractmethod
    def parse(self, raw_log: str) -> Optional[LogEntry]:
        """解析单条日志"""
        pass

    @abstractmethod
    def parse_batch(self, raw_logs: List[str]) -> List[LogEntry]:
        """批量解析日志"""
        pass

    @abstractmethod
    async def parse_async(self, raw_log: str) -> Optional[LogEntry]:
        """异步解析单条日志"""
        pass

    @abstractmethod
    def supports_format(self, log_format: str) -> bool:
        """检查是否支持指定格式"""
        pass


class ISecurityRuleEngine(ABC):
    """安全规则引擎接口"""

    @abstractmethod
    def load_rules(self, rules_path: str) -> None:
        """加载安全规则"""
        pass

    @abstractmethod
    def evaluate(self, log_entry: LogEntry) -> List[SecurityRule]:
        """评估日志条目是否匹配规则"""
        pass

    @abstractmethod
    async def evaluate_async(self, log_entry: LogEntry) -> List[SecurityRule]:
        """异步评估日志条目"""
        pass

    @abstractmethod
    def get_rules_by_category(self, category: str) -> List[SecurityRule]:
        """根据类别获取规则"""
        pass

    @abstractmethod
    def add_rule(self, rule: SecurityRule) -> None:
        """添加新规则"""
        pass


class IAIAnalyzer(ABC):
    """AI分析器接口"""

    @abstractmethod
    async def analyze_log(self, log_entry: LogEntry, context: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """分析单条日志"""
        pass

    @abstractmethod
    async def analyze_batch(self, log_entries: List[LogEntry]) -> List[Optional[str]]:
        """批量分析日志"""
        pass

    @abstractmethod
    async def analyze_stream(self, log_entries: AsyncIterator[LogEntry]) -> AsyncIterator[Optional[str]]:
        """流式分析日志"""
        pass

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查服务是否可用"""
        pass


class IThreatScorer(ABC):
    """威胁评分器接口"""

    @abstractmethod
    def calculate_score(self, log_entry: LogEntry, matched_rules: List[SecurityRule]) -> float:
        """计算威胁评分"""
        pass

    @abstractmethod
    def get_threat_level(self, score: float) -> str:
        """根据评分获取威胁等级"""
        pass

    @abstractmethod
    async def calculate_score_async(self, log_entry: LogEntry, matched_rules: List[SecurityRule]) -> float:
        """异步计算威胁评分"""
        pass


class IReportGenerator(ABC):
    """报告生成器接口"""

    @abstractmethod
    def generate_html_report(self, results: List[AnalysisResult], output_path: str) -> bool:
        """生成HTML报告"""
        pass

    @abstractmethod
    def generate_json_report(self, results: List[AnalysisResult], output_path: str) -> bool:
        """生成JSON报告"""
        pass

    @abstractmethod
    def generate_csv_report(self, results: List[AnalysisResult], output_path: str) -> bool:
        """生成CSV报告"""
        pass

    @abstractmethod
    async def generate_report_async(self, results: List[AnalysisResult],
                                  format_type: str, output_path: str) -> bool:
        """异步生成报告"""
        pass


class IConfigManager(ABC):
    """配置管理器接口"""

    @abstractmethod
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置"""
        pass

    @abstractmethod
    def save_config(self, config: Dict[str, Any], config_path: str) -> bool:
        """保存配置"""
        pass

    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        pass

    @abstractmethod
    def set(self, key: str, value: Any) -> None:
        """设置配置项"""
        pass

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """验证配置"""
        pass


class ICache(ABC):
    """缓存接口"""

    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """获取缓存项"""
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存项"""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """删除缓存项"""
        pass

    @abstractmethod
    def clear(self) -> None:
        """清空缓存"""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """检查缓存项是否存在"""
        pass


class ILogStorage(ABC):
    """日志存储接口"""

    @abstractmethod
    def store(self, log_entry: LogEntry) -> bool:
        """存储日志条目"""
        pass

    @abstractmethod
    def retrieve(self, query: Dict[str, Any]) -> Iterator[LogEntry]:
        """检索日志条目"""
        pass

    @abstractmethod
    async def store_async(self, log_entry: LogEntry) -> bool:
        """异步存储日志条目"""
        pass

    @abstractmethod
    async def retrieve_async(self, query: Dict[str, Any]) -> AsyncIterator[LogEntry]:
        """异步检索日志条目"""
        pass


class IMetricsCollector(ABC):
    """指标收集器接口"""

    @abstractmethod
    def increment_counter(self, name: str, value: int = 1, tags: Dict[str, str] = None) -> None:
        """增加计数器"""
        pass

    @abstractmethod
    def record_timing(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """记录计时"""
        pass

    @abstractmethod
    def set_gauge(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """设置仪表盘值"""
        pass

    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        pass


class IEventPublisher(ABC):
    """事件发布器接口"""

    @abstractmethod
    async def publish(self, event_name: str, data: Dict[str, Any]) -> None:
        """发布事件"""
        pass

    @abstractmethod
    def subscribe(self, event_name: str, handler) -> None:
        """订阅事件"""
        pass

    @abstractmethod
    def unsubscribe(self, event_name: str, handler) -> None:
        """取消订阅事件"""
        pass


class ISecurityLogger(ABC):
    """安全日志记录器接口"""

    @abstractmethod
    def log_threat(self, level: str, message: str, threat_data: Dict[str, Any] = None) -> None:
        """记录威胁日志"""
        pass

    @abstractmethod
    def log_analysis(self, level: str, message: str, analysis_data: Dict[str, Any] = None) -> None:
        """记录分析日志"""
        pass

    @abstractmethod
    def log_system(self, level: str, message: str, system_data: Dict[str, Any] = None) -> None:
        """记录系统日志"""
        pass


class INotificationService(ABC):
    """通知服务接口"""

    @abstractmethod
    async def send_alert(self, message: str, severity: str, details: Dict[str, Any] = None) -> bool:
        """发送告警通知"""
        pass

    @abstractmethod
    async def send_report(self, report_path: str, recipients: List[str]) -> bool:
        """发送报告"""
        pass


# 工厂接口
class ILogParserFactory(ABC):
    """日志解析器工厂接口"""

    @abstractmethod
    def create_parser(self, format_type: str) -> ILogParser:
        """创建日志解析器"""
        pass

    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """获取支持的格式列表"""
        pass


class IAIAnalyzerFactory(ABC):
    """AI分析器工厂接口"""

    @abstractmethod
    def create_analyzer(self, provider: str, config: Dict[str, Any]) -> IAIAnalyzer:
        """创建AI分析器"""
        pass

    @abstractmethod
    def get_available_providers(self) -> List[str]:
        """获取可用的提供商列表"""
        pass


class IReportGeneratorFactory(ABC):
    """报告生成器工厂接口"""

    @abstractmethod
    def create_generator(self, format_type: str) -> IReportGenerator:
        """创建报告生成器"""
        pass

    @abstractmethod
    def get_supported_formats(self) -> List[str]:
        """获取支持的格式列表"""
        pass