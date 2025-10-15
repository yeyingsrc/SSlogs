import os
import logging
from typing import Dict, Any, List
from pathlib import Path
import yaml
from string import Template

class ConfigurationError(Exception):
    """配置相关错误"""
    pass

class ConfigManager:
    """增强的配置管理器 - 支持环境变量和配置验证"""

    def __init__(self, config_path: str):
        self.config_path = config_path
        self._config = None
        self.logger = logging.getLogger(__name__)

    def load_config(self) -> Dict[str, Any]:
        """加载配置并处理环境变量"""
        try:
            if not os.path.exists(self.config_path):
                raise ConfigurationError(f"配置文件不存在: {self.config_path}")

            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_content = f.read()

            # 使用Template替换环境变量
            template = Template(config_content)
            try:
                rendered_content = template.substitute(os.environ)
            except KeyError as e:
                raise ConfigurationError(f"缺少必需的环境变量: {e}")

            self._config = yaml.safe_load(rendered_content)

            # 验证配置
            validation_errors = self._validate_config()
            if validation_errors:
                raise ConfigurationError(f"配置验证失败:\n" + "\n".join(validation_errors))

            # 设置默认值
            self._set_defaults()

            return self._config

        except yaml.YAMLError as e:
            raise ConfigurationError(f"YAML解析失败: {e}")
        except Exception as e:
            raise ConfigurationError(f"加载配置失败: {e}")

    def _validate_config(self) -> List[str]:
        """验证配置完整性"""
        errors = []

        if not self._config:
            errors.append("配置文件为空")
            return errors

        # 检查必需字段
        required_fields = ['log_format', 'log_path', 'rule_dir', 'output_dir']
        for field in required_fields:
            if field not in self._config:
                errors.append(f"缺少必需字段: {field}")

        # 验证AI配置
        ai_config = self._config.get('ai', {})
        if ai_config.get('type') == 'cloud':
            cloud_provider = ai_config.get('cloud_provider')
            if cloud_provider == 'deepseek':
                deepseek_config = self._config.get('deepseek', {})
                if not deepseek_config.get('api_key') or deepseek_config.get('api_key') == 'your-api-key-here':
                    errors.append("DeepSeek API密钥未配置或使用默认值")

        # 验证路径
        for path_field in ['rule_dir', 'output_dir']:
            if path_field in self._config:
                path_value = self._config[path_field]
                if not isinstance(path_value, str):
                    errors.append(f"{path_field} 必须是字符串路径")

        return errors

    def _set_defaults(self):
        """设置默认配置值"""
        if not self._config:
            self._config = {}

        # 分析配置默认值
        self._config.setdefault('analysis', {})
        analysis = self._config['analysis']
        analysis.setdefault('batch_size', 1000)
        analysis.setdefault('max_events', 100)
        analysis.setdefault('memory_limit_mb', 500)

        # AI分析配置默认值
        self._config.setdefault('ai_analysis', {})
        ai_analysis = self._config['ai_analysis']
        ai_analysis.setdefault('high_risk_only', True)
        ai_analysis.setdefault('successful_attacks_only', True)
        ai_analysis.setdefault('success_status_codes', ['200', '201', '202', '204', '301', '302', '304'])
        ai_analysis.setdefault('max_ai_analysis', 5)
        ai_analysis.setdefault('high_risk_severity', 'high')

        # 服务器配置默认值
        self._config.setdefault('server', {})
        self._config['server'].setdefault('ip', '未知')

        # AI配置默认值
        self._config.setdefault('ai', {})
        ai = self._config['ai']
        ai.setdefault('type', 'cloud')
        ai.setdefault('cloud_provider', 'deepseek')
        ai.setdefault('local_provider', 'ollama')

        # DeepSeek配置默认值
        self._config.setdefault('deepseek', {})
        deepseek = self._config['deepseek']
        deepseek.setdefault('model', 'deepseek-ai/DeepSeek-V3')
        deepseek.setdefault('base_url', 'https://api.siliconflow.cn/v1/chat/completions')
        deepseek.setdefault('timeout', 30)
        deepseek.setdefault('max_tokens', 2048)

        # Ollama配置默认值
        self._config.setdefault('ollama', {})
        ollama = self._config['ollama']
        ollama.setdefault('model', 'deepseek-r1:14b')
        ollama.setdefault('base_url', 'http://localhost:11434/api/chat')
        ollama.setdefault('timeout', 60)

        # 重试配置默认值
        ai.setdefault('max_retries', 3)
        ai.setdefault('retry_delay', 1)
        ai.setdefault('retry_backoff', 2)
        ai.setdefault('default_timeout', 30)

    def get_config(self) -> Dict[str, Any]:
        """获取配置，自动加载如果未加载"""
        if self._config is None:
            self.load_config()
        return self._config

    def reload_config(self) -> Dict[str, Any]:
        """重新加载配置"""
        self._config = None
        return self.load_config()

    def get_safe_config(self) -> Dict[str, Any]:
        """获取安全的配置（隐藏敏感信息）"""
        config = self.get_config().copy()

        # 隐藏敏感信息
        if 'deepseek' in config and 'api_key' in config['deepseek']:
            api_key = config['deepseek']['api_key']
            if api_key and len(api_key) > 8:
                config['deepseek']['api_key'] = api_key[:4] + '*' * (len(api_key) - 8) + api_key[-4:]
            else:
                config['deepseek']['api_key'] = '***'

        return config