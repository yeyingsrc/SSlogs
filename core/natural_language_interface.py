#!/usr/bin/env python3
"""
自然语言查询接口
提供直观的自然语言查询功能，让用户可以用日常语言查询安全日志和分析结果
"""

import asyncio
import json
import logging
import re
from typing import Dict, List, Any, Optional, Tuple, AsyncGenerator
from datetime import datetime, timedelta
from dataclasses import dataclass
from pathlib import Path

from core.intelligent_log_analyzer import IntelligentLogAnalyzer
from core.ai_config_manager import get_ai_config_manager

@dataclass
class QueryIntent:
    """查询意图"""
    intent_type: str  # summary, threat_analysis, ip_investigation, pattern_search, etc.
    parameters: Dict[str, Any]
    confidence: float
    raw_query: str

@dataclass
class QueryResult:
    """查询结果"""
    query: str
    intent: QueryIntent
    answer: str
    data: Any
    processing_time: float
    timestamp: datetime
    sources: List[str]

class NaturalLanguageInterface:
    """自然语言查询接口"""

    def __init__(self, analyzer: IntelligentLogAnalyzer):
        self.analyzer = analyzer
        self.logger = logging.getLogger(__name__)
        self.config_manager = get_ai_config_manager()

        # 查询历史
        self.query_history = []
        self.query_patterns = self._load_query_patterns()

        # 意图识别关键词
        self.intent_keywords = {
            'summary': ['总结', '概况', '概览', '总体', '摘要', '情况'],
            'threat_analysis': ['威胁', '危险', '风险', '安全', '攻击'],
            'ip_investigation': ['IP', '地址', '来源', '访客'],
            'pattern_search': ['模式', '规律', '趋势', '行为'],
            'time_analysis': ['时间', '最近', '今天', '昨天', '小时', '分钟'],
            'rule_analysis': ['规则', '匹配', '检测', '触发'],
            'recommendation': ['建议', '措施', '应对', '解决方案'],
            'statistics': ['统计', '数量', '次数', '比例', '百分比'],
            'top_analysis': ['最多', '最高', '排名', '前列', '热门'],
            'comparison': ['对比', '比较', '差异', '变化'],
            'explanation': ['解释', '原因', '为什么', '如何']
        }

    def _load_query_patterns(self) -> Dict[str, List[str]]:
        """加载查询模式"""
        return {
            'summary_patterns': [
                r'最近.*?(情况|概况|总结)',
                r'总体.*?(安全|威胁)',
                r'当前.*?(状态|状况)',
                r'今天.*?(安全|威胁)',
                r'24小时.*?(总结|概览)'
            ],
            'threat_patterns': [
                r'有哪些.*?(威胁|风险|危险)',
                r'检测到.*?(攻击|入侵|威胁)',
                r'高危.*?(IP|请求|行为)',
                r'严重.*?(安全事件|威胁)',
                r'需要.*?(关注|处理)'
            ],
            'ip_patterns': [
                r'IP\s*([0-9.]+)',
                r'地址\s*([0-9.]+)',
                r'来源\s*([0-9.]+)',
                r'查询\s*([0-9.]+).*?IP',
                r'分析\s*([0-9.]+).*?行为'
            ],
            'time_patterns': [
                r'最近\s*(\d+)\s*(小时|分钟|天)',
                r'过去\s*(\d+)\s*(小时|分钟|天)',
                r'(\d+)\s*(小时|分钟|天)\s*前',
                r'今天.*?(威胁|攻击|事件)',
                r'昨天.*?(威胁|攻击|事件)'
            ],
            'top_patterns': [
                r'(最多|最高|最频繁).*?(IP|攻击|威胁)',
                r'排名前\s*(\d+).*?(IP|威胁)',
                r'热门.*?(IP|攻击|威胁)',
                r'TOP\s*(\d+).*?(IP|威胁)'
            ],
            'statistics_patterns': [
                r'多少.*?(攻击|威胁|请求)',
                r'统计.*?(攻击|威胁|请求)',
                r'数量.*?(攻击|威胁|请求)',
                r'比例.*?(攻击|威胁|请求)'
            ]
        }

    def parse_query_intent(self, query: str) -> QueryIntent:
        """解析查询意图"""
        query_lower = query.lower()
        best_intent = 'general'
        best_confidence = 0.0
        parameters = {}

        # 使用模式匹配识别意图
        for intent_type, patterns in self.query_patterns.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    confidence = 0.8  # 模式匹配的基础置信度
                    if confidence > best_confidence:
                        best_intent = intent_type
                        best_confidence = confidence

                    # 提取参数
                        if intent_type == 'ip_patterns':
                            ip_match = re.search(r'([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})', query)
                            if ip_match:
                                parameters['ip'] = ip_match.group(1)

                        elif intent_type == 'time_patterns':
                            time_match = re.search(r'(\d+)\s*(小时|分钟|天)', query_lower)
                            if time_match:
                                value = int(time_match.group(1))
                                unit = time_match.group(2)
                                if unit in ['小时', 'hour', 'h']:
                                    parameters['time_window'] = value * 3600
                                elif unit in ['分钟', 'minute', 'm']:
                                    parameters['time_window'] = value * 60
                                elif unit in ['天', 'day', 'd']:
                                    parameters['time_window'] = value * 86400

                        elif intent_type == 'top_patterns':
                            top_match = re.search(r'(\d+)', query)
                            if top_match:
                                parameters['limit'] = int(top_match.group(1))

        # 使用关键词匹配补充意图识别
        for intent_type, keywords in self.intent_keywords.items():
            keyword_matches = sum(1 for keyword in keywords if keyword in query_lower)
            if keyword_matches > 0:
                confidence = min(keyword_matches * 0.2, 0.9)
                if confidence > best_confidence:
                    best_intent = intent_type
                    best_confidence = confidence

        # 特殊情况处理
        if '为什么' in query_lower or '原因' in query_lower or '解释' in query_lower:
            best_intent = 'explanation'
            best_confidence = 0.9

        return QueryIntent(
            intent_type=best_intent,
            parameters=parameters,
            confidence=best_confidence,
            raw_query=query
        )

    def process_query(self, query: str) -> QueryResult:
        """处理自然语言查询"""
        start_time = datetime.now()

        try:
            # 解析查询意图
            intent = self.parse_query_intent(query)

            # 根据意图处理查询
            if intent.intent_type == 'summary':
                answer, data, sources = self._handle_summary_query(intent)
            elif intent.intent_type == 'threat_analysis':
                answer, data, sources = self._handle_threat_analysis_query(intent)
            elif intent.intent_type == 'ip_investigation':
                answer, data, sources = self._handle_ip_investigation_query(intent)
            elif intent.intent_type == 'pattern_search':
                answer, data, sources = self._handle_pattern_search_query(intent)
            elif intent.intent_type == 'time_analysis':
                answer, data, sources = self._handle_time_analysis_query(intent)
            elif intent.intent_type == 'rule_analysis':
                answer, data, sources = self._handle_rule_analysis_query(intent)
            elif intent.intent_type == 'recommendation':
                answer, data, sources = self._handle_recommendation_query(intent)
            elif intent.intent_type == 'statistics':
                answer, data, sources = self._handle_statistics_query(intent)
            elif intent.intent_type == 'top_analysis':
                answer, data, sources = self._handle_top_analysis_query(intent)
            elif intent.intent_type == 'explanation':
                answer, data, sources = self._handle_explanation_query(intent)
            else:
                answer, data, sources = self._handle_general_query(intent)

            processing_time = (datetime.now() - start_time).total_seconds()

            # 记录查询历史
            result = QueryResult(
                query=query,
                intent=intent,
                answer=answer,
                data=data,
                processing_time=processing_time,
                timestamp=start_time,
                sources=sources
            )
            self.query_history.append(result)

            return result

        except Exception as e:
            self.logger.error(f"处理查询失败: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()

            return QueryResult(
                query=query,
                intent=QueryIntent('error', {}, 0.0, query),
                answer=f"查询处理失败: {str(e)}",
                data=None,
                processing_time=processing_time,
                timestamp=start_time,
                sources=[]
            )

    async def process_query_async(self, query: str) -> QueryResult:
        """异步处理自然语言查询"""
        start_time = datetime.now()

        try:
            # 解析查询意图
            intent = self.parse_query_intent(query)

            # 根据意图处理查询
            if intent.intent_type == 'summary':
                answer, data, sources = await self._handle_summary_query_async(intent)
            elif intent.intent_type == 'explanation':
                answer, data, sources = await self._handle_explanation_query_async(intent)
            else:
                # 其他查询类型暂时使用同步处理
                result = self.process_query(query)
                return result

            processing_time = (datetime.now() - start_time).total_seconds()

            return QueryResult(
                query=query,
                intent=intent,
                answer=answer,
                data=data,
                processing_time=processing_time,
                timestamp=start_time,
                sources=sources
            )

        except Exception as e:
            self.logger.error(f"异步处理查询失败: {e}")
            processing_time = (datetime.now() - start_time).total_seconds()

            return QueryResult(
                query=query,
                intent=QueryIntent('error', {}, 0.0, query),
                answer=f"查询处理失败: {str(e)}",
                data=None,
                processing_time=processing_time,
                timestamp=start_time,
                sources=[]
            )

    def _handle_summary_query(self, intent: QueryIntent) -> Tuple[str, Any, List[str]]:
        """处理摘要查询"""
        time_window = intent.parameters.get('time_window', 3600)
        threat_summary = self.analyzer.get_threat_summary(time_window)

        answer = f"""📊 **安全威胁摘要（最近{time_window//3600}小时）**

**总体情况：**
- 总分析数：{threat_summary['total_analyses']}
- 检测到威胁：{threat_summary['threat_count']} 次
- 威胁检出率：{threat_summary['threat_rate']:.1f}%
- 平均威胁评分：{threat_summary['avg_threat_score']:.2f}

**风险分布：**
"""
        for risk_level, count in threat_summary['risk_distribution'].items():
            answer += f"- {risk_level}级：{count} 次\n"

        if threat_summary['top_threat_ips']:
            answer += "\n**高风险IP地址：**\n"
            for i, ip_info in enumerate(threat_summary['top_threat_ips'][:5], 1):
                answer += f"{i}. {ip_info['ip']} - 威胁{ip_info['threat_count']}次，平均评分{ip_info['avg_score']:.1f}\n"

        if threat_summary['threat_trends']:
            answer += "\n**威胁趋势：**\n"
            for trend in threat_summary['threat_trends'][-5:]:
                answer += f"- {trend['time']}：{trend['count']}次威胁，平均评分{trend['avg_score']:.1f}\n"

        answer += f"\n**活跃威胁模式：**{threat_summary['active_patterns']} 个"

        return answer, threat_summary, ['threat_summary']

    def _handle_threat_analysis_query(self, intent: QueryIntent) -> Tuple[str, Any, List[str]]:
        """处理威胁分析查询"""
        time_window = intent.parameters.get('time_window', 3600)
        threat_summary = self.analyzer.get_threat_summary(time_window)

        high_threat_logs = [
            r for r in self.analyzer.analysis_history
            if (r.analysis_timestamp >= datetime.now() - timedelta(seconds=time_window) and
                r.final_threat_score >= 6.0)
        ]

        answer = f"🚨 **威胁分析报告（最近{time_window//3600}小时）**\n\n"

        if high_threat_logs:
            answer += f"检测到 {len(high_threat_logs)} 个高风险威胁事件：\n\n"

            # 按威胁评分排序
            high_threat_logs.sort(key=lambda x: x.final_threat_score, reverse=True)

            for i, result in enumerate(high_threat_logs[:10], 1):
                log_entry = result.log_entry
                answer += f"{i}. **威胁评分：{result.final_threat_score:.1f} ({result.risk_level}级)**\n"
                answer += f"   时间：{log_entry.get('timestamp', 'N/A')}\n"
                answer += f"   来源IP：{log_entry.get('src_ip', 'N/A')}\n"
                answer += f"   请求路径：{log_entry.get('request_path', 'N/A')}\n"
                answer += f"   分析来源：{result.analysis_source}\n"
                if result.recommendations:
                    answer += f"   建议：{result.recommendations[0]}\n"
                answer += "\n"
        else:
            answer += "在指定时间窗口内未检测到高风险威胁事件。\n"

        # 威胁模式分析
        if self.analyzer.threat_patterns:
            answer += "\n**活跃威胁模式：**\n"
            top_patterns = sorted(self.analyzer.threat_patterns.values(),
                                key=lambda x: x.frequency, reverse=True)[:5]
            for pattern in top_patterns:
                answer += f"- {pattern.pattern_name}：{pattern.frequency} 次，严重级别：{pattern.severity}\n"

        return answer, {'high_threat_logs': high_threat_logs, 'patterns': self.analyzer.threat_patterns}, ['analysis_history', 'threat_patterns']

    def _handle_ip_investigation_query(self, QueryIntent) -> Tuple[str, Any, List[str]]:
        """处理IP调查查询"""
        ip_address = intent.parameters.get('ip', '')
        if not ip_address:
            return "请提供要调查的IP地址。", None, []

        # 查找该IP的相关记录
        ip_logs = [
            r for r in self.analyzer.analysis_history
            if r.log_entry.get('src_ip') == ip_address
        ]

        if not ip_logs:
            return f"未找到IP地址 {ip_address} 的相关记录。", None, []

        # 统计信息
        threat_logs = [r for r in ip_logs if r.final_threat_score >= 5.0]
        total_requests = len(ip_logs)
        threat_count = len(threat_logs)

        answer = f"🔍 **IP地址调查报告：{ip_address}**\n\n"
        answer += f"**基本信息：**\n"
        answer += f"- 总请求数：{total_requests}\n"
        answer += f"- 威胁请求数：{threat_count}\n"
        answer += f"- 威胁率：{threat_count/total_requests*100:.1f}%\n"
        answer += f"- IP声誉评分：{self.analyzer.ip_reputation.get(ip_address, 0)}\n\n"

        if threat_logs:
            answer += f"**威胁事件详情（最近10条）：**\n"
            threat_logs.sort(key=lambda x: x.final_threat_score, reverse=True)

            for result in threat_logs[:10]:
                log_entry = result.log_entry
                answer += f"- 评分：{result.final_threat_score:.1f} ({result.risk_level})\n"
                answer += f"  时间：{log_entry.get('timestamp', 'N/A')}\n"
                answer += f"  路径：{log_entry.get('request_path', 'N/A')}\n"
                answer += f"  用户代理：{log_entry.get('user_agent', 'N/A')[:50]}...\n\n"

        # 分析该IP的行为模式
        user_agents = set()
        paths = set()
        for result in ip_logs:
            log_entry = result.log_entry
            if log_entry.get('user_agent'):
                user_agents.add(log_entry['user_agent'])
            if log_entry.get('request_path'):
                paths.add(log_entry['request_path'])

        answer += f"**行为模式分析：**\n"
        answer += f"- 不同用户代理：{len(user_agents)} 个\n"
        answer += f"- 不同访问路径：{len(paths)} 个\n"

        if user_agents:
            answer += f"- 主要用户代理：{list(user_agents)[0][:80]}...\n"

        # 威胁建议
        if threat_count > total_requests * 0.5:
            answer += "\n⚠️ **威胁评估：高风险IP**\n"
            answer += "建议：立即封禁该IP地址，并加强监控。\n"
        elif threat_count > 0:
            answer += "\n⚠️ **威胁评估：中风险IP**\n"
            answer += "建议：密切监控该IP的活动，考虑限制访问频率。\n"
        else:
            answer += "\n✅ **威胁评估：低风险IP**\n"
            answer += "该IP目前表现正常，无需特殊处理。\n"

        return answer, {
            'ip_address': ip_address,
            'total_requests': total_requests,
            'threat_count': threat_count,
            'logs': ip_logs,
            'reputation_score': self.analyzer.ip_reputation.get(ip_address, 0)
        }, ['analysis_history', 'ip_reputation']

    def _handle_pattern_search_query(self, QueryIntent) -> Tuple[str, Any, List[str]]:
        """处理模式搜索查询"""
        # 查找活跃的威胁模式
        if self.analyzer.threat_patterns:
            patterns = sorted(self.analyzer.threat_patterns.values(),
                            key=lambda x: x.frequency, reverse=True)

            answer = f"🔎 **威胁模式搜索结果**\n\n"
            answer += f"发现 {len(patterns)} 个威胁模式：\n\n"

            for i, pattern in enumerate(patterns[:10], 1):
                answer += f"{i}. **{pattern.pattern_name}**\n"
                answer += f"   描述：{pattern.description}\n"
                answer += f"   出现频率：{pattern.frequency} 次\n"
                answer += f"   严重级别：{pattern.severity}\n"
                answer += f"   首次发现：{pattern.first_seen.strftime('%Y-%m-%d %H:%M')}\n"
                answer += f"   最后发现：{pattern.last_seen.strftime('%Y-%m-%d %H:%M')}\n"
                answer += f"   影响IP数量：{len(pattern.affected_ips)}\n\n"

                if pattern.affected_ips:
                    answer += f"   主要来源IP：{', '.join(pattern.affected_ips[:5])}\n\n"
        else:
            answer = "🔎 **威胁模式搜索结果**\n\n当前未检测到特定的威胁模式。"

        return answer, {'patterns': patterns}, ['threat_patterns']

    def _handle_time_analysis_query(self, QueryIntent) -> Tuple[str, Any, List[str]]:
        """处理时间分析查询"""
        time_window = intent.parameters.get('time_window', 3600)
        threat_summary = self.analyzer.get_threat_summary(time_window)

        answer = f"⏰ **时间范围分析（最近{time_window//3600}小时）**\n\n"

        if threat_summary['threat_trends']:
            answer += "**威胁时间分布：**\n"
            for trend in threat_summary['threat_trends']:
                answer += f"- {trend['time']}：{trend['count']} 次威胁事件\n"

            # 分析高峰时段
            peak_time = max(threat_summary['threat_trends'], key=lambda x: x['count'])
            answer += f"\n**威胁高峰时段：**{peak_time['time']}（{peak_time['count']} 次）\n"

            # 分析趋势
            if len(threat_summary['threat_trends']) > 1:
                recent_avg = statistics.mean([t['count'] for t in threat_summary['threat_trends'][-3:]])
                earlier_avg = statistics.mean([t['count'] for t in threat_summary['threat_trends'][:-3]])

                if recent_avg > earlier_avg * 1.2:
                    answer += "📈 **趋势：威胁活动呈上升趋势**\n"
                elif recent_avg < earlier_avg * 0.8:
                    answer += "📉 **趋势：威胁活动呈下降趋势**\n"
                else:
                    answer += "➡️ **趋势：威胁活动相对稳定**\n"
        else:
            answer += "在指定时间范围内没有检测到威胁事件。\n"

        return answer, threat_summary, ['analysis_history']

    def _handle_rule_analysis_query(self, QueryIntent) -> Tuple[str, Any, List[str]]:
        """处理规则分析查询"""
        rule_stats = self.analyzer.rule_engine.get_rule_statistics()

        answer = f"⚙️ **规则引擎分析报告**\n\n"
        answer += f"**规则概况：**\n"
        answer += f"- 总规则数：{rule_stats['total_rules']}\n"
        answer += f"- 总匹配次数：{rule_stats['total_matches']}\n"
        answer += f"- 平均每规则匹配：{rule_stats['total_matches']/rule_stats['total_rules']:.1f} 次\n\n"

        if rule_stats['most_triggered_rules']:
            answer += "**最活跃规则（前10名）：**\n"
            for i, (rule_id, count) in enumerate(rule_stats['most_triggered_rules'][:10], 1):
                answer += f"{i}. 规则ID：{rule_id} - 触发次数：{count}\n"

        # 规则性能分析
        recent_results = list(self.analyzer.analysis_history)[-100:]
        if recent_results:
            rule_performance = defaultdict(list)
            for result in recent_results:
                for match in result.rule_matches:
                    rule_performance[match['rule']['name']].append(result.final_threat_score)

            answer += f"\n**规则性能（最近100次分析）：**\n"
            for rule_name, scores in sorted(rule_performance.items(),
                                          key=lambda x: statistics.mean(x[1]), reverse=True)[:5]:
                avg_score = statistics.mean(scores)
                answer += f"- {rule_name}：平均威胁评分 {avg_score:.2f}\n"

        return answer, rule_stats, ['rule_engine']

    def _handle_recommendation_query(self, QueryIntent) -> Tuple[str, Any, List[str]]:
        """处理建议查询"""
        # 获取最近的高威胁事件
        recent_threats = [
            r for r in self.analyzer.analysis_history[-50:]
            if r.final_threat_score >= 6.0
        ]

        if not recent_threats:
            return "✅ **安全建议**\n\n当前系统安全状况良好，未检测到需要特别关注的高风险事件。\n\n**常规安全建议：**\n1. 定期更新安全规则\n2. 监控异常流量模式\n3. 定期审查日志文件", None, []

        # 收集建议
        all_recommendations = []
        for result in recent_threats:
            all_recommendations.extend(result.recommendations)

        # 统计建议频率
        recommendation_freq = defaultdict(int)
        for rec in all_recommendations:
            recommendation_freq[rec] += 1

        answer = f"💡 **智能安全建议**（基于最近50次高风险事件）\n\n"

        if recommendation_freq:
            answer += "**主要安全建议（按重要性排序）：**\n"
            sorted_recommendations = sorted(recommendation_freq.items(),
                                            key=lambda x: x[1], reverse=True)[:10]

            for i, (recommendation, count) in enumerate(sorted_recommendations, 1):
                answer += f"{i}. {recommendation}（出现 {count} 次）\n"

        # 威胁类型分析
        threat_types = defaultdict(int)
        for result in recent_threats:
            if result.ai_analysis and result.ai_analysis.threat_analysis.attack_types:
                for attack_type in result.ai_analysis.threat_analysis.attack_types:
                    threat_types[attack_type] += 1

        if threat_types:
            answer += f"\n**主要威胁类型：**\n"
            for threat_type, count in sorted(threat_types.items(), key=lambda x: x[1], reverse=True)[:5]:
                answer += f"- {threat_type}：{count} 次\n"

        answer += f"\n**总体建议：**\n"
        if len(recent_threats) > 20:
            answer += "- 系统面临较多威胁，建议立即采取防护措施\n"
        elif len(recent_threats) > 10:
            answer += "- 系统存在一定安全风险，建议加强监控\n"
        else:
            answer += "- 系统安全状况相对稳定，继续保持现有防护措施\n"

        return answer, {
            'recommendations': list(set(all_recommendations)),
            'threat_types': dict(threat_types),
            'threat_count': len(recent_threats)
        }, ['analysis_history']

    def _handle_statistics_query(self, QueryIntent) -> Tuple[str, Any, List[str]]:
        """处理统计查询"""
        performance_report = self.analyzer.get_performance_report()

        answer = f"📊 **系统性能统计报告**\n\n"
        answer += f"**处理统计：**\n"
        answer += f"- 总分析数：{performance_report['total_analyses']}\n"
        answer += f"- 平均处理时间：{performance_report['avg_processing_time']:.3f} 秒\n"
        answer += f"- AI使用率：{performance_report['ai_usage_rate']:.1f}%\n"
        answer += f"- AI成功率：{performance_report['ai_success_rate']:.1f}%\n"
        answer += f"- 纯规则分析率：{performance_report['rule_only_rate']:.1f}%\n\n"

        # 分析缓存效率
        if self.ai_analyzer:
            cache_status = self.ai_analyzer.get_analyzer_status()['cache_status']
            answer += f"**缓存效率：**\n"
            answer += f"- 缓存大小：{cache_status['cache_size']} 条记录\n"
            answer += f"- 缓存TTL：{cache_status['cache_ttl']} 秒\n\n"

        # 威胁检测统计
        threat_summary = self.analyzer.get_threat_summary(3600)
        answer += f"**威胁检测统计（最近1小时）：**\n"
        answer += f"- 总分析数：{threat_summary['total_analyses']}\n"
        answer += f"- 威胁检测数：{threat_summary['threat_count']}\n"
        answer += f"- 威胁检出率：{threat_summary['threat_rate']:.1f}%\n"
        answer += f"- 平均威胁评分：{threat_summary['avg_threat_score']:.2f}\n"

        return answer, {
            'performance': performance_report,
            'threat_summary': threat_summary
        }, ['analyzer_status', 'analysis_history']

    def _handle_top_analysis_query(self, QueryIntent) -> Tuple[str, Any, List[str]]:
        """处理热门分析查询"""
        limit = intent.parameters.get('limit', 10)

        # 获取高风险IP
        threat_summary = self.analyzer.get_threat_summary(3600)
        top_ips = threat_summary.get('top_threat_ips', [])

        answer = f"🏆 **热门威胁分析（前{limit}名）**\n\n"

        if top_ips:
            answer += f"**高风险IP地址排名：**\n"
            for i, ip_info in enumerate(top_ips[:limit], 1):
                answer += f"{i}. {ip_info['ip']}\n"
                answer += f"   威胁次数：{ip_info['threat_count']}\n"
                answer += f"   平均评分：{ip_info['avg_score']:.2f}\n"
                answer += f"   最高评分：{ip_info['max_score']:.2f}\n\n"

        # 获取热门威胁模式
        if self.analyzer.threat_patterns:
            top_patterns = sorted(self.analyzer.threat_patterns.values(),
                                key=lambda x: x.frequency, reverse=True)

            answer += f"**热门威胁模式：**\n"
            for i, pattern in enumerate(top_patterns[:limit], 1):
                answer += f"{i}. {pattern.pattern_name}\n"
                answer += f"   出现频率：{pattern.frequency}\n"
                answer += f"   严重级别：{pattern.severity}\n"
                answer += f"   影响IP数：{len(pattern.affected_ips)}\n\n"

        # 获取最高威胁评分的日志
        high_score_logs = sorted(self.analyzer.analysis_history,
                                key=lambda x: x.final_threat_score, reverse=True)

        answer += f"**最高威胁评分事件：**\n"
        for i, result in enumerate(high_score_logs[:limit], 1):
            log_entry = result.log_entry
            answer += f"{i}. 评分：{result.final_threat_score:.1f}\n"
            answer += f"   时间：{log_entry.get('timestamp', 'N/A')}\n"
            answer += f"   IP：{log_entry.get('src_ip', 'N/A')}\n"
            answer += f"   路径：{log_entry.get('request_path', 'N/A')}\n\n"

        return answer, {
            'top_ips': top_ips[:limit],
            'top_patterns': top_patterns[:limit],
            'top_logs': high_score_logs[:limit]
        }, ['analysis_history', 'threat_patterns']

    def _handle_explanation_query(self, intent: QueryIntent) -> Tuple[str, Any, List[str]]:
        """处理解释查询"""
        # 这里需要AI分析器来提供解释
        if not self.analyzer.ai_analyzer:
            return "❌ AI分析功能未启用，无法提供详细解释。", None, []

        # 使用AI分析器进行解释
        recent_results = list(self.analyzer.analysis_history)[-10:]

        if recent_results:
            # 选择最高威胁评分的结果进行解释
            highest_threat = max(recent_results, key=lambda x: x.final_threat_score)

            if highest_threat.rule_matches:
                rule_name = highest_threat.rule_matches[0]['rule']['name']
                explanation = self.analyzer.ai_analyzer.explain_detection(
                    rule_name, highest_threat.log_entry, highest_threat.final_threat_score
                )

                if explanation:
                    answer = f"🤖 **AI智能解释**\n\n"
                    answer += f"基于规则 **{rule_name}** 的检测分析：\n\n"
                    answer += explanation

                    return answer, {
                        'explanation': explanation,
                        'rule_name': rule_name,
                        'log_entry': highest_threat.log_entry,
                        'threat_score': highest_threat.final_threat_score
                    }, ['ai_analysis']

        return "❌ 找不到合适的日志条目进行解释。", None, []

    async def _handle_summary_query_async(self, intent: QueryIntent) -> Tuple[str, Any, List[str]]:
        """异步处理摘要查询"""
        # 摘要查询不需要AI，直接返回同步结果
        return self._handle_summary_query(intent)

    async def _handle_explanation_query_async(self, intent: QueryIntent) -> Tuple[str, Any, List[str]]:
        """异步处理解释查询"""
        if not self.analyzer.ai_analyzer:
            return "❌ AI分析功能未启用，无法提供详细解释。", None, []

        recent_results = list(self.analyzer.analysis_history)[-10:]
        if recent_results:
            highest_threat = max(recent_results, key=lambda x: x.final_threat_score)

            if highest_threat.rule_matches:
                rule_name = highest_threat.rule_matches[0]['rule']['name']
                explanation = await self.analyzer.ai_analyzer.analyzer.explain_detection(
                    rule_name, highest_threat.log_entry, highest_threat.final_threat_score
                )

                if explanation:
                    answer = f"🤖 **AI智能解释**\n\n"
                    answer += f"基于规则 **{rule_name}** 的检测分析：\n\n"
                    answer += explanation

                    return answer, {
                        'explanation': explanation,
                        'rule_name': rule_name,
                        'log_entry': highest_threat.log_entry,
                        'threat_score': highest_threat.final_threat_score
                    }, ['ai_analysis']

        return "❌ 找不到合适的日志条目进行解释。", None, []

    def _handle_general_query(self, intent: QueryIntent) -> Tuple[str, Any, List[str]]:
        """处理通用查询"""
        answer = f"🤖 **AI助手**\n\n"
        answer += f"我理解您想查询：{intent.raw_query}\n\n"

        if self.analyzer.ai_analyzer:
            # 使用AI分析器处理通用查询
            recent_logs = [
                r.log_entry for r in self.analyzer.analysis_history[-20:]
            ]

            ai_response = self.analyzer.ai_analyzer.natural_language_query(intent.raw_query, recent_logs)

            if ai_response:
                answer += ai_response
                return answer, {'ai_response': ai_response}, ['ai_analysis']

        answer += "我可以帮您进行以下类型的查询：\n\n"
        answer += "📊 **安全概览**：\n"
        answer += "- 最近安全情况如何？\n"
        answer += "- 今天有什么威胁事件？\n"
        answer += "- 24小时安全总结\n\n"

        answer += "🔍 **威胁分析**：\n"
        answer += "- 检测到哪些威胁？\n"
        answer += "- 有什么高风险IP？\n"
        answer += "- 威胁模式分析\n\n"

        answer += "🔎 **IP调查**：\n"
        answer += "- 分析IP地址 192.168.1.100\n"
        answer += "- 查询来源IP的行为\n\n"

        answer += "📈 **统计分析**：\n"
        answer += "- 威胁事件统计\n"
        answer += "- 规则匹配统计\n"
        answer += "- 性能指标分析\n\n"

        answer += "💡 **建议查询**：\n"
        answer += "- 有什么安全建议？\n"
        answer += "- 应该如何应对？\n"

        return answer, None, []

    def get_query_history(self, limit: int = 50) -> List[QueryResult]:
        """获取查询历史"""
        return self.query_history[-limit:]

    def clear_query_history(self):
        """清空查询历史"""
        self.query_history.clear()

    def get_query_statistics(self) -> Dict[str, Any]:
        """获取查询统计信息"""
        if not self.query_history:
            return {
                'total_queries': 0,
                'avg_processing_time': 0.0,
                'intent_distribution': {}
            }

        total_queries = len(self.query_history)
        avg_processing_time = sum(q.processing_time for q in self.query_history) / total_queries

        intent_distribution = defaultdict(int)
        for query in self.query_history:
            intent_distribution[query.intent.intent_type] += 1

        return {
            'total_queries': total_queries,
            'avg_processing_time': avg_processing_time,
            'intent_distribution': dict(intent_distribution),
            'ai_usage_rate': sum(1 for q in self.query_history if 'ai_analysis' in q.sources) / total_queries * 100
        }