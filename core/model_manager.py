#!/usr/bin/env python3
"""
模型管理器
管理LM Studio模型的发现、选择和配置
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

from core.lm_studio_connector import LMStudioConnector, LMStudioConfig, get_lm_studio_connector
from core.ai_config_manager import get_ai_config_manager

@dataclass
class ModelInfo:
    """模型信息"""
    id: str
    name: str
    size: str
    modified: str
    status: str = "available"  # available, loading, error
    parameters: Optional[str] = None
    quantization: Optional[str] = None
    description: Optional[str] = None
    capabilities: Optional[List[str]] = None
    recommended: bool = False
    compatibility_score: float = 0.0

@dataclass
class ServerStatus:
    """服务器状态"""
    connected: bool
    host: str
    port: int
    model_loaded: bool
    current_model: Optional[str]
    available_models_count: int
    response_time: float
    error_message: Optional[str] = None

class ModelManager:
    """模型管理器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config_manager = get_ai_config_manager()
        self._connector: Optional[LMStudioConnector] = None
        self._last_refresh_time = 0
        self._refresh_cache_timeout = 30  # 30秒缓存
        self._cached_models: List[ModelInfo] = []
        self._cached_server_status: Optional[ServerStatus] = None

    @property
    def connector(self) -> LMStudioConnector:
        """获取LM Studio连接器"""
        if self._connector is None:
            self._connector = get_lm_studio_connector()
        return self._connector

    def get_server_status(self, force_refresh: bool = False) -> ServerStatus:
        """获取服务器状态"""
        current_time = time.time()

        # 使用缓存（除非强制刷新）
        if (not force_refresh and
            self._cached_server_status and
            current_time - self._last_refresh_time < self._refresh_cache_timeout):
            return self._cached_server_status

        try:
            config = self.connector.config
            start_time = time.time()

            # 检查连接
            connected = self.connector.check_connection()
            response_time = time.time() - start_time

            if connected:
                # 获取当前模型和可用模型
                available_models = self.connector.get_available_models()
                current_model = self._get_currently_loaded_model()

                status = ServerStatus(
                    connected=True,
                    host=config.host,
                    port=config.port,
                    model_loaded=bool(current_model),
                    current_model=current_model,
                    available_models_count=len(available_models),
                    response_time=response_time
                )
            else:
                status = ServerStatus(
                    connected=False,
                    host=config.host,
                    port=config.port,
                    model_loaded=False,
                    current_model=None,
                    available_models_count=0,
                    response_time=response_time,
                    error_message="无法连接到LM Studio服务器"
                )

        except Exception as e:
            config = self.connector.config
            status = ServerStatus(
                connected=False,
                host=config.host,
                port=config.port,
                model_loaded=False,
                current_model=None,
                available_models_count=0,
                response_time=0.0,
                error_message=str(e)
            )
            self.logger.error(f"获取服务器状态失败: {e}")

        self._cached_server_status = status
        self._last_refresh_time = current_time
        return status

    def _get_currently_loaded_model(self) -> Optional[str]:
        """获取当前加载的模型"""
        try:
            # 尝试通过API获取当前模型
            response = self.connector._make_request("GET", "/v1/models")
            if response and "data" in response:
                models = response["data"]
                if models:
                    # 通常第一个模型是当前加载的模型
                    return models[0].get("id")
        except Exception:
            pass

        # 如果API失败，尝试从配置获取
        config = self.config_manager.get_lm_studio_config()
        return config.model_name or None

    def refresh_models(self, force_refresh: bool = True) -> List[ModelInfo]:
        """刷新可用模型列表"""
        current_time = time.time()

        # 检查缓存
        if (not force_refresh and
            self._cached_models and
            current_time - self._last_refresh_time < self._refresh_cache_timeout):
            return self._cached_models

        try:
            # 确保连接正常
            if not self.connector.check_connection():
                self.logger.warning("LM Studio未连接，无法刷新模型列表")
                return []

            # 获取原始模型列表
            raw_models = self.connector.get_available_models()

            # 转换为ModelInfo对象
            models = []
            compatibility_config = self.config_manager.get_model_compatibility_config()

            for model_id in raw_models:
                model_info = self._parse_model_info(model_id, compatibility_config)
                if model_info:
                    models.append(model_info)

            # 按推荐程度和兼容性排序
            models.sort(key=lambda m: (m.recommended, m.compatibility_score), reverse=True)

            self._cached_models = models
            self._last_refresh_time = current_time

            self.logger.info(f"刷新模型列表完成，发现 {len(models)} 个模型")
            return models

        except Exception as e:
            self.logger.error(f"刷新模型列表失败: {e}")
            return []

    def _parse_model_info(self, model_id: str, compatibility_config: Dict) -> Optional[ModelInfo]:
        """解析模型信息"""
        try:
            # 从模型ID解析信息
            parts = model_id.split("-")

            # 基础信息
            name = model_id.replace("_", " ").title()
            size = ""
            parameters = ""
            quantization = ""

            # 解析参数大小
            for part in parts:
                if part.endswith("b") or part.endswith("B"):
                    try:
                        params = float(part[:-1])
                        if params < 1000:
                            parameters = f"{params}B"
                        else:
                            parameters = f"{params/1000:.1f}B"
                    except:
                        pass
                elif part in ["q4", "q5", "q8", "q4_k_m", "q5_k_m", "q8_0"]:
                    quantization = part.upper()
                elif part in ["chat", "instruct", "base"]:
                    if part != "base":
                        name += f" ({part.title()})"

            # 计算兼容性评分
            compatibility_score = self._calculate_compatibility_score(model_id, compatibility_config)

            # 检查是否推荐
            recommended = self._is_recommended_model(model_id, compatibility_config)

            # 获取描述
            description = self._generate_model_description(model_id, parameters, quantization)

            return ModelInfo(
                id=model_id,
                name=name,
                size=size,
                modified="",  # LM Studio API不提供此信息
                parameters=parameters,
                quantization=quantization,
                description=description,
                capabilities=self._detect_model_capabilities(model_id),
                recommended=recommended,
                compatibility_score=compatibility_score
            )

        except Exception as e:
            self.logger.error(f"解析模型信息失败 {model_id}: {e}")
            return None

    def _calculate_compatibility_score(self, model_id: str, config: Dict) -> float:
        """计算模型兼容性评分"""
        score = 0.0
        model_lower = model_id.lower()

        # 检查支持的系列
        supported_series = config.get("supported_series", [])
        for series in supported_series:
            if series in model_lower:
                score += 3.0
                break

        # 检查模型大小偏好
        preferred_sizes = config.get("preferred_sizes", [])
        for size in preferred_sizes:
            if f"{size}b" in model_lower or f"{size}B" in model_lower:
                score += 2.0
                break

        # 检查避免的特征
        avoid_features = config.get("avoid_features", [])
        for feature in avoid_features:
            if feature in model_lower:
                score -= 2.0

        # 检查指令调优
        if any(keyword in model_lower for keyword in ["chat", "instruct", "sft"]):
            score += 1.5

        # 检查量化质量
        if "q8" in model_lower:
            score += 1.0
        elif "q4" in model_lower:
            score += 0.5

        return max(0.0, min(5.0, score))

    def _is_recommended_model(self, model_id: str, config: Dict) -> bool:
        """检查是否为推荐模型"""
        model_lower = model_id.lower()

        # 推荐的模型特征
        recommended_patterns = [
            "chat", "instruct",  # 指令调优
            "7b", "8b",          # 适中大小
            "q4", "q5"           # 合适的量化
        ]

        # 避免的特征
        avoid_patterns = ["base", "raw", "300b", "70b"]  # 太大或未调优

        # 计算推荐度
        positive_score = sum(1 for pattern in recommended_patterns if pattern in model_lower)
        negative_score = sum(1 for pattern in avoid_patterns if pattern in model_lower)

        return positive_score >= 2 and negative_score == 0

    def _detect_model_capabilities(self, model_id: str) -> List[str]:
        """检测模型能力"""
        capabilities = []
        model_lower = model_id.lower()

        # 基础能力
        capabilities.append("text-generation")

        # 特殊能力
        if "chat" in model_lower or "instruct" in model_lower:
            capabilities.append("conversation")
            capabilities.append("instruction-following")

        if "code" in model_lower:
            capabilities.append("code-generation")

        if any(size in model_lower for size in ["70b", "65b", "40b"]):
            capabilities.append("complex-reasoning")

        return capabilities

    def _generate_model_description(self, model_id: str, parameters: str, quantization: str) -> str:
        """生成模型描述"""
        parts = []

        if parameters:
            parts.append(f"{parameters}参数")

        if quantization:
            parts.append(f"{quantization}量化")

        model_lower = model_id.lower()

        # 模型类型描述
        if "llama" in model_lower:
            parts.append("Llama系列模型")
        elif "qwen" in model_lower:
            parts.append("通义千问系列")
        elif "mistral" in model_lower:
            parts.append("Mistral系列")
        elif "yi" in model_lower:
            parts.append("零一万物系列")
        elif "deepseek" in model_lower:
            parts.append("深度求索系列")
        elif "chatglm" in model_lower:
            parts.append("ChatGLM系列")
        else:
            parts.append("开源大语言模型")

        # 用途描述
        if "chat" in model_lower or "instruct" in model_lower:
            parts.append("适合对话和指令跟随")

        return "，".join(parts) if parts else "大语言模型"

    def select_model(self, model_id: str) -> bool:
        """选择模型"""
        try:
            # 验证模型是否可用
            available_models = self.refresh_models()
            model_ids = [m.id for m in available_models]

            if model_id not in model_ids:
                self.logger.error(f"模型 {model_id} 不在可用列表中")
                return False

            # 更新配置
            config = self.config_manager.get_lm_studio_config()
            config.model_name = model_id

            # 保存配置
            success = self.config_manager.update_lm_studio_config(config)

            if success:
                self.logger.info(f"已选择模型: {model_id}")
                # 清除连接器缓存以使用新配置
                self._connector = None
            else:
                self.logger.error("保存模型配置失败")

            return success

        except Exception as e:
            self.logger.error(f"选择模型失败: {e}")
            return False

    def get_current_model(self) -> Optional[ModelInfo]:
        """获取当前选中的模型"""
        try:
            config = self.config_manager.get_lm_studio_config()
            current_model_id = config.model_name

            if not current_model_id:
                return None

            # 从缓存中查找
            for model in self._cached_models:
                if model.id == current_model_id:
                    return model

            # 如果缓存中没有，刷新并查找
            models = self.refresh_models()
            for model in models:
                if model.id == current_model_id:
                    return model

            return None

        except Exception as e:
            self.logger.error(f"获取当前模型失败: {e}")
            return None

    def test_model(self, model_id: str, test_prompt: str = "你好，请简单介绍一下自己。") -> Dict[str, Any]:
        """测试模型响应"""
        try:
            # 临时切换到测试模型
            original_model = self.config_manager.get_lm_studio_config().model_name

            # 选择测试模型
            if not self.select_model(model_id):
                return {
                    "success": False,
                    "error": "无法选择模型",
                    "response_time": 0.0
                }

            # 发送测试请求
            start_time = time.time()

            messages = [
                {"role": "user", "content": test_prompt}
            ]

            response = self.connector.chat_completion(messages)

            response_time = time.time() - start_time

            # 恢复原始模型
            if original_model:
                self.select_model(original_model)

            return {
                "success": True,
                "response": response,
                "response_time": response_time,
                "model_id": model_id
            }

        except Exception as e:
            self.logger.error(f"测试模型失败 {model_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "response_time": 0.0,
                "model_id": model_id
            }

    def get_model_recommendations(self, use_case: str = "general") -> List[ModelInfo]:
        """获取模型推荐"""
        try:
            models = self.refresh_models()

            # 根据用例筛选和排序
            if use_case == "security_analysis":
                # 安全分析需要逻辑推理能力强的模型
                security_keywords = ["instruct", "chat", "70b", "34b", "13b"]
                recommended = []

                for model in models:
                    score = 0
                    model_lower = model.id.lower()

                    # 偏好指令调优模型
                    for keyword in security_keywords:
                        if keyword in model_lower:
                            score += 1

                    # 避免基础模型
                    if "base" in model_lower:
                        score -= 2

                    model.compatibility_score = score
                    recommended.append(model)

                recommended.sort(key=lambda m: m.compatibility_score, reverse=True)
                return recommended[:5]  # 返回前5个推荐

            elif use_case == "speed":
                # 速度优先，选择较小的模型
                speed_models = [m for m in models if "7b" in m.id.lower() or "8b" in m.id.lower()]
                speed_models.sort(key=lambda m: m.compatibility_score, reverse=True)
                return speed_models[:3]

            else:
                # 通用推荐
                return [m for m in models if m.recommended][:5]

        except Exception as e:
            self.logger.error(f"获取模型推荐失败: {e}")
            return []

    def export_model_list(self, format: str = "json") -> str:
        """导出模型列表"""
        try:
            models = self.refresh_models()

            if format.lower() == "json":
                return json.dumps([asdict(model) for model in models],
                                indent=2, ensure_ascii=False)

            elif format.lower() == "csv":
                import csv
                import io

                output = io.StringIO()
                writer = csv.writer(output)

                # 写入标题行
                writer.writerow(["ID", "名称", "参数", "量化", "推荐", "兼容性评分", "描述"])

                # 写入数据行
                for model in models:
                    writer.writerow([
                        model.id,
                        model.name,
                        model.parameters or "",
                        model.quantization or "",
                        "是" if model.recommended else "否",
                        f"{model.compatibility_score:.1f}",
                        model.description or ""
                    ])

                return output.getvalue()

            else:
                raise ValueError(f"不支持的导出格式: {format}")

        except Exception as e:
            self.logger.error(f"导出模型列表失败: {e}")
            return ""

# 全局模型管理器实例
_global_model_manager = None

def get_model_manager() -> ModelManager:
    """获取全局模型管理器实例"""
    global _global_model_manager
    if _global_model_manager is None:
        _global_model_manager = ModelManager()
    return _global_model_manager

def reset_model_manager():
    """重置全局模型管理器"""
    global _global_model_manager
    _global_model_manager = None