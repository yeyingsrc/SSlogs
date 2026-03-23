import asyncio
import aiohttp
import logging
import yaml
import time
from typing import Dict, Any, List, Optional, AsyncGenerator
from .exceptions import AIServiceError, AIServiceUnavailableError, AIAuthenticationError, AIRateLimitError


class AsyncAIAnalyzer:
    """异步AI分析器 - 支持并发处理多个日志分析请求"""

    def __init__(self, config_path: str = 'config.yaml'):
        self.config = self._load_config(config_path)
        self.ai_type = self.config.get('ai', {}).get('type', 'cloud')
        self.cloud_provider = self.config.get('ai', {}).get('cloud_provider', 'deepseek')
        self.local_provider = self.config.get('ai', {}).get('local_provider', 'ollama')
        self.logger = logging.getLogger(__name__)

        # 重试配置
        self.max_retries = self.config.get('ai', {}).get('max_retries', 3)
        self.retry_delay = self.config.get('ai', {}).get('retry_delay', 1)
        self.retry_backoff = self.config.get('ai', {}).get('retry_backoff', 2)

        # 超时配置
        self.default_timeout = self.config.get('ai', {}).get('default_timeout', 30)

        # 并发控制
        self.max_concurrent_requests = self.config.get('ai', {}).get('max_concurrent_requests', 5)
        self.semaphore = asyncio.Semaphore(self.max_concurrent_requests)

        # 连接池配置
        self.connector_config = {
            'limit': 100,  # 总连接池大小
            'limit_per_host': 20,  # 每个主机的连接数
            'ttl_dns_cache': 300,  # DNS缓存时间
            'use_dns_cache': True,
        }

        # 加载云端模型配置
        if self.cloud_provider == 'deepseek':
            self.deepseek_config = self.config.get('deepseek', {})
            self.api_key = self.deepseek_config.get('api_key', '')
            self.cloud_model = self.deepseek_config.get('model', 'deepseek-ai/DeepSeek-V3')
            self.cloud_base_url = self.deepseek_config.get('base_url', 'https://api.siliconflow.cn/v1/chat/completions')
            self.cloud_headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }

        # 加载本地模型配置
        if self.local_provider == 'ollama':
            self.ollama_config = self.config.get('ollama', {})
            self.local_model = self.ollama_config.get('model', 'deepseek-r1:1.5b')
            self.local_base_url = self.ollama_config.get('base_url', 'http://localhost:11434/api/chat')
            self.local_headers = {
                'Content-Type': 'application/json'
            }

    async def __aenter__(self):
        """异步上下文管理器入口"""
        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(**self.connector_config),
            timeout=aiohttp.ClientTimeout(total=self.default_timeout)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        if hasattr(self, 'session'):
            await self.session.close()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logging.error(f"加载配置文件失败: {e}")
            return {}

    async def _make_request_with_retry(self, url: str, headers: Dict[str, str], payload: Dict[str, Any], timeout: int) -> Dict[str, Any]:
        """带重试机制的异步请求方法"""
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                async with self.semaphore:  # 控制并发请求数
                    async with self.session.post(url, headers=headers, json=payload, timeout=timeout) as response:
                        response.raise_for_status()
                        return await response.json()

            except asyncio.TimeoutError as e:
                last_exception = AIServiceUnavailableError(
                    f"AI服务请求超时 (尝试 {attempt + 1}/{self.max_retries})",
                    error_code="TIMEOUT",
                    details={"url": url, "timeout": timeout, "attempt": attempt + 1}
                )
                self.logger.warning(str(last_exception))

            except aiohttp.ClientConnectorError as e:
                last_exception = AIServiceUnavailableError(
                    f"无法连接到AI服务 (尝试 {attempt + 1}/{self.max_retries})",
                    error_code="CONNECTION_ERROR",
                    details={"url": url, "attempt": attempt + 1}
                )
                self.logger.warning(str(last_exception))

            except aiohttp.ClientResponseError as e:
                status_code = e.status
                error_details = {
                    "status_code": status_code,
                    "url": url,
                    "attempt": attempt + 1,
                    "response_text": await e.text() if hasattr(e, 'text') else ''
                }

                if status_code == 401:
                    raise AIAuthenticationError(
                        "AI服务认证失败，请检查API密钥",
                        error_code="AUTHENTICATION_FAILED",
                        details=error_details
                    )
                elif status_code == 429:
                    last_exception = AIRateLimitError(
                        f"AI服务请求频率限制 (尝试 {attempt + 1}/{self.max_retries})",
                        error_code="RATE_LIMIT",
                        details=error_details
                    )
                    self.logger.warning(str(last_exception))
                elif 400 <= status_code < 500:
                    raise AIServiceError(
                        f"AI服务客户端错误: HTTP {status_code}",
                        error_code="CLIENT_ERROR",
                        details=error_details
                    )
                elif status_code >= 500:
                    last_exception = AIServiceUnavailableError(
                        f"AI服务服务器错误: HTTP {status_code} (尝试 {attempt + 1}/{self.max_retries})",
                        error_code="SERVER_ERROR",
                        details=error_details
                    )
                    self.logger.warning(str(last_exception))

            except Exception as e:
                last_exception = AIServiceError(
                    f"AI服务未知错误: {e} (尝试 {attempt + 1}/{self.max_retries})",
                    error_code="UNKNOWN_ERROR",
                    details={"url": url, "error": str(e), "attempt": attempt + 1}
                )
                self.logger.warning(str(last_exception))

            # 如果不是最后一次尝试，等待后重试
            if attempt < self.max_retries - 1:
                wait_time = self.retry_delay * (2 ** attempt)  # 指数退避
                self.logger.info(f"等待 {wait_time} 秒后重试...")
                await asyncio.sleep(wait_time)

        # 所有重试都失败了，抛出最后一个异常
        if last_exception:
            raise last_exception
        else:
            raise AIServiceUnavailableError(
                "所有重试尝试都失败了",
                error_code="ALL_RETRIES_FAILED"
            )

    def _get_attack_specific_prompt(self, log_context: str, attack_category: str = None, attack_name: str = None) -> str:
        """根据攻击类型生成专门的AI分析提示词"""
        # 重用原有的提示词生成逻辑
        # 这里简化实现，实际应该从原AIAnalyzer类中复制完整的提示词生成逻辑

        base_framework = """
请基于以下日志内容进行深度安全分析：

**分析要求:**
1. 攻击技术分析（技术手段、攻击复杂度、载荷特征）
2. 影响范围评估（数据风险、系统损害、业务影响）
3. 应急响应措施（立即处置、漏洞修复、后续监控）
4. 威胁情报分析（攻击者特征、组织归属、后续威胁）

**日志内容:**
{log_context}

**输出格式:**
请使用结构化的Markdown格式回复，包含上述四个方面的详细分析。
"""

        return base_framework.format(log_context=log_context)

    async def analyze_log_async(self, log_context: str, attack_category: str = None, attack_name: str = None, threat_score: float = None) -> str:
        """异步AI分析单条日志"""
        if not log_context or not log_context.strip():
            return "无有效日志内容可供分析"

        # 限制日志长度以提升性能
        if len(log_context) > 5000:
            log_context = log_context[:5000] + "\n... (日志内容被截断) ..."

        # 生成专门的提示词
        prompt = self._get_attack_specific_prompt(log_context, attack_category, attack_name)

        try:
            if self.ai_type == 'local' and self.local_provider == 'ollama':
                return await self._analyze_with_ollama_async(prompt)
            else:
                try:
                    return await self._analyze_with_cloud_async(prompt)
                except Exception as e:
                    error_msg = f"云端AI分析失败: {str(e)}"
                    self.logger.warning(error_msg)
                    return self._generate_fallback_analysis(attack_category, threat_score)

        except Exception as e:
            self.logger.error(f"AI分析失败: {e}")
            return self._generate_fallback_analysis(attack_category, threat_score)

    async def analyze_logs_batch(self, log_entries: List[Dict[str, Any]], max_concurrent: int = None) -> List[Dict[str, Any]]:
        """批量异步分析多个日志条目"""
        if max_concurrent:
            # 临时调整并发数
            original_semaphore = self.semaphore
            self.semaphore = asyncio.Semaphore(max_concurrent)

        try:
            tasks = []
            for i, entry in enumerate(log_entries):
                task = self._analyze_single_entry_async(entry, i)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed_results.append({
                        'index': i,
                        'success': False,
                        'error': str(result),
                        'analysis': '分析失败'
                    })
                else:
                    processed_results.append({
                        'index': i,
                        'success': True,
                        'analysis': result
                    })

            return processed_results

        finally:
            if max_concurrent:
                # 恢复原始并发控制
                self.semaphore = original_semaphore

    async def _analyze_single_entry_async(self, entry: Dict[str, Any], index: int) -> str:
        """分析单个日志条目"""
        log_context = entry.get('log_context', '')
        attack_category = entry.get('attack_category')
        attack_name = entry.get('attack_name')
        threat_score = entry.get('threat_score')

        return await self.analyze_log_async(log_context, attack_category, attack_name, threat_score)

    async def analyze_logs_stream(self, log_entries: AsyncGenerator[Dict[str, Any], None]) -> AsyncGenerator[Dict[str, Any], None]:
        """流式异步分析日志条目"""
        async for entry in log_entries:
            try:
                analysis = await self._analyze_single_entry_async(entry, 0)
                yield {
                    'entry': entry,
                    'success': True,
                    'analysis': analysis
                }
            except Exception as e:
                yield {
                    'entry': entry,
                    'success': False,
                    'error': str(e),
                    'analysis': '分析失败'
                }

    def _generate_fallback_analysis(self, attack_category: str, threat_score: float) -> str:
        """生成备用分析结果（当AI不可用时）"""
        # 简化的备用分析逻辑
        template = f"""
## 安全威胁分析

### 攻击检测
检测到 {attack_category or '未知'} 类型的安全威胁。

### 风险评估
基于检测到的攻击模式，建议立即检查相关系统日志。

### 应急响应
1. 检查相关系统日志
2. 评估数据安全风险
3. 实施临时防护措施
4. 加强监控措施
"""
        return template

    async def _analyze_with_ollama_async(self, prompt: str) -> str:
        """使用本地Ollama模型进行异步分析"""
        payload = {
            "model": self.local_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }

        try:
            result = await self._make_request_with_retry(
                self.local_base_url,
                self.local_headers,
                payload,
                self.ollama_config.get('timeout', 60)
            )

            # 处理Ollama响应格式
            if 'message' in result and 'content' in result['message']:
                return result['message']['content']
            else:
                self.logger.error(f"Ollama响应格式异常: {result}")
                return "AI分析结果格式异常"
        except Exception as e:
            self.logger.error(f"Ollama分析失败: {e}")
            return f"本地AI分析失败: {str(e)}"

    async def _analyze_with_cloud_async(self, prompt: str) -> str:
        """使用云端模型进行异步分析"""
        if not self.api_key:
            return "AI分析失败: 未配置API密钥"

        payload = {
            "model": self.cloud_model,
            "stream": False,
            "max_tokens": self.deepseek_config.get('max_tokens', 1024),
            "temperature": 0.7,
            "top_p": 0.7,
            "messages": [{"role": "user", "content": prompt}]
        }

        try:
            result = await self._make_request_with_retry(
                self.cloud_base_url,
                self.cloud_headers,
                payload,
                self.deepseek_config.get('timeout', 30)
            )

            # 处理云端API响应格式
            if 'choices' in result and len(result['choices']) > 0:
                message = result['choices'][0].get('message', {})
                content = message.get('content', '')
                if content:
                    return content
                else:
                    self.logger.error("AI返回内容为空")
                    return "AI分析结果为空"
            else:
                self.logger.error(f"云端API响应格式异常: {result}")
                return "AI分析结果格式异常"
        except Exception as e:
            self.logger.error(f"云端AI分析失败: {e}")
            return f"云端AI分析失败: {str(e)}"

    async def get_ai_health_status(self) -> Dict[str, Any]:
        """检查AI服务健康状态"""
        status = {
            'cloud_service': False,
            'local_service': False,
            'last_check': time.time()
        }

        # 检查云端服务
        if self.api_key:
            try:
                test_payload = {
                    "model": self.cloud_model,
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 10
                }
                await self._make_request_with_retry(
                    self.cloud_base_url,
                    self.cloud_headers,
                    test_payload,
                    10
                )
                status['cloud_service'] = True
            except Exception as e:
                self.logger.warning(f"云端AI服务不可用: {e}")

        # 检查本地服务
        try:
            test_payload = {
                "model": self.local_model,
                "messages": [{"role": "user", "content": "test"}]
            }
            await self._make_request_with_retry(
                self.local_base_url,
                self.local_headers,
                test_payload,
                10
            )
            status['local_service'] = True
        except Exception as e:
            self.logger.warning(f"本地AI服务不可用: {e}")

        return status


# 便捷函数
async def analyze_logs_concurrently(log_entries: List[Dict[str, Any]], config_path: str = 'config.yaml') -> List[Dict[str, Any]]:
    """并发分析多个日志条目的便捷函数"""
    async with AsyncAIAnalyzer(config_path) as analyzer:
        return await analyzer.analyze_logs_batch(log_entries)


async def analyze_log_entry(log_entry: Dict[str, Any], config_path: str = 'config.yaml') -> str:
    """分析单个日志条目的便捷函数"""
    async with AsyncAIAnalyzer(config_path) as analyzer:
        return await analyzer._analyze_single_entry_async(log_entry, 0)