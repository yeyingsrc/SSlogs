import re
import html
import hashlib
import hmac
import secrets
import time
import logging
from typing import Dict, Any, List, Optional, Tuple, Union, Callable, Pattern
from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse, unquote
import ipaddress
from pathlib import Path

from .exceptions import SecurityValidationError


class ValidationLevel(Enum):
    """验证级别"""
    PERMISSIVE = "permissive"      # 宽松验证
    MODERATE = "moderate"          # 适中验证
    STRICT = "strict"             # 严格验证
    PARANOID = "paranoid"         # 偏执验证


class ThreatType(Enum):
    """威胁类型"""
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    COMMAND_INJECTION = "command_injection"
    PATH_TRAVERSAL = "path_traversal"
    LDAP_INJECTION = "ldap_injection"
    XXE = "xxe"
    SSRF = "ssrf"
    DESERIALIZATION = "deserialization"
    BUFFER_OVERFLOW = "buffer_overflow"
    FORMAT_STRING = "format_string"
    RACE_CONDITION = "race_condition"


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    threats: List[ThreatType] = None
    risk_score: float = 0.0
    sanitized_input: Optional[str] = None
    details: Dict[str, Any] = None

    def __post_init__(self):
        if self.threats is None:
            self.threats = []
        if self.details is None:
            self.details = {}


@dataclass
class SecurityRule:
    """安全规则"""
    name: str
    pattern: Pattern
    threat_type: ThreatType
    severity: str  # low, medium, high, critical
    description: str = ""
    enabled: bool = True


class InputValidator:
    """输入验证器"""

    def __init__(self, validation_level: ValidationLevel = ValidationLevel.MODERATE):
        self.validation_level = validation_level
        self.logger = logging.getLogger(__name__)
        self.custom_rules: List[SecurityRule] = []
        self._init_default_rules()

    def _init_default_rules(self):
        """初始化默认安全规则"""
        default_rules = [
            # SQL注入模式
            SecurityRule(
                name="SQL Injection - Union Select",
                pattern=re.compile(r'(?i)(union\s+select|select\s+.*\s+from\s+)', re.IGNORECASE),
                threat_type=ThreatType.SQL_INJECTION,
                severity="high",
                description="检测SQL注入中的UNION SELECT攻击"
            ),
            SecurityRule(
                name="SQL Injection - Comments",
                pattern=re.compile(r'(?i)(--|#|/\*|\*/)', re.IGNORECASE),
                threat_type=ThreatType.SQL_INJECTION,
                severity="medium",
                description="检测SQL注释字符"
            ),
            SecurityRule(
                name="SQL Injection - Boolean",
                pattern=re.compile(r'(?i)(\bor\b\s+1\s*=\s*1|\band\b\s+1\s*=\s*1)', re.IGNORECASE),
                threat_type=ThreatType.SQL_INJECTION,
                severity="high",
                description="检测SQL布尔注入"
            ),

            # XSS模式
            SecurityRule(
                name="XSS - Script Tag",
                pattern=re.compile(r'(?i)(<script[^>]*>.*?</script>)', re.IGNORECASE | re.DOTALL),
                threat_type=ThreatType.XSS,
                severity="critical",
                description="检测Script标签注入"
            ),
            SecurityRule(
                name="XSS - Event Handlers",
                pattern=re.compile(r'(?i)(onload|onerror|onclick|onmouseover\s*=)', re.IGNORECASE),
                threat_type=ThreatType.XSS,
                severity="high",
                description="检测JavaScript事件处理器"
            ),
            SecurityRule(
                name="XSS - JavaScript",
                pattern=re.compile(r'(?i)(javascript:|vbscript:)', re.IGNORECASE),
                threat_type=ThreatType.XSS,
                severity="high",
                description="检测JavaScript协议"
            ),

            # 命令注入模式
            SecurityRule(
                name="Command Injection - Unix",
                pattern=re.compile(r'(?i)(;|\||&|`|\$\(|\$\{)', re.IGNORECASE),
                threat_type=ThreatType.COMMAND_INJECTION,
                severity="critical",
                description="检测Unix命令注入字符"
            ),
            SecurityRule(
                name="Command Injection - Commands",
                pattern=re.compile(r'(?i)(cat\s+|ls\s+|rm\s+-rf|wget\s+|curl\s+|nc\s+)', re.IGNORECASE),
                threat_type=ThreatType.COMMAND_INJECTION,
                severity="high",
                description="检测常见Unix命令"
            ),

            # 路径遍历模式
            SecurityRule(
                name="Path Traversal",
                pattern=re.compile(r'(?i)(\.\./|\.\.\\|%2e%2e%2f|%2e%2e%5c)', re.IGNORECASE),
                threat_type=ThreatType.PATH_TRAVERSAL,
                severity="high",
                description="检测路径遍历攻击"
            ),

            # LDAP注入模式
            SecurityRule(
                name="LDAP Injection",
                pattern=re.compile(r'(?i)(\*\)|\(\|\()', re.IGNORECASE),
                threat_type=ThreatType.LDAP_INJECTION,
                severity="medium",
                description="检测LDAP注入语法"
            ),

            # XXE模式
            SecurityRule(
                name="XXE - Entity",
                pattern=re.compile(r'(?i)(<!DOCTYPE.*<!ENTITY|&[a-zA-Z]+;)', re.IGNORECASE),
                threat_type=ThreatType.XXE,
                severity="high",
                description="检测XML外部实体注入"
            ),

            # SSRF模式
            SecurityRule(
                name="SSRF - Localhost",
                pattern=re.compile(r'(?i)(localhost|127\.0\.0\.1|0\.0\.0\.0|::1)', re.IGNORECASE),
                threat_type=ThreatType.SSRF,
                severity="high",
                description="检测SSRF本地地址"
            ),
            SecurityRule(
                name="SSRF - Private Networks",
                pattern=re.compile(r'(?i)(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.)', re.IGNORECASE),
                threat_type=ThreatType.SSRF,
                severity="medium",
                description="检测SSRF私有网络地址"
            ),
        ]

        # 根据验证级别调整规则
        if self.validation_level == ValidationLevel.PERMISSIVE:
            # 只启用高危和严重规则
            default_rules = [r for r in default_rules if r.severity in ['high', 'critical']]
        elif self.validation_level == ValidationLevel.PARANOID:
            # 启用所有规则
            pass
        else:
            # 默认启用中危及以上规则
            default_rules = [r for r in default_rules if r.severity in ['medium', 'high', 'critical']]

        self.custom_rules.extend(default_rules)

    def add_rule(self, rule: SecurityRule) -> None:
        """添加自定义安全规则"""
        self.custom_rules.append(rule)
        self.logger.info(f"添加安全规则: {rule.name}")

    def remove_rule(self, rule_name: str) -> bool:
        """移除安全规则"""
        for i, rule in enumerate(self.custom_rules):
            if rule.name == rule_name:
                del self.custom_rules[i]
                self.logger.info(f"移除安全规则: {rule_name}")
                return True
        return False

    def validate_input(self, input_data: str, input_type: str = "general") -> ValidationResult:
        """验证输入数据"""
        if not input_data:
            return ValidationResult(is_valid=True, threats=[], risk_score=0.0)

        # 基础清理
        cleaned_input = self._basic_cleanup(input_data)

        # 检查威胁
        detected_threats = []
        risk_score = 0.0
        details = {}

        for rule in self.custom_rules:
            if not rule.enabled:
                continue

            try:
                matches = rule.pattern.findall(cleaned_input)
                if matches:
                    detected_threats.append(rule.threat_type)

                    # 计算风险评分
                    severity_weights = {'low': 1.0, 'medium': 2.5, 'high': 5.0, 'critical': 10.0}
                    risk_score += severity_weights.get(rule.severity, 1.0)

                    details[rule.name] = {
                        'matches': matches[:3],  # 只保留前3个匹配
                        'severity': rule.severity,
                        'description': rule.description
                    }

                    self.logger.warning(f"检测到威胁: {rule.name} - {rule.threat_type.value}")

            except Exception as e:
                self.logger.error(f"规则 {rule.name} 执行失败: {e}")

        # 限制风险评分最大值
        risk_score = min(risk_score, 20.0)

        # 根据验证级别调整结果
        is_valid = True
        if self.validation_level == ValidationLevel.STRICT:
            is_valid = len(detected_threats) == 0
        elif self.validation_level == ValidationLevel.PARANOID:
            is_valid = len(detected_threats) == 0 and risk_score == 0.0

        return ValidationResult(
            is_valid=is_valid,
            threats=detected_threats,
            risk_score=risk_score,
            sanitized_input=cleaned_input,
            details=details
        )

    def _basic_cleanup(self, input_data: str) -> str:
        """基础输入清理"""
        try:
            # HTML解码
            cleaned = html.unescape(input_data)

            # URL解码
            cleaned = unquote(cleaned)

            # 移除控制字符（除了换行符和制表符）
            cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', cleaned)

            # 标准化空白字符
            cleaned = ' '.join(cleaned.split())

            return cleaned
        except Exception as e:
            self.logger.error(f"输入清理失败: {e}")
            return input_data

    def sanitize_input(self, input_data: str, allowed_tags: List[str] = None) -> str:
        """清理输入数据"""
        if allowed_tags is None:
            allowed_tags = []

        try:
            # HTML实体编码
            sanitized = html.escape(input_data)

            # 如果允许特定标签，选择性解码
            if allowed_tags:
                for tag in allowed_tags:
                    sanitized = sanitized.replace(f"&lt;{tag}&gt;", f"<{tag}>")
                    sanitized = sanitized.replace(f"&lt;/{tag}&gt;", f"</{tag}>")

            return sanitized
        except Exception as e:
            self.logger.error(f"输入清理失败: {e}")
            return input_data

    def validate_file_path(self, file_path: str, allowed_dirs: List[str] = None) -> ValidationResult:
        """验证文件路径安全性"""
        threats = []
        risk_score = 0.0
        details = {}

        try:
            path = Path(file_path).resolve()

            # 检查路径遍历
            if '..' in file_path:
                threats.append(ThreatType.PATH_TRAVERSAL)
                risk_score += 5.0
                details['path_traversal'] = "检测到路径遍历字符"

            # 检查是否在允许的目录中
            if allowed_dirs:
                is_allowed = False
                for allowed_dir in allowed_dirs:
                    allowed_path = Path(allowed_dir).resolve()
                    try:
                        path.relative_to(allowed_path)
                        is_allowed = True
                        break
                    except ValueError:
                        continue

                if not is_allowed:
                    threats.append(ThreatType.PATH_TRAVERSAL)
                    risk_score += 3.0
                    details['directory_restriction'] = "路径不在允许的目录中"

            # 检查敏感文件
            sensitive_patterns = [
                r'(?i)(password|secret|key|token)\.(txt|conf|config)',
                r'(?i)(\.htaccess|web\.config|\.env)',
                r'(?i)(shadow|passwd|hosts)',
            ]

            for pattern in sensitive_patterns:
                if re.search(pattern, str(path)):
                    risk_score += 2.0
                    details['sensitive_file'] = f"匹配敏感文件模式: {pattern}"

            return ValidationResult(
                is_valid=len(threats) == 0,
                threats=threats,
                risk_score=risk_score,
                sanitized_input=str(path),
                details=details
            )

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                threats=[ThreatType.PATH_TRAVERSAL],
                risk_score=5.0,
                details={'error': str(e)}
            )

    def validate_ip_address(self, ip_str: str, allow_private: bool = True,
                           allow_localhost: bool = True) -> ValidationResult:
        """验证IP地址安全性"""
        threats = []
        risk_score = 0.0
        details = {}

        try:
            ip = ipaddress.ip_address(ip_str)

            # 检查私有地址
            if ip.is_private and not allow_private:
                threats.append(ThreatType.SSRF)
                risk_score += 3.0
                details['private_ip'] = "私有IP地址被禁止"

            # 检查本地地址
            if ip.is_loopback and not allow_localhost:
                threats.append(ThreatType.SSRF)
                risk_score += 4.0
                details['localhost_ip'] = "本地IP地址被禁止"

            # 检查保留地址
            if ip.is_reserved:
                risk_score += 2.0
                details['reserved_ip'] = "保留IP地址"

            # 检查多播地址
            if ip.is_multicast:
                risk_score += 1.5
                details['multicast_ip'] = "多播IP地址"

            return ValidationResult(
                is_valid=len(threats) == 0,
                threats=threats,
                risk_score=risk_score,
                sanitized_input=str(ip),
                details=details
            )

        except ValueError:
            return ValidationResult(
                is_valid=False,
                threats=[ThreatType.SSRF],
                risk_score=5.0,
                details={'invalid_ip': "无效的IP地址格式"}
            )

    def validate_url(self, url: str, allowed_schemes: List[str] = None,
                    allowed_domains: List[str] = None) -> ValidationResult:
        """验证URL安全性"""
        threats = []
        risk_score = 0.0
        details = {}

        try:
            parsed = urlparse(url)

            # 检查协议
            if allowed_schemes and parsed.scheme not in allowed_schemes:
                risk_score += 3.0
                details['invalid_scheme'] = f"不允许的协议: {parsed.scheme}"

            # 检查域名
            if allowed_domains and parsed.netloc not in allowed_domains:
                risk_score += 2.0
                details['invalid_domain'] = f"不允许的域名: {parsed.netloc}"

            # 检查SSRF
            if parsed.hostname:
                ip_validation = self.validate_ip_address(
                    parsed.hostname, allow_private=False, allow_localhost=False
                )
                if not ip_validation.is_valid:
                    threats.extend(ip_validation.threats)
                    risk_score += ip_validation.risk_score
                    details.update(ip_validation.details)

            # 检查文件扩展名
            if parsed.path:
                dangerous_extensions = ['.exe', '.bat', '.cmd', '.sh', '.php', '.asp', '.jsp']
                for ext in dangerous_extensions:
                    if parsed.path.lower().endswith(ext):
                        risk_score += 2.0
                        details['dangerous_extension'] = f"危险文件扩展名: {ext}"

            return ValidationResult(
                is_valid=len(threats) == 0 and risk_score < 5.0,
                threats=threats,
                risk_score=risk_score,
                sanitized_input=url,
                details=details
            )

        except Exception as e:
            return ValidationResult(
                is_valid=False,
                threats=[ThreatType.SSRF],
                risk_score=5.0,
                details={'invalid_url': str(e)}
            )


class SecurityManager:
    """安全管理器"""

    def __init__(self, validation_level: ValidationLevel = ValidationLevel.MODERATE):
        self.validator = InputValidator(validation_level)
        self.logger = logging.getLogger(__name__)
        self.session_tokens: Dict[str, Dict[str, Any]] = {}
        self.rate_limits: Dict[str, List[float]] = {}

    def create_session_token(self, user_id: str, expiry_minutes: int = 60) -> str:
        """创建会话令牌"""
        token = secrets.token_urlsafe(32)
        expiry_time = time.time() + (expiry_minutes * 60)

        self.session_tokens[token] = {
            'user_id': user_id,
            'created_time': time.time(),
            'expiry_time': expiry_time,
            'last_accessed': time.time()
        }

        self.logger.info(f"创建会话令牌: {user_id}")
        return token

    def validate_session_token(self, token: str) -> bool:
        """验证会话令牌"""
        if token not in self.session_tokens:
            return False

        session = self.session_tokens[token]
        if time.time() > session['expiry_time']:
            del self.session_tokens[token]
            return False

        # 更新最后访问时间
        session['last_accessed'] = time.time()
        return True

    def revoke_session_token(self, token: str) -> bool:
        """撤销会话令牌"""
        if token in self.session_tokens:
            del self.session_tokens[token]
            self.logger.info(f"撤销会话令牌: {token}")
            return True
        return False

    def check_rate_limit(self, identifier: str, max_requests: int,
                        time_window: int = 60) -> bool:
        """检查速率限制"""
        current_time = time.time()

        if identifier not in self.rate_limits:
            self.rate_limits[identifier] = []

        # 清理过期记录
        self.rate_limits[identifier] = [
            req_time for req_time in self.rate_limits[identifier]
            if current_time - req_time < time_window
        ]

        # 检查是否超过限制
        if len(self.rate_limits[identifier]) >= max_requests:
            return False

        # 记录当前请求
        self.rate_limits[identifier].append(current_time)
        return True

    def hash_password(self, password: str, salt: str = None) -> Tuple[str, str]:
        """安全哈希密码"""
        if salt is None:
            salt = secrets.token_hex(16)

        # 使用PBKDF2进行密码哈希
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # 迭代次数
        )

        return password_hash.hex(), salt

    def verify_password(self, password: str, hash_value: str, salt: str) -> bool:
        """验证密码"""
        computed_hash, _ = self.hash_password(password, salt)
        return hmac.compare_digest(computed_hash, hash_value)

    def generate_secure_filename(self, original_filename: str) -> str:
        """生成安全的文件名"""
        # 移除路径信息
        filename = Path(original_filename).name

        # 移除危险字符
        filename = re.sub(r'[^\w\-_\.]', '', filename)

        # 生成随机前缀
        prefix = secrets.token_hex(8)

        # 保持原始扩展名
        suffix = Path(filename).suffix

        return f"{prefix}_{filename}{suffix}"

    def cleanup_expired_sessions(self) -> int:
        """清理过期会话"""
        current_time = time.time()
        expired_tokens = [
            token for token, session in self.session_tokens.items()
            if current_time > session['expiry_time']
        ]

        for token in expired_tokens:
            del self.session_tokens[token]

        self.logger.info(f"清理过期会话: {len(expired_tokens)}")
        return len(expired_tokens)


# 全局安全管理器
_global_security_manager: Optional[SecurityManager] = None


def get_security_manager() -> SecurityManager:
    """获取全局安全管理器"""
    global _global_security_manager
    if _global_security_manager is None:
        _global_security_manager = SecurityManager()
    return _global_security_manager


def init_security_manager(validation_level: ValidationLevel = ValidationLevel.MODERATE) -> SecurityManager:
    """初始化全局安全管理器"""
    global _global_security_manager
    _global_security_manager = SecurityManager(validation_level)
    return _global_security_manager


# 便捷函数
def validate_input(input_data: str, input_type: str = "general") -> ValidationResult:
    """验证输入的便捷函数"""
    manager = get_security_manager()
    return manager.validator.validate_input(input_data, input_type)


def sanitize_input(input_data: str, allowed_tags: List[str] = None) -> str:
    """清理输入的便捷函数"""
    manager = get_security_manager()
    return manager.validator.sanitize_input(input_data, allowed_tags)


def create_session_token(user_id: str, expiry_minutes: int = 60) -> str:
    """创建会话令牌的便捷函数"""
    manager = get_security_manager()
    return manager.create_session_token(user_id, expiry_minutes)


def validate_session_token(token: str) -> bool:
    """验证会话令牌的便捷函数"""
    manager = get_security_manager()
    return manager.validate_session_token(token)