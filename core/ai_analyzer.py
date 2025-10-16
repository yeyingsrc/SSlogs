import requests
import logging
import yaml
import time
from typing import Dict, Any
from .exceptions import AIServiceError, AIServiceUnavailableError, AIAuthenticationError, AIRateLimitError

class AIAnalyzer:
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

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logging.error(f"加载配置文件失败: {e}")
            return {}

    def _make_request_with_retry(self, url: str, headers: Dict[str, str], payload: Dict[str, Any], timeout: int) -> requests.Response:
        """带重试机制的请求方法"""
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=timeout)
                response.raise_for_status()
                return response

            except requests.exceptions.Timeout as e:
                last_exception = AIServiceUnavailableError(
                    f"AI服务请求超时 (尝试 {attempt + 1}/{self.max_retries})",
                    error_code="TIMEOUT",
                    details={"url": url, "timeout": timeout, "attempt": attempt + 1}
                )
                self.logger.warning(str(last_exception))

            except requests.exceptions.ConnectionError as e:
                last_exception = AIServiceUnavailableError(
                    f"无法连接到AI服务 (尝试 {attempt + 1}/{self.max_retries})",
                    error_code="CONNECTION_ERROR",
                    details={"url": url, "attempt": attempt + 1}
                )
                self.logger.warning(str(last_exception))

            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code
                error_details = {
                    "status_code": status_code,
                    "url": url,
                    "attempt": attempt + 1,
                    "response_text": e.response.text[:200] if hasattr(e.response, 'text') else ''
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

            except requests.exceptions.RequestException as e:
                last_exception = AIServiceError(
                    f"AI服务请求异常: {e} (尝试 {attempt + 1}/{self.max_retries})",
                    error_code="REQUEST_EXCEPTION",
                    details={"url": url, "error": str(e), "attempt": attempt + 1}
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
                time.sleep(wait_time)

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

        # 通用分析框架
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

        # 针对不同攻击类型的专门提示词
        specialized_prompts = {
            'injection': f"""
作为数据库安全专家，请重点分析以下SQL注入攻击：

**重点关注:**
- 注入类型（UNION、Boolean、Time-based、存储过程）
- 数据库指纹识别和权限提升可能
- 数据泄露范围和敏感信息访问
- 数据库持久化后门风险

{base_framework}
""",

            'xss': f"""
作为Web应用安全专家，请重点分析以下XSS攻击：

**重点关注:**
- XSS类型（反射型、存储型、DOM型）
- 会话劫持和Cookie窃取风险
- 浏览器攻击向量（CSRF、Clickjacking配合）
- 持久化攻击和蠕虫传播可能

{base_framework}
""",

            'rce': f"""
作为系统安全专家，请重点分析以下远程代码执行攻击：

**重点关注:**
- 代码执行上下文和权限级别
- 系统持久化机制和后门安装
- 横向移动和内网渗透风险
- 数据窃取和系统控制威胁

{base_framework}
""",

            'ssrf': f"""
作为网络安全专家，请重点分析以下SSRF攻击：

**重点关注:**
- 目标服务识别（内网、云服务、元数据）
- 信息泄露范围和敏感数据访问
- 服务指纹识别和后续攻击可能
- 云环境凭证窃取风险

{base_framework}
""",

            'api_security': f"""
作为API安全专家，请重点分析以下API安全威胁：

**重点关注:**
- API类型（REST、GraphQL、gRPC）和攻击面
- 认证绕过和权限提升机制
- 数据泄露和业务逻辑滥用
- API滥用和拒绝服务风险

{base_framework}
""",

            'cloud_security': f"""
作为云安全专家，请重点分析以下云原生威胁：

**重点关注:**
- 云服务类型（K8s、Docker、Serverless）和攻击面
- 容器逃逸和宿主机访问风险
- 云配置错误和凭证泄露
- 横向云环境渗透威胁

{base_framework}
"""
        }

        # 根据攻击类别选择专门提示词
        if attack_category in specialized_prompts:
            return specialized_prompts[attack_category].format(log_context=log_context)

        # 如果有具体攻击名称，尝试从名称推断类型
        if attack_name:
            attack_name_lower = attack_name.lower()
            if 'sql' in attack_name_lower or 'injection' in attack_name_lower:
                return specialized_prompts['injection'].format(log_context=log_context)
            elif 'xss' in attack_name_lower or 'script' in attack_name_lower:
                return specialized_prompts['xss'].format(log_context=log_context)
            elif 'rce' in attack_name_lower or 'command' in attack_name_lower or 'exec' in attack_name_lower:
                return specialized_prompts['rce'].format(log_context=log_context)
            elif 'ssrf' in attack_name_lower:
                return specialized_prompts['ssrf'].format(log_context=log_context)
            elif 'api' in attack_name_lower or 'graphql' in attack_name_lower or 'rest' in attack_name_lower:
                return specialized_prompts['api_security'].format(log_context=log_context)
            elif 'kubernetes' in attack_name_lower or 'docker' in attack_name_lower or 'cloud' in attack_name_lower:
                return specialized_prompts['cloud_security'].format(log_context=log_context)

        # 默认使用通用提示词
        return base_framework.format(log_context=log_context)

    def analyze_log(self, log_context: str, attack_category: str = None, attack_name: str = None, threat_score: float = None) -> str:
        """增强的AI分析 - 支持攻击类型特定的深度分析"""
        if not log_context or not log_context.strip():
            return "无有效日志内容可供分析"

        # 为避免过长的上下文影响性能，限制日志长度
        if len(log_context) > 5000:
            log_context = log_context[:5000] + "\n... (日志内容被截断) ..."

        # 根据威胁评分调整分析的深度
        urgency_level = "常规" if not threat_score or threat_score < 6.0 else "紧急"

        # 生成攻击类型特定的提示词
        prompt = self._get_attack_specific_prompt(log_context, attack_category, attack_name)

        # 添加威胁评分相关信息
        if threat_score:
            prompt = f"**威胁评分:** {threat_score:.1f}/10.0 ({urgency_level}级别)\n\n{prompt}"

        try:
            if self.ai_type == 'local' and self.local_provider == 'ollama':
                return self._analyze_with_ollama(prompt)
            else:
                try:
                    return self._analyze_with_cloud(prompt)
                except Exception as e:
                    error_msg = f"云端AI分析失败: {str(e)}"
                    self.logger.warning(error_msg)
                    return self._generate_fallback_analysis(attack_category, threat_score)

        except Exception as e:
            self.logger.error(f"AI分析失败: {e}")
            return self._generate_fallback_analysis(attack_category, threat_score)

    def _generate_fallback_analysis(self, attack_category: str, threat_score: float) -> str:
        """生成备用分析结果（当AI不可用时）"""

        fallback_templates = {
            'injection': """
## SQL注入攻击分析

### 攻击技术分析
检测到SQL注入攻击尝试，攻击者可能通过参数注入恶意SQL代码来：
- 窃取数据库中的敏感信息
- 绕过身份验证机制
- 执行数据库管理命令

### 影响评估
- **数据风险**: 高 - 可能导致数据泄露或篡改
- **系统风险**: 中 - 可能获得数据库管理权限

### 应急措施
1. 立即检查数据库访问日志
2. 修复注入漏洞（参数化查询）
3. 更改数据库凭据
4. 监控异常数据库操作
""",

            'xss': """
## XSS攻击分析

### 攻击技术分析
检测到跨站脚本攻击，攻击者可能试图：
- 窃取用户会话Cookie
- 执行恶意JavaScript代码
- 重定向用户到钓鱼网站

### 影响评估
- **用户风险**: 高 - 可能导致会话劫持
- **数据风险**: 中 - 可能窃取用户输入

### 应急措施
1. 检查输出编码机制
2. 实施内容安全策略(CSP)
3. 更新Web应用防火墙规则
4. 通知用户修改密码
""",

            'rce': """
## 远程代码执行攻击分析

### 攻击技术分析
检测到远程代码执行攻击，这是最高危的攻击类型：
- 攻击者已在服务器上执行命令
- 可能安装后门或恶意软件
- 存在完全控制服务器的风险

### 影响评估
- **系统风险**: 严重 - 服务器可能被完全控制
- **数据风险**: 严重 - 所有数据可能被访问或窃取

### 应急措施
1. **立即隔离受影响的服务器**
2. 检查系统进程和网络连接
3. 分析系统日志寻找持久化机制
4. 重新构建受感染系统
""",

            'ssrf': """
## SSRF攻击分析

### 攻击技术分析
检测到服务器端请求伪造攻击，攻击者可能：
- 探测内网服务和拓扑结构
- 访问云服务元数据
- 绕过防火墙限制

### 影响评估
- **内网风险**: 高 - 可能探测内部服务
- **云风险**: 中 - 可能访问云元数据

### 应急措施
1. 检查内网服务访问日志
2. 限制服务器出站网络访问
3. 更新云服务安全配置
4. 监控异常网络请求
"""
        }

        template = fallback_templates.get(attack_category, """
## 安全威胁分析

### 攻击检测
检测到潜在的安全威胁，需要进一步调查。

### 风险评估
基于检测到的攻击模式，建议：
- 检查相关系统日志
- 评估数据安全风险
- 实施临时防护措施

### 应急响应
1. 隔离受影响的服务
2. 收集和分析日志
3. 修复识别的漏洞
4. 加强监控措施
""")

        # 添加威胁评分信息
        if threat_score:
            threat_level = "严重" if threat_score >= 8.0 else "高" if threat_score >= 6.0 else "中" if threat_score >= 4.0 else "低"
            template = f"**威胁评分:** {threat_score:.1f}/10.0 ({threat_level}风险)\n\n{template}"

        return template

    def _analyze_with_ollama(self, prompt: str) -> str:
        """使用本地Ollama模型进行分析"""
        payload = {
            "model": self.local_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }
        
        try:
            response = self._make_request_with_retry(
                self.local_base_url,
                self.local_headers,
                payload,
                self.ollama_config.get('timeout', 60)
            )
            result = response.json()
            
            # 处理Ollama响应格式
            if 'message' in result and 'content' in result['message']:
                return result['message']['content']
            else:
                self.logger.error(f"Ollama响应格式异常: {result}")
                return "AI分析结果格式异常"
        except Exception as e:
            self.logger.error(f"Ollama分析失败: {e}")
            return f"本地AI分析失败: {str(e)}"

    def _analyze_with_cloud(self, prompt: str) -> str:
        """使用云端模型进行分析"""
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
            response = self._make_request_with_retry(
                self.cloud_base_url,
                self.cloud_headers,
                payload,
                self.deepseek_config.get('timeout', 30)
            )
            result = response.json()
            
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

    def generate_parsing_rules(self, log_sample: str) -> Dict[str, Any]:
        """根据日志样例生成解析规则"""
        if not log_sample or not log_sample.strip():
            return {"error": "日志样例为空"}
        
        prompt = f"""任务:分析日志样例并生成仅包含YAML格式的解析规则，无任何额外文本或解释。
日志样例: {log_sample}
输出要求:
1. 仅返回YAML数组，每个元素必须包含name和regex字段
2. regex使用单引号包裹，确保能匹配整个字段内容
3. 字段名使用下划线命名法(snake_case)
4. 按日志出现顺序排列字段
示例格式:
- name: src_ip
  regex: '(\d+\.\d+\.\d+\.\d+)'
- name: timestamp
  regex: '\[(.*?)\]'
- name: request_method
  regex: '"([A-Z]+)'
严格遵循上述格式，不要添加任何说明文字！"""

        try:
            if self.ai_type == 'local' and self.local_provider == 'ollama':
                ai_content = self._generate_rules_with_ollama(prompt)
            else:
                ai_content = self._generate_rules_with_cloud(prompt)
            
            if not ai_content:
                return {"error": "AI未返回有效内容"}
            
            return self._parse_yaml_rules(ai_content)
        except Exception as e:
            self.logger.error(f"生成解析规则失败: {e}")
            return {"error": str(e)}

    def _generate_rules_with_ollama(self, prompt: str) -> str:
        """使用Ollama生成规则"""
        payload = {
            "model": self.local_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }
        
        response = self._make_request_with_retry(
            f"{self.local_base_url}/api/chat",
            self.local_headers,
            payload,
            self.ollama_config.get('timeout', 60)
        )
        result = response.json()
        return result.get('message', {}).get('content', '')

    def _generate_rules_with_cloud(self, prompt: str) -> str:
        """使用云端服务生成规则"""
        payload = {
            "model": self.cloud_model,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        response = self._make_request_with_retry(
            self.cloud_base_url,
            self.cloud_headers,
            payload,
            self.deepseek_config.get('timeout', 60)
        )
        result = response.json()
        return result.get("choices", [{}])[0].get("message", {}).get("content", "")

    def _parse_yaml_rules(self, ai_content: str) -> Dict[str, Any]:
        """解析AI返回的YAML规则"""
        try:
            # 提取YAML内容（处理可能的代码块标记）
            import re
            yaml_match = re.search(r'```yaml\n(.*?)\n```', ai_content, re.DOTALL)
            if yaml_match:
                yaml_content = yaml_match.group(1)
            else:
                # 尝试直接使用内容作为YAML
                yaml_content = ai_content.strip()

            if not yaml_content:
                self.logger.error("AI返回内容为空")
                return {"error": "AI返回内容为空"}

            parsed_rules = yaml.safe_load(yaml_content)
            if not isinstance(parsed_rules, list):
                self.logger.error(f"AI返回格式错误，预期列表但得到: {type(parsed_rules).__name__}")
                return {"error": f"AI返回格式错误，预期列表但得到: {type(parsed_rules).__name__}"}

            # 转换为字段字典
            fields = {}
            for item in parsed_rules:
                if isinstance(item, dict) and 'name' in item and 'regex' in item:
                    fields[item['name']] = item['regex']
                else:
                    self.logger.warning(f"无效的规则项: {item}")

            return {"fields": fields}

        except yaml.YAMLError as e:
            self.logger.error(f"YAML解析失败: {e}\n原始内容: {ai_content}")
            return {"error": f"YAML解析失败: {e}"}
        except Exception as e:
            self.logger.error(f"解析规则失败: {e}")
            return {"error": str(e)}