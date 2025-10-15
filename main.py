import yaml
import argparse
import os
import glob
import gc
import signal
import sys
from typing import List, Dict, Any, Generator, Optional

# 导入核心模块
from core.parser import LogParser
from core.rule_engine import RuleEngine
from core.ai_analyzer import AIAnalyzer
from core.reporter import ReportGenerator
from core.ip_utils import analyze_ip_access, IPGeoLocator
from core.config_manager import ConfigManager, ConfigurationError
from core.performance import performance_monitor, memory_monitor, error_rate_monitor, get_performance_summary
from core.exceptions import LogAnalysisError, ParsingError, AIServiceError, ReportGenerationError

import gzip
import tarfile
import zipfile
import patoolib
import shutil
import logging
import re
from io import BytesIO
import tempfile
from collections import Counter

class LogHunter:
    def __init__(self, config_path: str, ai_enabled: bool = False, server_ip: Optional[str] = None, disable_signal_handlers: bool = False):
        """
        日志分析主类
        """
        self.interrupted = False

        # 使用新的配置管理器
        self.config_manager = ConfigManager(config_path)
        try:
            self.config = self.config_manager.load_config()
        except ConfigurationError as e:
            print(f"配置错误: {e}")
            sys.exit(1)

        self.logger = self._init_logger()
        self.server_ip = server_ip or self.config.get('server', {}).get('ip', '未知')
        self.batch_size = self.config.get('analysis', {}).get('batch_size', 1000)
        self.max_events = self.config.get('analysis', {}).get('max_events', 100)
        self.memory_limit = self.config.get('analysis', {}).get('memory_limit_mb', 500) * 1024 * 1024

        try:
            self.parser = LogParser(self.config['log_format'])
            self.rule_engine = RuleEngine(self.config['rule_dir'])
        except (ParsingError, Exception) as e:
            self.logger.error(f"初始化解析器或规则引擎失败: {e}")
            raise LogAnalysisError(f"组件初始化失败: {e}")

        self.ai_enabled = ai_enabled
        try:
            self.ai_analyzer = AIAnalyzer(config_path=config_path) if ai_enabled else None
        except Exception as e:
            self.logger.warning(f"AI分析器初始化失败: {e}")
            self.ai_analyzer = None
            self.ai_enabled = False

        self.reporter = ReportGenerator(self.config['output_dir'])
        self.ip_counter = Counter()

        # 只在主线程中设置信号处理器
        if not disable_signal_handlers:
            try:
                signal.signal(signal.SIGINT, self._signal_handler)
                signal.signal(signal.SIGTERM, self._signal_handler)
            except (ValueError, RuntimeError):
                # 在多线程环境中信号处理可能不适用，忽略错误
                pass

    def _init_logger(self) -> logging.Logger:
        log_level = self.config.get('log_level', 'INFO').upper()
        log_file = self.config.get('log_file', 'loghunter.log')
        logger = logging.getLogger("LogHunter")
        if not logger.hasHandlers():
            logging.basicConfig(
                level=getattr(logging, log_level, logging.INFO),
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_file, encoding='utf-8'),
                    logging.StreamHandler()
                ]
            )
        return logger

    def _signal_handler(self, signum, frame):
        signal_name = 'SIGINT' if signum == signal.SIGINT else 'SIGTERM'
        self.logger.info(f"\n收到信号 {signal_name}，正在优雅关闭...")
        self.interrupted = True

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 设置默认值以提高健壮性
        if not config:
            config = {}
            
        # 确保必要字段存在
        required_fields = ['log_format', 'log_path', 'rule_dir', 'output_dir']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"配置文件缺少必要字段: {field}")
        
        # 设置默认值
        config.setdefault('analysis', {})
        config['analysis'].setdefault('batch_size', 1000)
        config['analysis'].setdefault('max_events', 100)
        config['analysis'].setdefault('memory_limit_mb', 500)
        
        config.setdefault('ai_analysis', {})
        config['ai_analysis'].setdefault('high_risk_only', True)
        config['ai_analysis'].setdefault('successful_attacks_only', True)
        config['ai_analysis'].setdefault('success_status_codes', ['200', '201', '202', '204', '301', '302', '304'])
        config['ai_analysis'].setdefault('max_ai_analysis', 5)
        config['ai_analysis'].setdefault('high_risk_severity', 'high')
        
        config.setdefault('server', {})
        config['server'].setdefault('ip', '未知')
        
        return config

    def _read_log_file_chunked(self) -> Generator[str, None, None]:
        """
        以生成器方式分块读取日志文件，优化内存使用
        """
        log_pattern = self.config['log_path']
        log_files = glob.glob(log_pattern, recursive=True)
        allowed_extensions = ('.log', '.gz', '.tar.gz', '.zip', '.rar')
        log_files = [f for f in log_files if f.lower().endswith(allowed_extensions) and os.path.isfile(f)]
        if not log_files:
            raise FileNotFoundError(f"未找到日志文件: {log_pattern}")
        
        total_files = len(log_files)
        self.logger.info(f"找到 {total_files} 个日志文件待处理")
        
        for i, file in enumerate(log_files, 1):
            if self.interrupted:
                self.logger.info("检测到中断信号，停止读取日志文件")
                break
            self.logger.info(f"正在处理文件 ({i}/{total_files}): {file}")
            try:
                # 逐行读取文件内容
                for line in self._extract_file_content_line_by_line(file):
                    yield line
            except Exception as e:
                self.logger.warning(f"读取日志文件失败 {file}: {str(e)}")
                continue

    def _extract_file_content_line_by_line(self, file: str) -> Generator[str, None, None]:
        """
        逐行提取文件内容，支持多种压缩格式，优化内存使用
        """
        if file.endswith('.gz') and not file.endswith('.tar.gz'):
            with gzip.open(file, 'rt', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    yield line
        elif file.endswith('.tar.gz'):
            with tarfile.open(file, 'r:gz') as tar:
                for member in tar.getmembers():
                    if member.isfile() and member.name.lower().endswith('.log'):
                        with tar.extractfile(member) as f:
                            for line in f:
                                yield line.decode('utf-8', errors='ignore')
        elif file.endswith('.zip'):
            with zipfile.ZipFile(file, 'r') as zip_ref:
                for member in zip_ref.namelist():
                    if member.lower().endswith('.log'):
                        with zip_ref.open(member) as f:
                            for line in f:
                                yield line.decode('utf-8', errors='ignore')
        elif file.endswith('.rar'):
            with tempfile.TemporaryDirectory() as temp_dir:
                try:
                    patoolib.extract_archive(file, outdir=temp_dir, verbosity=-1)
                    for root, _, files in os.walk(temp_dir):
                        for f in files:
                            if f.lower().endswith('.log'):
                                with open(os.path.join(root, f), 'r', encoding='utf-8', errors='ignore') as log_f:
                                    for line in log_f:
                                        yield line
                except Exception as e:
                    self.logger.warning(f"解压RAR文件失败 {file}: {e}")
        else:  # .log文件
            with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    yield line

    def _get_log_context(self, logs: List[str], line_num: int, context_lines: int = 5) -> str:
        start = max(0, line_num - context_lines)
        end = min(len(logs), line_num + context_lines + 1)
        context = []
        for i in range(start, end):
            context.append(f"{i+1}: {logs[i].strip()}")
        return '\n'.join(context)

    def update_log_format_config(self, new_fields):
        try:
            with open('config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            if 'log_format' in config and 'fields' in config['log_format']:
                config['log_format']['fields'] = new_fields
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
        matched_entries = []
        context_lines = self.config.get('context_lines', 5)
        for batch_start in range(0, len(logs), self.batch_size):
            if self.interrupted:
                self.logger.info("检测到中断信号，停止处理日志")
                break
            batch_end = min(batch_start + self.batch_size, len(logs))
            batch = logs[batch_start:batch_end]
            self.logger.info(f"处理批次 {batch_start//self.batch_size + 1}: 行 {batch_start+1} - {batch_end}")
            for line_num, line in enumerate(batch, start=batch_start):
                if self.interrupted:
                    self.logger.info("检测到中断信号，停止处理当前批次")
                    return matched_entries
                log_entry = self.parser.parse_log_line(line)
                if not log_entry:
                    continue
                ip = log_entry.get('src_ip')
                if ip:
                    self.ip_counter[ip] += 1
                matches = self.rule_engine.match_log(log_entry)
                if matches:
                    context = self._get_log_context(logs, line_num, context_lines)
                    for match in matches:
                        matched_entries.append({'match': match, 'context': context})
                    if len(matched_entries) >= self.max_events:
                        self.logger.info(f"达到最大事件数量限制 ({self.max_events})，停止处理")
                        return matched_entries
            gc.collect()
        return matched_entries
    
    @performance_monitor(name="log_processing", track_memory=True)
    @error_rate_monitor(window_size=50)
    @memory_monitor(threshold_mb=200.0)
    def _process_logs_in_batches_with_generator(self, log_generator: Generator[str, None, None]) -> List[Dict[str, Any]]:
        """使用生成器方式处理日志批次，优化内存使用"""
        matched_entries = []
        context_lines = self.config.get('context_lines', 5)
        batch_buffer = []  # 缓冲区存储当前批次的日志行
        line_count = 0
        batch_num = 1
        
        def process_batch(batch_lines, start_line_num):
            """处理单个批次"""
            for i, line_content in enumerate(batch_lines):
                if self.interrupted:
                    self.logger.info("检测到中断信号，停止处理当前批次")
                    return False
                    
                log_entry = self.parser.parse_log_line(line_content)
                if not log_entry:
                    continue
                    
                ip = log_entry.get('src_ip')
                if ip:
                    self.ip_counter[ip] += 1
                    
                matches = self.rule_engine.match_log(log_entry)
                if matches:
                    # 为上下文创建一个小的缓冲区（包含前后几行）
                    context_start = max(0, i - context_lines)
                    context_end = min(len(batch_lines), i + context_lines + 1)
                    context_lines_list = batch_lines[context_start:context_end]
                    context = '\n'.join([f"{j+context_start+1}: {context_lines_list[j].strip()}"
                                       for j in range(len(context_lines_list))])
                    
                    for match in matches:
                        matched_entries.append({'match': match, 'context': context})
                    if len(matched_entries) >= self.max_events:
                        self.logger.info(f"达到最大事件数量限制 ({self.max_events})，停止处理")
                        return False
            return True
        
        for line in log_generator:
            if self.interrupted:
                self.logger.info("检测到中断信号，停止处理日志")
                break
                
            batch_buffer.append(line)
            line_count += 1
            
            # 当缓冲区达到批次大小时，处理这一批次
            if len(batch_buffer) >= self.batch_size:
                self.logger.info(f"处理批次 {batch_num}: 行 {line_count-len(batch_buffer)+1} - {line_count}")
                
                # 处理当前批次
                if not process_batch(batch_buffer, line_count-len(batch_buffer)+1):
                    return matched_entries
                
                # 清空缓冲区，准备下一个批次
                batch_buffer.clear()
                batch_num += 1
                gc.collect()
        
        # 处理最后一个不完整的批次
        if batch_buffer and not self.interrupted:
            self.logger.info(f"处理最后批次 {batch_num}: 行 {line_count-len(batch_buffer)+1} - {line_count}")
            if not process_batch(batch_buffer, line_count-len(batch_buffer)+1):
                return matched_entries
        
        return matched_entries

    def _check_interrupted(self) -> bool:
        if self.interrupted:
            self.logger.info("程序已被中断，正在处理收尾工作...")
            return True
        return False

    @performance_monitor(name="main_analysis", track_memory=True)
    @error_rate_monitor(window_size=20)
    def run(self):
        """
        运行日志分析流程
        """
        try:
            if self._check_interrupted():
                return
            
            # 逐行处理日志，不再一次性加载到内存
            log_generator = self._read_log_file_chunked()
            
            if self._check_interrupted():
                self.logger.info("读取文件过程中被中断，生成部分结果报告")
                return
            
            # 预览前5条日志
            preview_logs = self._preview_log_lines(log_generator)
            
            # 显示预览结果
            self._show_preview_results(preview_logs)
            
            # 重新创建生成器，包含预览日志
            def log_generator_with_preview():
                # 先返回预览过的日志
                for line in preview_logs:
                    yield line
                # 继续处理剩余的日志
                yield from self._read_log_file_chunked()
            
            # 处理日志并获取匹配条目
            matched_entries = self._process_logs_in_batches_with_generator(log_generator_with_preview())
            
            if self._check_interrupted():
                self.logger.info("日志处理过程中被中断，生成已处理结果的报告")
            
            # 过滤和排序匹配条目
            filtered_entries = self._filter_and_sort_entries(matched_entries)
            
            # 获取需要AI分析的条目
            top_critical_entries = self._get_top_critical_entries(filtered_entries)
            
            # 获取匹配的日志条目
            matched_logs = [entry['match'] for entry in top_critical_entries]
            
            # 执行AI分析
            ai_results = self._perform_ai_analysis(top_critical_entries)
            
            # 处理IP统计
            internal_ips, external_ip_details = self._process_ip_statistics()
            
            # 生成报告
            if matched_logs or self.ip_counter:
                if self._check_interrupted():
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
            # 输出性能摘要
            try:
                performance_summary = get_performance_summary()
                self.logger.info("性能监控摘要:")
                for line in performance_summary.split('\n'):
                    if line.strip():
                        self.logger.info(line)
            except Exception as e:
                self.logger.warning(f"生成性能摘要失败: {e}")

            # 输出解析器统计
            if hasattr(self.parser, 'get_statistics'):
                parser_stats = self.parser.get_statistics()
                self.logger.info(f"解析器统计: {parser_stats}")

            if hasattr(self.parser, 'get_cache_statistics'):
                cache_stats = self.parser.get_cache_statistics()
                self.logger.info(f"缓存统计: {cache_stats}")

            if self.interrupted:
                self.logger.info("程序已安全退出")
                sys.exit(0)
    
    def _preview_log_lines(self, log_generator) -> List[str]:
        """预览日志行"""
        preview_logs = []
        for i, line in enumerate(log_generator):
            if i < 5:
                preview_logs.append(line)
            else:
                # 将生成器重新组合，包含已读取的预览日志
                break
        return preview_logs
    
    def _show_preview_results(self, preview_logs: List[str]):
        """显示预览结果"""
        self.logger.info(f"开始处理日志文件: {self.config['log_path']}")
        self.logger.info("前5条日志解析结果:")
        for i, line in enumerate(preview_logs):
            if self._check_interrupted():
                break
            log_entry = self.parser.parse_log_line(line)
            if log_entry:
                self.logger.info(f"日志 {i+1}: IP={log_entry.get('src_ip', '')}, 方法={log_entry.get('method', '')}, URL={log_entry.get('url', '')}")
            else:
                self.logger.info(f"日志 {i+1}: 解析失败")
    
    def _filter_and_sort_entries(self, matched_entries: List[Dict]) -> List[Dict]:
        """过滤和排序匹配条目"""
        severity_priority = {'high': 3, 'medium': 2, 'low': 1}
        sorted_entries = sorted(
            matched_entries, 
            key=lambda x: severity_priority.get(x['match']['rule'].get('severity', 'low'), 0), 
            reverse=True
        )
        
        ai_config = self.config.get('ai_analysis', {})
        high_risk_only = ai_config.get('high_risk_only', True)
        successful_attacks_only = ai_config.get('successful_attacks_only', True) 
        success_status_codes = ai_config.get('success_status_codes', ['200', '201', '202', '204', '301', '302', '304'])
        high_risk_severity = ai_config.get('high_risk_severity', 'high')
        
        filtered_entries = []
        for entry in sorted_entries:
            if self._check_interrupted():
                break
            rule = entry['match']['rule']
            log_entry = entry['match']['log_entry']
            status_code = log_entry.get('status_code', log_entry.get('status', 'unknown'))
            should_analyze = True
            if high_risk_only and rule.get('severity') != high_risk_severity:
                should_analyze = False
            if should_analyze and successful_attacks_only:
                if status_code not in success_status_codes:
                    should_analyze = False
            if should_analyze:
                filtered_entries.append(entry)
                attack_type = "高风险成功攻击" if high_risk_only and successful_attacks_only else "安全事件"
                self.logger.info(f"发现{attack_type}: {rule['name']} - 状态码: {status_code} - IP: {log_entry.get('src_ip', 'unknown')}")
        
        return filtered_entries
    
    def _get_top_critical_entries(self, filtered_entries: List[Dict]) -> List[Dict]:
        """获取需要AI分析的前N个条目"""
        ai_config = self.config.get('ai_analysis', {})
        max_ai_analysis = ai_config.get('max_ai_analysis', 5)
        
        top_critical_entries = filtered_entries[:max_ai_analysis]
        self.logger.info(f"总计发现 {len(filtered_entries)} 个安全事件")
        self.logger.info(f"其中符合AI分析条件的事件 {len(filtered_entries)} 个")
        self.logger.info(f"将对TOP{len(top_critical_entries)}个事件进行AI深度分析")
        return top_critical_entries
    
    def _perform_ai_analysis(self, top_critical_entries: List[Dict]) -> List[str]:
        """执行增强的AI分析"""
        ai_results = []

        if not top_critical_entries:
            return ai_results

        ai_config = self.config.get('ai_analysis', {})
        high_risk_only = ai_config.get('high_risk_only', True)
        successful_attacks_only = ai_config.get('successful_attacks_only', True)

        attack_type = "高风险成功攻击" if high_risk_only and successful_attacks_only else "重要安全事件"

        if self.ai_enabled and self.ai_analyzer:
            self.logger.info(f"开始AI深度分析{attack_type}...")
            for i, entry in enumerate(top_critical_entries, 1):
                if self._check_interrupted():
                    break

                # 提取攻击信息用于增强AI分析
                rule = entry.get('match', {}).get('rule', {})
                threat_score = entry.get('threat_score')

                if threat_score:
                    # 使用新的威胁评分系统
                    attack_category = rule.get('category', 'unknown')
                    attack_name = rule.get('name', 'unknown attack')
                    score_value = threat_score.score
                    severity = threat_score.severity
                    confidence = threat_score.confidence

                    self.logger.info(f"AI分析进度: {i}/{len(top_critical_entries)} - {attack_name} "
                                   f"(评分: {score_value:.1f}/10.0, 严重度: {severity}, 置信度: {confidence:.1f})")

                    # 调用增强的AI分析接口
                    ai_result = self.ai_analyzer.analyze_log(
                        log_context=entry['context'],
                        attack_category=attack_category,
                        attack_name=attack_name,
                        threat_score=score_value
                    )
                else:
                    # 兼容旧版本格式
                    rule_name = rule.get('name', 'unknown attack')
                    src_ip = entry.get('match', {}).get('log_entry', {}).get('src_ip', 'unknown')
                    status = entry.get('match', {}).get('log_entry', {}).get('status_code',
                                entry.get('match', {}).get('log_entry', {}).get('status', 'unknown'))

                    self.logger.info(f"AI分析进度: {i}/{len(top_critical_entries)} - {rule_name} (IP: {src_ip}, 状态: {status})")
                    ai_result = self.ai_analyzer.analyze_log(entry['context'])

                ai_results.append(ai_result)
        elif not top_critical_entries:
            condition_desc = []
            if high_risk_only:
                condition_desc.append("高风险")
            if successful_attacks_only:
                condition_desc.append("攻击成功")
            self.logger.info(f"未发现符合条件的{'和'.join(condition_desc)}事件，跳过AI分析")

        return ai_results
    
    def _process_ip_statistics(self) -> tuple:
        """处理IP统计信息"""
        if not self._check_interrupted():
            internal_ips, external_ips = analyze_ip_access(list(self.ip_counter.elements()), self.config['geoip_db_path'])
            external_ip_details = []
            if external_ips:
                try:
                    locator = IPGeoLocator(self.config['geoip_db_path'])
                    for ip, count in list(external_ips.items())[:20]:
                        if self._check_interrupted():
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
        
        return internal_ips, external_ip_details

def main():
    parser = argparse.ArgumentParser(description='应急分析溯源日志工具')
    parser.add_argument('--config', default='config.yaml', help='配置文件路径')
    parser.add_argument('--ai', action='store_true', help='启用AI分析')
    parser.add_argument('--generate-rules', type=str, help='从日志样例生成解析规则')
    parser.add_argument('--server-ip', type=str, help='指定服务器主机IP地址')
    args = parser.parse_args()
    if args.generate_rules:
        log_hunter = LogHunter(args.config, ai_enabled=True)
        rules = log_hunter.ai_analyzer.generate_parsing_rules(args.generate_rules)
        if 'fields' in rules:
            success = log_hunter.update_log_format_config(rules['fields'])
            if success:
                print("日志解析规则已成功生成并更新到config.yaml")
            else:
                print("生成规则成功，但更新配置文件失败")
        else:
            print(f"生成解析规则失败: {rules.get('error', '未知错误')}")
        return
    server_ip = args.server_ip
    if not server_ip:
        print("="*50)
        print("欢迎使用应急分析溯源日志工具")
        print("="*50)
        while True:
            server_ip = input("请输入服务器主机IP地址（输入q退出）: ").strip()
            if server_ip.lower() == 'q':
                print("已退出程序。")
                return
            if server_ip:
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
    log_hunter = LogHunter(args.config, ai_enabled=args.ai, server_ip=server_ip)
    log_hunter.run()

if __name__ == "__main__":
    main()