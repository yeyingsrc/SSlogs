import mmap
import gc
import os
import psutil
import logging
from typing import Iterator, Dict, Any, Optional, AsyncIterator, Generator
from pathlib import Path
import asyncio
import aiofiles
import asyncio


class MemoryOptimizedProcessor:
    """内存优化的大文件处理器"""

    def __init__(self, chunk_size: int = 8192, max_memory_usage: float = 0.8):
        self.chunk_size = chunk_size
        self.max_memory_usage = max_memory_usage  # 最大内存使用率
        self.logger = logging.getLogger(__name__)

    def get_memory_usage(self) -> float:
        """获取当前内存使用率"""
        return psutil.virtual_memory().percent / 100.0

    def check_memory_pressure(self) -> bool:
        """检查内存压力是否过高"""
        return self.get_memory_usage() > self.max_memory_usage

    def force_garbage_collection(self):
        """强制垃圾回收"""
        gc.collect()
        self.logger.debug("执行垃圾回收")

    def read_file_mmap(self, file_path: str) -> Iterator[str]:
        """使用内存映射读取大文件"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mmapped_file:
                    buffer = ''
                    while True:
                        chunk = mmapped_file.read(self.chunk_size).decode('utf-8', errors='ignore')
                        if not chunk:
                            if buffer:
                                yield buffer
                            break

                        # 按行分割
                        lines = (buffer + chunk).split('\n')
                        buffer = lines[-1]  # 保留最后一个不完整的行

                        for line in lines[:-1]:
                            if line.strip():  # 跳过空行
                                yield line

        except Exception as e:
            self.logger.error(f"内存映射读取文件失败 {file_path}: {e}")
            # 降级到普通文件读取
            yield from self.read_file_chunks(file_path)

    def read_file_chunks(self, file_path: str) -> Iterator[str]:
        """分块读取大文件"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                buffer = ''
                while True:
                    chunk = f.read(self.chunk_size)
                    if not chunk:
                        if buffer:
                            yield buffer
                        break

                    # 按行分割
                    lines = (buffer + chunk).split('\n')
                    buffer = lines[-1]

                    for line in lines[:-1]:
                        if line.strip():
                            yield line

                    # 定期检查内存使用情况
                    if self.check_memory_pressure():
                        self.force_garbage_collection()

        except Exception as e:
            self.logger.error(f"分块读取文件失败 {file_path}: {e}")
            raise

    async def read_file_async(self, file_path: str) -> AsyncIterator[str]:
        """异步读取文件"""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                buffer = ''
                while True:
                    chunk = await f.read(self.chunk_size)
                    if not chunk:
                        if buffer:
                            yield buffer
                        break

                    lines = (buffer + chunk).split('\n')
                    buffer = lines[-1]

                    for line in lines[:-1]:
                        if line.strip():
                            yield line

                    # 异步检查内存压力
                    if self.check_memory_pressure():
                        await asyncio.to_thread(self.force_garbage_collection)

        except Exception as e:
            self.logger.error(f"异步读取文件失败 {file_path}: {e}")
            raise

    def process_large_file_streaming(self, file_path: str, processor_func) -> Iterator[Dict[str, Any]]:
        """流式处理大文件"""
        processed_count = 0
        batch_size = 100  # 批处理大小
        batch = []

        try:
            for line in self.read_file_mmap(file_path):
                batch.append(line)
                processed_count += 1

                # 批处理
                if len(batch) >= batch_size:
                    yield from self._process_batch(batch, processor_func)
                    batch = []

                    # 定期垃圾回收
                    if processed_count % 1000 == 0:
                        self.force_garbage_collection()
                        self.logger.info(f"已处理 {processed_count} 行，内存使用: {self.get_memory_usage():.2%}")

            # 处理最后一批
            if batch:
                yield from self._process_batch(batch, processor_func)

        except Exception as e:
            self.logger.error(f"流式处理文件失败 {file_path}: {e}")
            raise

    def _process_batch(self, batch: list, processor_func) -> Iterator[Dict[str, Any]]:
        """处理一批数据"""
        try:
            for item in batch:
                try:
                    result = processor_func(item)
                    if result:
                        yield result
                except Exception as e:
                    self.logger.warning(f"处理单条数据失败: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"批处理失败: {e}")
            raise

    async def process_large_file_async(self, file_path: str, processor_func) -> AsyncIterator[Dict[str, Any]]:
        """异步流式处理大文件"""
        processed_count = 0
        batch_size = 100
        batch = []

        try:
            async for line in self.read_file_async(file_path):
                batch.append(line)
                processed_count += 1

                if len(batch) >= batch_size:
                    async for result in self._process_batch_async(batch, processor_func):
                        yield result
                    batch = []

                    if processed_count % 1000 == 0:
                        await asyncio.to_thread(self.force_garbage_collection)
                        self.logger.info(f"异步已处理 {processed_count} 行，内存使用: {self.get_memory_usage():.2%}")

            if batch:
                async for result in self._process_batch_async(batch, processor_func):
                    yield result

        except Exception as e:
            self.logger.error(f"异步流式处理文件失败 {file_path}: {e}")
            raise

    async def _process_batch_async(self, batch: list, processor_func) -> AsyncIterator[Dict[str, Any]]:
        """异步处理一批数据"""
        try:
            # 并发处理批次中的项目
            tasks = []
            for item in batch:
                if asyncio.iscoroutinefunction(processor_func):
                    task = processor_func(item)
                else:
                    task = asyncio.to_thread(processor_func, item)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    self.logger.warning(f"异步处理单条数据失败: {result}")
                    continue
                if result:
                    yield result

        except Exception as e:
            self.logger.error(f"异步批处理失败: {e}")
            raise


class MemoryEfficientLogProcessor:
    """内存高效的日志处理器"""

    def __init__(self, memory_limit_mb: int = 1024):
        self.memory_limit_bytes = memory_limit_mb * 1024 * 1024
        self.current_memory_usage = 0
        self.logger = logging.getLogger(__name__)

    def estimate_line_memory(self, line: str) -> int:
        """估算一行日志占用的内存"""
        # 粗略估算：字符数 * 2 bytes (UTF-8编码) + 对象开销
        return len(line.encode('utf-8')) + 200

    def can_process_line(self, line: str) -> bool:
        """检查是否可以处理该行（内存限制）"""
        line_memory = self.estimate_line_memory(line)
        if self.current_memory_usage + line_memory > self.memory_limit_bytes:
            return False
        return True

    def process_lines_with_limit(self, lines: Iterator[str], processor_func) -> Iterator[Dict[str, Any]]:
        """在内存限制下处理日志行"""
        for line in lines:
            if self.can_process_line(line):
                line_memory = self.estimate_line_memory(line)
                self.current_memory_usage += line_memory

                try:
                    result = processor_func(line)
                    if result:
                        yield result
                except Exception as e:
                    self.logger.warning(f"处理行失败: {e}")
                finally:
                    self.current_memory_usage -= line_memory
            else:
                self.logger.warning(f"内存限制，跳过行: {line[:100]}...")
                # 强制垃圾回收释放内存
                gc.collect()


class StreamingDataProcessor:
    """流式数据处理器"""

    def __init__(self, buffer_size: int = 1000):
        self.buffer_size = buffer_size
        self.logger = logging.getLogger(__name__)

    def create_streaming_pipeline(self, file_path: str) -> 'StreamingPipeline':
        """创建流式处理管道"""
        return StreamingPipeline(file_path, self.buffer_size)

    def process_multiple_files(self, file_paths: list, processor_func) -> Iterator[Dict[str, Any]]:
        """处理多个文件"""
        for file_path in file_paths:
            self.logger.info(f"开始处理文件: {file_path}")
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line_num, line in enumerate(f, 1):
                        if line.strip():
                            try:
                                result = processor_func(line.strip(), file_path, line_num)
                                if result:
                                    yield result
                            except Exception as e:
                                self.logger.warning(f"处理 {file_path}:{line_num} 失败: {e}")
            except Exception as e:
                self.logger.error(f"处理文件 {file_path} 失败: {e}")
                continue


class StreamingPipeline:
    """流式处理管道"""

    def __init__(self, file_path: str, buffer_size: int = 1000):
        self.file_path = file_path
        self.buffer_size = buffer_size
        self.filters = []
        self.transformers = []
        self.aggregators = []
        self.logger = logging.getLogger(__name__)

    def add_filter(self, filter_func):
        """添加过滤器"""
        self.filters.append(filter_func)
        return self

    def add_transformer(self, transformer_func):
        """添加转换器"""
        self.transformers.append(transformer_func)
        return self

    def add_aggregator(self, aggregator_func):
        """添加聚合器"""
        self.aggregators.append(aggregator_func)
        return self

    def execute(self) -> Iterator[Dict[str, Any]]:
        """执行处理管道"""
        buffer = []
        processed_count = 0

        try:
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    processed_item = {'raw': line}

                    # 应用过滤器
                    should_continue = False
                    for filter_func in self.filters:
                        try:
                            if not filter_func(processed_item):
                                should_continue = True
                                break
                        except Exception as e:
                            self.logger.warning(f"过滤器失败: {e}")
                            should_continue = True
                            break

                    if should_continue:
                        continue

                    # 应用转换器
                    for transformer_func in self.transformers:
                        try:
                            processed_item = transformer_func(processed_item)
                            if not processed_item:  # 转换器可能返回None表示跳过
                                break
                        except Exception as e:
                            self.logger.warning(f"转换器失败: {e}")
                            break

                    if processed_item:
                        buffer.append(processed_item)
                        processed_count += 1

                        # 缓冲区满时输出并应用聚合器
                        if len(buffer) >= self.buffer_size:
                            yield from self._process_buffer(buffer)
                            buffer = []

                            if processed_count % 10000 == 0:
                                gc.collect()
                                self.logger.info(f"已处理 {processed_count} 行")

                # 处理最后的缓冲区
                if buffer:
                    yield from self._process_buffer(buffer)

        except Exception as e:
            self.logger.error(f"执行处理管道失败: {e}")
            raise

    def _process_buffer(self, buffer: list) -> Iterator[Dict[str, Any]]:
        """处理缓冲区数据"""
        # 应用聚合器
        for item in buffer:
            for aggregator_func in self.aggregators:
                try:
                    item = aggregator_func(item)
                    if not item:
                        break
                except Exception as e:
                    self.logger.warning(f"聚合器失败: {e}")
                    break

            if item:
                yield item


# 便捷函数
def create_memory_efficient_processor(chunk_size: int = 8192, max_memory_usage: float = 0.8) -> MemoryOptimizedProcessor:
    """创建内存优化处理器"""
    return MemoryOptimizedProcessor(chunk_size, max_memory_usage)


def create_streaming_processor(buffer_size: int = 1000) -> StreamingDataProcessor:
    """创建流式处理器"""
    return StreamingDataProcessor(buffer_size)


async def process_large_logs_async(file_path: str, processor_func, batch_size: int = 100) -> AsyncIterator[Dict[str, Any]]:
    """异步处理大日志文件"""
    processor = MemoryOptimizedProcessor()
    async for result in processor.process_large_file_async(file_path, processor_func):
        yield result


def process_large_logs_sync(file_path: str, processor_func, batch_size: int = 100) -> Iterator[Dict[str, Any]]:
    """同步处理大日志文件"""
    processor = MemoryOptimizedProcessor()
    yield from processor.process_large_file_streaming(file_path, processor_func)