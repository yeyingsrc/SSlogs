# 🚨 应急日志收集工具

## 简介
这是一个专为应急场景设计的快速日志收集工具，能够自动查找并打包系统中的所有access.log文件。

## 使用方法

### 快速启动
```bash
python3 emergency_log_collector.py
```

### 功能特点
- 🔍 **自动扫描**: 自动查找系统中常见的access.log位置
- 🔐 **权限处理**: 支持sudo权限复制需要特权的日志
- 📦 **自动打包**: 自动创建压缩包到/tmp目录
- 📊 **实时统计**: 显示收集的文件数量和总大小

### 支持的日志位置
- Apache: `/var/log/apache2/access.log*`
- Nginx: `/var/log/nginx/access.log*`
- Httpd: `/var/log/httpd/access.log*`
- Lighttpd: `/var/log/lighttpd/access.log`
- Caddy: `/var/log/caddy/access.log`
- 用户目录: `~/access.log*`
- 当前目录: `./access.log*`

### 输出文件
压缩包将保存在 `/tmp/access_logs_YYYYMMDD_HHMMSS.tar.gz`

### 使用示例
```bash
# 运行工具
python3 emergency_log_collector.py

# 查看生成的文件
ls -la /tmp/access_logs_*.tar.gz

# 解压查看内容
tar -xzf /tmp/access_logs_20250723_112620.tar.gz
tar -tzf /tmp/access_logs_20250723_112620.tar.gz
```

### 注意事项
- 需要Python 3.6+环境
- 部分系统日志可能需要sudo权限
- 压缩包会自动包含原始目录结构
- 临时文件会在压缩后自动清理

## 应急场景使用
在发生安全事件或系统故障时，立即运行此工具可以快速收集所有access.log文件，便于后续分析和取证。