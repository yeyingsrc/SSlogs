#!/usr/bin/env python3
"""
AI配置管理器
管理LM Studio模型配置和AI功能设置
"""

import yaml
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import os

from core.lm_studio_connector import LMStudioConfig, SECURITY_ANALYSIS_CONFIG, THREAT_ASSESSMENT_CONFIG, INTERACTIVE_QUERY_CONFIG

@dataclass
class AIAnalysisConfig:
    """AI分析配置"""
    threat_analysis: bool = True
    natural_language_query: bool = True
    rule_explanation: bool = True
    security_recommendations: bool = True
    batch_analysis: bool = True

@dataclass
class AnalysisThresholds:
    """分析阈值配置"""
    confidence_threshold: float = 0.3
    threat_score_threshold: float = 5.0
    processing_time_threshold: float = 10.0

@dataclass
class ScoringWeights:
    """评分权重配置"""
    ai_weight: float = 0.4
    rule_weight: float = 0.6
    threat_levels: Dict[str, float] = None

    def __post_init__(self):
        if self.threat_levels is None:
            self.threat_levels = {
                "critical": 9.5,
                "high": 7.5,
                "medium": 5.5,
                "low": 3.5
            }

@dataclass
class PerformanceConfig:
    """性能配置"""
    max_concurrent_requests: int = 5
    batch_size: int = 10
    request_timeout: int = 30
    batch_timeout: int = 60
    max_memory_usage: str = "1GB"
    max_cpu_usage: int = 50

@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    detailed_logging: bool = False
    log_requests: bool = False
    log_responses: bool = False

@dataclass
class SecurityConfig:
    """安全配置"""
    filter_sensitive_data: bool = True
    sensitive_fields: List[str] = None

    def __post_init__(self):
        if self.sensitive_fields is None:
            self.sensitive_fields = [
                "password", "token", "api_key", "secret", "credential",
                "session", "cookie", "authorization", "auth"
            ]

class AIConfigManager:
    """AI配置管理器"""

    def __init__(self, config_file: str = "config/ai_config.yaml"):
        self.config_file = Path(config_file)
        self.logger = logging.getLogger(__name__)
        self.config = {}

        # 加载配置
        self.load_config()

    def load_config(self) -> bool:
        """加载配置文件"""
        try:
            if not self.config_file.exists():
                self.logger.warning(f"配置文件不存在: {self.config_file}，使用默认配置")
                self._create_default_config()
                return False

            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)

            self.logger.info(f"AI配置已加载: {self.config_file}")
            return True

        except Exception as e:
            self.logger.error(f"加载AI配置失败: {e}")
            self._create_default_config()
            return False

    def save_config(self) -> bool:
        """保存配置文件"""
        try:
            # 确保目录存在
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True, indent=2)

            self.logger.info(f"AI配置已保存: {self.config_file}")
            return True

        except Exception as e:
            self.logger.error(f"保存AI配置失败: {e}")
            return False

    def _create_default_config(self):
        """创建默认配置"""
        self.config = {
            "lm_studio": {
                "host": "127.0.0.1",
                "port": 1234,
                "timeout": 30,
                "retry_attempts": 3,
                "retry_delay": 1.0,
                "model": {
                    "preferred_model": "",
                    "max_tokens": 2048,
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "frequency_penalty": 0.0,
                    "presence_penalty": 0.0
                },
                "cache": {
                    "enabled": True,
                    "ttl": 3600,
                    "max_size": 1000
                }
            },
            "ai_features": {
                "threat_analysis": True,
                "natural_language_query": True,
                "rule_explanation": True,
                "security_recommendations": True,
                "batch_analysis": True
            },
            "analysis": {
                "scoring_weights": {
                    "ai_weight": 0.4,
                    "rule_weight": 0.6,
                    "threat_levels": {
                        "critical": 9.5,
                        "high": 7.5,
                        "medium": 5.5,
                        "low": 3.5
                    }
                },
                "thresholds": {
                    "confidence_threshold": 0.3,
                    "threat_score_threshold": 5.0,
                    "processing_time_threshold": 10.0
                }
            },
            "performance": {
                "max_concurrent_requests": 5,
                "batch_size": 10,
                "request_timeout": 30,
                "batch_timeout": 60,
                "max_memory_usage": "1GB",
                "max_cpu_usage": 50
            },
            "logging": {
                "level": "INFO",
                "detailed_logging": False,
                "log_requests": False,
                "log_responses": False
            },
            "security": {
                "filter_sensitive_data": True,
                "sensitive_fields": [
                    "password", "token", "api_key", "secret", "credential",
                    "session", "cookie", "authorization", "auth"
                ]
            }
        }

        self.save_config()

    def get_lm_studio_config(self) -> LMStudioConfig:
        """获取LM Studio配置"""
        lm_config = self.config.get("lm_studio", {})

        # 解析API配置
        api_config = lm_config.get("api", {})
        from core.lm_studio_connector import LMStudioAPIConfig, LMStudioModelConfig

        api = LMStudioAPIConfig(
            base_url=api_config.get("base_url", f"http://{lm_config.get('host', '127.0.0.1')}:{lm_config.get('port', 1234)}/v1"),
            chat_endpoint=api_config.get("chat_endpoint", "/chat/completions"),
            models_endpoint=api_config.get("models_endpoint", "/models"),
            api_key=api_config.get("api_key", ""),
            headers=api_config.get("headers", {"Content-Type": "application/json"})
        )

        # 解析模型配置
        model_config = lm_config.get("model", {})
        model = LMStudioModelConfig(
            preferred_model=model_config.get("preferred_model", ""),
            model_mapping=model_config.get("model_mapping", {}),
            max_tokens=model_config.get("max_tokens", 2048),
            temperature=model_config.get("temperature", 0.7),
            top_p=model_config.get("top_p", 0.9),
            frequency_penalty=model_config.get("frequency_penalty", 0.0),
            presence_penalty=model_config.get("presence_penalty", 0.0),
            stream=model_config.get("stream", False),
            response_format=model_config.get("response_format", {"type": "text"})
        )

        return LMStudioConfig(
            host=lm_config.get("host", "127.0.0.1"),
            port=lm_config.get("port", 1234),
            timeout=lm_config.get("timeout", 30),
            retry_attempts=lm_config.get("retry_attempts", 3),
            retry_delay=lm_config.get("retry_delay", 1.0),
            api=api,
            model=model
        )

    def get_preset_config(self, preset_name: str) -> Optional[LMStudioConfig]:
        """获取预设配置"""
        presets = self.config.get("presets", {})
        preset_config = presets.get(preset_name)

        if not preset_config:
            self.logger.warning(f"预设配置不存在: {preset_name}")
            return None

        base_config = self.get_lm_studio_config()

        # 应用预设配置
        from core.lm_studio_connector import LMStudioAPIConfig, LMStudioModelConfig

        # 创建新的模型配置，应用预设值
        model = LMStudioModelConfig(
            preferred_model=base_config.model.preferred_model,
            model_mapping=base_config.model.model_mapping,
            max_tokens=preset_config.get("max_tokens", base_config.model.max_tokens),
            temperature=preset_config.get("temperature", base_config.model.temperature),
            top_p=preset_config.get("top_p", base_config.model.top_p),
            frequency_penalty=base_config.model.frequency_penalty,
            presence_penalty=base_config.model.presence_penalty,
            stream=base_config.model.stream,
            response_format=base_config.model.response_format
        )

        return LMStudioConfig(
            host=base_config.host,
            port=base_config.port,
            timeout=base_config.timeout,
            retry_attempts=base_config.retry_attempts,
            retry_delay=base_config.retry_delay,
            api=base_config.api,
            model=model
        )

    def get_ai_features_config(self) -> AIAnalysisConfig:
        """获取AI功能配置"""
        features = self.config.get("ai_features", {})

        return AIAnalysisConfig(
            threat_analysis=features.get("threat_analysis", True),
            natural_language_query=features.get("natural_language_query", True),
            rule_explanation=features.get("rule_explanation", True),
            security_recommendations=features.get("security_recommendations", True),
            batch_analysis=features.get("batch_analysis", True)
        )

    def get_analysis_config(self) -> Dict[str, Any]:
        """获取分析配置"""
        analysis = self.config.get("analysis", {})

        return {
            "scoring_weights": ScoringWeights(
                ai_weight=analysis.get("scoring_weights", {}).get("ai_weight", 0.4),
                rule_weight=analysis.get("scoring_weights", {}).get("rule_weight", 0.6),
                threat_levels=analysis.get("scoring_weights", {}).get("threat_levels", {
                    "critical": 9.5, "high": 7.5, "medium": 5.5, "low": 3.5
                })
            ),
            "thresholds": AnalysisThresholds(
                confidence_threshold=analysis.get("thresholds", {}).get("confidence_threshold", 0.3),
                threat_score_threshold=analysis.get("thresholds", {}).get("threat_score_threshold", 5.0),
                processing_time_threshold=analysis.get("thresholds", {}).get("processing_time_threshold", 10.0)
            )
        }

    def get_performance_config(self) -> PerformanceConfig:
        """获取性能配置"""
        perf = self.config.get("performance", {})

        return PerformanceConfig(
            max_concurrent_requests=perf.get("max_concurrent_requests", 5),
            batch_size=perf.get("batch_size", 10),
            request_timeout=perf.get("request_timeout", 30),
            batch_timeout=perf.get("batch_timeout", 60),
            max_memory_usage=perf.get("max_memory_usage", "1GB"),
            max_cpu_usage=perf.get("max_cpu_usage", 50)
        )

    def get_logging_config(self) -> LoggingConfig:
        """获取日志配置"""
        logging_config = self.config.get("logging", {})

        return LoggingConfig(
            level=logging_config.get("level", "INFO"),
            detailed_logging=logging_config.get("detailed_logging", False),
            log_requests=logging_config.get("log_requests", False),
            log_responses=logging_config.get("log_responses", False)
        )

    def get_security_config(self) -> SecurityConfig:
        """获取安全配置"""
        security = self.config.get("security", {})

        return SecurityConfig(
            filter_sensitive_data=security.get("filter_sensitive_data", True),
            sensitive_fields=security.get("sensitive_fields", [
                "password", "token", "api_key", "secret", "credential",
                "session", "cookie", "authorization", "auth"
            ])
        )

    def get_prompt_template(self, template_name: str) -> Optional[str]:
        """获取提示词模板"""
        prompts = self.config.get("prompts", {})
        return prompts.get(template_name)

    def update_lm_studio_config(self, config: LMStudioConfig) -> bool:
        """更新LM Studio配置"""
        try:
            if "lm_studio" not in self.config:
                self.config["lm_studio"] = {}

            lm_config = self.config["lm_studio"]
            lm_config["host"] = config.host
            lm_config["port"] = config.port
            lm_config["timeout"] = config.timeout
            lm_config["retry_attempts"] = config.retry_attempts
            lm_config["retry_delay"] = config.retry_delay

            if "model" not in lm_config:
                lm_config["model"] = {}

            lm_config["model"]["preferred_model"] = config.model.preferred_model
            lm_config["model"]["max_tokens"] = config.model.max_tokens
            lm_config["model"]["temperature"] = config.model.temperature
            lm_config["model"]["top_p"] = config.model.top_p

            return self.save_config()

        except Exception as e:
            self.logger.error(f"更新LM Studio配置失败: {e}")
            return False

    def update_ai_features(self, features: AIAnalysisConfig) -> bool:
        """更新AI功能配置"""
        try:
            self.config["ai_features"] = asdict(features)
            return self.save_config()

        except Exception as e:
            self.logger.error(f"更新AI功能配置失败: {e}")
            return False

    def enable_ai_feature(self, feature: str) -> bool:
        """启用特定AI功能"""
        try:
            if "ai_features" not in self.config:
                self.config["ai_features"] = {}

            self.config["ai_features"][feature] = True
            return self.save_config()

        except Exception as e:
            self.logger.error(f"启用AI功能失败: {e}")
            return False

    def disable_ai_feature(self, feature: str) -> bool:
        """禁用特定AI功能"""
        try:
            if "ai_features" not in self.config:
                self.config["ai_features"] = {}

            self.config["ai_features"][feature] = False
            return self.save_config()

        except Exception as e:
            self.logger.error(f"禁用AI功能失败: {e}")
            return False

    def is_feature_enabled(self, feature: str) -> bool:
        """检查AI功能是否启用"""
        return self.config.get("ai_features", {}).get(feature, False)

    def get_model_compatibility_config(self) -> Dict[str, Any]:
        """获取模型兼容性配置"""
        return self.config.get("model_compatibility", {
            "supported_series": ["llama", "qwen", "chatglm", "mistral", "mixtral", "yi", "deepseek", "baichuan"],
            "preferred_sizes": [7, 13, 34, 70],
            "avoid_features": ["base", "raw"]
        })

    def validate_config(self) -> List[str]:
        """验证配置有效性"""
        issues = []

        # 验证LM Studio配置
        lm_config = self.config.get("lm_studio", {})
        if not lm_config.get("host"):
            issues.append("LM Studio主机地址未配置")
        if not lm_config.get("port"):
            issues.append("LM Studio端口未配置")

        # 验证模型配置
        model_config = lm_config.get("model", {})
        if model_config.get("max_tokens", 0) <= 0:
            issues.append("最大令牌数必须大于0")
        if not (0 <= model_config.get("temperature", 0.5) <= 2):
            issues.append("温度参数必须在0-2之间")

        # 验证分析配置
        analysis = self.config.get("analysis", {})
        scoring = analysis.get("scoring_weights", {})
        ai_weight = scoring.get("ai_weight", 0.4)
        rule_weight = scoring.get("rule_weight", 0.6)
        if abs(ai_weight + rule_weight - 1.0) > 0.01:
            issues.append("AI权重和规则权重之和必须等于1.0")

        # 验证性能配置
        perf = self.config.get("performance", {})
        if perf.get("max_concurrent_requests", 0) <= 0:
            issues.append("最大并发请求数必须大于0")
        if perf.get("batch_size", 0) <= 0:
            issues.append("批处理大小必须大于0")

        return issues

    def export_config(self, output_file: str) -> bool:
        """导出配置到文件"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)

            self.logger.info(f"配置已导出到: {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"导出配置失败: {e}")
            return False

    def import_config(self, input_file: str) -> bool:
        """从文件导入配置"""
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)

            # 验证导入的配置
            self.config = imported_config
            issues = self.validate_config()

            if issues:
                self.logger.warning(f"导入的配置存在以下问题: {issues}")
                return False

            return self.save_config()

        except Exception as e:
            self.logger.error(f"导入配置失败: {e}")
            return False

    def get_full_config(self) -> Dict[str, Any]:
        """获取完整配置"""
        return self.config.copy()

    def reset_to_default(self) -> bool:
        """重置为默认配置"""
        try:
            self._create_default_config()
            self.logger.info("配置已重置为默认值")
            return True

        except Exception as e:
            self.logger.error(f"重置配置失败: {e}")
            return False

# 全局配置管理器实例
_global_config_manager = None

def get_ai_config_manager(config_file: str = "config/ai_config.yaml") -> AIConfigManager:
    """获取全局AI配置管理器实例"""
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = AIConfigManager(config_file)
    return _global_config_manager

def reset_ai_config_manager():
    """重置全局AI配置管理器"""
    global _global_config_manager
    _global_config_manager = None