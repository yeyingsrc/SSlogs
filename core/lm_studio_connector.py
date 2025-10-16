#!/usr/bin/env python3
"""
LM Studio 本地AI模型连接器
支持本地运行的大语言模型进行智能安全分析
"""

import requests
import json
import logging
import time
from typing import Dict, List, Any, Optional, AsyncGenerator
from dataclasses import dataclass
import asyncio
import aiohttp
from pathlib import Path

@dataclass
class LMStudioAPIConfig:
    """LM Studio API配置"""
    base_url: str = "http://127.0.0.1:1234/v1"
    chat_endpoint: str = "/chat/completions"
    models_endpoint: str = "/models"
    api_key: str = ""
    headers: Dict[str, str] = None

    def __post_init__(self):
        if self.headers is None:
            self.headers = {
                "Content-Type": "application/json",
                "User-Agent": "SSlogs-AI/1.0"
            }

@dataclass
class LMStudioModelConfig:
    """LM Studio模型配置"""
    preferred_model: str = ""
    model_mapping: Dict[str, str] = None
    max_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 0.9
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stream: bool = False
    response_format: Dict[str, str] = None

    def __post_init__(self):
        if self.model_mapping is None:
            self.model_mapping = {}
        if self.response_format is None:
            self.response_format = {"type": "text"}

@dataclass
class LMStudioConfig:
    """LM Studio配置"""
    host: str = "127.0.0.1"
    port: int = 1234
    timeout: int = 30
    retry_attempts: int = 3
    retry_delay: float = 1.0
    api: LMStudioAPIConfig = None
    model: LMStudioModelConfig = None

    def __post_init__(self):
        if self.api is None:
            self.api = LMStudioAPIConfig()
        if self.model is None:
            self.model = LMStudioModelConfig()

        # 根据host和port更新API base_url
        if not self.api.base_url or "127.0.0.1" in self.api.base_url:
            self.api.base_url = f"http://{self.host}:{self.port}/v1"

    def get_mapped_model_name(self, model_id: str) -> str:
        """获取映射后的模型名称"""
        return self.model.model_mapping.get(model_id, model_id)

    def get_actual_model_id(self, model_name: str) -> str:
        """根据映射名称获取实际模型ID"""
        # 反向查找映射
        for actual_id, mapped_name in self.model.model_mapping.items():
            if mapped_name == model_name:
                return actual_id
        return model_name

@dataclass
class ChatMessage:
    """聊天消息"""
    role: str  # system, user, assistant
    content: str
    timestamp: float = None

class LMStudioConnector:
    """LM Studio模型连接器"""

    def __init__(self, config: LMStudioConfig = None):
        self.config = config or LMStudioConfig()
        self.logger = logging.getLogger(__name__)
        self.base_url = self.config.api.base_url
        self.session = None
        self.available_models = []
        self.current_model = None
        self._headers = self.config.api.headers.copy()

        # 添加API密钥（如果配置了）
        if self.config.api.api_key:
            self._headers["Authorization"] = f"Bearer {self.config.api.api_key}"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            self.session.close()

    async def __aenter__(self):
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def _ensure_session(self):
        """确保HTTP会话存在"""
        if self.session is None:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            )

    def check_connection(self) -> bool:
        """检查与LM Studio的连接"""
        try:
            models_url = f"{self.base_url}{self.config.api.models_endpoint}"
            response = requests.get(models_url, headers=self._headers, timeout=5)
            if response.status_code == 200:
                models = response.json().get("data", [])
                self.available_models = [model["id"] for model in models]
                self.logger.info(f"检测到 {len(self.available_models)} 个可用模型")
                return True
            else:
                self.logger.error(f"LM Studio连接失败: HTTP {response.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"无法连接到LM Studio: {e}")
            return False

    def test_connection(self) -> bool:
        """测试与LM Studio的连接（向后兼容）"""
        return self.check_connection()

    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        if not self.available_models:
            self.test_connection()
        return self.available_models

    def set_model(self, model_name: str) -> bool:
        """设置当前使用的模型"""
        if model_name in self.available_models or self.test_connection():
            if model_name in self.available_models:
                self.current_model = model_name
                self.config.model_name = model_name
                self.logger.info(f"已设置模型: {model_name}")
                return True
            else:
                self.logger.warning(f"模型 {model_name} 不可用")
                return False
        return False

    def _prepare_chat_payload(self, messages: List[ChatMessage], **kwargs) -> Dict[str, Any]:
        """准备聊天请求载荷"""
        # 确定使用的模型
        model_name = kwargs.get("model", self.config.model.preferred_model or self.current_model)

        # 如果使用的是映射名称，获取实际模型ID
        actual_model_id = self.config.get_actual_model_id(model_name)

        # 合并配置和参数
        payload = {
            "model": actual_model_id,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content
                }
                for msg in messages
            ],
            "max_tokens": kwargs.get("max_tokens", self.config.model.max_tokens),
            "temperature": kwargs.get("temperature", self.config.model.temperature),
            "top_p": kwargs.get("top_p", self.config.model.top_p),
            "frequency_penalty": kwargs.get("frequency_penalty", self.config.model.frequency_penalty),
            "presence_penalty": kwargs.get("presence_penalty", self.config.model.presence_penalty),
            "stream": kwargs.get("stream", self.config.model.stream),
            "response_format": kwargs.get("response_format", self.config.model.response_format)
        }

        # 添加额外参数
        extra_params = ["stop", "logprobs", "top_k", "repeat_penalty"]
        for param in extra_params:
            if param in kwargs:
                payload[param] = kwargs[param]

        return payload

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """发起HTTP请求"""
        url = f"{self.base_url}{endpoint}"

        # 合并请求头
        headers = self._headers.copy()
        if 'headers' in kwargs:
            headers.update(kwargs.pop('headers'))

        return requests.request(method, url, headers=headers, **kwargs)

    def chat_completion(self, messages: List[ChatMessage], **kwargs) -> Optional[str]:
        """同步聊天完成"""
        try:
            payload = self._prepare_chat_payload(messages, **kwargs)

            response = self._make_request(
                "POST",
                self.config.api.chat_endpoint,
                json=payload,
                timeout=self.config.timeout
            )

            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                self.logger.error(f"聊天请求失败: HTTP {response.status_code}")
                self.logger.error(f"响应内容: {response.text}")
                return None

        except Exception as e:
            self.logger.error(f"聊天完成异常: {e}")
            return None

    async def chat_completion_async(self, messages: List[ChatMessage], **kwargs) -> Optional[str]:
        """异步聊天完成"""
        await self._ensure_session()

        for attempt in range(self.config.retry_attempts):
            try:
                payload = self._prepare_chat_payload(messages, **kwargs)

                async with self.session.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=payload
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result["choices"][0]["message"]["content"]
                    else:
                        self.logger.error(f"异步聊天请求失败: HTTP {response.status}")

            except Exception as e:
                self.logger.warning(f"异步聊天完成异常 (尝试 {attempt + 1}/{self.config.retry_attempts}): {e}")
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(self.config.retry_delay)
                else:
                    self.logger.error(f"异步聊天完成最终失败: {e}")
                    return None

        return None

    async def chat_completion_stream(self, messages: List[ChatMessage], **kwargs) -> AsyncGenerator[str, None]:
        """流式聊天完成"""
        await self._ensure_session()

        try:
            payload = self._prepare_chat_payload(messages, stream=True, **kwargs)

            async with self.session.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload
            ) as response:
                if response.status == 200:
                    async for line in response.content:
                        if line:
                            line = line.decode('utf-8').strip()
                            if line.startswith('data: '):
                                data = line[6:]
                                if data == '[DONE]':
                                    break
                                try:
                                    json_data = json.loads(data)
                                    if 'choices' in json_data and json_data['choices']:
                                        delta = json_data['choices'][0].get('delta', {})
                                        if 'content' in delta:
                                            yield delta['content']
                                except json.JSONDecodeError:
                                    continue
                else:
                    self.logger.error(f"流式聊天请求失败: HTTP {response.status}")

        except Exception as e:
            self.logger.error(f"流式聊天完成异常: {e}")

    def analyze_security_log(self, log_entry: Dict[str, Any]) -> Optional[str]:
        """分析安全日志"""
        system_prompt = """你是一个专业的网络安全分析师。请分析以下日志条目，识别潜在的安全威胁、攻击模式或异常行为。

请提供以下分析：
1. 威胁等级评估（低/中/高/严重）
2. 攻击类型识别
3. 风险因素分析
4. 建议的响应措施

请用中文回答，保持专业和准确。"""

        user_prompt = f"""请分析以下安全日志：

时间戳: {log_entry.get('timestamp', 'N/A')}
源IP: {log_entry.get('src_ip', 'N/A')}
请求方法: {log_entry.get('request_method', 'N/A')}
请求路径: {log_entry.get('request_path', 'N/A')}
用户代理: {log_entry.get('user_agent', 'N/A')}
状态码: {log_entry.get('status_code', 'N/A')}

请求头: {log_entry.get('request_headers', {})}
请求体: {log_entry.get('request_body', 'N/A')}

其他信息: {log_entry.get('additional_info', 'N/A')}"""

        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_prompt)
        ]

        return self.chat_completion(messages, temperature=0.3)

    async def analyze_security_log_async(self, log_entry: Dict[str, Any]) -> Optional[str]:
        """异步分析安全日志"""
        system_prompt = """你是一个专业的网络安全分析师。请分析以下日志条目，识别潜在的安全威胁、攻击模式或异常行为。

请提供以下分析：
1. 威胁等级评估（低/中/高/严重）
2. 攻击类型识别
3. 风险因素分析
4. 建议的响应措施

请用中文回答，保持专业和准确。"""

        user_prompt = f"""请分析以下安全日志：

时间戳: {log_entry.get('timestamp', 'N/A')}
源IP: {log_entry.get('src_ip', 'N/A')}
请求方法: {log_entry.get('request_method', 'N/A')}
请求路径: {log_entry.get('request_path', 'N/A')}
用户代理: {log_entry.get('user_agent', 'N/A')}
状态码: {log_entry.get('status_code', 'N/A')}

请求头: {log_entry.get('request_headers', {})}
请求体: {log_entry.get('request_body', 'N/A')}

其他信息: {log_entry.get('additional_info', 'N/A')}"""

        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_prompt)
        ]

        return await self.chat_completion_async(messages, temperature=0.3)

    def generate_security_recommendations(self, threat_analysis: str, context: Dict[str, Any] = None) -> Optional[str]:
        """生成安全建议"""
        system_prompt = """基于威胁分析结果，请生成具体的安全建议和响应措施。

建议应该包括：
1. 立即响应措施
2. 短期防护策略
3. 长期安全改进建议
4. 相关规则优化建议

请用中文回答，提供可操作的具体建议。"""

        context_info = ""
        if context:
            context_info = f"\n\n上下文信息：\n{json.dumps(context, indent=2, ensure_ascii=False)}"

        user_prompt = f"""威胁分析结果：
{threat_analysis}{context_info}

请基于以上分析提供详细的安全建议。"""

        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_prompt)
        ]

        return self.chat_completion(messages, temperature=0.4)

    def explain_rule_match(self, rule_name: str, log_entry: Dict[str, Any], threat_score: float) -> Optional[str]:
        """解释规则匹配原因"""
        system_prompt = """你是一个安全规则专家。请解释为什么特定规则会匹配到某个日志条目，以及这个匹配的安全意义。

解释应该包括：
1. 规则匹配的具体原因
2. 检测到的攻击模式
3. 威胁评估
4. 业务影响分析

请用中文回答，保持专业且易懂。"""

        user_prompt = f"""请解释以下规则匹配：

规则名称: {rule_name}
威胁评分: {threat_score}

日志详情:
时间戳: {log_entry.get('timestamp', 'N/A')}
源IP: {log_entry.get('src_ip', 'N/A')}
请求路径: {log_entry.get('request_path', 'N/A')}
用户代理: {log_entry.get('user_agent', 'N/A')}
请求体: {log_entry.get('request_body', 'N/A')}
请求头: {log_entry.get('request_headers', {})}

请详细解释为什么这个规则会匹配到上述日志。"""

        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_prompt)
        ]

        return self.chat_completion(messages, temperature=0.3)

    def natural_language_query(self, query: str, log_data: List[Dict[str, Any]] = None) -> Optional[str]:
        """自然语言查询接口"""
        system_prompt = """你是一个安全数据分析助手。用户可以用自然语言查询安全日志数据。

请理解用户的查询意图，并提供：
1. 查询结果的直接回答
2. 相关的安全分析
3. 发现的威胁模式
4. 建议的进一步分析方向

请用中文回答，保持专业和有帮助。"""

        context_info = ""
        if log_data:
            context_info = f"\n\n相关日志数据（最近{len(log_data)}条）：\n"
            for i, log in enumerate(log_data[-5:], 1):  # 只显示最近5条
                context_info += f"{i}. IP:{log.get('src_ip')} 路径:{log.get('request_path')} 时间:{log.get('timestamp')}\n"

        user_prompt = f"""用户查询：{query}{context_info}

请基于上述信息回答用户的问题。"""

        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_prompt)
        ]

        return self.chat_completion(messages, temperature=0.5)

    def get_model_info(self) -> Dict[str, Any]:
        """获取当前模型信息"""
        if not self.current_model:
            self.test_connection()

        return {
            "current_model": self.current_model,
            "available_models": self.available_models,
            "config": {
                "host": self.config.host,
                "port": self.config.port,
                "max_tokens": self.config.model.max_tokens,
                "temperature": self.config.model.temperature,
                "timeout": self.config.timeout
            }
        }

# 预设配置
SECURITY_ANALYSIS_CONFIG = LMStudioConfig(
    timeout=30,
    model=LMStudioModelConfig(
        temperature=0.3,  # 较低温度确保准确性
        max_tokens=1024
    )
)

THREAT_ASSESSMENT_CONFIG = LMStudioConfig(
    timeout=20,
    model=LMStudioModelConfig(
        temperature=0.2,  # 更低温度确保一致性
        max_tokens=512
    )
)

INTERACTIVE_QUERY_CONFIG = LMStudioConfig(
    timeout=45,
    model=LMStudioModelConfig(
        temperature=0.5,  # 中等温度允许灵活性
        max_tokens=2048
    )
)