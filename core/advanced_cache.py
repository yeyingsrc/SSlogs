import time
import json
import threading
import hashlib
import pickle
import asyncio
from typing import Any, Dict, Optional, List, Callable, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
from pathlib import Path
import weakref
from collections import OrderedDict
import logging

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from .interfaces import ICache
from .exceptions import CacheError


class CachePolicy(Enum):
    """缓存策略"""
    LRU = "lru"                    # 最近最少使用
    LFU = "lfu"                    # 最少使用频率
    FIFO = "fifo"                  # 先进先出
    TTL = "ttl"                    # 基于时间


@dataclass
class CacheEntry:
    """缓存条目"""
    value: Any
    created_time: float
    last_accessed: float
    access_count: int = 0
    ttl: Optional[float] = None
    size_bytes: int = 0

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return time.time() > (self.created_time + self.ttl)

    def touch(self) -> None:
        """更新访问信息"""
        self.last_accessed = time.time()
        self.access_count += 1


class MemoryCache(ICache):
    """内存缓存实现"""

    def __init__(self, max_size: int = 1000, policy: CachePolicy = CachePolicy.LRU,
                 default_ttl: Optional[float] = None):
        self.max_size = max_size
        self.policy = policy
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'deletes': 0,
            'evictions': 0
        }

    def get(self, key: str) -> Optional[Any]:
        """获取缓存项"""
        with self._lock:
            if key not in self._cache:
                self._stats['misses'] += 1
                return None

            entry = self._cache[key]
            if entry.is_expired():
                del self._cache[key]
                self._stats['misses'] += 1
                return None

            entry.touch()
            self._stats['hits'] += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """设置缓存项"""
        try:
            with self._lock:
                # 计算值的大小
                size_bytes = len(pickle.dumps(value))

                # 检查是否需要驱逐
                if key not in self._cache and len(self._cache) >= self.max_size:
                    self._evict()

                ttl = ttl or self.default_ttl
                now = time.time()

                self._cache[key] = CacheEntry(
                    value=value,
                    created_time=now,
                    last_accessed=now,
                    ttl=ttl,
                    size_bytes=size_bytes
                )

                self._stats['sets'] += 1
                return True

        except Exception as e:
            logging.error(f"设置缓存项失败: {e}")
            return False

    def delete(self, key: str) -> bool:
        """删除缓存项"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats['deletes'] += 1
                return True
            return False

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()

    def exists(self, key: str) -> bool:
        """检查缓存项是否存在"""
        with self._lock:
            if key not in self._cache:
                return False

            entry = self._cache[key]
            if entry.is_expired():
                del self._cache[key]
                return False

            return True

    def _evict(self) -> None:
        """驱逐缓存项"""
        if not self._cache:
            return

        if self.policy == CachePolicy.LRU:
            # 找到最近最少使用的项
            oldest_key = min(self._cache.keys(),
                           key=lambda k: self._cache[k].last_accessed)
        elif self.policy == CachePolicy.LFU:
            # 找到最少使用的项
            lfu_key = min(self._cache.keys(),
                         key=lambda k: self._cache[k].access_count)
            oldest_key = lfu_key
        elif self.policy == CachePolicy.FIFO:
            # 找到最旧的项
            oldest_key = min(self._cache.keys(),
                           key=lambda k: self._cache[k].created_time)
        else:
            # 默认随机删除
            oldest_key = next(iter(self._cache.keys()))

        del self._cache[oldest_key]
        self._stats['evictions'] += 1

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            total_requests = self._stats['hits'] + self._stats['misses']
            hit_rate = self._stats['hits'] / total_requests if total_requests > 0 else 0

            return {
                **self._stats,
                'size': len(self._cache),
                'max_size': self.max_size,
                'hit_rate': hit_rate,
                'total_memory_bytes': sum(entry.size_bytes for entry in self._cache.values())
            }


class FileCache(ICache):
    """文件缓存实现"""

    def __init__(self, cache_dir: str = "cache", max_files: int = 1000,
                 default_ttl: Optional[float] = None):
        self.cache_dir = Path(cache_dir)
        self.max_files = max_files
        self.default_ttl = default_ttl
        self.cache_dir.mkdir(exist_ok=True)
        self._lock = threading.RLock()
        self._index_file = self.cache_dir / "index.json"
        self._index = self._load_index()

    def _load_index(self) -> Dict[str, Dict[str, Any]]:
        """加载缓存索引"""
        if self._index_file.exists():
            try:
                with open(self._index_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"加载缓存索引失败: {e}")
        return {}

    def _save_index(self) -> None:
        """保存缓存索引"""
        try:
            with open(self._index_file, 'w') as f:
                json.dump(self._index, f, indent=2)
        except Exception as e:
            logging.error(f"保存缓存索引失败: {e}")

    def _get_cache_file(self, key: str) -> Path:
        """获取缓存文件路径"""
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{safe_key}.cache"

    def get(self, key: str) -> Optional[Any]:
        """获取缓存项"""
        with self._lock:
            if key not in self._index:
                return None

            info = self._index[key]
            ttl = info.get('ttl')
            created_time = info.get('created_time', 0)

            # 检查是否过期
            if ttl and time.time() > (created_time + ttl):
                self.delete(key)
                return None

            cache_file = self._get_cache_file(key)
            if not cache_file.exists():
                del self._index[key]
                self._save_index()
                return None

            try:
                with open(cache_file, 'rb') as f:
                    value = pickle.load(f)

                # 更新访问信息
                self._index[key]['last_accessed'] = time.time()
                self._index[key]['access_count'] = self._index[key].get('access_count', 0) + 1
                self._save_index()

                return value
            except Exception as e:
                logging.error(f"读取缓存文件失败: {e}")
                self.delete(key)
                return None

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """设置缓存项"""
        try:
            with self._lock:
                cache_file = self._get_cache_file(key)

                # 检查文件数量限制
                if key not in self._index and len(self._index) >= self.max_files:
                    self._cleanup_old_files()

                ttl = ttl or self.default_ttl
                now = time.time()

                # 保存值到文件
                with open(cache_file, 'wb') as f:
                    pickle.dump(value, f)

                # 更新索引
                self._index[key] = {
                    'created_time': now,
                    'last_accessed': now,
                    'access_count': 0,
                    'ttl': ttl,
                    'file_size': cache_file.stat().st_size
                }

                self._save_index()
                return True

        except Exception as e:
            logging.error(f"设置缓存项失败: {e}")
            return False

    def delete(self, key: str) -> bool:
        """删除缓存项"""
        with self._lock:
            if key in self._index:
                cache_file = self._get_cache_file(key)
                if cache_file.exists():
                    cache_file.unlink()
                del self._index[key]
                self._save_index()
                return True
            return False

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            # 删除所有缓存文件
            for cache_file in self.cache_dir.glob("*.cache"):
                cache_file.unlink()

            # 清空索引
            self._index.clear()
            self._save_index()

    def exists(self, key: str) -> bool:
        """检查缓存项是否存在"""
        with self._lock:
            if key not in self._index:
                return False

            info = self._index[key]
            ttl = info.get('ttl')
            created_time = info.get('created_time', 0)

            if ttl and time.time() > (created_time + ttl):
                self.delete(key)
                return False

            cache_file = self._get_cache_file(key)
            return cache_file.exists()

    def _cleanup_old_files(self) -> None:
        """清理旧文件"""
        if not self._index:
            return

        # 找到最少使用的文件
        oldest_key = min(self._index.keys(),
                        key=lambda k: self._index[k].get('access_count', 0))
        self.delete(oldest_key)


class RedisCache(ICache):
    """Redis缓存实现"""

    def __init__(self, host: str = 'localhost', port: int = 6379,
                 db: int = 0, password: Optional[str] = None,
                 prefix: str = "sslogs:", default_ttl: Optional[float] = None):
        if not REDIS_AVAILABLE:
            raise CacheError("Redis不可用，请安装redis库")

        self.redis_client = redis.Redis(
            host=host, port=port, db=db, password=password,
            decode_responses=False  # 使用二进制模式以支持pickle
        )
        self.prefix = prefix
        self.default_ttl = default_ttl

        # 测试连接
        try:
            self.redis_client.ping()
        except Exception as e:
            raise CacheError(f"Redis连接失败: {e}")

    def _make_key(self, key: str) -> str:
        """生成Redis键"""
        return f"{self.prefix}{key}"

    def get(self, key: str) -> Optional[Any]:
        """获取缓存项"""
        try:
            redis_key = self._make_key(key)
            data = self.redis_client.get(redis_key)
            if data is None:
                return None
            return pickle.loads(data)
        except Exception as e:
            logging.error(f"Redis获取缓存失败: {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """设置缓存项"""
        try:
            redis_key = self._make_key(key)
            data = pickle.dumps(value)
            ttl = ttl or self.default_ttl

            if ttl:
                return self.redis_client.setex(redis_key, int(ttl), data)
            else:
                return self.redis_client.set(redis_key, data)
        except Exception as e:
            logging.error(f"Redis设置缓存失败: {e}")
            return False

    def delete(self, key: str) -> bool:
        """删除缓存项"""
        try:
            redis_key = self._make_key(key)
            return bool(self.redis_client.delete(redis_key))
        except Exception as e:
            logging.error(f"Redis删除缓存失败: {e}")
            return False

    def clear(self) -> None:
        """清空缓存"""
        try:
            pattern = f"{self.prefix}*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
        except Exception as e:
            logging.error(f"Redis清空缓存失败: {e}")

    def exists(self, key: str) -> bool:
        """检查缓存项是否存在"""
        try:
            redis_key = self._make_key(key)
            return bool(self.redis_client.exists(redis_key))
        except Exception as e:
            logging.error(f"Redis检查缓存存在性失败: {e}")
            return False


class MultiLevelCache(ICache):
    """多级缓存"""

    def __init__(self, levels: List[ICache]):
        self.levels = levels
        self._lock = threading.RLock()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存项（按级别查找）"""
        with self._lock:
            for i, cache in enumerate(self.levels):
                value = cache.get(key)
                if value is not None:
                    # 将值回填到更高级别的缓存
                    for j in range(i):
                        self.levels[j].set(key, value)
                    return value
            return None

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """设置缓存项（所有级别）"""
        success = True
        with self._lock:
            for cache in self.levels:
                if not cache.set(key, value, ttl):
                    success = False
        return success

    def delete(self, key: str) -> bool:
        """删除缓存项（所有级别）"""
        success = True
        with self._lock:
            for cache in self.levels:
                if not cache.delete(key):
                    success = False
        return success

    def clear(self) -> None:
        """清空所有缓存级别"""
        with self._lock:
            for cache in self.levels:
                cache.clear()

    def exists(self, key: str) -> bool:
        """检查缓存项是否存在（任一级别）"""
        with self._lock:
            return any(cache.exists(key) for cache in self.levels)


class CacheManager:
    """缓存管理器"""

    def __init__(self):
        self.caches: Dict[str, ICache] = {}
        self.default_cache_name = "default"

    def create_memory_cache(self, name: str, max_size: int = 1000,
                          policy: CachePolicy = CachePolicy.LRU,
                          default_ttl: Optional[float] = None) -> MemoryCache:
        """创建内存缓存"""
        cache = MemoryCache(max_size, policy, default_ttl)
        self.caches[name] = cache
        return cache

    def create_file_cache(self, name: str, cache_dir: str = None,
                        max_files: int = 1000,
                        default_ttl: Optional[float] = None) -> FileCache:
        """创建文件缓存"""
        if cache_dir is None:
            cache_dir = f"cache/{name}"
        cache = FileCache(cache_dir, max_files, default_ttl)
        self.caches[name] = cache
        return cache

    def create_redis_cache(self, name: str, host: str = 'localhost',
                          port: int = 6379, db: int = 0,
                          password: Optional[str] = None,
                          prefix: str = "sslogs:",
                          default_ttl: Optional[float] = None) -> RedisCache:
        """创建Redis缓存"""
        cache = RedisCache(host, port, db, password, prefix, default_ttl)
        self.caches[name] = cache
        return cache

    def create_multi_level_cache(self, name: str,
                                levels: List[Tuple[str, Dict[str, Any]]]) -> MultiLevelCache:
        """创建多级缓存"""
        cache_levels = []
        for level_name, config in levels:
            if level_name in self.caches:
                cache_levels.append(self.caches[level_name])
            else:
                # 根据配置创建缓存
                cache_type = config.get('type', 'memory')
                if cache_type == 'memory':
                    cache = self.create_memory_cache(
                        level_name,
                        max_size=config.get('max_size', 1000),
                        policy=CachePolicy(config.get('policy', 'lru')),
                        default_ttl=config.get('default_ttl')
                    )
                else:
                    raise CacheError(f"不支持的缓存类型: {cache_type}")
                cache_levels.append(cache)

        multi_cache = MultiLevelCache(cache_levels)
        self.caches[name] = multi_cache
        return multi_cache

    def get_cache(self, name: str = None) -> ICache:
        """获取缓存实例"""
        cache_name = name or self.default_cache_name
        if cache_name not in self.caches:
            # 创建默认内存缓存
            self.create_memory_cache(cache_name)
        return self.caches[cache_name]

    def set_default_cache(self, name: str) -> None:
        """设置默认缓存"""
        if name in self.caches:
            self.default_cache_name = name

    def remove_cache(self, name: str) -> bool:
        """移除缓存"""
        if name in self.caches:
            del self.caches[name]
            return True
        return False

    def list_caches(self) -> List[str]:
        """列出所有缓存名称"""
        return list(self.caches.keys())

    def clear_all_caches(self) -> None:
        """清空所有缓存"""
        for cache in self.caches.values():
            cache.clear()


# 全局缓存管理器
_global_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器"""
    global _global_cache_manager
    if _global_cache_manager is None:
        _global_cache_manager = CacheManager()
    return _global_cache_manager


def cache_result(ttl: Optional[float] = None, cache_name: str = "default",
                key_func: Optional[Callable] = None):
    """缓存函数结果的装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache_manager = get_cache_manager()
            cache = cache_manager.get_cache(cache_name)

            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hash((args, tuple(sorted(kwargs.items()))))}"

            # 尝试从缓存获取
            result = cache.get(cache_key)
            if result is not None:
                return result

            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result

        return wrapper
    return decorator


def async_cache_result(ttl: Optional[float] = None, cache_name: str = "default",
                      key_func: Optional[Callable] = None):
    """缓存异步函数结果的装饰器"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            cache_manager = get_cache_manager()
            cache = cache_manager.get_cache(cache_name)

            # 生成缓存键
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hash((args, tuple(sorted(kwargs.items()))))}"

            # 尝试从缓存获取
            result = cache.get(cache_key)
            if result is not None:
                return result

            # 执行函数并缓存结果
            result = await func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            return result

        return wrapper
    return decorator


# 便捷函数
def get_cache(cache_name: str = None) -> ICache:
    """获取缓存的便捷函数"""
    return get_cache_manager().get_cache(cache_name)