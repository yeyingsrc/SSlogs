#!/usr/bin/env python3
import os
import re
import yaml
import json
import requests
import signal
import sys
from datetime import datetime
from jinja2 import Template
import logging
from typing import List, Dict, Optional

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LogAnalyzer:
    def __init__(self, config_path: str = 'config.yaml'):
        # 初始化中断标志
        self.interrupted = False
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.config = self.load_config(config_path)
        self.rules = self.load_rules()
        self.api_key = self.config.get('deepseek_api', {}).get('api_key', '')
        self.api_endpoint = self.config.get('deepseek_api', {}).get('endpoint', 'https://api.deepseek.com/analyze')
        self.report_template = self.load_report_template()

    def _signal_handler(self, signum, frame):
        """处理中断信号"""
        signal_name = 'SIGINT' if signum == signal.SIGINT else 'SIGTERM'
        logger.info(f"\n收到信号 {signal_name}，正在优雅关闭...")
        self.interrupted = True

    def load_config(self, config_path: str) -> Dict:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            raise

    def load_rules(self) -> List[Dict]:
        """加载规则文件"""
        rules = []
        rules_dir = self.config.get('rules', {}).get('directory', 'rules')
        if not os.path.exists(rules_dir):
            logger.warning(f"规则目录 {rules_dir} 不存在，将使用默认规则")
            return self._get_default_rules()

        for filename in os.listdir(rules_dir):
            if filename.endswith('.yaml') or filename.endswith('.yml'):
                try:
                    with open(os.path.join(rules_dir, filename), 'r', encoding='utf-8') as f:
                        rule = yaml.safe_load(f)
                        if rule and isinstance(rule, dict):
                            rules.append(rule)
                except Exception as e:
                    logger.error(f"加载规则文件 {filename} 失败: {e}")
        return rules if rules else self._get_default_rules()

    def _get_default_rules(self) -> List[Dict]:
        """返回默认规则"""
        return [
            {
                'name': 'SQL注入检测',
                'pattern': r'(union select|select.*from|insert.*into|delete.*from|drop table|xp_cmdshell)',
                'severity': 'high',
                'category': 'injection'
            },
            {
                'name': 'XSS攻击检测',
                'pattern': r'(<script.*?>.*?</script>|javascript:|onerror=|onclick=)',
                'severity': 'medium',
                'category': 'xss'
            },
            {
                'name': '敏感路径访问',
                'pattern': r'(/etc/passwd|/proc/self/environ|/var/log/|.git/)',
                'severity': 'high',
                'category': 'path_traversal'
            }
        ]

    def load_report_template(self) -> Template:
        """加载报告模板"""
        template_path = self.config.get('report', {}).get('template', 'templates/report_template.html')
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return Template(f.read())
        except Exception as e:
            logger.warning(f"加载报告模板失败，使用默认模板: {e}")
            # 默认HTML模板
            return Template('''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>日志分析报告 - {{ analysis_time }}</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }
        .header { background-color: #f2f2f2; padding: 10px; border-radius: 5px; }
        .issue { border: 1px solid #ffcccc; background-color: #fff0f0; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .severity-high { color: #ff0000; }
        .severity-medium { color: #ff9900; }
        .severity-low { color: #ffff00; }
        .log-snippet { background-color: #f8f8f8; padding: 10px; border-radius: 3px; font-family: monospace; }
        .ai-analysis { background-color: #e6f7ff; padding: 10px; border-radius: 5px; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>日志分析报告</h1>
        <p>分析时间: {{ analysis_time }}</p>
        <p>日志文件: {{ log_file }}</p>
        <p>发现问题: {{ issue_count }} 个</p>
    </div>
    {% for issue in issues %}
    <div class="issue">
        <h3>问题: {{ issue.rule_name }} (严重程度: <span class="severity-{{ issue.severity }}">{{ issue.severity }}</span>)</h3>
        <p>类别: {{ issue.category }}</p>
        <p>描述: {{ issue.description }}</p>
        <p>攻击时间: {{ issue.timestamp }}</p>
        <p>源IP: {{ issue.ip }}</p>
        <h4>匹配日志行:</h4>
        <div class="log-snippet">{{ issue.log_line }}</div>
        <h4>上下文日志:</h4>
        <div class="log-snippet">{{ issue.context }}</div>
        <h4>AI分析结果:</h4>
        <div class="ai-analysis">{{ issue.ai_analysis }}</div>
    </div>
    {% endfor %}
</body>
</html>''')

    def parse_log_line(self, line: str) -> Optional[Dict]:
        """解析单条日志行"""
        try:
            parsed = {}
            for field in self.config.get('log_format', {}).get('fields', []):
                name = field.get('name')
                pattern = field.get('regex')
                if name and pattern:
                    match = re.search(pattern, line)
                    if match:
                        parsed[name] = match.group(1)
            # 解析时间戳
            if 'timestamp' in parsed:
                try:
                    parsed['timestamp'] = datetime.strptime(
                        parsed['timestamp'], 
                        self.config.get('log_format', {}).get('timestamp_format', '%d/%b/%Y:%H:%M:%S %z')
                    )
                except Exception as e:
                    logger.warning(f"时间戳解析失败: {e}")
            return parsed
        except Exception as e:
            logger.error(f"日志行解析失败: {e}")
            return None

    def analyze_log_file(self, log_path: str) -> List[Dict]:
        """分析日志文件"""
        issues = []
        context_lines = self.config.get('analysis', {}).get('context_lines', 5)
        batch_size = self.config.get('analysis', {}).get('batch_size', 1000)

        if not os.path.exists(log_path):
            logger.error(f"日志文件 {log_path} 不存在")
            return []

        # 读取日志文件
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception as e:
            logger.error(f"读取日志文件失败: {e}")
            return []

        # 批量处理日志
        for i in range(0, len(lines), batch_size):
            # 检查中断信号
            if self.interrupted:
                logger.info("检测到中断信号，停止日志分析")
                break
                
            batch = lines[i:i+batch_size]
            logger.info(f"处理批次 {i//batch_size + 1}: 行 {i+1} - {min(i+batch_size, len(lines))}")
            
            for line_num, line in enumerate(batch, start=i+1):
                # 检查中断信号
                if self.interrupted:
                    logger.info("检测到中断信号，停止处理当前批次")
                    break
                    
                parsed_line = self.parse_log_line(line)
                if not parsed_line:
                    continue

                # 应用规则检测
                for rule in self.rules:
                    pattern = rule.get('pattern')
                    if pattern and re.search(pattern, line, re.IGNORECASE):
                        # 获取上下文日志
                        start = max(0, line_num - context_lines - 1)
                        end = min(len(lines), line_num + context_lines)
                        context = '\n'.join([f"{idx+1}: {l.strip()}" for idx, l in enumerate(lines[start:end])])

                        # 调用DeepSeek API分析
                        ai_analysis = self.call_deepseek_api(rule, line, context)

                        issue = {
                            'rule_name': rule.get('name', '未知规则'),
                            'severity': rule.get('severity', 'medium'),
                            'category': rule.get('category', 'unknown'),
                            'description': rule.get('description', '无描述'),
                            'log_line': line.strip(),
                            'line_number': line_num,
                            'timestamp': parsed_line.get('timestamp', '未知时间'),
                            'ip': parsed_line.get('ip', '未知IP'),
                            'context': context,
                            'ai_analysis': ai_analysis
                        }
                        issues.append(issue)
                        logger.info(f"发现问题日志: {rule.get('name')} (行号: {line_num})")

        return issues



    def generate_report(self, issues: List[Dict], log_path: str, output_path: Optional[str] = None) -> str:
        """生成分析报告"""
        if not issues:
            logger.info("未发现问题日志，无需生成报告")
            return ""

        # 确定输出路径
        if not output_path:
            report_dir = self.config.get('report', {}).get('output_directory', 'reports')
            os.makedirs(report_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_format = self.config.get('report', {}).get('output_format', 'html')
            output_path = os.path.join(report_dir, f"log_analysis_report_{timestamp}.{output_format}")

        # 渲染报告
        analysis_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        html_content = self.report_template.render(
            analysis_time=analysis_time,
            log_file=log_path,
            issue_count=len(issues),
            issues=issues
        )

        # 保存报告
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"分析报告已生成: {output_path}")
        return output_path

    def run(self, log_path: str) -> None:
        """运行日志分析工具"""
        try:
            # 检查初始中断状态
            if self.interrupted:
                logger.info("程序已被中断，退出分析")
                return
                
            logger.info(f"开始分析日志文件: {log_path}")
            issues = self.analyze_log_file(log_path)
            
            if self.interrupted:
                logger.info("分析过程中被中断，生成部分结果报告")
                
            if issues:
                report_path = self.generate_report(issues, log_path)
                status_msg = "部分分析" if self.interrupted else "日志分析"
                logger.info(f"{status_msg}完成，共发现 {len(issues)} 个问题，报告已保存至 {report_path}")
            else:
                status_msg = "部分分析" if self.interrupted else "日志分析"
                logger.info(f"{status_msg}完成，未发现问题")
                
        except KeyboardInterrupt:
            logger.info("\n收到键盘中断信号，正在安全退出...")
            self.interrupted = True
        except Exception as e:
            logger.error(f"分析过程中发生错误: {e}")
        finally:
            if self.interrupted:
                logger.info("程序已安全退出")
                sys.exit(0)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='应急分析溯源日志工具')
    parser.add_argument('log_path', help='日志文件路径')
    parser.add_argument('-c', '--config', default='config/config.yaml', help='配置文件路径')
    args = parser.parse_args()

    analyzer = LogAnalyzer(args.config)
    analyzer.run(args.log_path)