import json
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from functools import lru_cache

logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir = Path(__file__).parent / "templates"
        self.templates_dir.mkdir(exist_ok=True)
        self._stats_cache = {}

    def generate_report(self, matched_logs: List[Dict[str, Any]], ai_results: List[str],
                       report_type: str = "html", internal_ips: Optional[Dict[str, int]] = None,
                       external_ip_details: Optional[List[Dict[str, Any]]] = None,
                       server_ip: str = "unknown") -> str:
        """生成日志分析报告"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"log_analysis_report_{timestamp}.{report_type}"
            filepath = self.output_dir / filename

            internal_ips = internal_ips or {}
            external_ip_details = external_ip_details or []
            
            content = self._build_report_content(
                matched_logs, ai_results, report_type, 
                internal_ips, external_ip_details, server_ip
            )

            filepath.write_text(content, encoding="utf-8")
            logger.info(f"报告已生成: {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"生成报告失败: {e}")
            raise

    def _build_report_content(self, matched_logs: List[Dict[str, Any]], ai_results: List[str], 
                             report_type: str, internal_ips: Dict[str, int], 
                             external_ip_details: List[Dict[str, Any]], server_ip: str) -> str:
        """构建报告内容"""
        report_data = self._prepare_report_data(matched_logs, ai_results, internal_ips, external_ip_details, server_ip)
        
        if report_type == "html":
            return self._build_html_content(report_data)
        elif report_type == "markdown":
            return self._build_markdown_content(report_data)
        elif report_type == "json":
            return self._build_json_content(report_data)
        else:
            raise ValueError(f"不支持的报告类型: {report_type}")

    def _build_html_content(self, report_data: Dict[str, Any]) -> str:
        """构建HTML格式报告 - 优化版本"""
        try:
            css_content = self._load_css_styles()
            
            # 构建HTML内容的各个部分
            header = self._build_html_header(report_data['metadata'], css_content)
            stats_section = self._build_stats_section(report_data['metadata'])
            attack_types_section = self._build_attack_types_section(report_data['metadata']['attack_type_stats'])
            ip_statistics_section = self._build_ip_statistics_section(report_data['ip_statistics'])
            security_events_section = self._build_security_events_section(report_data['security_events'])
            footer = self._build_html_footer()
            
            # 拼接所有部分
            html_parts = [header, stats_section, attack_types_section, ip_statistics_section, security_events_section, footer]
            return ''.join(html_parts)
        except Exception as e:
            logger.error(f"构建HTML内容失败: {e}")
            raise

    def _load_css_styles(self) -> str:
        """加载CSS样式"""
        css_file = self.templates_dir / "styles.css"
        if css_file.exists():
            return css_file.read_text(encoding='utf-8')
        else:
            logger.warning("CSS文件不存在，使用默认样式")
            return self._get_default_css()

    def _get_default_css(self) -> str:
        """获取默认CSS样式"""
        return """
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
        .header h1 { margin: 0; font-size: 2.5em; }
        .header p { margin: 5px 0; opacity: 0.9; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; margin-bottom: 30px; }
        .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-left: 4px solid #667eea; }
        .stat-number { font-size: 2em; font-weight: bold; color: #333; }
        .stat-label { color: #666; font-size: 0.9em; text-transform: uppercase; letter-spacing: 1px; }
        .severity-high { border-left-color: #e74c3c; }
        .severity-medium { border-left-color: #f39c12; }
        .severity-low { border-left-color: #f1c40f; }
        .section { background: white; margin: 20px 0; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .section h2 { color: #333; border-bottom: 2px solid #667eea; padding-bottom: 10px; }
        .table-responsive { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; margin: 15px 0; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f8f9fa; font-weight: 600; color: #333; }
        tr:hover { background-color: #f8f9fa; }
        .issue { border: 1px solid #e0e0e0; margin: 15px 0; padding: 20px; border-radius: 8px; background: #fafafa; }
        .issue-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; }
        .issue-title { font-size: 1.3em; font-weight: bold; color: #333; }
        .severity-badge { padding: 4px 12px; border-radius: 20px; font-size: 0.8em; font-weight: bold; text-transform: uppercase; }
        .severity-badge.high { background-color: #e74c3c; color: white; }
        .severity-badge.medium { background-color: #f39c12; color: white; }
        .severity-badge.low { background-color: #f1c40f; color: #333; }
        .issue-details { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 15px; }
        .detail-item { }
        .detail-label { font-weight: bold; color: #555; }
        .detail-value { color: #333; word-break: break-all; }
        .ai-analysis { background: #e8f4fd; padding: 15px; border-radius: 5px; border-left: 4px solid #2196f3; }
        .ai-analysis h4 { margin-top: 0; color: #1976d2; }
        .ai-analysis pre { background: white; padding: 10px; border-radius: 3px; white-space: pre-wrap; word-wrap: break-word; }
        .no-data { text-align: center; color: #666; font-style: italic; padding: 20px; }
        """

    def _build_html_header(self, metadata: Dict[str, Any], css_content: str) -> str:
        """构建HTML头部"""
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset='UTF-8'>
    <title>日志分析报告 - {metadata['generated_at']}</title>
    <style>{css_content}</style>
</head>
<body>
    <div class='container'>
        <div class='header'>
            <h1>🔍 日志分析报告</h1>
            <p>📅 生成时间: {metadata['generated_at']}</p>
            <p>🎯 目标服务器: {metadata['server_ip']}</p>
        </div>"""

    def _build_stats_section(self, metadata: Dict[str, Any]) -> str:
        """构建统计信息部分"""
        severity_stats = metadata['severity_stats']
        return f"""
        <div class='stats-grid'>
            <div class='stat-card'>
                <div class='stat-number'>{metadata['total_events']}</div>
                <div class='stat-label'>安全事件总数</div>
            </div>
            <div class='stat-card severity-high'>
                <div class='stat-number'>{severity_stats.get('high', 0)}</div>
                <div class='stat-label'>高危事件</div>
            </div>
            <div class='stat-card severity-medium'>
                <div class='stat-number'>{severity_stats.get('medium', 0)}</div>
                <div class='stat-label'>中危事件</div>
            </div>
            <div class='stat-card severity-low'>
                <div class='stat-number'>{severity_stats.get('low', 0)}</div>
                <div class='stat-label'>低危事件</div>
            </div>
        </div>"""

    def _build_attack_types_section(self, attack_type_stats: List[Dict[str, Any]]) -> str:
        """构建攻击类型TOP10部分"""
        table_rows = ""
        if attack_type_stats:
            total_attacks = sum(stat['count'] for stat in attack_type_stats)
            for i, stat in enumerate(attack_type_stats[:10], 1):
                percentage = (stat['count'] / total_attacks * 100) if total_attacks > 0 else 0
                table_rows += f"""
                        <tr>
                            <td>{i}</td>
                            <td>{stat['type']}</td>
                            <td>{stat['count']}</td>
                            <td>{percentage:.1f}%</td>
                            <td><span class='severity-badge {stat['max_severity']}'>{stat['max_severity']}</span></td>
                        </tr>"""
        else:
            table_rows = "<tr><td colspan='5' class='no-data'>暂无攻击事件</td></tr>"

        return f"""
        <div class='section'>
            <h2>🎯 攻击类型TOP10</h2>
            <div class='table-responsive'>
                <table>
                    <thead>
                        <tr>
                            <th>排名</th>
                            <th>攻击类型</th>
                            <th>事件数量</th>
                            <th>占比</th>
                            <th>最高风险级别</th>
                        </tr>
                    </thead>
                    <tbody>{table_rows}</tbody>
                </table>
            </div>
        </div>"""

    def _build_ip_statistics_section(self, ip_stats: Dict[str, Any]) -> str:
        """构建IP统计部分"""
        external_rows = self._build_external_ip_rows(ip_stats['external_ip_details'])
        internal_rows = self._build_internal_ip_rows(ip_stats['internal_ips'])
        
        return f"""
        <div class='section'>
            <h2>📊 IP访问统计</h2>
            
            <h3>🌍 外网IP访问排名</h3>
            <div class='table-responsive'>
                <table>
                    <thead>
                        <tr>
                            <th>IP地址</th>
                            <th>访问次数</th>
                            <th>地理位置</th>
                            <th>风险等级</th>
                        </tr>
                    </thead>
                    <tbody>{external_rows}</tbody>
                </table>
            </div>

            <h3>🏠 内网IP访问排名</h3>
            <div class='table-responsive'>
                <table>
                    <thead>
                        <tr>
                            <th>IP地址</th>
                            <th>访问次数</th>
                            <th>访问占比</th>
                        </tr>
                    </thead>
                    <tbody>{internal_rows}</tbody>
                </table>
            </div>
        </div>"""

    def _build_external_ip_rows(self, external_ip_details: List[Dict[str, Any]]) -> str:
        """构建外网IP表格行"""
        if not external_ip_details:
            return "<tr><td colspan='4' class='no-data'>无外网IP访问记录</td></tr>"
        
        rows = ""
        for ip_info in sorted(external_ip_details, key=lambda x: x['count'], reverse=True):
            risk_level = self._assess_ip_risk(ip_info['count'])
            rows += f"""
                        <tr>
                            <td>{ip_info['ip']}</td>
                            <td>{ip_info['count']}</td>
                            <td>{ip_info['location']}</td>
                            <td><span class='severity-badge {risk_level.lower()}'>{risk_level}</span></td>
                        </tr>"""
        return rows

    def _build_internal_ip_rows(self, internal_ips: Dict[str, int]) -> str:
        """构建内网IP表格行"""
        if not internal_ips:
            return "<tr><td colspan='3' class='no-data'>无内网IP访问记录</td></tr>"
        
        total_internal = sum(internal_ips.values())
        rows = ""
        for ip, count in sorted(internal_ips.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_internal * 100) if total_internal > 0 else 0
            rows += f"""
                        <tr>
                            <td>{ip}</td>
                            <td>{count}</td>
                            <td>{percentage:.1f}%</td>
                        </tr>"""
        return rows

    def _build_security_events_section(self, events: List[Dict[str, Any]]) -> str:
        """构建安全事件详情部分"""
        if not events:
            return """
        <div class='section'>
            <h2>🚨 安全事件详情</h2>
            <div class='no-data'>暂无安全事件</div>
        </div>"""
        
        events_html = ""
        for event in events:
            events_html += self._build_single_event_html(event)
        
        return f"""
        <div class='section'>
            <h2>🚨 安全事件详情</h2>
            {events_html}
        </div>"""

    def _build_single_event_html(self, event: Dict[str, Any]) -> str:
        """构建单个安全事件的HTML"""
        rule = event['rule']
        log_entry = event['log_entry']
        ai_analysis = event['ai_analysis']
        severity = rule.get('severity', 'medium')
        
        return f"""
            <div class='issue'>
                <div class='issue-header'>
                    <div class='issue-title'>#{event['index']} {rule['name']}</div>
                    <span class='severity-badge {severity}'>{severity}</span>
                </div>
                
                <div class='issue-details'>
                    <div class='detail-item'>
                        <div class='detail-label'>攻击类型:</div>
                        <div class='detail-value'>{rule.get('category', '未知')}</div>
                    </div>
                    <div class='detail-item'>
                        <div class='detail-label'>源IP:</div>
                        <div class='detail-value'>{log_entry.get('src_ip', '未知')}</div>
                    </div>
                    <div class='detail-item'>
                        <div class='detail-label'>攻击时间:</div>
                        <div class='detail-value'>{log_entry.get('timestamp', '未知')}</div>
                    </div>
                    <div class='detail-item'>
                        <div class='detail-label'>请求方法:</div>
                        <div class='detail-value'>{log_entry.get('method', '未知')}</div>
                    </div>
                    <div class='detail-item'>
                        <div class='detail-label'>攻击路径:</div>
                        <div class='detail-value'>{log_entry.get('url', '未知')}</div>
                    </div>
                    <div class='detail-item'>
                        <div class='detail-label'>用户代理:</div>
                        <div class='detail-value'>{self._truncate_text(log_entry.get('user_agent', '未知'), 100)}</div>
                    </div>
                </div>
                
                <div class='ai-analysis'>
                    <h4>🤖 AI安全分析</h4>
                    <pre>{ai_analysis}</pre>
                </div>
            </div>"""

    def _build_html_footer(self) -> str:
        """构建HTML尾部"""
        return """
        </div>
</body>
</html>"""

    @staticmethod
    def _truncate_text(text: str, max_length: int) -> str:
        """截断文本"""
        if len(text) <= max_length:
            return text
        return text[:max_length] + '...'

    def _build_markdown_content(self, report_data: Dict[str, Any]) -> str:
        """构建Markdown格式报告 - 优化版本"""
        metadata = report_data['metadata']
        ip_stats = report_data['ip_statistics']
        events = report_data['security_events']
        
        content = [
            "# 🔍 日志分析报告",
            "",
            f"**📅 生成时间:** {metadata['generated_at']}",
            f"**🎯 目标服务器:** {metadata['server_ip']}",
            f"**📊 安全事件总数:** {metadata['total_events']}",
            "",
            "## 📈 威胁概览",
            "",
            f"- **高危事件:** {metadata['severity_stats'].get('high', 0)} 个",
            f"- **中危事件:** {metadata['severity_stats'].get('medium', 0)} 个", 
            f"- **低危事件:** {metadata['severity_stats'].get('low', 0)} 个",
            "",
        ]

        content.extend(self._build_markdown_ip_section(ip_stats))
        content.extend(self._build_markdown_events_section(events))

        return '\n'.join(content)

    def _build_markdown_ip_section(self, ip_stats: Dict[str, Any]) -> List[str]:
        """构建Markdown格式的IP统计部分"""
        content = ["## 📊 IP访问统计", "", "### 🏠 内网IP访问排名", ""]

        if ip_stats['internal_ips']:
            content.extend([
                "| IP地址 | 访问次数 | 访问占比 |",
                "|--------|----------|----------|"
            ])
            total_internal = sum(ip_stats['internal_ips'].values())
            for ip, count in sorted(ip_stats['internal_ips'].items(), key=lambda x: x[1], reverse=True):
                percentage = (count / total_internal * 100) if total_internal > 0 else 0
                content.append(f"| {ip} | {count} | {percentage:.1f}% |")
        else:
            content.append("*无内网IP访问记录*")
        
        content.extend(["", "### 🌍 外网IP访问排名", ""])

        if ip_stats['external_ip_details']:
            content.extend([
                "| IP地址 | 访问次数 | 地理位置 | 风险等级 |",
                "|--------|----------|----------|----------|"
            ])
            for ip_info in sorted(ip_stats['external_ip_details'], key=lambda x: x['count'], reverse=True):
                risk_level = self._assess_ip_risk(ip_info['count'])
                content.append(f"| {ip_info['ip']} | {ip_info['count']} | {ip_info['location']} | {risk_level} |")
        else:
            content.append("*无外网IP访问记录*")

        return content

    def _build_markdown_events_section(self, events: List[Dict[str, Any]]) -> List[str]:
        """构建Markdown格式的安全事件部分"""
        content = ["", "## 🚨 安全事件详情", ""]

        if events:
            for event in events:
                rule = event['rule']
                log_entry = event['log_entry']
                severity = rule.get('severity', 'medium')
                
                content.extend([
                    f"### 事件 #{event['index']}: {rule['name']}",
                    "",
                    f"**严重程度:** {severity}",
                    f"**攻击类型:** {rule.get('category', '未知')}",
                    f"**源IP地址:** {log_entry.get('src_ip', '未知')}",
                    f"**攻击时间:** {log_entry.get('timestamp', '未知')}",
                    f"**请求方法:** {log_entry.get('method', '未知')}",
                    f"**攻击路径:** {log_entry.get('url', '未知')}",
                    f"**用户代理:** {log_entry.get('user_agent', '未知')}",
                    "",
                    "**🤖 AI安全分析:**",
                    "```",
                    event['ai_analysis'],
                    "```",
                    ""
                ])
        else:
            content.append("*暂无安全事件*")

        return content

    def _build_json_content(self, report_data: Dict[str, Any]) -> str:
        """构建JSON格式报告"""
        return json.dumps(report_data, ensure_ascii=False, indent=2)

    def _prepare_report_data(self, matched_logs: List[Dict[str, Any]], ai_results: List[str],
                            internal_ips: Dict[str, int], external_ip_details: List[Dict[str, Any]], 
                            server_ip: str) -> Dict[str, Any]:
        """准备报告所需的统一数据结构"""
        severity_stats = self._calculate_severity_stats(matched_logs)
        attack_type_stats = self._calculate_attack_type_stats(matched_logs)
        
        return {
            'metadata': {
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'server_ip': server_ip,
                'total_events': len(matched_logs),
                'severity_stats': severity_stats,
                'attack_type_stats': attack_type_stats
            },
            'ip_statistics': {
                'internal_ips': internal_ips,
                'external_ip_details': external_ip_details
            },
            'security_events': [
                {
                    'index': i + 1,
                    'rule': item['rule'],
                    'log_entry': item['log_entry'],
                    'ai_analysis': ai_result,
                    'risk_assessment': self._assess_event_risk(item.get('rule', {}).get('severity', 'medium'))
                }
                for i, (item, ai_result) in enumerate(zip(matched_logs, ai_results))
            ]
        }

    def _calculate_severity_stats(self, matched_logs: List[Dict[str, Any]]) -> Dict[str, int]:
        """计算严重程度统计 - 优化版本"""
        stats = {"high": 0, "medium": 0, "low": 0}
        for item in matched_logs:
            severity = item.get('rule', {}).get('severity', 'medium')
            if severity in stats:
                stats[severity] += 1
        return stats

    @lru_cache(maxsize=32)
    def _assess_ip_risk(self, access_count: int) -> str:
        """评估IP风险等级 - 添加缓存"""
        if access_count > 100:
            return "HIGH"
        elif access_count > 10:
            return "MEDIUM"
        else:
            return "LOW"

    def _calculate_attack_type_stats(self, matched_logs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """计算攻击类型统计 - 优化版本"""
        type_stats = {}
        severity_priority = {'high': 3, 'medium': 2, 'low': 1}
        
        for item in matched_logs:
            rule = item.get('rule', {})
            attack_type = rule.get('category', rule.get('name', '未知攻击'))
            severity = rule.get('severity', 'medium')
            
            if attack_type not in type_stats:
                type_stats[attack_type] = {
                    'count': 0,
                    'max_severity': severity,
                    'max_severity_priority': severity_priority.get(severity, 0)
                }
            
            type_stats[attack_type]['count'] += 1
            
            # 更新最高严重级别
            if severity_priority.get(severity, 0) > type_stats[attack_type]['max_severity_priority']:
                type_stats[attack_type]['max_severity'] = severity
                type_stats[attack_type]['max_severity_priority'] = severity_priority.get(severity, 0)
        
        # 转换为列表并按攻击数量排序
        return [
            {'type': attack_type, 'count': stats['count'], 'max_severity': stats['max_severity']}
            for attack_type, stats in sorted(type_stats.items(), key=lambda x: x[1]['count'], reverse=True)
        ]

    @lru_cache(maxsize=16)
    def _assess_event_risk(self, severity: str) -> Dict[str, Any]:
        """评估事件风险 - 添加缓存"""
        risk_mapping = {
            "high": {"score": 9, "level": "严重", "action": "立即处理"},
            "medium": {"score": 6, "level": "中等", "action": "及时处理"},
            "low": {"score": 3, "level": "较低", "action": "关注监控"}
        }
        return risk_mapping.get(severity, risk_mapping["medium"])