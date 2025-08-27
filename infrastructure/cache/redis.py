import json
import logging
import pickle
from contextlib import asynccontextmanager, contextmanager
from enum import Enum
from typing import Any, Dict, List, Optional,  Set, Type,  TypeVar

import redis
import redis.asyncio as aioredis
from pydantic import Field, field_validator
from redis.connection import ConnectionPool
from redis.sentinel import Sentinel
from redis.exceptions import ConnectionError, TimeoutError
from pydantic_settings import BaseSettings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

T = TypeVar('T')


class RedisMode(str, Enum):
    """Redis deployment modes"""
    STANDALONE = "standalone"
    SENTINEL = "sentinel"
    CLUSTER = "cluster"


class SerializationFormat(str, Enum):
    """Serialization formats for Redis values"""
    JSON = "json"
    PICKLE = "pickle"
    STRING = "string"


class RedisConfig(BaseSettings):
    """Redis configuration with Pydantic validation"""
    
    # Connection settings
    mode: RedisMode = RedisMode.STANDALONE
    host: str = Field(default="localhost", description="Redis host")
    port: int = Field(default=6379, ge=1, le=65535, description="Redis port")
    username: Optional[str] = Field(default=None, description="Redis username (Redis 6+)")
    password: Optional[str] = Field(default=None, description="Redis password")
    db: int = Field(default=0, ge=0, le=15, description="Redis database number")
    
    # Connection pool settings
    max_connections: int = Field(default=50, ge=1, description="Max connections in pool")
    retry_on_timeout: bool = Field(default=True, description="Retry on timeout")
    retry_on_error: List[Type[Exception]] = Field(default_factory=lambda: [ConnectionError, TimeoutError])
    health_check_interval: int = Field(default=30, ge=0, description="Health check interval in seconds")
    
    # Timeout settings
    socket_timeout: float = Field(default=5.0, ge=0.1, description="Socket timeout in seconds")
    socket_connect_timeout: float = Field(default=5.0, ge=0.1, description="Connect timeout in seconds")
    socket_keepalive: bool = Field(default=True, description="Enable TCP keepalive")
    socket_keepalive_options: Dict[str, int] = Field(default_factory=dict)
    
    # SSL settings
    ssl: bool = Field(default=False, description="Enable SSL/TLS")
    ssl_cert_reqs: Optional[str] = Field(default=None, description="SSL cert requirements")
    ssl_ca_certs: Optional[str] = Field(default=None, description="SSL CA certs path")
    ssl_certfile: Optional[str] = Field(default=None, description="SSL cert file path")
    ssl_keyfile: Optional[str] = Field(default=None, description="SSL key file path")
    ssl_check_hostname: bool = Field(default=False, description="Check SSL hostname")
    
    # Sentinel settings (for HA setup)
    sentinel_hosts: List[str] = Field(default_factory=list, description="Sentinel host:port list")
    sentinel_service_name: str = Field(default="mymaster", description="Sentinel service name")
    sentinel_password: Optional[str] = Field(default=None, description="Sentinel password")
    
    # Cluster settings
    cluster_nodes: List[str] = Field(default_factory=list, description="Cluster node host:port list")
    
    # Serialization
    default_serialization: SerializationFormat = SerializationFormat.JSON
    compress_data: bool = Field(default=False, description="Compress data before storing")
    
    # Default expiration
    default_ttl: Optional[int] = Field(default=None, ge=1, description="Default TTL in seconds")
    
    # Connection URL (alternative to individual settings)
    redis_url: Optional[str] = Field(default=None, description="Redis URL (overrides other settings)")
    
    class Config:
        env_prefix = "REDIS_"
        case_sensitive = False
        env_file = ".env"
    
    @property
    def connection_kwargs(self) -> Dict[str, Any]:
        """Get connection parameters for Redis client"""
        kwargs = {
            'socket_timeout': self.socket_timeout,
            'socket_connect_timeout': self.socket_connect_timeout,
            'socket_keepalive': self.socket_keepalive,
            'socket_keepalive_options': self.socket_keepalive_options,
            'retry_on_timeout': self.retry_on_timeout,
            'health_check_interval': self.health_check_interval,
        }
        
        if self.password:
            kwargs['password'] = self.password
        if self.username:
            kwargs['username'] = self.username
        
        if self.ssl:
            kwargs.update({
                'ssl': self.ssl,
                'ssl_cert_reqs': self.ssl_cert_reqs,
                'ssl_ca_certs': self.ssl_ca_certs,
                'ssl_certfile': self.ssl_certfile,
                'ssl_keyfile': self.ssl_keyfile,
                'ssl_check_hostname': self.ssl_check_hostname,
            })
        
        return {k: v for k, v in kwargs.items() if v is not None}


class RedisSerializer:
    
    @staticmethod
    def serialize(data: Any, format: SerializationFormat) -> bytes:
        if format == SerializationFormat.STRING:
            if isinstance(data, (str, int, float, bool)):
                return str(data).encode('utf-8')
            else:
                raise ValueError("String format only supports primitive types")
        elif format == SerializationFormat.JSON:
            return json.dumps(data, default=str).encode('utf-8')
        elif format == SerializationFormat.PICKLE:
            return pickle.dumps(data)
        else:
            raise ValueError(f"Unsupported serialization format: {format}")
    
    @staticmethod
    def deserialize(data: bytes, format: SerializationFormat) -> Any:
        if format == SerializationFormat.STRING:
            return data.decode('utf-8')
        elif format == SerializationFormat.JSON:
            return json.loads(data.decode('utf-8'))
        elif format == SerializationFormat.PICKLE:
            return pickle.loads(data)
        else:
            raise ValueError(f"Unsupported serialization format: {format}")


class RedisConnector:
    
    def __init__(self, config: RedisConfig):
        self.config = config
        self._sync_client: Optional[redis.Redis] = None
        self._async_client: Optional[aioredis.Redis] = None
        self._connection_pool: Optional[ConnectionPool] = None
        self._async_connection_pool: Optional[aioredis.ConnectionPool] = None
        self._sentinel: Optional[Sentinel] = None
        self.serializer = RedisSerializer()
        
        self._setup_sync_client()
        self._setup_async_client()
    
    def _setup_sync_client(self):
        try:
            if self.config.redis_url:
                self._sync_client = redis.from_url(
                    self.config.redis_url,
                    max_connections=self.config.max_connections,
                    **self.config.connection_kwargs
                )
            elif self.config.mode == RedisMode.SENTINEL:
                if not self.config.sentinel_hosts:
                    raise ValueError("Sentinel hosts must be specified for sentinel mode")
                
                sentinels = []
                for host_port in self.config.sentinel_hosts:
                    host, port = host_port.split(':')
                    sentinels.append((host, int(port)))
                
                self._sentinel = Sentinel(
                    sentinels,
                    sentinel_kwargs={'password': self.config.sentinel_password},
                    **self.config.connection_kwargs
                )
                self._sync_client = self._sentinel.master_for(
                    self.config.sentinel_service_name,
                    db=self.config.db
                )
            else:  # Standalone mode
                self._connection_pool = ConnectionPool(
                    host=self.config.host,
                    port=self.config.port,
                    db=self.config.db,
                    max_connections=self.config.max_connections,
                    **self.config.connection_kwargs
                )
                self._sync_client = redis.Redis(connection_pool=self._connection_pool)
            
            logger.info(f"Sync Redis client created for {self.config.mode.value} mode")
            
        except Exception as e:
            logger.error(f"Failed to create sync Redis client: {e}")
            raise
    
    def _setup_async_client(self):
        try:
            if self.config.redis_url:
                self._async_client = aioredis.from_url(
                    self.config.redis_url,
                    max_connections=self.config.max_connections,
                    **self.config.connection_kwargs
                )
            elif self.config.mode == RedisMode.SENTINEL:
                logger.warning("Async sentinel support is limited, falling back to direct connection")
                self._async_connection_pool = aioredis.ConnectionPool(
                    host=self.config.host,
                    port=self.config.port,
                    db=self.config.db,
                    max_connections=self.config.max_connections,
                    **self.config.connection_kwargs
                )
                self._async_client = aioredis.Redis(connection_pool=self._async_connection_pool)
            else:
                self._async_connection_pool = aioredis.ConnectionPool(
                    host=self.config.host,
                    port=self.config.port,
                    db=self.config.db,
                    max_connections=self.config.max_connections,
                    **self.config.connection_kwargs
                )
                self._async_client = aioredis.Redis(connection_pool=self._async_connection_pool)
            
            logger.info(f"Async Redis client created for {self.config.mode.value} mode")
            
        except Exception as e:
            logger.error(f"Failed to create async Redis client: {e}")
            raise
    
    @contextmanager
    def get_client(self):
        if not self._sync_client:
            raise RuntimeError("Sync Redis client not initialized")
        yield self._sync_client
    
    @asynccontextmanager
    async def get_async_client(self):
        if not self._async_client:
            raise RuntimeError("Async Redis client not initialized")
        yield self._async_client
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, 
            format: Optional[SerializationFormat] = None) -> bool:
        format = format or self.config.default_serialization
        ttl = ttl or self.config.default_ttl
        
        try:
            serialized_value = self.serializer.serialize(value, format)
            with self.get_client() as client:
                return client.set(key, serialized_value, ex=ttl)
        except Exception as e:
            logger.error(f"Failed to set key {key}: {e}")
            return False
    
    def get(self, key: str, format: Optional[SerializationFormat] = None) -> Any:
        format = format or self.config.default_serialization
        
        try:
            with self.get_client() as client:
                data = client.get(key)
                if data is None:
                    return None
                return self.serializer.deserialize(data, format)
        except Exception as e:
            logger.error(f"Failed to get key {key}: {e}")
            return None
    
    def delete(self, *keys: str) -> int:
        try:
            with self.get_client() as client:
                return client.delete(*keys)
        except Exception as e:
            logger.error(f"Failed to delete keys {keys}: {e}")
            return 0
    
    def exists(self, *keys: str) -> int:
        try:
            with self.get_client() as client:
                return client.exists(*keys)
        except Exception as e:
            logger.error(f"Failed to check existence of keys {keys}: {e}")
            return 0
    
    def expire(self, key: str, seconds: int) -> bool:
        try:
            with self.get_client() as client:
                return client.expire(key, seconds)
        except Exception as e:
            logger.error(f"Failed to set expiration for key {key}: {e}")
            return False
    
    def ttl(self, key: str) -> int:
        try:
            with self.get_client() as client:
                return client.ttl(key)
        except Exception as e:
            logger.error(f"Failed to get TTL for key {key}: {e}")
            return -1
    
    def hset(self, name: str, mapping: Dict[str, Any], 
             format: Optional[SerializationFormat] = None) -> int:
        format = format or self.config.default_serialization
        
        try:
            serialized_mapping = {}
            for field, value in mapping.items():
                serialized_mapping[field] = self.serializer.serialize(value, format)
            
            with self.get_client() as client:
                return client.hset(name, mapping=serialized_mapping)
        except Exception as e:
            logger.error(f"Failed to set hash {name}: {e}")
            return 0
    
    def hget(self, name: str, key: str, format: Optional[SerializationFormat] = None) -> Any:
        format = format or self.config.default_serialization
        
        try:
            with self.get_client() as client:
                data = client.hget(name, key)
                if data is None:
                    return None
                return self.serializer.deserialize(data, format)
        except Exception as e:
            logger.error(f"Failed to get hash field {name}:{key}: {e}")
            return None
    
    def hgetall(self, name: str, format: Optional[SerializationFormat] = None) -> Dict[str, Any]:
        format = format or self.config.default_serialization
        
        try:
            with self.get_client() as client:
                data = client.hgetall(name)
                result = {}
                for field, value in data.items():
                    field_str = field.decode('utf-8') if isinstance(field, bytes) else field
                    result[field_str] = self.serializer.deserialize(value, format)
                return result
        except Exception as e:
            logger.error(f"Failed to get all hash fields for {name}: {e}")
            return {}
    
    def lpush(self, name: str, *values: Any, format: Optional[SerializationFormat] = None) -> int:
        format = format or self.config.default_serialization
        
        try:
            serialized_values = [self.serializer.serialize(v, format) for v in values]
            with self.get_client() as client:
                return client.lpush(name, *serialized_values)
        except Exception as e:
            logger.error(f"Failed to push to list {name}: {e}")
            return 0
    
    def rpush(self, name: str, *values: Any, format: Optional[SerializationFormat] = None) -> int:
        format = format or self.config.default_serialization
        
        try:
            serialized_values = [self.serializer.serialize(v, format) for v in values]
            with self.get_client() as client:
                return client.rpush(name, *serialized_values)
        except Exception as e:
            logger.error(f"Failed to push to list {name}: {e}")
            return 0
    
    def lrange(self, name: str, start: int, end: int, 
               format: Optional[SerializationFormat] = None) -> List[Any]:
        format = format or self.config.default_serialization
        
        try:
            with self.get_client() as client:
                data = client.lrange(name, start, end)
                return [self.serializer.deserialize(item, format) for item in data]
        except Exception as e:
            logger.error(f"Failed to get list range for {name}: {e}")
            return []
    
    def sadd(self, name: str, *values: Any, format: Optional[SerializationFormat] = None) -> int:
        format = format or self.config.default_serialization
        
        try:
            serialized_values = [self.serializer.serialize(v, format) for v in values]
            with self.get_client() as client:
                return client.sadd(name, *serialized_values)
        except Exception as e:
            logger.error(f"Failed to add to set {name}: {e}")
            return 0
    
    def smembers(self, name: str, format: Optional[SerializationFormat] = None) -> Set[Any]:
        format = format or self.config.default_serialization
        
        try:
            with self.get_client() as client:
                data = client.smembers(name)
                return {self.serializer.deserialize(item, format) for item in data}
        except Exception as e:
            logger.error(f"Failed to get set members for {name}: {e}")
            return set()
    

    async def set_async(self, key: str, value: Any, ttl: Optional[int] = None,
                       format: Optional[SerializationFormat] = None) -> bool:
        format = format or self.config.default_serialization
        ttl = ttl or self.config.default_ttl
        
        try:
            serialized_value = self.serializer.serialize(value, format)
            async with self.get_async_client() as client:
                return await client.set(key, serialized_value, ex=ttl)
        except Exception as e:
            logger.error(f"Failed to set key {key} async: {e}")
            return False
    
    async def get_async(self, key: str, format: Optional[SerializationFormat] = None) -> Any:
        format = format or self.config.default_serialization
        
        try:
            async with self.get_async_client() as client:
                data = await client.get(key)
                if data is None:
                    return None
                return self.serializer.deserialize(data, format)
        except Exception as e:
            logger.error(f"Failed to get key {key} async: {e}")
            return None
    
    async def delete_async(self, *keys: str) -> int:
        try:
            async with self.get_async_client() as client:
                return await client.delete(*keys)
        except Exception as e:
            logger.error(f"Failed to delete keys {keys} async: {e}")
            return 0
    

    def pipeline(self):
        """Get Redis pipeline for batch operations"""
        return self._sync_client.pipeline()
    
    async def pipeline_async(self):
        """Get async Redis pipeline for batch operations"""
        return self._async_client.pipeline()
    
    def ping(self) -> bool:
        try:
            with self.get_client() as client:
                return client.ping()
        except Exception as e:
            logger.error(f"Ping failed: {e}")
            return False
    
    async def ping_async(self) -> bool:
        try:
            async with self.get_async_client() as client:
                return await client.ping()
        except Exception as e:
            logger.error(f"Async ping failed: {e}")
            return False
    
    def info(self, section: Optional[str] = None) -> Dict[str, Any]:
        """Get Redis server info"""
        try:
            with self.get_client() as client:
                return client.info(section)
        except Exception as e:
            logger.error(f"Failed to get info: {e}")
            return {}
    
    def get_memory_usage(self, key: str) -> int:
        """Get memory usage of a key"""
        try:
            with self.get_client() as client:
                return client.memory_usage(key) or 0
        except Exception as e:
            logger.error(f"Failed to get memory usage for {key}: {e}")
            return 0
    

    def keys(self, pattern: str = "*") -> List[str]:
        try:
            with self.get_client() as client:
                keys = client.keys(pattern)
                return [key.decode('utf-8') if isinstance(key, bytes) else key for key in keys]
        except Exception as e:
            logger.error(f"Failed to get keys with pattern {pattern}: {e}")
            return []
    
    def scan_iter(self, match: str = "*", count: int = 1000):
        """Iterate over keys matching pattern (production-safe)"""
        try:
            with self.get_client() as client:
                for key in client.scan_iter(match=match, count=count):
                    yield key.decode('utf-8') if isinstance(key, bytes) else key
        except Exception as e:
            logger.error(f"Failed to scan keys with pattern {match}: {e}")
    
    def close(self):
        if self._connection_pool:
            self._connection_pool.disconnect()
        if self._sync_client:
            try:
                self._sync_client.close()
            except AttributeError:
                pass 
        logger.info("Sync Redis connections closed")
    
    async def close_async(self):
        if self._async_client:
            await self._async_client.close()
        if self._async_connection_pool:
            await self._async_connection_pool.disconnect()
        logger.info("Async Redis connections closed")
    
    async def close_all(self):
        """Close all connections"""
        self.close()
        await self.close_async()



def create_redis_connector(
    host: str = "localhost",
    port: int = 6379,
    password: Optional[str] = None,
    db: int = 0,
    **kwargs
) -> RedisConnector:
    """Factory function to create Redis connector"""
    config_dict = {
        "host": host,
        "port": port,
        "password": password,
        "db": db,
        **kwargs
    }
    
    config = RedisConfig(**config_dict)
    return RedisConnector(config)