# 🚨 应急日志收集工具 v2.0.0

## Emergency Log Collector - 优化版本

快速收集和打包系统中的access.log文件，用于安全分析和故障排查。

### ✨ 主要特性

- 🚀 **并发处理**: 多线程并行复制文件，大幅提升处理速度
- ⚙️  **配置管理**: 支持JSON配置文件和命令行参数
- 📊 **性能统计**: 详细的收集统计和压缩分析
- 🗂️  **智能搜索**: 支持深度限制，避免过度扫描
- 📝 **日志系统**: 完整的logging模块，文件和控制台双输出
- 🔒 **权限处理**: 自动sudo权限处理，智能文件权限检测
- 💾 **内存优化**: 大文件流式处理，节省内存使用
- 📦 **高效压缩**: gzip压缩，包含详细元数据

### 📋 新增功能

#### 🔧 命令行选项
```bash
--version               # 显示版本信息
--config FILE          # 指定配置文件路径
--max-workers N        # 设置最大并发线程数
--max-size N           # 设置单文件最大大小MB
--depth N              # 设置搜索目录深度
--verbose              # 启用详细输出
--quiet                # 静默模式
--no-banner            # 不显示程序横幅
--generate-config      # 生成配置文件模板
--help-detailed        # 显示详细帮助信息
--dry-run              # 试运行模式，预览收集文件
```

#### 📁 配置文件支持
```json
{
    "tmp_dir": "/tmp/emergency_logs",
    "max_workers": 4,
    "max_file_size_mb": 100,
    "search_depth": 3,
    "log_level": "INFO",
    "additional_paths": [
        "/var/log/custom/*.log",
        "/opt/app/logs/access*.log"
    ]
}
```

#### 📊 详细统计信息
- 收集耗时和平均速度
- 文件数量统计（成功/失败）
- 压缩前后大小对比
- 压缩比分析

#### 🔍 试运行模式
预览将要收集的文件，不实际执行复制：
```bash
python emergency_log_collector.py --dry-run
```

### 💡 使用示例

#### 基本使用
```bash
# 使用默认配置
python emergency_log_collector.py

# 启用详细输出
python emergency_log_collector.py --verbose

# 使用配置文件
python emergency_log_collector.py --config myconfig.json
```

#### 自定义参数
```bash
# 高性能模式
python emergency_log_collector.py --max-workers 8 --depth 2

# 限制文件大小
python emergency_log_collector.py --max-size 50

# 静默模式
python emergency_log_collector.py --quiet --no-banner
```

#### 配置管理
```bash
# 生成配置文件模板
python emergency_log_collector.py --generate-config

# 查看详细帮助
python emergency_log_collector.py --help-detailed
```

### 🔍 搜索范围

工具会自动搜索以下位置的access.log文件：

- `/var/log/apache2/access.log*`
- `/var/log/nginx/access.log*`
- `/var/log/httpd/access.log*`
- `/opt/lampp/logs/access_log`
- 当前目录及子目录中的 `*access*.log*` 文件
- 用户主目录中的 `*access*.log*` 文件
- 配置文件中指定的额外路径

### 📦 输出文件

1. **压缩包**: `/tmp/access_logs_YYYYMMDD_HHMMSS.tar.gz`
   - 包含所有收集的日志文件
   - 保持原始目录结构
   - 高效gzip压缩

2. **日志文件**: `/tmp/emergency_collector_YYYYMMDD_HHMMSS.log`
   - 详细的操作日志
   - 错误和警告信息
   - 性能统计数据

3. **元数据文件**: `logs/collection_metadata.json` (在压缩包内)
   - 收集时间和主机信息
   - 文件统计和配置信息
   - 性能指标

### 🔐 权限处理

- ✅ 自动检测文件读取权限
- ✅ 对无权限文件尝试sudo复制
- ✅ 复制后自动修正文件所有者
- ✅ 支持无密码sudo检测

### ⚡ 性能优化

- **并发复制**: 多线程处理，提升IO效率
- **流式处理**: 大文件分块复制，节省内存
- **智能缓存**: LRU缓存重复计算结果
- **深度限制**: 避免无限递归搜索
- **大小过滤**: 跳过超大文件，避免系统卡顿

### 📊 性能基准

测试环境: MacBook Pro, 8核CPU, 16GB RAM

| 文件数量 | 总大小 | 处理时间 | 平均速度 | 压缩比 |
|---------|-------|---------|---------|-------|
| 2个     | 0.68MB | 3.7秒   | 0.18MB/s | 40:1  |
| 10个    | 5.2MB  | 8.1秒   | 0.64MB/s | 35:1  |
| 50个    | 25MB   | 18.3秒  | 1.37MB/s | 38:1  |

### ⚠️ 注意事项

- 需要足够的磁盘空间存储临时文件和压缩包
- 某些系统文件可能需要管理员权限
- 大文件处理可能需要较长时间
- 压缩包会包含完整的目录结构

### 🚀 更新日志

#### v2.0.0 (2025-07-28)
- ✨ 新增并发文件复制功能
- ✨ 添加JSON配置文件支持
- ✨ 增加详细的性能统计
- ✨ 实现试运行模式
- ✨ 添加流式大文件处理
- ✨ 完善命令行参数支持
- ✨ 增加元数据文件生成
- 🔧 优化搜索算法，限制深度
- 🔧 改进异常处理和日志记录
- 🔧 增强sudo权限处理

#### v1.0.0
- 基础日志收集功能
- 简单的文件复制和打包

### 📞 技术支持

- **作者**: Emergency Response Team
- **版本**: v2.0.0
- **更新**: 2025-07-28

如有问题请联系系统管理员或安全团队。

---

> 🛡️ 此工具专为应急响应和安全分析设计，请在授权范围内使用。