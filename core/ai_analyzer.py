import requests
import logging
import yaml
import time
from typing import Dict, Any

class AIAnalyzer:
    def __init__(self, config_path: str = 'config.yaml'):
        self.config = self._load_config(config_path)
        self.ai_type = self.config.get('ai', {}).get('type', 'cloud')
        self.cloud_provider = self.config.get('ai', {}).get('cloud_provider', 'deepseek')
        self.local_provider = self.config.get('ai', {}).get('local_provider', 'ollama')
        self.logger = logging.getLogger(__name__)
        
        # 重试配置
        self.max_retries = 3
        self.retry_delay = 1

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
        for attempt in range(self.max_retries):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=timeout)
                response.raise_for_status()
                return response
            except requests.exceptions.Timeout:
                self.logger.warning(f"请求超时 (尝试 {attempt + 1}/{self.max_retries})")
            except requests.exceptions.ConnectionError:
                self.logger.warning(f"连接错误 (尝试 {attempt + 1}/{self.max_retries})")
            except requests.exceptions.HTTPError as e:
                self.logger.warning(f"HTTP错误: {e.response.status_code} (尝试 {attempt + 1}/{self.max_retries})")
            except Exception as e:
                self.logger.warning(f"请求失败: {e} (尝试 {attempt + 1}/{self.max_retries})")
            
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay * (2 ** attempt))  # 指数退避
        
        raise Exception("所有重试尝试都失败了")

    def analyze_log(self, log_context: str) -> str:
        """将日志上下文发送给AI进行分析"""
        if not log_context or not log_context.strip():
            return "无有效日志内容可供分析"
        
        prompt = f"""作为网络安全应急响应专家，请深度分析以下高风险成功攻击日志。这些日志已确认为：
1. 高风险安全威胁
2. 攻击执行成功（HTTP状态码显示成功）

请重点分析以下方面：
**攻击分析:**
- 具体攻击类型和技术手段
- 攻击载荷的危害程度和技术复杂度
- 攻击者可能获得的权限或数据

**影响评估:**
- 系统遭受的实际损害
- 可能被窃取或篡改的数据
- 对业务连续性的潜在影响

**应急措施:**
- 立即需要采取的阻断措施
- 系统加固和漏洞修复建议
- 后续监控和检测要点

**威胁情报:**
- 攻击者的技术特征分析
- 可能的攻击组织或工具特征
- 后续攻击的可能性评估

日志内容：
{log_context}

请以专业、简洁的格式回复，重点关注实际威胁和应对措施："""

        try:
            if self.ai_type == 'local' and self.local_provider == 'ollama':
                return self._analyze_with_ollama(prompt)
            else:
                return self._analyze_with_cloud(prompt)
        except Exception as e:
            self.logger.error(f"AI分析失败: {e}")
            return f"AI分析失败: {str(e)}"

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