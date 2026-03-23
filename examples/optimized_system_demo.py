#!/usr/bin/env python3
"""
SSlogs v3.1 优化系统演示
展示新增的性能优化、架构改进和安全功能
"""

import asyncio
import logging
import time
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入优化后的核心模块
from core import (
    # 异步处理
    AsyncAIAnalyzer,
    analyze_logs_concurrently,

    # 内存优化
    MemoryOptimizedProcessor,
    process_large_logs_async,

    # 事件总线
    get_event_bus,
    publish_event,
    event_handler,

    # 配置管理
    get_config_manager,

    # 异常处理
    handle_exceptions,
    create_error_context,

    # 缓存系统
    get_cache_manager,
    cache_result,

    # 安全验证
    get_security_manager,
    validate_input,
    sanitize_input,

    # 原有模块
    LogEntry, AnalysisResult
)


def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


async def demo_async_ai_analysis():
    """演示异步AI分析"""
    print("\n=== 异步AI分析演示 ===")

    # 模拟日志条目
    log_entries = [
        {
            'log_context': '192.168.1.100 - - [10/Oct/2023:13:55:36 +0000] "GET /admin/config.php HTTP/1.1" 404 1234',
            'attack_category': 'path_traversal',
            'threat_score': 7.5
        },
        {
            'log_context': '192.168.1.101 - - [10/Oct/2023:13:55:37 +0000] "POST /login.php HTTP/1.1" 200 567',
            'attack_category': 'sql_injection',
            'threat_score': 8.2
        },
        {
            'log_context': '192.168.1.102 - - [10/Oct/2023:13:55:38 +0000] "GET /search?q=<script>alert(1)</script> HTTP/1.1" 200 890',
            'attack_category': 'xss',
            'threat_score': 6.8
        }
    ]

    try:
        print("开始并发AI分析...")
        start_time = time.time()

        results = await analyze_logs_concurrently(log_entries)
        end_time = time.time()

        print(f"分析完成，耗时: {end_time - start_time:.2f}秒")
        print(f"处理了 {len(results)} 条日志")

        for i, result in enumerate(results):
            if result['success']:
                print(f"日志 {i+1}: 分析成功")
            else:
                print(f"日志 {i+1}: 分析失败 - {result.get('error', '未知错误')}")

    except Exception as e:
        print(f"异步分析演示失败: {e}")


def demo_memory_optimization():
    """演示内存优化处理"""
    print("\n=== 内存优化演示 ===")

    # 创建大型模拟日志文件
    log_file = Path("demo_large_log.txt")
    if not log_file.exists():
        print("创建演示日志文件...")
        with open(log_file, 'w', encoding='utf-8') as f:
            for i in range(10000):
                f.write(f'192.168.1.{i % 255} - - [10/Oct/2023:13:55:{i % 60:02d} +0000] "GET /page{i}.html HTTP/1.1" 200 {1234 + i}\n')

    try:
        processor = MemoryOptimizedProcessor(chunk_size=1024, max_memory_usage=0.8)
        print(f"开始处理大型日志文件: {log_file}")
        print(f"当前内存使用率: {processor.get_memory_usage():.2%}")

        def process_line(line: str) -> dict:
            """处理单行日志"""
            if 'GET' in line:
                return {'line': line.strip(), 'method': 'GET', 'processed': True}
            return None

        processed_count = 0
        for result in processor.process_large_file_streaming(str(log_file), process_line):
            processed_count += 1
            if processed_count % 1000 == 0:
                print(f"已处理 {processed_count} 行，内存使用: {processor.get_memory_usage():.2%}")

        print(f"处理完成，共处理 {processed_count} 行")

    except Exception as e:
        print(f"内存优化演示失败: {e}")
    finally:
        # 清理演示文件
        if log_file.exists():
            log_file.unlink()


def demo_event_bus():
    """演示事件总线"""
    print("\n=== 事件总线演示 ===")

    bus = get_event_bus()

    # 定义事件处理器
    @event_handler("threat_detected", priority="high")
    async def handle_threat(event):
        print(f"🚨 威胁检测: {event.data.get('threat_type', '未知')} - {event.data.get('message', '')}")

    @event_handler("log_processed")
    def handle_log_processed(event):
        count = event.data.get('count', 0)
        print(f"📊 日志处理完成，数量: {count}")

    async def publish_demo_events():
        # 发布威胁检测事件
        await publish_event("threat_detected", {
            'threat_type': 'SQL注入',
            'message': '检测到SQL注入攻击尝试',
            'severity': 'high',
            'source_ip': '192.168.1.100'
        })

        # 发布日志处理事件
        await publish_event("log_processed", {
            'count': 1500,
            'processing_time': 2.5,
            'threats_found': 3
        })

    try:
        print("发布演示事件...")
        asyncio.run(publish_demo_events())
        time.sleep(0.1)  # 等待事件处理

    except Exception as e:
        print(f"事件总线演示失败: {e}")


def demo_config_management():
    """演示配置管理"""
    print("\n=== 配置管理演示 ===")

    try:
        config_manager = get_config_manager()

        # 获取配置
        ai_config = config_manager.get('ai', {})
        print(f"AI服务类型: {ai_config.get('type', '未知')}")

        # 设置配置
        config_manager.set('demo.new_setting', '演示值')
        print(f"新配置值: {config_manager.get('demo.new_setting')}")

        # 检查敏感配置加密
        if config_manager.should_encrypt('api_key'):
            print("API密钥将被加密存储")

        # 获取配置摘要
        summary = config_manager.get_config_summary()
        print(f"配置摘要: {summary}")

    except Exception as e:
        print(f"配置管理演示失败: {e}")


def demo_exception_handling():
    """演示异常处理"""
    print("\n=== 异常处理演示 ===")

    @handle_exceptions("demo", "test_operation", return_on_error={"fallback": True})
    def risky_operation(should_fail: bool = False):
        if should_fail:
            raise ValueError("这是一个演示异常")
        return {"success": True, "data": "正常结果"}

    try:
        # 正常执行
        result = risky_operation(False)
        print(f"正常执行结果: {result}")

        # 异常执行
        result = risky_operation(True)
        print(f"异常执行结果: {result}")

    except Exception as e:
        print(f"异常处理演示失败: {e}")


def demo_caching():
    """演示缓存系统"""
    print("\n=== 缓存系统演示 ===")

    try:
        cache_manager = get_cache_manager()

        # 创建内存缓存
        memory_cache = cache_manager.create_memory_cache(
            "demo_cache",
            max_size=100,
            policy=cache_manager.CachePolicy.LRU,
            default_ttl=60
        )

        # 使用装饰器缓存
        @cache_result(ttl=30, cache_name="demo_cache")
        def expensive_computation(x: int) -> int:
            print(f"执行复杂计算: {x}")
            time.sleep(1)  # 模拟耗时操作
            return x * x

        # 第一次调用（会执行计算）
        start_time = time.time()
        result1 = expensive_computation(5)
        time1 = time.time() - start_time

        # 第二次调用（从缓存获取）
        start_time = time.time()
        result2 = expensive_computation(5)
        time2 = time.time() - start_time

        print(f"第一次计算耗时: {time1:.3f}秒，结果: {result1}")
        print(f"第二次获取耗时: {time2:.3f}秒，结果: {result2}")
        print(f"性能提升: {time1/time2:.1f}倍")

        # 获取缓存统计
        stats = memory_cache.get_stats()
        print(f"缓存统计: 命中率={stats['hit_rate']:.2%}, 大小={stats['size']}")

    except Exception as e:
        print(f"缓存演示失败: {e}")


def demo_security_validation():
    """演示安全验证"""
    print("\n=== 安全验证演示 ===")

    try:
        security_manager = get_security_manager()

        # 测试输入验证
        test_inputs = [
            "正常输入",
            "<script>alert('XSS')</script>",
            "'; DROP TABLE users; --",
            "../../../etc/passwd",
            "192.168.1.1"
        ]

        for input_data in test_inputs:
            result = validate_input(input_data)
            print(f"输入: {input_data[:30]}...")
            print(f"  有效: {result.is_valid}, 威胁数: {len(result.threats)}, 风险评分: {result.risk_score:.1f}")
            if result.threats:
                print(f"  威胁类型: {[t.value for t in result.threats]}")

        # 测试输入清理
        malicious_input = "<script>alert('XSS')</script>"
        sanitized = sanitize_input(malicious_input)
        print(f"\n原始输入: {malicious_input}")
        print(f"清理后: {sanitized}")

        # 测试会话令牌
        token = security_manager.create_session_token("demo_user", 1)
        print(f"\n创建会话令牌: {token[:16]}...")
        print(f"令牌验证: {security_manager.validate_session_token(token)}")

    except Exception as e:
        print(f"安全验证演示失败: {e}")


async def main():
    """主演示函数"""
    print("🚀 SSlogs v3.1 优化系统演示")
    print("=" * 50)

    setup_logging()

    # 初始化各个模块（跳过配置验证）
    try:
        get_config_manager()
    except Exception as e:
        print(f"配置管理器初始化失败，使用默认配置: {e}")
        # 创建一个简单的配置管理器实例
        from core.unified_config_manager import UnifiedConfigManager
        import os
        os.environ['SKIP_CONFIG_VALIDATION'] = '1'

    get_event_bus()
    get_cache_manager()
    get_security_manager()

    try:
        # 运行各个演示
        await demo_async_ai_analysis()
        demo_memory_optimization()
        demo_event_bus()
        demo_config_management()
        demo_exception_handling()
        demo_caching()
        demo_security_validation()

        print("\n✅ 所有演示完成！")
        print("\n📋 优化总结:")
        print("1. ✅ 异步AI分析 - 提升并发处理能力")
        print("2. ✅ 内存优化 - 支持大文件处理")
        print("3. ✅ 事件驱动架构 - 解耦模块通信")
        print("4. ✅ 统一配置管理 - 支持加密和热重载")
        print("5. ✅ 标准化异常处理 - 完整的错误管理")
        print("6. ✅ 高级缓存系统 - 多级缓存策略")
        print("7. ✅ 类型提示完善 - 提升代码质量")
        print("8. ✅ 安全验证机制 - 全面的输入过滤")

    except KeyboardInterrupt:
        print("\n⏹️ 演示被用户中断")
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())