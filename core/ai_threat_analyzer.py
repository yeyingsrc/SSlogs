#!/usr/bin/env python3
"""
AI驱动的威胁分析模块
使用本地LLM模型进行智能安全分析和威胁评估
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
import hashlib

from core.lm_studio_connector import LMStudioConnector, LMStudioConfig, ChatMessage, SECURITY_ANALYSIS_CONFIG

@dataclass
class ThreatAnalysis:
    """威胁分析结果"""
    threat_level: str  # 低, 中, 高, 严重
    attack_types: List[str]
    risk_factors: List[str]
    confidence: float
    analysis_summary: str
    recommendations: List[str]
    timestamp: datetime
    rule_matches: List[str]
    threat_score: float

@dataclass
class AIDetectionResult:
    """AI检测结果"""
    is_malicious: bool
    threat_analysis: ThreatAnalysis
    raw_analysis: str
    processing_time: float
    model_used: str
    confidence_score: float

class AIThreatAnalyzer:
    """AI威胁分析器"""

    def __init__(self, lm_config: LMStudioConfig = None):
        self.lm_config = lm_config or SECURITY_ANALYSIS_CONFIG
        self.connector = LMStudioConnector(self.lm_config)
        self.logger = logging.getLogger(__name__)
        self.analysis_cache = {}  # 分析结果缓存
        self.cache_ttl = 3600  # 缓存1小时

        # 初始化连接器
        self._initialize_connector()

    def _initialize_connector(self):
        """初始化LM Studio连接器"""
        try:
            if self.connector.test_connection():
                available_models = self.connector.get_available_models()
                if available_models:
                    # 使用第一个可用模型
                    self.connector.set_model(available_models[0])
                    self.logger.info(f"AI威胁分析器已初始化，使用模型: {available_models[0]}")
                else:
                    self.logger.warning("未找到可用模型")
            else:
                self.logger.error("无法连接到LM Studio")
        except Exception as e:
            self.logger.error(f"AI威胁分析器初始化失败: {e}")

    def _generate_cache_key(self, log_entry: Dict[str, Any]) -> str:
        """生成缓存键"""
        # 使用关键日志字段生成哈希
        key_data = {
            'src_ip': log_entry.get('src_ip'),
            'request_path': log_entry.get('request_path'),
            'user_agent': log_entry.get('user_agent'),
            'request_body': log_entry.get('request_body'),
            'status_code': log_entry.get('status_code')
        }
        key_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(key_str.encode('utf-8')).hexdigest()

    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """检查缓存是否有效"""
        return time.time() - cache_entry['timestamp'] < self.cache_ttl

    def _parse_threat_analysis(self, raw_analysis: str) -> ThreatAnalysis:
        """解析AI分析的威胁信息"""
        try:
            # 这里使用简单的文本解析，实际项目中可能需要更复杂的NLP处理
            lines = raw_analysis.split('\n')
            threat_level = "中"  # 默认值
            attack_types = []
            risk_factors = []
            confidence = 0.5
            recommendations = []

            current_section = None

            for line in lines:
                line = line.strip()
                if "威胁等级" in line or "威胁级别" in line:
                    if "严重" in line:
                        threat_level = "严重"
                    elif "高" in line:
                        threat_level = "高"
                    elif "中" in line:
                        threat_level = "中"
                    elif "低" in line:
                        threat_level = "低"
                elif "攻击类型" in line:
                    current_section = "attack_types"
                elif "风险因素" in line:
                    current_section = "risk_factors"
                elif "建议" in line or "措施" in line:
                    current_section = "recommendations"
                elif line.startswith('-') or line.startswith('•') or line.startswith('*'):
                    content = line.lstrip('-•* ').strip()
                    if current_section == "attack_types":
                        attack_types.append(content)
                    elif current_section == "risk_factors":
                        risk_factors.append(content)
                    elif current_section == "recommendations":
                        recommendations.append(content)

            # 根据威胁等级调整置信度
            confidence_map = {"严重": 0.9, "高": 0.8, "中": 0.6, "低": 0.4}
            confidence = confidence_map.get(threat_level, 0.5)

            return ThreatAnalysis(
                threat_level=threat_level,
                attack_types=attack_types,
                risk_factors=risk_factors,
                confidence=confidence,
                analysis_summary=raw_analysis,
                recommendations=recommendations,
                timestamp=datetime.now(),
                rule_matches=[],
                threat_score=self._calculate_threat_score(threat_level, confidence)
            )

        except Exception as e:
            self.logger.error(f"解析威胁分析失败: {e}")
            # 返回默认分析结果
            return ThreatAnalysis(
                threat_level="中",
                attack_types=["未知威胁"],
                risk_factors=["分析解析失败"],
                confidence=0.3,
                analysis_summary=raw_analysis,
                recommendations=["建议人工审查"],
                timestamp=datetime.now(),
                rule_matches=[],
                threat_score=5.0
            )

    def _calculate_threat_score(self, threat_level: str, confidence: float) -> float:
        """计算威胁评分"""
        base_scores = {"严重": 9.0, "高": 7.5, "中": 5.5, "低": 3.5}
        base_score = base_scores.get(threat_level, 5.5)

        # 调整评分范围到1-10
        adjusted_score = base_score * confidence + (1.0 - confidence) * 5.0
        return min(max(adjusted_score, 1.0), 10.0)

    def analyze_log_entry(self, log_entry: Dict[str, Any], rule_matches: List[str] = None) -> Optional[AIDetectionResult]:
        """分析单个日志条目"""
        start_time = time.time()

        # 检查缓存
        cache_key = self._generate_cache_key(log_entry)
        if cache_key in self.analysis_cache and self._is_cache_valid(self.analysis_cache[cache_key]):
            self.logger.debug(f"使用缓存的分析结果: {cache_key}")
            cached_result = self.analysis_cache[cache_key]['result']
            cached_result.processing_time = time.time() - start_time
            return cached_result

        try:
            # 准备增强的日志数据
            enhanced_log = log_entry.copy()
            if rule_matches:
                enhanced_log['matched_rules'] = rule_matches
                enhanced_log['rule_count'] = len(rule_matches)

            # 执行AI分析
            raw_analysis = self.connector.analyze_security_log(enhanced_log)

            if raw_analysis:
                # 解析分析结果
                threat_analysis = self._parse_threat_analysis(raw_analysis)
                threat_analysis.rule_matches = rule_matches or []

                # 创建检测结果
                result = AIDetectionResult(
                    is_malicious=threat_analysis.threat_level in ["高", "严重"],
                    threat_analysis=threat_analysis,
                    raw_analysis=raw_analysis,
                    processing_time=time.time() - start_time,
                    model_used=self.connector.current_model or "未知",
                    confidence_score=threat_analysis.confidence
                )

                # 缓存结果
                self.analysis_cache[cache_key] = {
                    'result': result,
                    'timestamp': time.time()
                }

                return result
            else:
                self.logger.error("AI分析返回空结果")
                return None

        except Exception as e:
            self.logger.error(f"日志条目AI分析失败: {e}")
            return None

    async def analyze_log_entry_async(self, log_entry: Dict[str, Any], rule_matches: List[str] = None) -> Optional[AIDetectionResult]:
        """异步分析单个日志条目"""
        start_time = time.time()

        # 检查缓存
        cache_key = self._generate_cache_key(log_entry)
        if cache_key in self.analysis_cache and self._is_cache_valid(self.analysis_cache[cache_key]):
            self.logger.debug(f"使用缓存的分析结果: {cache_key}")
            cached_result = self.analysis_cache[cache_key]['result']
            cached_result.processing_time = time.time() - start_time
            return cached_result

        try:
            # 准备增强的日志数据
            enhanced_log = log_entry.copy()
            if rule_matches:
                enhanced_log['matched_rules'] = rule_matches
                enhanced_log['rule_count'] = len(rule_matches)

            # 执行异步AI分析
            raw_analysis = await self.connector.analyze_security_log_async(enhanced_log)

            if raw_analysis:
                # 解析分析结果
                threat_analysis = self._parse_threat_analysis(raw_analysis)
                threat_analysis.rule_matches = rule_matches or []

                # 创建检测结果
                result = AIDetectionResult(
                    is_malicious=threat_analysis.threat_level in ["高", "严重"],
                    threat_analysis=threat_analysis,
                    raw_analysis=raw_analysis,
                    processing_time=time.time() - start_time,
                    model_used=self.connector.current_model or "未知",
                    confidence_score=threat_analysis.confidence
                )

                # 缓存结果
                self.analysis_cache[cache_key] = {
                    'result': result,
                    'timestamp': time.time()
                }

                return result
            else:
                self.logger.error("异步AI分析返回空结果")
                return None

        except Exception as e:
            self.logger.error(f"异步日志条目AI分析失败: {e}")
            return None

    def analyze_log_batch(self, log_entries: List[Dict[str, Any]], rule_matches_list: List[List[str]] = None) -> List[Optional[AIDetectionResult]]:
        """批量分析日志条目"""
        if rule_matches_list is None:
            rule_matches_list = [[] for _ in log_entries]

        results = []
        for log_entry, rule_matches in zip(log_entries, rule_matches_list):
            result = self.analyze_log_entry(log_entry, rule_matches)
            results.append(result)

        return results

    async def analyze_log_batch_async(self, log_entries: List[Dict[str, Any]], rule_matches_list: List[List[str]] = None) -> List[Optional[AIDetectionResult]]:
        """异步批量分析日志条目"""
        if rule_matches_list is None:
            rule_matches_list = [[] for _ in log_entries]

        # 创建异步任务
        tasks = []
        for log_entry, rule_matches in zip(log_entries, rule_matches_list):
            task = self.analyze_log_entry_async(log_entry, rule_matches)
            tasks.append(task)

        # 并发执行
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"批量分析中发生异常: {result}")
                processed_results.append(None)
            else:
                processed_results.append(result)

        return processed_results

    def get_security_recommendations(self, analysis_result: AIDetectionResult) -> List[str]:
        """获取安全建议"""
        try:
            # 使用AI生成详细建议
            recommendations = self.connector.generate_security_recommendations(
                analysis_result.raw_analysis,
                {
                    "threat_level": analysis_result.threat_analysis.threat_level,
                    "attack_types": analysis_result.threat_analysis.attack_types,
                    "confidence": analysis_result.confidence_score
                }
            )

            if recommendations:
                # 解析建议文本
                lines = recommendations.split('\n')
                parsed_recommendations = []
                for line in lines:
                    line = line.strip()
                    if line and (line.startswith('-') or line.startswith('•') or line.startswith('*') or line.isdigit()):
                        content = line.lstrip('-•* 0123456789.')
                        if content:
                            parsed_recommendations.append(content)

                return parsed_recommendations if parsed_recommendations else [recommendations]
            else:
                return analysis_result.threat_analysis.recommendations

        except Exception as e:
            self.logger.error(f"生成安全建议失败: {e}")
            return analysis_result.threat_analysis.recommendations

    def explain_detection(self, rule_name: str, log_entry: Dict[str, Any], threat_score: float) -> Optional[str]:
        """解释检测结果"""
        try:
            explanation = self.connector.explain_rule_match(rule_name, log_entry, threat_score)
            return explanation
        except Exception as e:
            self.logger.error(f"生成检测解释失败: {e}")
            return None

    def natural_language_query(self, query: str, log_data: List[Dict[str, Any]] = None) -> Optional[str]:
        """自然语言查询"""
        try:
            response = self.connector.natural_language_query(query, log_data)
            return response
        except Exception as e:
            self.logger.error(f"自然语言查询失败: {e}")
            return None

    def get_analyzer_status(self) -> Dict[str, Any]:
        """获取分析器状态"""
        return {
            "connector_status": {
                "connected": self.connector.test_connection(),
                "current_model": self.connector.current_model,
                "available_models": self.connector.get_available_models(),
                "model_info": self.connector.get_model_info()
            },
            "cache_status": {
                "cache_size": len(self.analysis_cache),
                "cache_ttl": self.cache_ttl
            },
            "config": {
                "temperature": self.lm_config.temperature,
                "max_tokens": self.lm_config.max_tokens,
                "timeout": self.lm_config.timeout
            }
        }

    def clear_cache(self):
        """清空分析缓存"""
        self.analysis_cache.clear()
        self.logger.info("分析缓存已清空")

    def export_analysis_results(self, results: List[AIDetectionResult], output_file: str) -> bool:
        """导出分析结果"""
        try:
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "analyzer_info": self.get_analyzer_status(),
                "results": [asdict(result) for result in results]
            }

            # 处理datetime对象
            for result in export_data["results"]:
                result["threat_analysis"]["timestamp"] = result["threat_analysis"]["timestamp"].isoformat()

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"分析结果已导出到: {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"导出分析结果失败: {e}")
            return False

# 全局分析器实例
_global_analyzer = None

def get_ai_threat_analyzer(lm_config: LMStudioConfig = None) -> AIThreatAnalyzer:
    """获取全局AI威胁分析器实例"""
    global _global_analyzer
    if _global_analyzer is None:
        _global_analyzer = AIThreatAnalyzer(lm_config)
    return _global_analyzer

def reset_ai_threat_analyzer():
    """重置全局AI威胁分析器"""
    global _global_analyzer
    _global_analyzer = None