# 废弃文件说明

此目录包含已废弃的优化版本文件，这些文件的功能已经合并到主模块中。

## 废弃文件列表

### parser_optimized.py
- **状态**: 已废弃
- **替代**: `parser.py` (已包含所有优化功能)
- **说明**: 原优化版本已合并到主解析器，包括缓存机制和性能优化

### reporter_optimized.py
- **状态**: 已废弃
- **替代**: `reporter.py` (已包含所有优化功能)
- **说明**: 原优化版本已合并到主报告生成器，包括LRU缓存和模板优化

### performance_test.py
- **状态**: 已废弃
- **说明**: 性能对比测试脚本，由于优化已合并到主模块，此脚本不再需要

## 迁移指南

如果您的代码仍在使用这些废弃文件，请进行以下替换：

1. `from core.parser_optimized import LogParser`
   → `from core.parser import LogParser`

2. `from core.reporter_optimized import ReportGenerator`
   → `from core.reporter import ReportGenerator`

3. 删除或更新对 `performance_test.py` 的引用

## 保留的优化模块

以下优化模块仍在使用中，**不是废弃文件**：

- `memory_optimized_processor.py` - 内存优化处理器
- `async_ai_analyzer.py` - 异步AI分析器
- `advanced_cache.py` - 高级缓存系统
- `event_bus.py` - 事件总线

## 清理计划

这些废弃文件将在下一个主要版本 (v4.0.0) 中完全移除。
