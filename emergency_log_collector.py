#!/usr/bin/env python3
"""
应急日志收集工具 - 优化版本 v2.0
用于快速抓取access.log并打包到tmp文件夹
支持并发处理、配置管理、详细日志记录

特性:
- 🚀 并发文件复制，提升处理速度
- ⚙️  JSON配置文件支持
- 📊 详细的性能统计和压缩分析  
- 🗂️  智能路径搜索，支持深度限制
- 📝 完整的日志记录系统
- 🔒 自动sudo权限处理
- 💾 流式复制大文件，节省内存
- 📦 高效压缩，包含元数据信息

作者: Emergency Response Team
版本: 2.0.0
更新: 2025-07-28
"""

import os
import sys
import shutil
import gzip
import tarfile
import subprocess
import logging
import json
import glob
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import time

VERSION = "2.0.0"
AUTHOR = "Emergency Response Team"
UPDATE_DATE = "2025-07-28"

def print_banner():
    """打印工具横幅"""
    banner = f"""
╔══════════════════════════════════════════════════════════════╗
║                   🚨 应急日志收集工具 v{VERSION}                    ║
║                     Emergency Log Collector                 ║
╠══════════════════════════════════════════════════════════════╣
║ 🚀 快速收集系统中的access.log文件                              ║
║ 📦 自动打包压缩，便于传输和分析                                  ║
║ ⚙️  支持并发处理，智能权限管理                                   ║
║ 📊 提供详细统计信息和元数据                                     ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def print_help_info():
    """打印详细帮助信息"""
    help_text = f"""
🔧 使用方法:
    python emergency_log_collector.py [选项]

📋 命令行选项:
    -h, --help              显示帮助信息
    -c, --config FILE       指定配置文件路径 (JSON格式)
    -w, --max-workers N     设置最大并发线程数 (默认: 4)
    -s, --max-size N        设置单文件最大大小MB (默认: 100)
    -d, --depth N           设置搜索目录深度 (默认: 3)
    -v, --verbose           启用详细输出 (DEBUG级别日志)
    --version               显示版本信息

💡 使用示例:
    # 基本使用
    python emergency_log_collector.py
    
    # 使用配置文件
    python emergency_log_collector.py --config /path/to/config.json
    
    # 自定义参数
    python emergency_log_collector.py --max-workers 8 --depth 2 --verbose
    
    # 限制文件大小
    python emergency_log_collector.py --max-size 50 --verbose

📁 配置文件格式 (JSON):
{{
    "tmp_dir": "/tmp/emergency_logs",      # 临时目录
    "max_workers": 4,                      # 并发线程数
    "max_file_size_mb": 100,              # 最大文件大小(MB)
    "search_depth": 3,                     # 搜索深度
    "log_level": "INFO",                   # 日志级别
    "additional_paths": [                  # 额外搜索路径
        "/var/log/custom/*.log",
        "/opt/app/logs/access*.log"
    ]
}}

🔍 工具会搜索以下位置:
    ✓ /var/log/apache2/access.log*
    ✓ /var/log/nginx/access.log*
    ✓ /var/log/httpd/access.log*
    ✓ /opt/lampp/logs/access_log
    ✓ 当前目录及子目录中的 *access*.log* 文件
    ✓ 用户主目录中的 *access*.log* 文件
    ✓ 配置文件中指定的额外路径

⚡ 性能特性:
    🔄 多线程并发复制文件
    💾 大文件流式处理，节省内存
    📏 智能文件大小过滤
    🎯 限制搜索深度，避免过度扫描
    🗜️  高效gzip压缩

📊 输出信息:
    📦 生成压缩包: /tmp/access_logs_YYYYMMDD_HHMMSS.tar.gz
    📝 详细日志: /tmp/emergency_collector_YYYYMMDD_HHMMSS.log
    📋 元数据文件: logs/collection_metadata.json (在压缩包内)

🔐 权限处理:
    ✓ 自动检测文件读取权限
    ✓ 对无权限文件尝试sudo复制
    ✓ 复制后自动修正文件所有者

⚠️  注意事项:
    • 需要足够的磁盘空间存储临时文件和压缩包
    • 某些系统文件可能需要管理员权限
    • 大文件处理可能需要较长时间
    • 压缩包会包含完整的目录结构

📞 技术支持:
    作者: {AUTHOR}
    版本: v{VERSION}
    更新: {UPDATE_DATE}
    
    如有问题请联系系统管理员或安全团队
"""
    print(help_text)

class EmergencyLogCollector:
    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.tmp_dir = Path(self.config.get('tmp_dir', '/tmp/emergency_logs'))
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.package_name = f"access_logs_{self.timestamp}.tar.gz"
        self.max_workers = self.config.get('max_workers', 4)
        self.max_file_size = self.config.get('max_file_size_mb', 100) * 1024 * 1024  # 转换为字节
        self.search_depth = self.config.get('search_depth', 3)
        self._setup_logging()
        self.stats = {
            'found_files': 0,
            'copied_files': 0,
            'failed_files': 0,
            'total_size': 0,
            'start_time': time.time()
        }
        
    def _load_config(self, config_path: Optional[str]) -> Dict:
        """加载配置文件"""
        default_config = {
            'tmp_dir': '/tmp/emergency_logs',
            'max_workers': 4,
            'max_file_size_mb': 100,
            'search_depth': 3,
            'log_level': 'INFO',
            'additional_paths': []
        }
        
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
            except Exception as e:
                print(f"警告: 无法加载配置文件 {config_path}: {e}")
        
        return default_config
    
    def _setup_logging(self):
        """设置日志记录"""
        log_level = getattr(logging, self.config.get('log_level', 'INFO').upper())
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(f'/tmp/emergency_collector_{self.timestamp}.log')
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    @lru_cache(maxsize=128)
    def _get_common_log_paths(self) -> List[str]:
        """获取常见日志路径 - 缓存结果"""
        base_paths = [
            "/var/log/apache2/access.log",
            "/var/log/httpd/access.log",
            "/var/log/nginx/access.log",
            "/var/log/apache2/access.log.1",
            "/var/log/httpd/access_log",
            "/var/log/nginx/access.log.1",
            "/var/log/lighttpd/access.log",
            "/var/log/caddy/access.log",
            "/opt/lampp/logs/access_log",
            "/usr/local/apache2/logs/access.log",
            "/var/log/httpd/access.log-*.gz",
            "/var/log/nginx/access.log-*.gz",
            "/var/log/apache2/access.log-*.gz"
        ]
        
        # 添加用户配置的额外路径
        base_paths.extend(self.config.get('additional_paths', []))
        return base_paths
    
    def find_access_logs(self) -> List[Path]:
        """查找系统中的access.log文件 - 优化版本"""
        self.logger.info("开始查找access.log文件...")
        found_logs: Set[Path] = set()
        
        # 1. 查找常见路径
        common_paths = self._get_common_log_paths()
        for path_str in common_paths:
            try:
                if '*' in path_str:
                    # 处理通配符
                    matches = glob.glob(path_str)
                    found_logs.update(Path(m) for m in matches if Path(m).is_file())
                else:
                    path = Path(path_str)
                    if path.exists() and path.is_file():
                        found_logs.add(path)
            except Exception as e:
                self.logger.warning(f"检查路径失败 {path_str}: {e}")
        
        # 2. 限制深度的递归搜索
        search_dirs = [Path.cwd(), Path.home()]
        for search_dir in search_dirs:
            try:
                found_logs.update(self._search_logs_with_depth(search_dir, self.search_depth))
            except Exception as e:
                self.logger.warning(f"搜索目录失败 {search_dir}: {e}")
        
        # 3. 过滤文件大小
        filtered_logs = []
        for log_file in found_logs:
            try:
                if log_file.stat().st_size <= self.max_file_size:
                    filtered_logs.append(log_file)
                else:
                    self.logger.warning(f"文件过大，跳过: {log_file} ({log_file.stat().st_size/1024/1024:.1f}MB)")
            except Exception as e:
                self.logger.warning(f"检查文件大小失败 {log_file}: {e}")
        
        self.stats['found_files'] = len(filtered_logs)
        self.logger.info(f"找到 {len(filtered_logs)} 个日志文件")
        return filtered_logs
    
    def _search_logs_with_depth(self, root_dir: Path, max_depth: int) -> Set[Path]:
        """限制深度的日志文件搜索"""
        found_logs: Set[Path] = set()
        
        def _recursive_search(current_dir: Path, current_depth: int):
            if current_depth > max_depth:
                return
            
            try:
                for item in current_dir.iterdir():
                    if item.is_file() and ('access' in item.name.lower() and 
                                          ('.log' in item.suffix or '.gz' in item.suffixes)):
                        found_logs.add(item)
                    elif item.is_dir() and not item.is_symlink():
                        _recursive_search(item, current_depth + 1)
            except (PermissionError, OSError):
                pass  # 忽略权限错误
        
        _recursive_search(root_dir, 0)
        return found_logs
    
    def check_permissions(self, log_path: Path) -> bool:
        """检查文件读取权限"""
        try:
            return os.access(log_path, os.R_OK) and log_path.is_file()
        except Exception as e:
            self.logger.debug(f"权限检查失败 {log_path}: {e}")
            return False
    
    def _copy_single_file(self, log_file: Path) -> Optional[Path]:
        """复制单个文件 - 支持并发调用"""
        if not self.check_permissions(log_file):
            self.logger.warning(f"无权限读取文件: {log_file}")
            return None
        
        try:
            # 创建相对路径结构
            rel_path = log_file.relative_to("/") if log_file.is_absolute() else log_file
            dest_path = self.tmp_dir / rel_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 流式复制大文件
            if log_file.stat().st_size > 10 * 1024 * 1024:  # 10MB以上使用流式复制
                self._stream_copy(log_file, dest_path)
            else:
                shutil.copy2(log_file, dest_path)
            
            file_size = dest_path.stat().st_size
            self.stats['total_size'] += file_size
            self.stats['copied_files'] += 1
            
            self.logger.info(f"复制成功: {log_file} -> {dest_path} ({file_size/1024:.1f}KB)")
            return dest_path
            
        except Exception as e:
            self.stats['failed_files'] += 1
            self.logger.error(f"复制失败: {log_file} - {e}")
            return None
    
    def _stream_copy(self, src: Path, dest: Path, chunk_size: int = 1024*1024):
        """流式复制大文件"""
        with open(src, 'rb') as fsrc, open(dest, 'wb') as fdest:
            while True:
                chunk = fsrc.read(chunk_size)
                if not chunk:
                    break
                fdest.write(chunk)
    
    def copy_logs(self, log_files: List[Path]) -> List[Path]:
        """并发复制日志文件到临时目录"""
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        copied_files = []
        
        self.logger.info(f"开始复制 {len(log_files)} 个文件，使用 {self.max_workers} 个线程")
        
        # 使用线程池并发复制
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有复制任务
            future_to_file = {executor.submit(self._copy_single_file, log_file): log_file 
                            for log_file in log_files}
            
            # 收集结果
            for future in as_completed(future_to_file):
                result = future.result()
                if result:
                    copied_files.append(result)
        
        self.logger.info(f"复制完成: 成功 {len(copied_files)} 个，失败 {self.stats['failed_files']} 个")
        return copied_files
    
    def create_package(self, log_files: List[Path]) -> Optional[Path]:
        """创建压缩包 - 优化版本"""
        if not log_files:
            self.logger.error("没有找到可复制的日志文件")
            return None
        
        package_path = Path("/tmp") / self.package_name
        
        try:
            self.logger.info(f"开始创建压缩包: {package_path}")
            
            with tarfile.open(package_path, "w:gz", compresslevel=6) as tar:
                # 添加元数据文件
                self._create_metadata_file()
                tar.add(self.tmp_dir, arcname="logs")
            
            package_size = package_path.stat().st_size
            compression_ratio = (self.stats['total_size'] / package_size) if package_size > 0 else 0
            
            # 清理临时目录
            shutil.rmtree(self.tmp_dir, ignore_errors=True)
            
            self.logger.info(f"压缩包创建成功: {package_path}")
            self.logger.info(f"压缩前: {self.stats['total_size']/1024/1024:.2f}MB, "
                           f"压缩后: {package_size/1024/1024:.2f}MB, "
                           f"压缩比: {compression_ratio:.1f}:1")
            return package_path
            
        except Exception as e:
            self.logger.error(f"创建压缩包失败: {e}")
            return None
    
    def _create_metadata_file(self):
        """创建元数据文件"""
        metadata = {
            'collection_time': datetime.now().isoformat(),
            'hostname': os.uname().nodename,
            'total_files': self.stats['copied_files'],
            'total_size_bytes': self.stats['total_size'],
            'collection_duration_seconds': time.time() - self.stats['start_time'],
            'config': self.config
        }
        
        metadata_path = self.tmp_dir / 'collection_metadata.json'
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    def print_summary(self):
        """打印收集摘要"""
        duration = time.time() - self.stats['start_time']
        print("\n" + "=" * 60)
        print("📊 收集摘要")
        print("=" * 60)
        print(f"⏱️  耗时: {duration:.2f} 秒")
        print(f"📁 发现文件: {self.stats['found_files']} 个")
        print(f"✅ 成功复制: {self.stats['copied_files']} 个")
        print(f"❌ 复制失败: {self.stats['failed_files']} 个")
        print(f"📦 总大小: {self.stats['total_size']/1024/1024:.2f} MB")
        print(f"⚡ 平均速度: {(self.stats['total_size']/1024/1024)/duration:.2f} MB/s")
        print("=" * 60)
    
    def run_sudo_copy(self, log_files: List[Path]) -> List[Path]:
        """使用sudo权限复制需要特权的日志 - 优化版本"""
        sudo_logs = [log_file for log_file in log_files if not self.check_permissions(log_file)]
        
        if not sudo_logs:
            return []
        
        self.logger.info(f"检测到 {len(sudo_logs)} 个需要sudo权限的文件")
        
        # 检查sudo可用性
        try:
            subprocess.run(["sudo", "-n", "true"], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            self.logger.warning("sudo需要密码或不可用，跳过特权文件复制")
            return []
        
        sudo_copied = []
        for log_file in sudo_logs:
            try:
                dest_path = self.tmp_dir / log_file.name
                cmd = ["sudo", "cp", str(log_file), str(dest_path)]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    # 修改文件权限
                    subprocess.run(["sudo", "chown", f"{os.getuid()}:{os.getgid()}", str(dest_path)], 
                                 capture_output=True)
                    sudo_copied.append(dest_path)
                    self.stats['copied_files'] += 1
                    self.logger.info(f"sudo复制成功: {log_file}")
                else:
                    self.stats['failed_files'] += 1
                    self.logger.error(f"sudo复制失败: {log_file} - {result.stderr}")
            except subprocess.TimeoutExpired:
                self.logger.error(f"sudo复制超时: {log_file}")
            except Exception as e:
                self.logger.error(f"sudo命令失败: {e}")
        
        return sudo_copied
    
    def run(self) -> bool:
        """主运行函数 - 优化版本"""
        try:
            self.logger.info("应急日志收集工具启动")
            print("🚨 应急日志收集工具启动...")
            print("=" * 50)
            
            # 查找日志文件
            log_files = self.find_access_logs()
            
            if not log_files:
                self.logger.warning("未找到任何access.log文件")
                print("❌ 未找到任何access.log文件")
                return False
            
            print(f"📁 找到 {len(log_files)} 个日志文件")
            
            # 显示权限状态
            accessible_files = [f for f in log_files if self.check_permissions(f)]
            restricted_files = [f for f in log_files if not self.check_permissions(f)]
            
            if accessible_files:
                print(f"✅ 可直接访问: {len(accessible_files)} 个")
            if restricted_files:
                print(f"🔐 需要特权访问: {len(restricted_files)} 个")
            
            # 复制有权限的文件
            copied_files = self.copy_logs(accessible_files) if accessible_files else []
            
            # 尝试使用sudo复制需要特权的文件
            if restricted_files:
                sudo_copied = self.run_sudo_copy(restricted_files)
                copied_files.extend(sudo_copied)
            
            if not copied_files:
                self.logger.error("没有成功复制任何日志文件")
                print("❌ 没有成功复制任何日志文件")
                return False
            
            # 创建压缩包
            package_path = self.create_package(copied_files)
            
            if package_path:
                print("\n🎉 应急日志收集完成！")
                self.print_summary()
                print(f"📦 压缩包位置: {package_path}")
                print(f"📝 日志文件: /tmp/emergency_collector_{self.timestamp}.log")
                print("\n💡 使用说明:")
                print(f"   解压命令: tar -xzf {package_path}")
                print(f"   查看内容: tar -tzf {package_path}")
                print(f"   查看元数据: tar -xzf {package_path} logs/collection_metadata.json -O")
                return True
            else:
                self.logger.error("创建压缩包失败")
                print("❌ 创建压缩包失败")
                return False
                
        except Exception as e:
            self.logger.error(f"运行过程中发生错误: {e}")
            print(f"❌ 运行失败: {e}")
            return False

def generate_config_template():
    """生成配置文件模板"""
    template = {
        "tmp_dir": "/tmp/emergency_logs",
        "max_workers": 4,
        "max_file_size_mb": 100,
        "search_depth": 3,
        "log_level": "INFO",
        "additional_paths": [
            "/var/log/custom/*.log",
            "/opt/app/logs/access*.log",
            "/home/*/logs/*access*.log"
        ]
    }
    
    config_path = "emergency_collector_config.json"
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(template, f, indent=4, ensure_ascii=False)
    
    print(f"✅ 配置文件模板已生成: {config_path}")
    print("📝 请根据需要修改配置参数，然后使用 --config 参数指定配置文件")
    return config_path

def main():
    """主函数 - 支持命令行参数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        prog='emergency_log_collector.py',
        description=f'应急日志收集工具 v{VERSION} - 快速收集和打包access.log文件',
        epilog="""
示例用法:
  %(prog)s                                    # 使用默认配置
  %(prog)s --verbose                          # 启用详细输出
  %(prog)s --config myconfig.json             # 使用配置文件
  %(prog)s --max-workers 8 --depth 2          # 自定义参数
  %(prog)s --generate-config                  # 生成配置文件模板
  %(prog)s --help-detailed                    # 显示详细帮助

更多信息请访问: https://github.com/emergency-response/log-collector
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--version', action='version', 
                       version=f'%(prog)s v{VERSION} by {AUTHOR} ({UPDATE_DATE})')
    
    parser.add_argument('--config', '-c', type=str, metavar='FILE',
                       help='配置文件路径 (JSON格式)')
    
    parser.add_argument('--max-workers', '-w', type=int, default=4, metavar='N',
                       help='最大并发线程数 (默认: %(default)s)')
    
    parser.add_argument('--max-size', '-s', type=int, default=100, metavar='N',
                       help='单文件最大大小MB (默认: %(default)s)')
    
    parser.add_argument('--depth', '-d', type=int, default=3, metavar='N',
                       help='搜索目录深度 (默认: %(default)s)')
    
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='启用详细输出 (DEBUG级别日志)')
    
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='静默模式，只输出错误信息')
    
    parser.add_argument('--no-banner', action='store_true',
                       help='不显示程序横幅')
    
    parser.add_argument('--generate-config', action='store_true',
                       help='生成配置文件模板并退出')
    
    parser.add_argument('--help-detailed', action='store_true',
                       help='显示详细帮助信息')
    
    parser.add_argument('--dry-run', action='store_true',
                       help='试运行模式，只显示会收集的文件，不实际复制')
    
    args = parser.parse_args()
    
    # 处理特殊命令
    if args.help_detailed:
        print_help_info()
        return 0
    
    if args.generate_config:
        generate_config_template()
        return 0
    
    # 显示横幅
    if not args.no_banner and not args.quiet:
        print_banner()
    
    # 动态配置
    config_override = {}
    if args.max_workers:
        config_override['max_workers'] = args.max_workers
    if args.max_size:
        config_override['max_file_size_mb'] = args.max_size
    if args.depth:
        config_override['search_depth'] = args.depth
    if args.verbose:
        config_override['log_level'] = 'DEBUG'
    elif args.quiet:
        config_override['log_level'] = 'ERROR'
    
    try:
        collector = EmergencyLogCollector(args.config)
        
        # 应用命令行覆盖
        collector.config.update(config_override)
        collector._setup_logging()  # 重新设置日志级别
        
        # 试运行模式
        if args.dry_run:
            print("🔍 试运行模式 - 扫描可收集的文件:")
            print("=" * 50)
            log_files = collector.find_access_logs()
            
            if not log_files:
                print("❌ 未找到任何access.log文件")
                return 1
            
            accessible_files = [f for f in log_files if collector.check_permissions(f)]
            restricted_files = [f for f in log_files if not collector.check_permissions(f)]
            
            total_size = 0
            print(f"\n✅ 可直接访问的文件 ({len(accessible_files)} 个):")
            for i, file_path in enumerate(accessible_files, 1):
                try:
                    size = file_path.stat().st_size
                    total_size += size
                    print(f"  {i:2d}. {file_path} ({size/1024:.1f}KB)")
                except:
                    print(f"  {i:2d}. {file_path} (大小未知)")
            
            if restricted_files:
                print(f"\n🔐 需要sudo权限的文件 ({len(restricted_files)} 个):")
                for i, file_path in enumerate(restricted_files, 1):
                    print(f"  {i:2d}. {file_path}")
            
            print(f"\n📊 统计信息:")
            print(f"   总文件数: {len(log_files)} 个")
            print(f"   预计大小: {total_size/1024/1024:.2f} MB")
            print(f"   使用配置: {args.config or '默认配置'}")
            print(f"   并发数: {collector.config['max_workers']} 个线程")
            print(f"   搜索深度: {collector.config['search_depth']} 层")
            print("\n💡 使用 --verbose 查看详细信息，去掉 --dry-run 开始实际收集")
            
            return 0
        
        # 正常运行
        success = collector.run()
        return 0 if success else 1
        
    except KeyboardInterrupt:
        if not args.quiet:
            print("\n⚠️ 操作被用户中断")
        return 130
        
    except Exception as e:
        if not args.quiet:
            print(f"\n💥 程序异常: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())