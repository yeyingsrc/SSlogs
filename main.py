import yaml
import argparse
import os
import glob
import gc
import signal
import sys
from typing import List, Dict, Any
from core.parser import LogParser
from core.rule_engine import RuleEngine
from core.ai_analyzer import AIAnalyzer
from core.reporter import ReportGenerator
from core.ip_utils import analyze_ip_access, IPGeoLocator
import gzip
import tarfile
import zipfile
import patoolib
import shutil
import logging
import re
from io import BytesIO

class LogHunter:
    def __init__(self, config_path: str, ai_enabled: bool = False, server_ip: str = None):
        # 初始化中断标志
        self.interrupted = False
        
        # 初始化日志
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # 加载配置文件
        self.config = self._load_config(config_path)
        
        # 设置服务器IP（优先使用传入的参数）
        self.server_ip = server_ip or self.config.get('server', {}).get('ip', '未知')
        
        # 性能配置
        self.batch_size = self.config.get('analysis', {}).get('batch_size', 1000)
        self.max_events = self.config.get('analysis', {}).get('max_events', 100)
        self.memory_limit = self.config.get('analysis', {}).get('memory_limit_mb', 500) * 1024 * 1024
        
        # 初始化各模块
        self.parser = LogParser(self.config['log_format'])
        self.rule_engine = RuleEngine(self.config['rule_dir'])
        self.ai_enabled = ai_enabled
        self.ai_analyzer = AIAnalyzer(config_path=config_path) if ai_enabled else None
        self.reporter = ReportGenerator(self.config['output_dir'])
        
        # IP分析相关初始化
        self.ip_list = []

    def _signal_handler(self, signum, frame):
        """处理中断信号"""
        signal_name = 'SIGINT' if signum == signal.SIGINT else 'SIGTERM'
        self.logger.info(f"\n收到信号 {signal_name}，正在优雅关闭...")
        self.interrupted = True

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _read_log_file_chunked(self) -> List[str]:
        """分块读取日志文件，优化内存使用"""
        log_pattern = self.config['log_path']
        log_files = glob.glob(log_pattern, recursive=True)
        allowed_extensions = ('.log', '.gz', '.tar.gz', '.zip', '.rar')
        log_files = [f for f in log_files if f.lower().endswith(allowed_extensions) and os.path.isfile(f)]

        if not log_files:
            raise FileNotFoundError(f"未找到日志文件: {log_pattern}")

        all_lines = []
        total_size = 0
        
        for file in log_files:
            # 检查中断信号
            if self.interrupted:
                self.logger.info("检测到中断信号，停止读取日志文件")
                break
                
            try:
                file_size = os.path.getsize(file)
                if total_size + file_size > self.memory_limit:
                    self.logger.warning(f"达到内存限制，跳过文件: {file}")
                    continue
                
                lines = self._extract_file_content(file)
                all_lines.extend(lines)
                total_size += file_size
                
                self.logger.info(f"成功读取日志文件: {file} ({len(lines)} 行)")
                
                # 强制垃圾回收
                del lines
                gc.collect()
                
            except Exception as e:
                self.logger.warning(f"读取日志文件失败 {file}: {str(e)}")
                continue

        return all_lines

    def _extract_file_content(self, file: str) -> List[str]:
        """提取文件内容"""
        if file.endswith('.gz'):
            with gzip.open(file, 'rt', encoding='utf-8', errors='ignore') as f:
                return f.readlines()
        elif file.endswith('.tar.gz'):
            lines = []
            with tarfile.open(file, 'r:gz') as tar:
                for member in tar.getmembers():
                    if member.isfile() and member.name.lower().endswith('.log'):
                        with tar.extractfile(member) as f:
                            content = f.read().decode('utf-8', errors='ignore')
                            lines.extend(content.splitlines())
            return lines
        elif file.endswith('.zip'):
            lines = []
            with zipfile.ZipFile(file, 'r') as zip_ref:
                for member in zip_ref.namelist():
                    if member.lower().endswith('.log'):
                        with zip_ref.open(member) as f:
                            content = f.read().decode('utf-8', errors='ignore')
                            lines.extend(content.splitlines())
            return lines
        elif file.endswith('.rar'):
            lines = []
            temp_dir = '/tmp/log_extract'
            os.makedirs(temp_dir, exist_ok=True)
            try:
                patoolib.extract_archive(file, outdir=temp_dir, verbosity=-1)
                for root, _, files in os.walk(temp_dir):
                    for f in files:
                        if f.lower().endswith('.log'):
                            with open(os.path.join(root, f), 'r', encoding='utf-8', errors='ignore') as log_f:
                                lines.extend(log_f.readlines())
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)
            return lines
        else:  # .log文件
            with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                return f.readlines()

    def _get_log_context(self, logs: List[str], line_num: int, context_lines: int = 5) -> str:
        """获取日志上下文"""
        start = max(0, line_num - context_lines)
        end = min(len(logs), line_num + context_lines + 1)
        context = []
        for i in range(start, end):
            context.append(f"{i+1}: {logs[i].strip()}")
        return '\n'.join(context)

    def update_log_format_config(self, new_fields):
        """更新配置文件中的日志格式字段定义"""
        try:
            # 读取现有配置
            with open('config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # 更新日志格式字段
            if 'log_format' in config and 'fields' in config['log_format']:
                config['log_format']['fields'] = new_fields
                # 写回配置文件
                with open('config.yaml', 'w', encoding='utf-8') as f:
                    yaml.safe_dump(config, f, sort_keys=False, allow_unicode=True)
                self.logger.info("日志解析规则已成功更新到config.yaml")
                return True
            else:
                self.logger.error("配置文件中未找到log_format.fields定义")
                return False
        except Exception as e:
            self.logger.error(f"更新配置文件失败: {e}")
            return False

    def _process_logs_in_batches(self, logs: List[str]) -> List[Dict[str, Any]]:
        """分批处理日志以优化性能"""
        matched_entries = []
        context_lines = self.config.get('context_lines', 5)
        
        for batch_start in range(0, len(logs), self.batch_size):
            # 检查中断信号
            if self.interrupted:
                self.logger.info("检测到中断信号，停止处理日志")
                break
                
            batch_end = min(batch_start + self.batch_size, len(logs))
            batch = logs[batch_start:batch_end]
            
            self.logger.info(f"处理批次 {batch_start//self.batch_size + 1}: 行 {batch_start+1} - {batch_end}")
            
            # 处理当前批次
            for line_num, line in enumerate(batch, start=batch_start):
                # 检查中断信号
                if self.interrupted:
                    self.logger.info("检测到中断信号，停止处理当前批次")
                    return matched_entries
                    
                # 解析日志行
                log_entry = self.parser.parse_log_line(line)
                if not log_entry:
                    continue

                # 提取IP地址
                ip = log_entry.get('src_ip')
                if ip:
                    self.ip_list.append(ip)

                # 规则匹配
                matches = self.rule_engine.match_log(log_entry)
                if matches:
                    # 获取上下文
                    context = self._get_log_context(logs, line_num, context_lines)
                    
                    # 存储匹配项和上下文
                    for match in matches:
                        matched_entries.append({
                            'match': match,
                            'context': context
                        })
                        
                    # 限制事件数量
                    if len(matched_entries) >= self.max_events:
                        self.logger.info(f"达到最大事件数量限制 ({self.max_events})，停止处理")
                        return matched_entries
            
            # 批次处理完成后强制垃圾回收
            gc.collect()
        
        return matched_entries

    def run(self):
        """运行日志分析流程"""
        try:
            # 检查初始中断状态
            if self.interrupted:
                self.logger.info("程序已被中断，退出分析")
                return
                
            # 读取日志文件
            logs = self._read_log_file_chunked()
            if self.interrupted:
                self.logger.info("读取文件过程中被中断，生成部分结果报告")
                return
                
            self.logger.info(f"成功加载日志文件: {self.config['log_path']} (共 {len(logs)} 行)")
            
            # 显示前5条日志解析示例
            self.logger.info("前5条日志解析结果:")
            for i, line in enumerate(logs[:5]):
                if self.interrupted:
                    break
                log_entry = self.parser.parse_log_line(line)
                if log_entry:
                    self.logger.info(f"日志 {i+1}: IP={log_entry.get('src_ip', '')}, 方法={log_entry.get('method', '')}, URL={log_entry.get('url', '')}")
                else:
                    self.logger.info(f"日志 {i+1}: 解析失败")
            
            # 分批处理日志
            matched_entries = self._process_logs_in_batches(logs)
            if self.interrupted:
                self.logger.info("日志处理过程中被中断，生成已处理结果的报告")
            
            # 按严重级别排序，并过滤出攻击成功且高风险的日志
            severity_priority = {'high': 3, 'medium': 2, 'low': 1}
            sorted_entries = sorted(
                matched_entries, 
                key=lambda x: severity_priority.get(x['match']['rule'].get('severity', 'low'), 0), 
                reverse=True
            )
            
            # 获取AI分析配置
            ai_config = self.config.get('ai_analysis', {})
            high_risk_only = ai_config.get('high_risk_only', True)
            successful_attacks_only = ai_config.get('successful_attacks_only', True) 
            success_status_codes = ai_config.get('success_status_codes', ['200', '201', '202', '204', '301', '302', '304'])
            max_ai_analysis = ai_config.get('max_ai_analysis', 5)
            high_risk_severity = ai_config.get('high_risk_severity', 'high')
            
            # 过滤出符合条件的日志用于AI分析
            filtered_entries = []
            
            for entry in sorted_entries:
                if self.interrupted:
                    break
                    
                rule = entry['match']['rule']
                log_entry = entry['match']['log_entry']
                
                # 获取状态码（在条件检查之前）
                status_code = log_entry.get('status_code', log_entry.get('status', 'unknown'))
                
                # 检查是否符合风险级别要求
                should_analyze = True
                if high_risk_only and rule.get('severity') != high_risk_severity:
                    should_analyze = False
                
                # 检查是否符合攻击成功要求
                if should_analyze and successful_attacks_only:
                    if status_code not in success_status_codes:
                        should_analyze = False
                
                if should_analyze:
                    filtered_entries.append(entry)
                    attack_type = "高风险成功攻击" if high_risk_only and successful_attacks_only else "安全事件"
                    self.logger.info(f"发现{attack_type}: {rule['name']} - 状态码: {status_code} - IP: {log_entry.get('src_ip', 'unknown')}")
            
            # 取前N条符合条件的事件进行AI分析
            top_critical_entries = filtered_entries[:max_ai_analysis]
            matched_logs = [entry['match'] for entry in top_critical_entries]
            
            self.logger.info(f"总计发现 {len(matched_entries)} 个安全事件")
            self.logger.info(f"其中符合AI分析条件的事件 {len(filtered_entries)} 个")
            self.logger.info(f"将对TOP{len(top_critical_entries)}个事件进行AI深度分析")
            
            # AI分析 - 只分析符合条件的攻击
            ai_results = []
            if self.ai_enabled and self.ai_analyzer and top_critical_entries:
                attack_type = "高风险成功攻击" if high_risk_only and successful_attacks_only else "重要安全事件"
                self.logger.info(f"开始AI深度分析{attack_type}...")
                for i, entry in enumerate(top_critical_entries, 1):
                    # 检查中断信号
                    if self.interrupted:
                        self.logger.info("检测到中断信号，停止AI分析")
                        break
                        
                    rule_name = entry['match']['rule']['name']
                    src_ip = entry['match']['log_entry'].get('src_ip', 'unknown')
                    status = entry['match']['log_entry'].get('status_code', entry['match']['log_entry'].get('status', 'unknown'))
                    self.logger.info(f"AI分析进度: {i}/{len(top_critical_entries)} - {rule_name} (IP: {src_ip}, 状态: {status})")
                    ai_result = self.ai_analyzer.analyze_log(entry['context'])
                    ai_results.append(ai_result)
            elif matched_entries and not top_critical_entries:
                condition_desc = []
                if high_risk_only:
                    condition_desc.append("高风险")
                if successful_attacks_only:
                    condition_desc.append("攻击成功")
                self.logger.info(f"未发现符合条件的{'和'.join(condition_desc)}事件，跳过AI分析")
                # 如果没有符合条件的事件，但有其他安全事件，取前5个进行基础报告
                matched_logs = [entry['match'] for entry in sorted_entries[:5]]

            # 分析IP访问情况
            if not self.interrupted:
                internal_ips, external_ips = analyze_ip_access(self.ip_list, self.config['geoip_db_path'])

                # 处理外网IP地理位置
                external_ip_details = []
                if external_ips:
                    try:
                        locator = IPGeoLocator(self.config['geoip_db_path'])
                        for ip, count in list(external_ips.items())[:20]:  # 限制处理数量
                            if self.interrupted:
                                break
                            try:
                                country_iso, country_name = locator.get_location(ip)
                                external_ip_details.append({
                                    'ip': ip,
                                    'count': count,
                                    'location': country_name or '未知'
                                })
                            except Exception as e:
                                self.logger.warning(f"处理IP {ip} 时出错: {str(e)}")
                        locator.close()
                    except Exception as e:
                        self.logger.error(f"IP地理位置分析初始化失败: {str(e)}")
            else:
                internal_ips, external_ips = {}, {}
                external_ip_details = []

            # 生成报告
            if matched_logs or self.ip_list:
                if self.interrupted:
                    self.logger.info("程序被中断，正在生成部分结果报告...")
                report_path = self.reporter.generate_report(
                    matched_logs, ai_results, self.config['report_type'],
                    internal_ips=internal_ips, 
                    external_ip_details=external_ip_details,
                    server_ip=self.server_ip
                )
                status_msg = "部分分析" if self.interrupted else "分析"
                self.logger.info(f"{status_msg}完成，共发现 {len(matched_logs)} 个安全事件，报告已生成: {report_path}")
            else:
                status_msg = "部分分析" if self.interrupted else "分析"
                self.logger.info(f"{status_msg}完成，未发现匹配的问题日志")

        except KeyboardInterrupt:
            self.logger.info("\n收到键盘中断信号，正在安全退出...")
            self.interrupted = True
        except Exception as e:
            self.logger.error(f"分析过程中发生错误: {str(e)}", exc_info=True)
        finally:
            if self.interrupted:
                self.logger.info("程序已安全退出")
                sys.exit(0)

def main():
    parser = argparse.ArgumentParser(description='应急分析溯源日志工具')
    parser.add_argument('--config', default='config.yaml', help='配置文件路径')
    parser.add_argument('--ai', action='store_true', help='启用AI分析')
    parser.add_argument('--generate-rules', type=str, help='从日志样例生成解析规则')
    parser.add_argument('--server-ip', type=str, help='指定服务器主机IP地址')
    args = parser.parse_args()
    
    if args.generate_rules:
        # 确保AI已启用
        log_hunter = LogHunter(args.config, ai_enabled=True)
        # 生成解析规则
        rules = log_hunter.ai_analyzer.generate_parsing_rules(args.generate_rules)
        if 'fields' in rules:
            # 更新配置文件
            success = log_hunter.update_log_format_config(rules['fields'])
            if success:
                print("日志解析规则已成功生成并更新到config.yaml")
            else:
                print("生成规则成功，但更新配置文件失败")
        else:
            print(f"生成解析规则失败: {rules.get('error', '未知错误')}")
        return
    
    # 获取服务器主机IP
    server_ip = args.server_ip
    if not server_ip:
        print("="*50)
        print("欢迎使用应急分析溯源日志工具")
        print("="*50)
        while True:
            server_ip = input("请输入服务器主机IP地址: ").strip()
            if server_ip:
                # 简单验证IP格式
                import socket
                try:
                    socket.inet_aton(server_ip)
                    break
                except socket.error:
                    print("IP地址格式不正确，请重新输入")
            else:
                print("IP地址不能为空，请重新输入")
    
    print(f"开始分析主机 {server_ip} 的日志...")
    print("="*50)
    
    # 正常日志分析流程
    log_hunter = LogHunter(args.config, ai_enabled=args.ai, server_ip=server_ip)
    log_hunter.run()

if __name__ == "__main__":
    main()