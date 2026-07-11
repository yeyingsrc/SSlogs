import re
import yaml
import time
import logging
import html
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Callable, Union
from urllib.parse import unquote, parse_qs
from collections import defaultdict, deque
from dataclasses import dataclass, field
import asyncio


def _parse_duration(value: Union[str, int, float]) -> float:
    """把 '60s' / '5m' / '2h' / 数字 解析为秒数。

    Args:
        value: 时间值，可以是字符串（带单位）或数字

    Returns:
        float: 解析后的秒数，解析失败回退到60s

    Examples:
        >>> _parse_duration('60s')
        60.0
        >>> _parse_duration('5m')
        300.0
        >>> _parse_duration(120)
        120.0
    """
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        s = value.strip().lower()
        try:
            if s.endswith('ms'):
                return float(s[:-2]) / 1000.0
            if s.endswith('s'):
                return float(s[:-1])
            if s.endswith('m'):
                return float(s[:-1]) * 60
            if s.endswith('h'):
                return float(s[:-1]) * 3600
            return float(s)
        except ValueError:
            pass
    return 60.0


@dataclass
class AggregationWindow:
    """跨事件滑动窗口聚合器。

    维护 (规则, 分组键, 端点) -> 时间戳队列 的映射，在时间窗口内
    计数达阈值时生成告警。用于暴力破解、目录爆破、高频请求等
    天然需要"跨事件计数"的检测——单行正则无法表达这类行为。
    """
    # buckets[(rule_name, group_value, path_key)] = deque([timestamps])
    buckets: Dict[Tuple[str, str, str], deque] = field(default_factory=dict)
    # 已在当前窗口内告警过的桶，避免同一桶反复刷屏（直到窗口滚动过期）
    alerted: Dict[Tuple[str, str, str], float] = field(default_factory=dict)

    def record(self, key: Tuple[str, str, str], timestamp: Optional[float] = None,
               failed_only: bool = False, is_failed: bool = False) -> None:
        """记录一次事件。failed_only=True 时仅当 is_failed 才计入。"""
        if failed_only and not is_failed:
            return
        ts = timestamp if timestamp is not None else time.time()
        dq = self.buckets.setdefault(key, deque())
        dq.append(ts)

    def count_in_window(self, key: Tuple[str, str, str], window: float,
                        now: Optional[float] = None) -> int:
        """返回 key 在最近 window 秒内的事件数，并顺手清理过期项。

        Args:
            key: 聚合键元组 (规则名, 分组值, 端点)
            window: 时间窗口（秒）
            now: 当前时间戳，None表示使用当前时间

        Returns:
            int: 窗口内的事件计数
        """
        now = now if now is not None else time.time()
        dq = self.buckets.get(key)
        if not dq:
            return 0
        # 从左弹出过期时间戳
        cutoff = now - window
        while dq and dq[0] < cutoff:
            dq.popleft()
        return len(dq)

    def mark_alerted(self, key: Tuple[str, str, str], now: float) -> None:
        self.alerted[key] = now

    def already_alerted(self, key: Tuple[str, str, str], window: float,
                        now: float) -> bool:
        last = self.alerted.get(key)
        if last is None:
            return False
        # 同一窗口内的告警已被记录过则抑制重复告警
        if now - last < window:
            return True
        return False

    def cleanup(self, max_window: float, now: Optional[float] = None) -> None:
        """清理所有桶中超过最大窗口的过期记录，控制内存占用。

        Args:
            max_window: 最大时间窗口（秒）
            now: 当前时间戳，None表示使用当前时间
        """
        now = now if now is not None else time.time()
        cutoff = now - max_window
        empty_keys = []
        for key, dq in self.buckets.items():
            while dq and dq[0] < cutoff:
                dq.popleft()
            if not dq:
                empty_keys.append(key)
        for key in empty_keys:
            del self.buckets[key]
            self.alerted.pop(key, None)

    # 测试辅助：直接向某桶写入时间戳
    def _record(self, key, timestamp, failed=False):
        self.record(key, timestamp=timestamp, is_failed=failed)

@dataclass
class ThreatScore:
    """威胁评分"""
    score: float
    severity: str
    confidence: float
    attack_vectors: List[str]
    risk_factors: List[str]
    confidence_level: str = 'medium'  # high, medium, low

class RuleEngine:
    """安全规则引擎 - 支持多阶段匹配和威胁评分"""

    def __init__(self, rule_dir: str, enable_ai_analysis: bool = False,
                 config: Optional[Dict[str, Any]] = None) -> None:
        """初始化规则引擎

        Args:
            rule_dir: 规则目录路径
            enable_ai_analysis: 是否启用AI分析
            config: 配置字典，用于读取白名单等配置

        Raises:
            FileNotFoundError: 规则目录不存在时
            yaml.YAMLError: 规则文件解析失败时
        """
        self.logger = logging.getLogger(__name__)
        self.rules: List[Dict[str, Any]] = []
        self.compiled_rules: Dict[str, Dict[str, Any]] = {}  # 预编译规则缓存
        self.rule_stats: defaultdict = defaultdict(int)  # 规则匹配统计
        self.enable_ai_analysis = enable_ai_analysis
        self.ai_analyzer: Optional[Any] = None

        # 延迟导入AI分析器以避免循环依赖
        if enable_ai_analysis:
            try:
                from core.ai_threat_analyzer import get_ai_threat_analyzer
                self.ai_analyzer = get_ai_threat_analyzer()
                self.logger.info("AI威胁分析已启用")
            except Exception as e:
                self.logger.warning(f"AI威胁分析初始化失败: {e}")
                self.enable_ai_analysis = False

        self._load_rules(rule_dir)
        self._compile_rules()

        # 跨事件聚合层：收集声明了 aggregation 字段的规则（如暴力破解/目录爆破）
        self._aggregator = AggregationWindow()
        self._aggregation_rules: List[Dict[str, Any]] = self._collect_aggregation_rules()
        self._aggregation_cleanup_every: int = 1000  # 每处理多少条做一次过期清理
        self._aggregation_observed: int = 0

        # 白名单：从配置读取，缺失时回退到内置默认值（向后兼容不传 config 的调用）
        self._load_whitelist(config)

    def _load_rules(self, rule_dir: str) -> List[Dict[str, Any]]:
        """从规则目录加载所有YAML规则文件

        Args:
            rule_dir: 规则目录路径

        Returns:
            List[Dict[str, Any]]: 加载的规则列表

        Raises:
            FileNotFoundError: 规则目录不存在时
        """
        rules = []
        rule_path = Path(rule_dir)
        if not rule_path.exists():
            raise FileNotFoundError(f"规则目录不存在: {rule_dir}")

        for file in list(rule_path.glob("*.yaml")) + list(rule_path.glob("*.yml")):
            with open(file, 'r', encoding='utf-8') as f:
                try:
                    rule_data = yaml.safe_load(f)
                    if isinstance(rule_data, dict):
                        # 验证规则必要字段
                        if all(k in rule_data for k in ['name', 'pattern']):
                            rule_data['source_file'] = file.name
                            rules.append(rule_data)
                        else:
                            self.logger.warning(f"规则文件 {file.name} 缺少必要字段")
                except yaml.YAMLError as e:
                    self.logger.error(f"解析规则文件 {file.name} 失败: {e}")

        self.rules = rules
        return rules

    def _compile_rules(self) -> None:
        """预编译所有规则以提升性能"""
        self.logger.info(f"开始预编译 {len(self.rules)} 个规则...")
        start_time = time.time()

        for i, rule in enumerate(self.rules):
            rule_id = f"{rule.get('category', 'unknown')}_{i}"
            try:
                compiled_rule = self._compile_single_rule(rule)
                self.compiled_rules[rule_id] = {
                    'rule': rule,
                    'compiled': compiled_rule,
                    'id': rule_id
                }
            except Exception as e:
                self.logger.error(f"编译规则失败 {rule.get('name', 'unknown')}: {e}")

        compile_time = time.time() - start_time
        self.logger.info(f"规则预编译完成，耗时 {compile_time:.3f}s，成功编译 {len(self.compiled_rules)} 个规则")

    def _compile_single_rule(self, rule: Dict[str, Any]) -> Dict[str, Any]:
        """编译单个规则

        Args:
            rule: 规则配置字典

        Returns:
            Dict[str, Any]: 编译后的规则字典

        Raises:
            re.error: 正则表达式编译失败时
        """
        pattern = rule.get('pattern', {})
        compiled = {}

        if isinstance(pattern, dict):
            for field, pattern_str in pattern.items():
                # decoded_* 键专门用于检测编码绕过，需要先解码再匹配
                needs_decode = field.lower().startswith('decoded_')
                compiled[field] = {
                    'regex': re.compile(pattern_str, re.IGNORECASE | re.DOTALL),
                    'needs_decode': needs_decode,
                    # 字段键名本身保留作为 target_field，
                    # 参数类键(params_*/decoded_*)在 _quick_match 中会被
                    # _is_param_field 识别并聚合到参数值，不再用 field.replace 截断
                    'field': field
                }
        elif isinstance(pattern, str):
            # 兼容旧版字符串模式
            compiled['legacy'] = {
                'regex': re.compile(pattern, re.IGNORECASE | re.DOTALL),
                'needs_decode': False,
                'field': 'combined'
            }

        return compiled

    # 内置默认白名单（与历史硬编码值保持一致），用于配置缺失时回退
    _DEFAULT_SAFE_AGENTS = [
        'googlebot', 'bingbot', 'slurp', 'duckduckbot',
        'baiduspider', 'yandexbot', 'facebookexternalhit',
        'twitterbot', 'linkedinbot', 'pinterest',
        'applebot', 'semrushbot', 'mj12bot',
        'ahrefsbot', 'dotbot', 'archive.org_bot',
    ]
    _DEFAULT_STATIC_EXTENSIONS = [
        '.css', '.js', '.jpg', '.jpeg', '.png', '.gif', '.svg',
        '.ico', '.woff', '.woff2', '.ttf', '.eot', '.otf',
        '.mp4', '.mp3', '.avi', '.mov', '.pdf', '.xml',
    ]
    _DEFAULT_HEALTH_PATHS = [
        '/health', '/healthcheck', '/ping', '/status',
        '/metrics', '/actuator/health', '/ready',
        '/.well-known/', '/robots.txt', '/favicon.ico',
    ]
    _DEFAULT_INTERNAL_IPS = ['127.0.0.1', '::1', 'localhost']

    def _load_whitelist(self, config: Optional[Dict[str, Any]]) -> None:
        """从配置加载白名单；配置缺失或为空列表时回退到内置默认值。

        配置示例（config.yaml 的 whitelist 节）：
            whitelist:
              safe_agents: [googlebot, ...]
              static_extensions: [.css, .js, ...]
              health_paths: [/health, ...]
              internal_ips: [127.0.0.1, 10.0.0.0/8]
        """
        wl = {}
        if isinstance(config, dict):
            wl = config.get('whitelist') or {}
        if not isinstance(wl, dict):
            wl = {}

        def _pick(key, default):
            val = wl.get(key)
            return [str(v).lower() for v in val] if val else list(default)

        self.safe_agents = _pick('safe_agents', self._DEFAULT_SAFE_AGENTS)
        # 静态扩展名/健康路径/internal_ip 保留原大小写比较逻辑，统一存小写以做不敏感匹配
        self.static_extensions = [e.lower() for e in _pick('static_extensions', self._DEFAULT_STATIC_EXTENSIONS)]
        self.health_paths = _pick('health_paths', self._DEFAULT_HEALTH_PATHS)
        self.internal_ips = _pick('internal_ips', self._DEFAULT_INTERNAL_IPS)

    def _collect_aggregation_rules(self) -> List[Dict[str, Any]]:
        """从已加载规则中收集声明了 aggregation 字段的规则，并预解析参数。"""
        agg_rules = []
        for rule in self.rules:
            agg = rule.get('aggregation')
            if not isinstance(agg, dict):
                continue
            window = _parse_duration(agg.get('window', 60))
            threshold = int(agg.get('threshold', 20))
            if threshold <= 0 or window <= 0:
                self.logger.warning(
                    f"规则 {rule.get('name')} 的 aggregation 阈值/窗口无效，已忽略"
                )
                continue
            # 可选：端点正则预编译（限定只统计某些路径）
            path_re = None
            path_pattern = agg.get('path_pattern')
            if path_pattern:
                try:
                    path_re = re.compile(path_pattern, re.IGNORECASE)
                except re.error as e:
                    self.logger.warning(
                        f"规则 {rule.get('name')} 的 path_pattern 编译失败: {e}"
                    )
            # 可选：只统计某些状态码（如暴力破解只计失败响应）
            failed_status = set(agg.get('failed_status', []))
            # 将状态码统一为字符串比较，避免 int/str 不匹配
            failed_status = {str(s) for s in failed_status}
            rule['_agg_compiled'] = {
                'window': window,
                'threshold': threshold,
                'field': agg.get('field', 'src_ip'),
                'path_re': path_re,
                'failed_status': failed_status,
                'failed_only': bool(failed_status),
            }
            agg_rules.append(rule)
        if agg_rules:
            self.logger.info(
                f"加载 {len(agg_rules)} 条聚合规则: "
                f"{[r.get('name') for r in agg_rules]}"
            )
        return agg_rules

    def _bucket_key(self, rule: Dict[str, Any], log_entry: Dict[str, Any],
                    agg: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
        """计算某条日志在某聚合规则下的桶键 (rule_name, group_value, path_key)。

        返回 None 表示该日志不参与此聚合规则（如端点不匹配）。
        """
        group_value = log_entry.get(agg['field'])
        if group_value is None:
            group_value = self._get_field_value(log_entry, agg['field'])
        if group_value is None:
            return None
        path = log_entry.get('request_path', '') or log_entry.get('url', '') or ''
        path_key = path
        if agg['path_re']:
            if not agg['path_re'].search(path):
                return None  # 端点不匹配，不参与该聚合
        return (rule.get('name', 'unknown'), str(group_value), path_key)

    def observe_for_aggregation(self, log_entry: Dict[str, Any]) -> List[Dict[str, Any]]:
        """将一条日志喂给聚合层，返回本次触发的聚合告警列表（可能为空）。

        与 match_log 解耦：可由调用方在逐行匹配之外单独调用，
        也可由 match_log 内部统一调用（见 match_log 实现）。
        """
        if not log_entry or not self._aggregation_rules:
            return []

        now = time.time()
        status = str(log_entry.get('status_code', log_entry.get('status', '')))
        alerts = []

        for rule in self._aggregation_rules:
            agg = rule['_agg_compiled']
            key = self._bucket_key(rule, log_entry, agg)
            if key is None:
                continue

            is_failed = status in agg['failed_status']
            self._aggregator.record(
                key, timestamp=now,
                failed_only=agg['failed_only'], is_failed=is_failed
            )

            count = self._aggregator.count_in_window(key, agg['window'], now)
            # 达阈值且本窗口内未告警过，则生成一条聚合告警
            if count >= agg['threshold'] and not self._aggregator.already_alerted(
                    key, agg['window'], now):
                alerts.append(self._build_aggregation_match(rule, log_entry, agg, count))
                self._aggregator.mark_alerted(key, now)

        # 周期性清理，防止长跑场景下 buckets 无限增长
        self._aggregation_observed += 1
        if self._aggregation_observed >= self._aggregation_cleanup_every:
            self._aggregator.cleanup(self._max_aggregation_window(), now)
            self._aggregation_observed = 0

        return alerts

    def _max_aggregation_window(self) -> float:
        """所有聚合规则中最大的窗口值，用于过期清理。"""
        m = 60.0
        for rule in self._aggregation_rules:
            w = rule.get('_agg_compiled', {}).get('window', 60)
            if w > m:
                m = w
        return m

    def _build_aggregation_match(self, rule: Dict[str, Any], log_entry: Dict[str, Any],
                                 agg: Dict[str, Any], count: int) -> Dict[str, Any]:
        """构造一条聚合告警，结构与普通 match_result 兼容，便于并入报告流程。"""
        # 聚合规则没有单行 pattern 命中，直接以声明参数构造评分依据
        match_details = {
            'matched_fields': [agg['field']],
            'required_decode': False,
            'confidence_level': 'high',  # 跨事件计数达阈值，置信度高
            'aggregated': True,
            'count': count,
            'threshold': agg['threshold'],
            'window_seconds': agg['window'],
            'group_value': log_entry.get(agg['field']),
        }
        threat_score = self._calculate_threat_score(rule, match_details)
        rule_id = rule.get('source_file', rule.get('category', 'unknown'))
        match_result = {
            'rule': rule,
            'log_entry': log_entry,
            'threat_score': threat_score,
            'match_details': match_details,
            'rule_id': rule_id,
            'timestamp': time.time(),
            'confidence_level': 'high',
        }
        self.rule_stats[rule_id] += 1
        return match_result

    def reset_aggregation(self) -> None:
        """清空所有聚合状态（测试与重跑时使用）。"""
        self._aggregator = AggregationWindow()
        self._aggregation_observed = 0

    def _decode_and_normalize(self, text: str) -> str:
        """解码和标准化文本"""
        if not text:
            return ""

        try:
            # URL解码
            decoded = unquote(text)

            # HTML解码
            decoded = html.unescape(decoded)

            # Base64解码（尝试但失败时忽略）
            try:
                import base64
                if decoded.strip().endswith('=') or len(decoded.strip()) % 4 == 0:
                    try:
                        base64_decoded = base64.b64decode(decoded).decode('utf-8', errors='ignore')
                        # 如果解码结果包含可读文本，则使用它
                        if any(c.isprintable() for c in base64_decoded):
                            decoded = base64_decoded
                    except:
                        pass
            except:
                pass

            return decoded
        except Exception as e:
            self.logger.debug(f"解码失败: {e}")
            return text

    def _extract_attack_context(self, log_entry: Dict[str, Any]) -> Dict[str, Any]:
        """提取攻击上下文信息"""
        context = {}

        # 提取URL参数
        if 'request_path' in log_entry:
            try:
                parsed = parse_qs(log_entry['request_path'])
                for key, values in parsed.items():
                    if values:
                        context[f'param_{key}'] = values[0]
            except:
                pass

        # 提取请求头
        headers = {}
        if 'request_headers' in log_entry:
            # 如果是字典形式，直接使用
            if isinstance(log_entry['request_headers'], dict):
                headers.update(log_entry['request_headers'])
            # 如果是字符串形式，解析它
            elif isinstance(log_entry['request_headers'], str):
                try:
                    # 简单的HTTP头解析
                    for line in log_entry['request_headers'].split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            headers[key.strip().lower()] = value.strip()
                except:
                    pass

        # 添加常用的请求头字段
        for field in ['user_agent', 'referer', 'x_forwarded_for', 'x-auth', 'x-block']:
            if field in log_entry:
                headers[field] = log_entry[field]
            # 尝试从headers字典中获取（不区分大小写）
            elif headers:
                for header_key, header_value in headers.items():
                    if header_key.lower() == field.lower():
                        headers[field] = header_value
                        break

        # 将headers合并到context中
        context.update(headers)

        # 提取请求体（如果有）
        if 'request_body' in log_entry:
            body = log_entry['request_body']
            # 如果是字典，转换为字符串
            if isinstance(body, dict):
                context['body'] = str(body)
            # 如果是字符串，直接使用
            elif isinstance(body, str):
                context['body'] = body

        # 处理其他特殊字段
        special_fields = ['status_code', 'response_size', 'processing_time']
        for field in special_fields:
            if field in log_entry:
                context[field] = str(log_entry[field])

        return context

    # 参数类字段键：这类键在规则里表示"请求参数"，但日志里没有同名字段，
    # 需要聚合 URL query 参数 + body 参数 + request_path 作为匹配目标。
    # 覆盖 params / params_* / decoded_params / decoded_* 等。
    @staticmethod
    def _is_param_field(field_name: str) -> bool:
        if not field_name:
            return False
        f = field_name.lower()
        if f == 'params':
            return True
        if f.startswith('params_'):
            return True
        if f == 'decoded_params' or f.startswith('decoded_'):
            return True
        return False

    def _collect_param_values(self, log_entry: Dict[str, Any], context: Dict[str, Any]) -> str:
        """聚合请求中所有参数值，供参数类字段键匹配。

        来源优先级：
        1. context 里的 param_xxx 键（_extract_attack_context 已解析 URL query）
        2. request_path / url 整体（攻击载荷常直接出现在路径里，如 /?id=union+select）
        3. request_body（POST 参数）
        用换行拼接，保证任一来源的载荷都能被独立匹配。
        """
        parts: List[str] = []
        # 1. 已解析的 query 参数值
        for k, v in context.items():
            if k.startswith('param_') and v:
                parts.append(str(v))
        # 2. request_path / url 原始串（含 query 部分，载荷可能未被 parse_qs 正确切分）
        for f in ('request_path', 'url', 'path'):
            val = log_entry.get(f)
            if val:
                parts.append(str(val))
        # 3. 请求体
        body = context.get('body') or log_entry.get('request_body')
        if body:
            parts.append(str(body))
        return '\n'.join(parts)

    def _collect_combined_text(self, log_entry: Dict[str, Any], context: Dict[str, Any]) -> str:
        """聚合整个请求的可匹配文本，供字符串 pattern(legacy combined)规则使用。

        覆盖薄规则(如 path_traversal/ssrf/xxe)的常见载荷位置：
        request_path、url、参数值、请求体、UA、referer。
        """
        parts: List[str] = []
        for f in ('request_path', 'url', 'request_line', 'request_body',
                  'user_agent', 'referer', 'request_headers'):
            val = log_entry.get(f)
            if val:
                parts.append(str(val))
        # 参数值（来自 context）
        for k, v in context.items():
            if k.startswith('param_') and v:
                parts.append(str(v))
        return '\n'.join(parts)

    def _get_field_value(self, data_dict: Dict[str, Any], field_name: str) -> Any:
        """递归获取嵌套字典中的字段值"""
        if not data_dict or not field_name:
            return None

        # 直接查找
        if field_name in data_dict:
            return data_dict[field_name]

        # 递归查找嵌套字典
        for key, value in data_dict.items():
            if isinstance(value, dict):
                result = self._get_field_value(value, field_name)
                if result is not None:
                    return result
            # 如果是列表，检查每个元素
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        result = self._get_field_value(item, field_name)
                        if result is not None:
                            return result

        return None

    def _calculate_threat_score(self, rule: Dict[str, Any], match_details: Dict[str, Any]) -> ThreatScore:
        """计算威胁评分（增强版 - 支持置信度分级）"""
        base_score = 0.0
        confidence = 0.5  # 基础置信度
        attack_vectors = []
        risk_factors = []
        confidence_level = 'medium'  # 默认中等置信度

        # 获取匹配的置信度级别（来自上下文分析）
        if 'confidence_level' in match_details:
            confidence_level = match_details['confidence_level']

        # 根据置信度级别调整基础置信度
        confidence_adjustments = {
            'high': 0.25,
            'medium': 0.0,
            'low': -0.15
        }
        confidence += confidence_adjustments.get(confidence_level, 0.0)

        # 基于严重级别的基础分数（更精确）
        severity_scores = {
            'critical': 9.5,
            'high': 7.5,
            'medium': 5.5,
            'low': 3.5
        }
        base_score = severity_scores.get(rule.get('severity', 'medium'), 5.5)

        # 高置信度模式额外加分
        if confidence_level == 'high':
            base_score += 1.5
            risk_factors.append('high_confidence_detection')
        elif confidence_level == 'low':
            base_score -= 1.0

        # 匹配字段权重分析
        matched_fields = match_details.get('matched_fields', [])
        field_weights = {
            'request_body': 1.5,    # 请求体攻击更危险
            'params': 1.2,          # 参数注入
            'user_agent': 0.8,      # 工具检测
            'request_path': 1.0,    # 路径注入
            'request_headers': 1.3, # 请求头攻击
            'src_ip': 0.7           # IP相关
        }

        # 计算字段匹配加分
        for field in matched_fields:
            if field in field_weights:
                base_score += field_weights[field]
                confidence += 0.08

                # 特定字段类型的攻击向量
                if field == 'request_body':
                    attack_vectors.append('payload_injection')
                    risk_factors.append('complex_attack')
                elif field == 'params':
                    attack_vectors.append('parameter_pollution')
                elif field == 'user_agent':
                    attack_vectors.append('automated_attack')
                    risk_factors.append('tool_detected')
                elif field == 'request_headers':
                    attack_vectors.append('header_manipulation')
                    risk_factors.append('protocol_abuse')

        # 编码绕过检测（更严格）
        if match_details.get('required_decode', False):
            attack_vectors.append('evasion_technique')
            base_score += 2.0
            confidence += 0.15
            risk_factors.append('obfuscation_attempt')

        # 规则类别威胁分析（更详细）
        # 注意：未在此字典中的 category 会走 _DEFAULT_CATEGORY_THREAT 兜底，
        # 避免新增 category 时遗漏导致拿不到类别加分。
        category = rule.get('category', '')
        category_threats = {
            'rce': {'score': 2.5, 'vector': 'remote_code_execution', 'risk': 'system_compromise'},
            'injection': {'score': 2.0, 'vector': 'code_injection', 'risk': 'data_manipulation'},
            'sql_injection': {'score': 2.8, 'vector': 'database_compromise', 'risk': 'data_breach'},
            'xss': {'score': 1.8, 'vector': 'client_side_attack', 'risk': 'session_hijack'},
            'ssrf': {'score': 2.2, 'vector': 'server_side_request', 'risk': 'internal_network_access'},
            'file_inclusion': {'score': 2.3, 'vector': 'file_manipulation', 'risk': 'code_execution'},
            'command_injection': {'score': 2.6, 'vector': 'system_command_execution', 'risk': 'privilege_escalation'},
            'log4j_vulnerability': {'score': 3.0, 'vector': 'jndi_injection', 'risk': 'remote_code_execution'},
            'api_security': {'score': 1.9, 'vector': 'api_abuse', 'risk': 'unauthorized_access'},
            'threat_intelligence': {'score': 2.1, 'vector': 'known_threat', 'risk': 'confirmed_attack'},
            'supply_chain': {'score': 2.4, 'vector': 'supply_chain_attack', 'risk': 'wide_impact'},
            'zero_trust': {'score': 1.7, 'vector': 'trust_violation', 'risk': 'policy_breach'},
            'automated_response': {'score': 1.5, 'vector': 'automation_trigger', 'risk': 'mass_attack'},
            'privacy_compliance': {'score': 1.6, 'vector': 'privacy_violation', 'risk': 'compliance_breach'},
            'financial_security': {'score': 2.7, 'vector': 'financial_fraud', 'risk': 'monetary_loss'},
            'user_behavior': {'score': 1.4, 'vector': 'behavioral_anomaly', 'risk': 'insider_threat'},
            'attack_chain': {'score': 2.9, 'vector': 'multi_stage_attack', 'risk': 'advanced_persistent_threat'},
            'ai_ml_anomaly': {'score': 1.3, 'vector': 'anomaly_detection', 'risk': 'unknown_pattern'},
            'cloud_native': {'score': 2.0, 'vector': 'cloud_attack', 'risk': 'container_escape'},
            'file_upload': {'score': 2.5, 'vector': 'malicious_upload', 'risk': 'webshell_implant'},
            # —— 以下为补全：覆盖规则库实际使用但原先缺失的 category ——
            'path_traversal': {'score': 2.0, 'vector': 'directory_traversal', 'risk': 'file_disclosure'},
            'brute_force': {'score': 1.8, 'vector': 'credential_attack', 'risk': 'account_takeover'},
            'csrf': {'score': 1.5, 'vector': 'cross_site_request', 'risk': 'unauthorized_action'},
            'reconnaissance': {'score': 1.0, 'vector': 'reconnaissance', 'risk': 'information_disclosure'},
            'scanning': {'score': 1.1, 'vector': 'active_scanning', 'risk': 'vulnerability_discovery'},
            'enumeration': {'score': 1.2, 'vector': 'resource_enumeration', 'risk': 'information_disclosure'},
            'anomaly': {'score': 1.0, 'vector': 'traffic_anomaly', 'risk': 'service_abuse'},
            'error_analysis': {'score': 0.8, 'vector': 'error_disclosure', 'risk': 'fingerprinting'},
            'deserialization': {'score': 2.4, 'vector': 'deserialization_attack', 'risk': 'remote_code_execution'},
            'authentication': {'score': 2.1, 'vector': 'auth_attack', 'risk': 'access_bypass'},
            'access_control': {'score': 1.9, 'vector': 'broken_access_control', 'risk': 'privilege_escalation'},
            'session_security': {'score': 1.7, 'vector': 'session_attack', 'risk': 'session_hijack'},
            'misconfiguration': {'score': 1.4, 'vector': 'security_misconfiguration', 'risk': 'exposure'},
            'information_disclosure': {'score': 1.3, 'vector': 'info_leak', 'risk': 'data_disclosure'},
            'sensitive_access': {'score': 1.6, 'vector': 'sensitive_data_access', 'risk': 'data_breach'},
            'request_smuggling': {'score': 2.3, 'vector': 'http_smuggling', 'risk': 'request_hijack'},
            'cache_poisoning': {'score': 1.8, 'vector': 'cache_poisoning', 'risk': 'content_injection'},
            'cryptography': {'score': 1.5, 'vector': 'weak_crypto', 'risk': 'data_compromise'},
            'crypto_mining': {'score': 1.4, 'vector': 'cryptomining', 'risk': 'resource_hijack'},
            'webshell': {'score': 2.6, 'vector': 'webshell_activity', 'risk': 'persistent_access'},
            'phishing': {'score': 1.6, 'vector': 'phishing', 'risk': 'credential_theft'},
            'business_logic': {'score': 1.9, 'vector': 'logic_abuse', 'risk': 'business_bypass'},
            'attack_tool': {'score': 2.0, 'vector': 'attack_tool', 'risk': 'active_exploitation'},
            'apt_threat': {'score': 2.8, 'vector': 'apt', 'risk': 'advanced_persistent_threat'},
            'attack_chain_correlation': {'score': 2.7, 'vector': 'attack_chain', 'risk': 'multi_stage_attack'},
            'user_behavior_analysis': {'score': 1.2, 'vector': 'behavioral_anomaly', 'risk': 'insider_threat'},
            'cloud_security': {'score': 2.0, 'vector': 'cloud_attack', 'risk': 'cloud_compromise'},
            'cloud_native_threats': {'score': 2.0, 'vector': 'cloud_native_attack', 'risk': 'container_escape'},
            'iot_security': {'score': 1.8, 'vector': 'iot_attack', 'risk': 'device_compromise'},
            'mobile_security': {'score': 1.7, 'vector': 'mobile_attack', 'risk': 'app_compromise'},
            'blockchain_security': {'score': 2.0, 'vector': 'web3_attack', 'risk': 'asset_theft'},
        }
        # 兜底：未收录的 category 给一个保守的中等加分，避免静默忽略
        _DEFAULT_CATEGORY_THREAT = {'score': 1.2, 'vector': 'unknown', 'risk': 'under_evaluation'}

        threat_info = category_threats.get(category, _DEFAULT_CATEGORY_THREAT)
        base_score += threat_info['score']
        attack_vectors.append(threat_info['vector'])
        risk_factors.append(threat_info['risk'])
        confidence += 0.12

        # 攻击模式严重性分析
        attack_patterns = rule.get('attack_patterns', [])
        if attack_patterns:
            high_risk_patterns = ['remote_code_execution', 'sql注入', '命令注入', '文件包含', 'SSRF', '反序列化']
            medium_risk_patterns = ['XSS', 'CSRF', '路径遍历', '信息泄露', '权限绕过']

            for pattern in attack_patterns:
                if any(high in pattern for high in high_risk_patterns):
                    base_score += 1.0
                    confidence += 0.1
                elif any(medium in pattern for medium in medium_risk_patterns):
                    base_score += 0.5
                    confidence += 0.05

        # 规则复杂度和覆盖范围
        pattern = rule.get('pattern', {})
        if isinstance(pattern, dict):
            pattern_count = len(pattern)
            if pattern_count >= 5:  # 复杂规则
                base_score += 0.3
                confidence += 0.05
            elif pattern_count >= 3:  # 中等复杂度
                base_score += 0.15

        # 威胁等级调整
        threat_level = rule.get('threat_level', '')
        if threat_level == 'critical':
            base_score += 1.0
            confidence += 0.1
        elif threat_level == 'high':
            base_score += 0.5

        # 响应状态码分析
        response_codes = rule.get('response_codes', [])
        dangerous_codes = [200, 201, 202]  # 成功响应表示攻击可能成功
        if any(code in dangerous_codes for code in response_codes):
            base_score += 0.4
            confidence += 0.08

        # 限制分数范围
        base_score = min(max(base_score, 1.0), 10.0)
        confidence = min(max(confidence, 0.1), 1.0)

        # 确定最终严重级别（更精确的阈值）
        if base_score >= 9.0:
            final_severity = 'critical'
        elif base_score >= 7.5:
            final_severity = 'high'
        elif base_score >= 5.0:
            final_severity = 'medium'
        else:
            final_severity = 'low'

        # 去重攻击向量和风险因子
        attack_vectors = list(set(attack_vectors))
        risk_factors = list(set(risk_factors))

        return ThreatScore(
            score=base_score,
            severity=final_severity,
            confidence=confidence,
            attack_vectors=attack_vectors,
            risk_factors=risk_factors,
            confidence_level=confidence_level
        )

    def match_log(self, log_entry: Dict[str, Any]) -> List[Dict[str, Any]]:
        """多阶段规则匹配"""
        if not log_entry:
            return []

        matched = []

        # 第一阶段：快速匹配
        quick_matches = self._quick_match(log_entry)

        # 第二阶段：上下文分析
        for match in quick_matches:
            context_match = self._context_analysis(match, log_entry)
            if context_match:
                # 将置信度级别传递给match的details
                match_details = match.get('details', {})
                if 'confidence_level' in match:
                    match_details['confidence_level'] = match['confidence_level']
                # 添加上下文标记
                if match.get('is_internal'):
                    match_details['is_internal'] = True
                if match.get('is_documentation'):
                    match_details['is_documentation'] = True
                if match.get('is_api_doc'):
                    match_details['is_api_doc'] = True

                # 第三阶段：威胁评分
                threat_score = self._calculate_threat_score(match['rule'], match_details)

                match_result = {
                    'rule': match['rule'],
                    'log_entry': log_entry,
                    'threat_score': threat_score,
                    'match_details': match_details,
                    'rule_id': match.get('rule_id'),
                    'timestamp': time.time(),
                    'confidence_level': match_details.get('confidence_level', 'medium')
                }

                matched.append(match_result)

                # 更新统计
                self.rule_stats[match.get('rule_id', 'unknown')] += 1

        # 跨事件聚合层：把当前日志喂给滑动窗口，并入可能触发的聚合告警。
        # 这样 main.py 调用 match_log 即可同时获得单行匹配与聚合告警，调用点无需改动。
        aggregation_alerts = self.observe_for_aggregation(log_entry)
        if aggregation_alerts:
            matched.extend(aggregation_alerts)

        # 按威胁评分和置信度排序
        matched.sort(key=lambda x: (x['threat_score'].score, x.get('confidence_level', 'medium')), reverse=True)

        return matched

    def _quick_match(self, log_entry: Dict[str, Any]) -> List[Dict[str, Any]]:
        """快速匹配阶段"""
        matches = []

        # 提取攻击上下文
        context = self._extract_attack_context(log_entry)

        for rule_id, rule_data in self.compiled_rules.items():
            rule = rule_data['rule']
            # 仅聚合的规则（如暴力破解）不在单行匹配阶段命中，
            # 其告警完全由 observe_for_aggregation 阈值触发，避免逐行误报。
            if rule.get('aggregation_only'):
                continue
            compiled = rule_data['compiled']
            match_details = {'matched_fields': [], 'required_decode': False}

            # 匹配编译后的规则
            for field_name, pattern_info in compiled.items():
                target_field = pattern_info['field']
                regex = pattern_info['regex']
                needs_decode = pattern_info['needs_decode']

                # 获取目标字段值。三种来源：
                # 1. 参数类键(params/params_*/decoded_*) → 聚合所有参数值
                # 2. 字符串 pattern 的 combined 键 → 聚合整个请求的可匹配文本
                # 3. 普通键(request_path/user_agent/...) → 直接取日志或上下文字段
                if self._is_param_field(target_field):
                    field_value = self._collect_param_values(log_entry, context)
                elif target_field == 'combined':
                    field_value = self._collect_combined_text(log_entry, context)
                else:
                    field_value = self._get_field_value(log_entry, target_field) or self._get_field_value(context, target_field)
                if not field_value:
                    continue

                # 如果字段值是复杂数据类型，转换为字符串
                if not isinstance(field_value, str):
                    field_value = str(field_value)

                # 如果需要解码，先解码再匹配
                original_value = field_value
                if needs_decode:
                    field_value = self._decode_and_normalize(field_value)
                    if field_value != original_value:
                        match_details['required_decode'] = True

                # 执行正则匹配
                if regex.search(field_value):
                    match_details['matched_fields'].append(target_field)

            # 如果有匹配的字段，则添加到结果
            if match_details['matched_fields']:
                matches.append({
                    'rule': rule,
                    'details': match_details,
                    'rule_id': rule_id
                })

        return matches

    def _context_analysis(self, match: Dict[str, Any], log_entry: Dict[str, Any]) -> bool:
        """上下文分析阶段 - 增强版"""
        # 获取请求的各个部分
        user_agent = log_entry.get('user_agent', '').lower()
        request_path = log_entry.get('request_path', '')
        referer = log_entry.get('referer', '')

        # 1. 已知安全爬虫白名单（可配置，见 config.yaml 的 whitelist.safe_agents）
        if any(agent in user_agent for agent in self.safe_agents):
            return False

        # 2. 静态资源请求（通常不是攻击目标）
        if any(request_path.lower().endswith(ext) for ext in self.static_extensions):
            return False

        # 3. 健康检查和监控端点
        if any(hp in request_path.lower() for hp in self.health_paths):
            return False

        # 4. 内部服务请求（可配置，见 whitelist.internal_ips）
        src_ip = log_entry.get('src_ip', '')
        if src_ip in self.internal_ips:
            # 内部请求降低优先级但不完全过滤
            match['is_internal'] = True

        # 5. 技术文档和学习网站（基于Referer）
        doc_referers = [
            'stackoverflow.com', 'github.com', 'developer.mozilla.org',
            'w3schools.com', 'wikipedia.org', 'medium.com',
            'stackoverflow.com', 'docs.', 'documentation'
        ]
        if any(dr in referer.lower() for dr in doc_referers):
            match['is_documentation'] = True

        # 6. 检测是否为API文档或示例
        api_doc_patterns = ['/api/docs', '/swagger', '/redoc', '/openapi', '/graphql']
        if any(ad in request_path.lower() for ad in api_doc_patterns):
            match['is_api_doc'] = True

        # 7. 分析置信度级别
        rule = match.get('rule', {})
        confidence_levels = rule.get('confidence_levels', {})
        matched_field = match.get('details', {}).get('matched_fields', [''])[0]

        # 根据匹配的字段确定置信度级别
        if confidence_levels:
            for level, fields in confidence_levels.items():
                if matched_field in fields or any(f in matched_field for f in fields):
                    match['confidence_level'] = level
                    break
            else:
                match['confidence_level'] = 'medium'
        else:
            match['confidence_level'] = 'medium'

        return True

    def get_rule_statistics(self) -> Dict[str, Any]:
        """获取规则匹配统计"""
        total_matches = sum(self.rule_stats.values())
        stats = {
            'total_rules': len(self.rules),
            'total_matches': total_matches,
            'rule_match_counts': dict(self.rule_stats),
            'most_triggered_rules': sorted(
                self.rule_stats.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }

        # 添加AI分析状态
        if self.enable_ai_analysis and self.ai_analyzer:
            stats['ai_analysis'] = self.ai_analyzer.get_analyzer_status()

        return stats

    def match_log_with_ai(self, log_entry: Dict[str, Any]) -> List[Dict[str, Any]]:
        """带AI增强的规则匹配"""
        # 首先执行传统规则匹配
        traditional_matches = self.match_log(log_entry)

        # 如果AI分析不可用，直接返回传统匹配结果
        if not self.enable_ai_analysis or not self.ai_analyzer:
            return traditional_matches

        try:
            # 提取匹配的规则名称
            matched_rule_names = [match['rule']['name'] for match in traditional_matches]

            # 执行AI分析
            ai_result = self.ai_analyzer.analyze_log_entry(log_entry, matched_rule_names)

            if ai_result:
                # 将AI分析结果整合到匹配结果中
                enhanced_matches = []

                for match in traditional_matches:
                    enhanced_match = match.copy()

                    # 添加AI分析信息
                    enhanced_match['ai_analysis'] = {
                        'is_malicious': ai_result.is_malicious,
                        'ai_threat_level': ai_result.threat_analysis.threat_level,
                        'ai_attack_types': ai_result.threat_analysis.attack_types,
                        'ai_confidence': ai_result.confidence_score,
                        'ai_recommendations': ai_result.threat_analysis.recommendations,
                        'ai_analysis_summary': ai_result.threat_analysis.analysis_summary,
                        'ai_processing_time': ai_result.processing_time,
                        'model_used': ai_result.model_used
                    }

                    # 如果AI分析认为是恶意的，提高威胁评分
                    if ai_result.is_malicious:
                        # 调整威胁评分，融合AI分析结果
                        original_score = enhanced_match['threat_score'].score
                        ai_score = ai_result.threat_analysis.threat_score

                        # 加权平均：AI权重0.4，规则权重0.6
                        blended_score = original_score * 0.6 + ai_score * 0.4

                        # 更新威胁评分
                        enhanced_match['threat_score'].score = blended_score

                        # 根据AI分析调整严重级别
                        if ai_result.threat_analysis.threat_level == '严重' and enhanced_match['threat_score'].severity != 'critical':
                            enhanced_match['threat_score'].severity = 'critical'
                        elif ai_result.threat_analysis.threat_level == '高' and enhanced_match['threat_score'].severity == 'low':
                            enhanced_match['threat_score'].severity = 'high'

                    enhanced_matches.append(enhanced_match)

                # 如果AI检测到威胁但传统规则没有匹配，创建AI专用匹配项
                if ai_result.is_malicious and not traditional_matches:
                    ai_match = {
                        'rule': {
                            'name': 'AI威胁检测',
                            'category': 'ai_detection',
                            'description': '基于AI模型的智能威胁检测',
                            'severity': ai_result.threat_analysis.threat_level.lower(),
                            'source': 'ai_analysis'
                        },
                        'log_entry': log_entry,
                        'threat_score': ThreatScore(
                            score=ai_result.threat_analysis.threat_score,
                            severity=ai_result.threat_analysis.threat_level.lower(),
                            confidence=ai_result.confidence_score,
                            attack_vectors=ai_result.threat_analysis.attack_types,
                            risk_factors=ai_result.threat_analysis.risk_factors
                        ),
                        'match_details': {
                            'matched_fields': ['ai_analysis'],
                            'ai_detected': True
                        },
                        'rule_id': 'ai_detection',
                        'timestamp': time.time(),
                        'ai_analysis': {
                            'is_malicious': ai_result.is_malicious,
                            'ai_threat_level': ai_result.threat_analysis.threat_level,
                            'ai_attack_types': ai_result.threat_analysis.attack_types,
                            'ai_confidence': ai_result.confidence_score,
                            'ai_recommendations': ai_result.threat_analysis.recommendations,
                            'ai_analysis_summary': ai_result.threat_analysis.analysis_summary,
                            'ai_processing_time': ai_result.processing_time,
                            'model_used': ai_result.model_used,
                            'pure_ai_detection': True
                        }
                    }
                    enhanced_matches.append(ai_match)

                return enhanced_matches
            else:
                # AI分析失败，返回传统匹配结果
                self.logger.warning("AI分析失败，使用传统规则匹配结果")
                return traditional_matches

        except Exception as e:
            self.logger.error(f"AI增强匹配失败: {e}")
            return traditional_matches

    async def match_log_with_ai_async(self, log_entry: Dict[str, Any]) -> List[Dict[str, Any]]:
        """异步AI增强规则匹配"""
        # 首先执行传统规则匹配
        traditional_matches = self.match_log(log_entry)

        # 如果AI分析不可用，直接返回传统匹配结果
        if not self.enable_ai_analysis or not self.ai_analyzer:
            return traditional_matches

        try:
            # 提取匹配的规则名称
            matched_rule_names = [match['rule']['name'] for match in traditional_matches]

            # 执行异步AI分析
            ai_result = await self.ai_analyzer.analyze_log_entry_async(log_entry, matched_rule_names)

            if ai_result:
                # 将AI分析结果整合到匹配结果中（与同步版本相同的逻辑）
                enhanced_matches = []

                for match in traditional_matches:
                    enhanced_match = match.copy()

                    # 添加AI分析信息
                    enhanced_match['ai_analysis'] = {
                        'is_malicious': ai_result.is_malicious,
                        'ai_threat_level': ai_result.threat_analysis.threat_level,
                        'ai_attack_types': ai_result.threat_analysis.attack_types,
                        'ai_confidence': ai_result.confidence_score,
                        'ai_recommendations': ai_result.threat_analysis.recommendations,
                        'ai_analysis_summary': ai_result.threat_analysis.analysis_summary,
                        'ai_processing_time': ai_result.processing_time,
                        'model_used': ai_result.model_used
                    }

                    # 如果AI分析认为是恶意的，提高威胁评分
                    if ai_result.is_malicious:
                        original_score = enhanced_match['threat_score'].score
                        ai_score = ai_result.threat_analysis.threat_score
                        blended_score = original_score * 0.6 + ai_score * 0.4

                        enhanced_match['threat_score'].score = blended_score

                        if ai_result.threat_analysis.threat_level == '严重' and enhanced_match['threat_score'].severity != 'critical':
                            enhanced_match['threat_score'].severity = 'critical'
                        elif ai_result.threat_analysis.threat_level == '高' and enhanced_match['threat_score'].severity == 'low':
                            enhanced_match['threat_score'].severity = 'high'

                    enhanced_matches.append(enhanced_match)

                # 如果AI检测到威胁但传统规则没有匹配，创建AI专用匹配项
                if ai_result.is_malicious and not traditional_matches:
                    ai_match = {
                        'rule': {
                            'name': 'AI威胁检测',
                            'category': 'ai_detection',
                            'description': '基于AI模型的智能威胁检测',
                            'severity': ai_result.threat_analysis.threat_level.lower(),
                            'source': 'ai_analysis'
                        },
                        'log_entry': log_entry,
                        'threat_score': ThreatScore(
                            score=ai_result.threat_analysis.threat_score,
                            severity=ai_result.threat_analysis.threat_level.lower(),
                            confidence=ai_result.confidence_score,
                            attack_vectors=ai_result.threat_analysis.attack_types,
                            risk_factors=ai_result.threat_analysis.risk_factors
                        ),
                        'match_details': {
                            'matched_fields': ['ai_analysis'],
                            'ai_detected': True
                        },
                        'rule_id': 'ai_detection',
                        'timestamp': time.time(),
                        'ai_analysis': {
                            'is_malicious': ai_result.is_malicious,
                            'ai_threat_level': ai_result.threat_analysis.threat_level,
                            'ai_attack_types': ai_result.threat_analysis.attack_types,
                            'ai_confidence': ai_result.confidence_score,
                            'ai_recommendations': ai_result.threat_analysis.recommendations,
                            'ai_analysis_summary': ai_result.threat_analysis.analysis_summary,
                            'ai_processing_time': ai_result.processing_time,
                            'model_used': ai_result.model_used,
                            'pure_ai_detection': True
                        }
                    }
                    enhanced_matches.append(ai_match)

                return enhanced_matches
            else:
                self.logger.warning("异步AI分析失败，使用传统规则匹配结果")
                return traditional_matches

        except Exception as e:
            self.logger.error(f"异步AI增强匹配失败: {e}")
            return traditional_matches

    def analyze_with_ai(self, log_entry: Dict[str, Any], rule_name: str, threat_score: float) -> Optional[str]:
        """使用AI解释规则匹配"""
        if not self.enable_ai_analysis or not self.ai_analyzer:
            return None

        try:
            explanation = self.ai_analyzer.explain_detection(rule_name, log_entry, threat_score)
            return explanation
        except Exception as e:
            self.logger.error(f"AI解释失败: {e}")
            return None

    def natural_language_query(self, query: str, log_data: List[Dict[str, Any]] = None) -> Optional[str]:
        """自然语言查询接口"""
        if not self.enable_ai_analysis or not self.ai_analyzer:
            return "AI分析功能未启用"

        try:
            response = self.ai_analyzer.natural_language_query(query, log_data)
            return response
        except Exception as e:
            self.logger.error(f"自然语言查询失败: {e}")
            return f"查询失败: {str(e)}"

    def get_ai_recommendations(self, log_entry: Dict[str, Any], rule_matches: List[Dict[str, Any]]) -> List[str]:
        """获取AI生成的安全建议"""
        if not self.enable_ai_analysis or not self.ai_analyzer:
            return ["AI分析功能未启用"]

        try:
            # 查找AI分析结果
            ai_analysis = None
            for match in rule_matches:
                if 'ai_analysis' in match:
                    ai_analysis = match['ai_analysis']
                    break

            if ai_analysis and ai_analysis.get('ai_recommendations'):
                return ai_analysis['ai_recommendations']

            # 如果没有找到AI分析结果，执行新的分析
            matched_rule_names = [match['rule']['name'] for match in rule_matches]
            ai_result = self.ai_analyzer.analyze_log_entry(log_entry, matched_rule_names)

            if ai_result:
                return self.ai_analyzer.get_security_recommendations(ai_result)

            return ["无法生成AI建议"]

        except Exception as e:
            self.logger.error(f"获取AI建议失败: {e}")
            return [f"建议生成失败: {str(e)}"]

    def enable_ai_support(self) -> bool:
        """启用AI支持"""
        if self.enable_ai_analysis:
            return True

        try:
            from core.ai_threat_analyzer import get_ai_threat_analyzer
            self.ai_analyzer = get_ai_threat_analyzer()
            self.enable_ai_analysis = True
            self.logger.info("AI威胁分析已启用")
            return True
        except Exception as e:
            self.logger.error(f"启用AI支持失败: {e}")
            return False

    def disable_ai_support(self):
        """禁用AI支持"""
        self.enable_ai_analysis = False
        self.ai_analyzer = None
        self.logger.info("AI威胁分析已禁用")