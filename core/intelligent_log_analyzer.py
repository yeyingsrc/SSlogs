#!/usr/bin/env python3
"""
智能日志分析模块
结合传统规则匹配和AI分析的高级日志分析系统
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional, Tuple, AsyncGenerator
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import statistics
from collections import defaultdict, deque

from core.rule_engine import RuleEngine, ThreatScore
from core.ai_threat_analyzer import AIThreatAnalyzer, AIDetectionResult
from core.ai_config_manager import get_ai_config_manager

@dataclass
class LogAnalysisResult:
    """日志分析结果"""
    log_entry: Dict[str, Any]
    rule_matches: List[Dict[str, Any]]
    ai_analysis: Optional[AIDetectionResult]
    final_threat_score: float
    risk_level: str
    recommendations: List[str]
    processing_time: float
    analysis_timestamp: datetime
    analysis_source: str  # "rules_only", "ai_enhanced", "ai_only"

@dataclass
class BatchAnalysisResult:
    """批量分析结果"""
    total_logs: int
    successful_analyses: int
    failed_analyses: int
    threat_detections: int
    processing_time: float
    results: List[LogAnalysisResult]
    statistics: Dict[str, Any]

@dataclass
class ThreatPattern:
    """威胁模式"""
    pattern_name: str
    description: str
    indicators: List[str]
    frequency: int
    severity: str
    first_seen: datetime
    last_seen: datetime
    affected_ips: List[str]

class IntelligentLogAnalyzer:
    """智能日志分析器"""

    def __init__(self, rule_engine: RuleEngine, ai_analyzer: AIThreatAnalyzer = None):
        self.rule_engine = rule_engine
        self.ai_analyzer = ai_analyzer
        self.logger = logging.getLogger(__name__)
        self.config_manager = get_ai_config_manager()

        # 分析历史和缓存
        self.analysis_history = deque(maxlen=1000)  # 最近1000次分析
        self.threat_patterns = {}  # 威胁模式库
        self.ip_reputation = defaultdict(int)  # IP声誉记录

        # 性能统计
        self.performance_stats = {
            'total_analyses': 0,
            'total_processing_time': 0.0,
            'ai_analyses': 0,
            'ai_failures': 0,
            'rule_only_analyses': 0
        }

        # 初始化配置
        self._load_configuration()

    def _load_configuration(self):
        """加载配置"""
        try:
            config = self.config_manager.get_analysis_config()
            self.scoring_weights = config["scoring_weights"]
            self.thresholds = config["thresholds"]

            perf_config = self.config_manager.get_performance_config()
            self.batch_size = perf_config.batch_size
            self.max_concurrent = perf_config.max_concurrent_requests

            self.logger.info("智能日志分析器配置已加载")
        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")
            # 使用默认配置
            self.scoring_weights = type('obj', (object,), {
                'ai_weight': 0.4, 'rule_weight': 0.6
            })()
            self.thresholds = type('obj', (object,), {
                'confidence_threshold': 0.3,
                'threat_score_threshold': 5.0,
                'processing_time_threshold': 10.0
            })()
            self.batch_size = 10
            self.max_concurrent = 5

    def analyze_log(self, log_entry: Dict[str, Any], force_ai: bool = False) -> LogAnalysisResult:
        """分析单个日志条目"""
        start_time = time.time()
        analysis_timestamp = datetime.now()

        try:
            # 第一阶段：传统规则匹配
            rule_matches = self.rule_engine.match_log(log_entry)
            rule_only = False

            # 第二阶段：AI增强分析
            ai_analysis = None
            ai_enhanced = False
            ai_only = False

            if self.ai_analyzer and (force_ai or self._should_use_ai_analysis(log_entry, rule_matches)):
                matched_rule_names = [match['rule']['name'] for match in rule_matches]
                ai_analysis = self.ai_analyzer.analyze_log_entry(log_entry, matched_rule_names)

                if ai_analysis:
                    ai_enhanced = True
                else:
                    self.performance_stats['ai_failures'] += 1
            elif not rule_matches and self.ai_analyzer:
                # 如果规则没有匹配，尝试纯AI分析
                ai_analysis = self.ai_analyzer.analyze_log_entry(log_entry, [])
                if ai_analysis:
                    ai_only = True

            # 第三阶段：结果融合和评分
            final_result = self._merge_analysis_results(
                log_entry, rule_matches, ai_analysis, rule_only, ai_enhanced, ai_only
            )

            # 第四阶段：威胁模式识别
            self._identify_threat_patterns(final_result)

            # 第五阶段：IP声誉更新
            self._update_ip_reputation(final_result)

            # 更新统计信息
            processing_time = time.time() - start_time
            self._update_performance_stats(final_result, processing_time)

            final_result.processing_time = processing_time
            final_result.analysis_timestamp = analysis_timestamp

            # 记录分析历史
            self.analysis_history.append(final_result)

            return final_result

        except Exception as e:
            self.logger.error(f"日志分析失败: {e}")
            processing_time = time.time() - start_time

            return LogAnalysisResult(
                log_entry=log_entry,
                rule_matches=[],
                ai_analysis=None,
                final_threat_score=0.0,
                risk_level="unknown",
                recommendations=[f"分析失败: {str(e)}"],
                processing_time=processing_time,
                analysis_timestamp=analysis_timestamp,
                analysis_source="error"
            )

    async def analyze_log_async(self, log_entry: Dict[str, Any], force_ai: bool = False) -> LogAnalysisResult:
        """异步分析单个日志条目"""
        start_time = time.time()
        analysis_timestamp = datetime.now()

        try:
            # 第一阶段：传统规则匹配
            rule_matches = self.rule_engine.match_log(log_entry)

            # 第二阶段：AI增强分析
            ai_analysis = None
            ai_enhanced = False
            ai_only = False

            if self.ai_analyzer and (force_ai or self._should_use_ai_analysis(log_entry, rule_matches)):
                matched_rule_names = [match['rule']['name'] for match in rule_matches]
                ai_analysis = await self.ai_analyzer.analyze_log_entry_async(log_entry, matched_rule_names)

                if ai_analysis:
                    ai_enhanced = True
                else:
                    self.performance_stats['ai_failures'] += 1
            elif not rule_matches and self.ai_analyzer:
                # 如果规则没有匹配，尝试纯AI分析
                ai_analysis = await self.ai_analyzer.analyze_log_entry_async(log_entry, [])
                if ai_analysis:
                    ai_only = True

            # 第三阶段：结果融合和评分
            final_result = self._merge_analysis_results(
                log_entry, rule_matches, ai_analysis, False, ai_enhanced, ai_only
            )

            # 第四阶段：威胁模式识别
            self._identify_threat_patterns(final_result)

            # 第五阶段：IP声誉更新
            self._update_ip_reputation(final_result)

            # 更新统计信息
            processing_time = time.time() - start_time
            self._update_performance_stats(final_result, processing_time)

            final_result.processing_time = processing_time
            final_result.analysis_timestamp = analysis_timestamp

            return final_result

        except Exception as e:
            self.logger.error(f"异步日志分析失败: {e}")
            processing_time = time.time() - start_time

            return LogAnalysisResult(
                log_entry=log_entry,
                rule_matches=[],
                ai_analysis=None,
                final_threat_score=0.0,
                risk_level="unknown",
                recommendations=[f"分析失败: {str(e)}"],
                processing_time=processing_time,
                analysis_timestamp=analysis_timestamp,
                analysis_source="error"
            )

    def analyze_batch(self, log_entries: List[Dict[str, Any]], force_ai: bool = False) -> BatchAnalysisResult:
        """批量分析日志条目"""
        start_time = time.time()
        results = []
        successful = 0
        failed = 0
        threat_detections = 0

        for log_entry in log_entries:
            try:
                result = self.analyze_log(log_entry, force_ai)
                results.append(result)
                successful += 1

                if result.final_threat_score >= self.thresholds.threat_score_threshold:
                    threat_detections += 1

            except Exception as e:
                self.logger.error(f"批量分析中处理日志失败: {e}")
                failed += 1

        processing_time = time.time() - start_time
        statistics = self._calculate_batch_statistics(results)

        return BatchAnalysisResult(
            total_logs=len(log_entries),
            successful_analyses=successful,
            failed_analyses=failed,
            threat_detections=threat_detections,
            processing_time=processing_time,
            results=results,
            statistics=statistics
        )

    async def analyze_batch_async(self, log_entries: List[Dict[str, Any]], force_ai: bool = False) -> BatchAnalysisResult:
        """异步批量分析日志条目"""
        start_time = time.time()

        # 创建异步任务
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def analyze_with_semaphore(log_entry):
            async with semaphore:
                return await self.analyze_log_async(log_entry, force_ai)

        # 并发执行分析
        tasks = [analyze_with_semaphore(log_entry) for log_entry in log_entries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理结果
        processed_results = []
        successful = 0
        failed = 0
        threat_detections = 0

        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"异步批量分析中发生异常: {result}")
                failed += 1
            else:
                processed_results.append(result)
                successful += 1

                if result.final_threat_score >= self.thresholds.threat_score_threshold:
                    threat_detections += 1

        processing_time = time.time() - start_time
        statistics = self._calculate_batch_statistics(processed_results)

        return BatchAnalysisResult(
            total_logs=len(log_entries),
            successful_analyses=successful,
            failed_analyses=failed,
            threat_detections=threat_detections,
            processing_time=processing_time,
            results=processed_results,
            statistics=statistics
        )

    def _should_use_ai_analysis(self, log_entry: Dict[str, Any], rule_matches: List[Dict[str, Any]]) -> bool:
        """判断是否应该使用AI分析"""
        if not self.ai_analyzer:
            return False

        # 如果规则没有匹配，尝试AI分析
        if not rule_matches:
            return True

        # 如果规则匹配的高威胁分数，需要AI确认
        high_threat_matches = [m for m in rule_matches if m['threat_score'].score >= 7.0]
        if high_threat_matches:
            return True

        # 检查异常模式
        src_ip = log_entry.get('src_ip', '')
        if self.ip_reputation.get(src_ip, 0) > 5:  # IP有不良记录
            return True

        # 检查敏感请求路径
        sensitive_paths = ['/admin', '/api/', '/config', '/system', '/root']
        request_path = log_entry.get('request_path', '').lower()
        if any(sensitive in request_path for sensitive in sensitive_paths):
            return True

        return False

    def _merge_analysis_results(self, log_entry: Dict[str, Any], rule_matches: List[Dict[str, Any]],
                              ai_analysis: Optional[AIDetectionResult], rule_only: bool,
                              ai_enhanced: bool, ai_only: bool) -> LogAnalysisResult:
        """融合规则匹配和AI分析结果"""

        # 确定分析来源
        if ai_only:
            analysis_source = "ai_only"
        elif ai_enhanced:
            analysis_source = "ai_enhanced"
        else:
            analysis_source = "rules_only"

        # 计算最终威胁评分
        final_threat_score = 0.0
        risk_level = "low"

        if ai_only and ai_analysis:
            # 纯AI分析
            final_threat_score = ai_analysis.threat_analysis.threat_score
            risk_level = ai_analysis.threat_analysis.threat_level

        elif ai_enhanced and ai_analysis:
            # AI增强分析：融合规则和AI评分
            rule_score = max([m['threat_score'].score for m in rule_matches]) if rule_matches else 0.0
            ai_score = ai_analysis.threat_analysis.threat_score

            final_threat_score = (rule_score * self.scoring_weights.rule_weight +
                                 ai_score * self.scoring_weights.ai_weight)

            # 根据AI分析调整风险级别
            if ai_analysis.is_malicious:
                risk_level = ai_analysis.threat_analysis.threat_level
            else:
                # 使用规则匹配的最高风险级别
                if rule_matches:
                    severity_scores = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
                    max_severity = max([severity_scores.get(m['threat_score'].severity, 0)
                                      for m in rule_matches])
                    severity_map = {4: 'critical', 3: 'high', 2: 'medium', 1: 'low'}
                    risk_level = severity_map.get(max_severity, 'low')

        elif rule_matches:
            # 仅规则匹配
            final_threat_score = max([m['threat_score'].score for m in rule_matches])
            severity_scores = {'critical': 4, 'high': 3, 'medium': 2, 'low': 1}
            max_severity = max([severity_scores.get(m['threat_score'].severity, 0)
                              for m in rule_matches])
            severity_map = {4: 'critical', 3: 'high', 2: 'medium', 1: 'low'}
            risk_level = severity_map.get(max_severity, 'low')

        # 生成建议
        recommendations = []
        if ai_analysis:
            recommendations = ai_analysis.threat_analysis.recommendations
        elif rule_matches:
            recommendations = [f"检测到{len(rule_matches)}个规则匹配，建议进一步调查"]

        return LogAnalysisResult(
            log_entry=log_entry,
            rule_matches=rule_matches,
            ai_analysis=ai_analysis,
            final_threat_score=final_threat_score,
            risk_level=risk_level,
            recommendations=recommendations,
            processing_time=0.0,  # 将在调用方法中设置
            analysis_timestamp=datetime.now(),
            analysis_source=analysis_source
        )

    def _identify_threat_patterns(self, result: LogAnalysisResult):
        """识别威胁模式"""
        if result.final_threat_score < self.thresholds.threat_score_threshold:
            return

        # 提取关键特征
        src_ip = result.log_entry.get('src_ip', '')
        request_path = result.log_entry.get('request_path', '')
        user_agent = result.log_entry.get('user_agent', '')

        # 基于规则匹配的模式识别
        if result.rule_matches:
            for match in result.rule_matches:
                rule_name = match['rule'].get('name', '')
                pattern_key = f"rule_{rule_name}"

                if pattern_key not in self.threat_patterns:
                    self.threat_patterns[pattern_key] = ThreatPattern(
                        pattern_name=rule_name,
                        description=match['rule'].get('description', ''),
                        indicators=[],
                        frequency=0,
                        severity=result.risk_level,
                        first_seen=result.analysis_timestamp,
                        last_seen=result.analysis_timestamp,
                        affected_ips=[]
                    )

                pattern = self.threat_patterns[pattern_key]
                pattern.frequency += 1
                pattern.last_seen = result.analysis_timestamp

                if src_ip and src_ip not in pattern.affected_ips:
                    pattern.affected_ips.append(src_ip)

        # 基于AI分析的模式识别
        if result.ai_analysis and result.ai_analysis.threat_analysis.attack_types:
            for attack_type in result.ai_analysis.threat_analysis.attack_types:
                pattern_key = f"ai_{attack_type}"

                if pattern_key not in self.threat_patterns:
                    self.threat_patterns[pattern_key] = ThreatPattern(
                        pattern_name=attack_type,
                        description=f"AI检测到的{attack_type}攻击模式",
                        indicators=[],
                        frequency=0,
                        severity=result.risk_level,
                        first_seen=result.analysis_timestamp,
                        last_seen=result.analysis_timestamp,
                        affected_ips=[]
                    )

                pattern = self.threat_patterns[pattern_key]
                pattern.frequency += 1
                pattern.last_seen = result.analysis_timestamp

                if src_ip and src_ip not in pattern.affected_ips:
                    pattern.affected_ips.append(src_ip)

    def _update_ip_reputation(self, result: LogAnalysisResult):
        """更新IP声誉"""
        src_ip = result.log_entry.get('src_ip', '')
        if not src_ip:
            return

        # 根据威胁评分调整IP声誉
        if result.final_threat_score >= 8.0:
            self.ip_reputation[src_ip] += 3  # 严重威胁
        elif result.final_threat_score >= 6.0:
            self.ip_reputation[src_ip] += 2  # 高威胁
        elif result.final_threat_score >= 4.0:
            self.ip_reputation[src_ip] += 1  # 中等威胁

    def _update_performance_stats(self, result: LogAnalysisResult, processing_time: float):
        """更新性能统计"""
        self.performance_stats['total_analyses'] += 1
        self.performance_stats['total_processing_time'] += processing_time

        if result.ai_analysis:
            self.performance_stats['ai_analyses'] += 1
        elif result.rule_matches:
            self.performance_stats['rule_only_analyses'] += 1

    def _calculate_batch_statistics(self, results: List[LogAnalysisResult]) -> Dict[str, Any]:
        """计算批量分析统计信息"""
        if not results:
            return {}

        threat_scores = [r.final_threat_score for r in results]
        processing_times = [r.processing_time for r in results]

        stats = {
            'avg_threat_score': statistics.mean(threat_scores),
            'max_threat_score': max(threat_scores),
            'min_threat_score': min(threat_scores),
            'avg_processing_time': statistics.mean(processing_times),
            'max_processing_time': max(processing_times),
            'min_processing_time': min(processing_times),
            'threat_distribution': defaultdict(int),
            'analysis_source_distribution': defaultdict(int),
            'top_threat_patterns': []
        }

        # 威胁分布统计
        for result in results:
            stats['threat_distribution'][result.risk_level] += 1
            stats['analysis_source_distribution'][result.analysis_source] += 1

        # 获取热门威胁模式
        if self.threat_patterns:
            top_patterns = sorted(self.threat_patterns.values(),
                                key=lambda x: x.frequency, reverse=True)[:10]
            stats['top_threat_patterns'] = [
                {
                    'name': p.pattern_name,
                    'frequency': p.frequency,
                    'severity': p.severity,
                    'affected_ips_count': len(p.affected_ips)
                }
                for p in top_patterns
            ]

        return stats

    def get_threat_summary(self, time_window: int = 3600) -> Dict[str, Any]:
        """获取威胁摘要（指定时间窗口内，秒）"""
        cutoff_time = datetime.now() - timedelta(seconds=time_window)

        # 过滤时间窗口内的分析结果
        recent_results = [
            r for r in self.analysis_history
            if r.analysis_timestamp >= cutoff_time
        ]

        if not recent_results:
            return {
                'time_window': time_window,
                'total_analyses': 0,
                'threat_count': 0,
                'avg_threat_score': 0.0,
                'top_risks': [],
                'threat_trends': []
            }

        # 计算统计信息
        threat_results = [r for r in recent_results
                         if r.final_threat_score >= self.thresholds.threat_score_threshold]

        # 风险分布
        risk_distribution = defaultdict(int)
        for result in recent_results:
            risk_distribution[result.risk_level] += 1

        # 威胁趋势（按时间分组）
        time_buckets = defaultdict(list)
        for result in threat_results:
            bucket = result.analysis_timestamp.strftime('%H:%M')
            time_buckets[bucket].append(result.final_threat_score)

        threat_trends = []
        for bucket, scores in sorted(time_buckets.items()):
            threat_trends.append({
                'time': bucket,
                'count': len(scores),
                'avg_score': statistics.mean(scores)
            })

        # IP威胁排名
        ip_threats = defaultdict(list)
        for result in threat_results:
            ip = result.log_entry.get('src_ip', '')
            if ip:
                ip_threats[ip].append(result.final_threat_score)

        top_ips = []
        for ip, scores in sorted(ip_threats.items(),
                               key=lambda x: statistics.mean(x[1]), reverse=True)[:10]:
            top_ips.append({
                'ip': ip,
                'threat_count': len(scores),
                'avg_score': statistics.mean(scores),
                'max_score': max(scores)
            })

        return {
            'time_window': time_window,
            'total_analyses': len(recent_results),
            'threat_count': len(threat_results),
            'threat_rate': len(threat_results) / len(recent_results) * 100,
            'avg_threat_score': statistics.mean([r.final_threat_score for r in recent_results]),
            'risk_distribution': dict(risk_distribution),
            'top_threat_ips': top_ips,
            'threat_trends': threat_trends,
            'active_patterns': len(self.threat_patterns)
        }

    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        total_analyses = self.performance_stats['total_analyses']
        if total_analyses == 0:
            return {
                'total_analyses': 0,
                'avg_processing_time': 0.0,
                'ai_usage_rate': 0.0,
                'ai_success_rate': 0.0
            }

        avg_processing_time = self.performance_stats['total_processing_time'] / total_analyses
        ai_usage_rate = self.performance_stats['ai_analyses'] / total_analyses * 100

        ai_success_rate = 0.0
        if self.performance_stats['ai_analyses'] > 0:
            ai_success_rate = (self.performance_stats['ai_analyses'] /
                             (self.performance_stats['ai_analyses'] + self.performance_stats['ai_failures'])) * 100

        return {
            'total_analyses': total_analyses,
            'avg_processing_time': avg_processing_time,
            'ai_usage_rate': ai_usage_rate,
            'ai_success_rate': ai_success_rate,
            'rule_only_rate': self.performance_stats['rule_only_analyses'] / total_analyses * 100,
            'cache_hit_rate': self.ai_analyzer.get_analyzer_status()['cache_status']['cache_size'] if self.ai_analyzer else 0
        }

    def export_analysis_results(self, output_file: str, time_window: int = 3600) -> bool:
        """导出分析结果"""
        try:
            cutoff_time = datetime.now() - timedelta(seconds=time_window)
            recent_results = [
                r for r in self.analysis_history
                if r.analysis_timestamp >= cutoff_time
            ]

            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'time_window': time_window,
                'total_results': len(recent_results),
                'performance_report': self.get_performance_report(),
                'threat_summary': self.get_threat_summary(time_window),
                'threat_patterns': {
                    key: asdict(pattern) for key, pattern in self.threat_patterns.items()
                },
                'results': [
                    {
                        'log_entry': result.log_entry,
                        'final_threat_score': result.final_threat_score,
                        'risk_level': result.risk_level,
                        'analysis_source': result.analysis_source,
                        'recommendations': result.recommendations,
                        'processing_time': result.processing_time,
                        'analysis_timestamp': result.analysis_timestamp.isoformat(),
                        'rule_matches_count': len(result.rule_matches),
                        'has_ai_analysis': result.ai_analysis is not None
                    }
                    for result in recent_results
                ]
            }

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"分析结果已导出到: {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"导出分析结果失败: {e}")
            return False

    def clear_history(self, older_than: int = 86400):
        """清理历史数据（默认清理24小时前的数据）"""
        cutoff_time = datetime.now() - timedelta(seconds=older_than)

        original_size = len(self.analysis_history)
        self.analysis_history = deque(
            [r for r in self.analysis_history if r.analysis_timestamp >= cutoff_time],
            maxlen=1000
        )

        # 清理旧的威胁模式
        old_patterns = []
        for key, pattern in self.threat_patterns.items():
            if pattern.last_seen < cutoff_time:
                old_patterns.append(key)

        for key in old_patterns:
            del self.threat_patterns[key]

        self.logger.info(f"已清理 {original_size - len(self.analysis_history)} 条历史记录和 {len(old_patterns)} 个威胁模式")

    def get_analysis_status(self) -> Dict[str, Any]:
        """获取分析器状态"""
        return {
            'rule_engine_status': {
                'total_rules': len(self.rule_engine.rules),
                'ai_enabled': self.rule_engine.enable_ai_analysis
            },
            'ai_analyzer_status': self.ai_analyzer.get_analyzer_status() if self.ai_analyzer else None,
            'performance_stats': self.get_performance_report(),
            'cache_info': {
                'analysis_history_size': len(self.analysis_history),
                'threat_patterns_count': len(self.threat_patterns),
                'ip_reputation_count': len(self.ip_reputation)
            }
        }