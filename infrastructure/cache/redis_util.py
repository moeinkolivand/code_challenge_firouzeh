import asyncio
import hashlib
from dataclasses import dataclass
from typing import Any, Callable, Optional,  TypeVar
from infrastructure.cache.redis import RedisConnector


F = TypeVar('F', bound=Callable[..., Any])


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    
    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0
    
    def reset(self):
        self.hits = self.misses = self.sets = self.deletes = self.errors = 0


class RedisCache:    
    def __init__(self, connector: RedisConnector, prefix: str = "cache"):
        self.connector = connector
        self.prefix = prefix
        self.stats = CacheStats()
    
    def _make_key(self, key: str) -> str:
        return f"{self.prefix}:{key}"
    
    def _hash_key(self, *args, **kwargs) -> str:
        key_data = str(args) + str(sorted(kwargs.items()))
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, key: str, default: Any = None) -> Any:
        try:
            cache_key = self._make_key(key)
            value = self.connector.get(cache_key)
            if value is not None:
                self.stats.hits += 1
                return value
            else:
                self.stats.misses += 1
                return default
        except Exception:
            self.stats.errors += 1
            return default
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            cache_key = self._make_key(key)
            result = self.connector.set(cache_key, value, ttl)
            if result:
                self.stats.sets += 1
            return result
        except Exception:
            self.stats.errors += 1
            return False
    
    def delete(self, key: str) -> bool:
        try:
            cache_key = self._make_key(key)
            result = self.connector.delete(cache_key) > 0
            if result:
                self.stats.deletes += 1
            return result
        except Exception:
            self.stats.errors += 1
            return False
    
    def exists(self, key: str) -> bool:
        try:
            cache_key = self._make_key(key)
            return self.connector.exists(cache_key) > 0
        except Exception:
            self.stats.errors += 1
            return False
    
    def clear_prefix(self, pattern: str = "*") -> int:
        try:
            full_pattern = f"{self.prefix}:{pattern}"
            count = 0
            for key in self.connector.scan_iter(match=full_pattern):
                if self.connector.delete(key) > 0:
                    count += 1
            self.stats.deletes += count
            return count
        except Exception:
            self.stats.errors += 1
            return 0
    
    def get_or_set(self, key: str, func: Callable[[], Any], ttl: Optional[int] = None) -> Any:
        value = self.get(key)
        if value is None:
            value = func()
            if value is not None:
                self.set(key, value, ttl)
        return value
    
    async def get_async(self, key: str, default: Any = None) -> Any:
        try:
            cache_key = self._make_key(key)
            value = await self.connector.get_async(cache_key)
            if value is not None:
                self.stats.hits += 1
                return value
            else:
                self.stats.misses += 1
                return default
        except Exception:
            self.stats.errors += 1
            return default
    
    async def set_async(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            cache_key = self._make_key(key)
            result = await self.connector.set_async(cache_key, value, ttl)
            if result:
                self.stats.sets += 1
            return result
        except Exception:
            self.stats.errors += 1
            return False
    
    async def get_or_set_async(self, key: str, func: Callable[[], Any], ttl: Optional[int] = None) -> Any:
        value = await self.get_async(key)
        if value is None:
            if asyncio.iscoroutinefunction(func):
                value = await func()
            else:
                value = func()
            if value is not None:
                await self.set_async(key, value, ttl)
        return value
