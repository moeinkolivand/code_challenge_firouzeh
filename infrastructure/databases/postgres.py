import logging
from contextlib import contextmanager, asynccontextmanager
from enum import Enum
from typing import Any, Dict, List, Optional,  AsyncGenerator, Generator

from pydantic import Field, field_validator
from sqlalchemy import create_engine, text, MetaData, inspect
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine
from pydantic_settings import BaseSettings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseBackend(str, Enum):
    """Supported database backends"""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    SQLITE = "sqlite"
    ORACLE = "oracle"
    MSSQL = "mssql"


class DatabaseConfig(BaseSettings):
    """Database configuration with Pydantic validation"""
    
    # Connection settings
    backend: DatabaseBackend = DatabaseBackend.POSTGRESQL
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    username: str = Field(default="", description="Database username")
    password: str = Field(default="", description="Database password")
    database: str = Field(default="", description="Database name")
    
    # Connection pool settings
    pool_size: int = Field(default=10, ge=1, le=50, description="Connection pool size")
    max_overflow: int = Field(default=20, ge=0, description="Max overflow connections")
    pool_timeout: int = Field(default=30, ge=1, description="Pool checkout timeout")
    pool_recycle: int = Field(default=3600, ge=300, description="Connection recycle time")
    pool_pre_ping: bool = Field(default=True, description="Enable connection health checks")
    
    # SSL and security
    ssl_mode: str = Field(default="prefer", description="SSL mode")
    ssl_cert: Optional[str] = Field(default=None, description="SSL certificate path")
    ssl_key: Optional[str] = Field(default=None, description="SSL key path")
    ssl_ca: Optional[str] = Field(default=None, description="SSL CA path")
    
    # Query settings
    query_timeout: int = Field(default=30, ge=1, description="Query timeout in seconds")
    echo_queries: bool = Field(default=False, description="Log SQL queries")
    
    # Async settings
    async_pool_size: int = Field(default=20, ge=1, description="Async pool size")
    async_max_overflow: int = Field(default=40, ge=0, description="Async max overflow")
    
    # Custom connection parameters
    connection_args: Dict[str, Any] = Field(default_factory=dict, description="Additional connection arguments")
    
    class Config:
        env_prefix = "DB_"
        case_sensitive = False
        env_file = ".env"
    

    def validate_port(cls, v, values):
        """Set default port based on backend"""
        backend = values.get('backend')
        if v == 5432 and backend:  # Only set if using default port
            defaults = {
                DatabaseBackend.POSTGRESQL: 5432,
                DatabaseBackend.MYSQL: 3306,
                DatabaseBackend.SQLITE: 0,
                DatabaseBackend.ORACLE: 1521,
                DatabaseBackend.MSSQL: 1433,
            }
            return defaults.get(backend, v)
        return v
    
    @property
    def sync_url(self) -> str:
        """Generate synchronous database URL"""
        return self._build_url(async_mode=False)
    
    @property
    def async_url(self) -> str:
        """Generate asynchronous database URL"""
        return self._build_url(async_mode=True)
    
    def _build_url(self, async_mode: bool = False) -> str:
        """Build database URL based on backend"""
        if self.backend == DatabaseBackend.SQLITE:
            prefix = "sqlite+aiosqlite" if async_mode else "sqlite"
            return f"{prefix}:///{self.database}"
        
        drivers = {
            DatabaseBackend.POSTGRESQL: {
                "sync": "postgresql+psycopg2",
                "async": "postgresql+asyncpg"
            },
            DatabaseBackend.MYSQL: {
                "sync": "mysql+pymysql",
                "async": "mysql+aiomysql"
            },
            DatabaseBackend.ORACLE: {
                "sync": "oracle+cx_oracle",
                "async": "oracle+cx_oracle_async"
            },
            DatabaseBackend.MSSQL: {
                "sync": "mssql+pyodbc",
                "async": "mssql+aioodbc"
            }
        }
        
        driver = drivers[self.backend]["async" if async_mode else "sync"]
        auth = f"{self.username}:{self.password}@" if self.username else ""
        
        return f"{driver}://{auth}{self.host}:{self.port}/{self.database}"


class DatabaseConnector:
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._sync_engine: Optional[Engine] = None
        self._async_engine: Optional[AsyncEngine] = None
        self._sync_session_factory: Optional[sessionmaker] = None
        self._async_session_factory: Optional[sessionmaker] = None
        self._metadata = MetaData()
        
        self._setup_sync_engine()
        self._setup_async_engine()
    
    def _setup_sync_engine(self):
        try:
            engine_kwargs = {
                "poolclass": QueuePool,
                "pool_size": self.config.pool_size,
                "max_overflow": self.config.max_overflow,
                "pool_timeout": self.config.pool_timeout,
                "pool_recycle": self.config.pool_recycle,
                "pool_pre_ping": self.config.pool_pre_ping,
                "echo": self.config.echo_queries,
                **self.config.connection_args
            }
            
            self._sync_engine = create_engine(self.config.sync_url, **engine_kwargs)
            self._sync_session_factory = sessionmaker(
                bind=self._sync_engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
            logger.info(f"Sync engine created for {self.config.backend.value}")
            
        except Exception as e:
            logger.error(f"Failed to create sync engine: {e}")
            raise
    
    def _setup_async_engine(self):
        if self.config.backend == DatabaseBackend.SQLITE:
            engine_kwargs = {
                "echo": self.config.echo_queries,
                **self.config.connection_args
            }
        else:
            engine_kwargs = {
                "pool_size": self.config.async_pool_size,
                "max_overflow": self.config.async_max_overflow,
                "pool_timeout": self.config.pool_timeout,
                "pool_recycle": self.config.pool_recycle,
                "pool_pre_ping": self.config.pool_pre_ping,
                "echo": self.config.echo_queries,
                **self.config.connection_args
            }
        
        try:
            self._async_engine = create_async_engine(self.config.async_url, **engine_kwargs)
            self._async_session_factory = sessionmaker(
                bind=self._async_engine,
                class_=AsyncSession,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False
            )
            logger.info(f"Async engine created for {self.config.backend.value}")
            
        except Exception as e:
            logger.error(f"Failed to create async engine: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        if not self._sync_session_factory:
            raise RuntimeError("Sync engine not initialized")
        
        session = self._sync_session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Session error: {e}")
            raise
        finally:
            session.close()
    
    @contextmanager
    def get_connection(self):
        if not self._sync_engine:
            raise RuntimeError("Sync engine not initialized")
        
        with self._sync_engine.connect() as conn:
            yield conn
    

    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        if not self._async_session_factory:
            raise RuntimeError("Async engine not initialized")
        
        session = self._async_session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Async session error: {e}")
            raise
        finally:
            await session.close()
    
    @asynccontextmanager
    async def get_async_connection(self):
        if not self._async_engine:
            raise RuntimeError("Async engine not initialized")
        
        async with self._async_engine.connect() as conn:
            yield conn
    

    def execute_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        with self.get_connection() as conn:
            result = conn.execute(text(query), params or {})
            return [dict(row._mapping) for row in result.fetchall()]
    
    async def execute_async_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        async with self.get_async_connection() as conn:
            result = await conn.execute(text(query), params or {})
            return [dict(row._mapping) for row in result.fetchall()]
    
    def execute_command(self, command: str, params: Optional[Dict] = None) -> int:
        with self.get_connection() as conn:
            result = conn.execute(text(command), params or {})
            conn.commit()
            return result.rowcount
    
    async def execute_async_command(self, command: str, params: Optional[Dict] = None) -> int:
        async with self.get_async_connection() as conn:
            result = await conn.execute(text(command), params or {})
            await conn.commit()
            return result.rowcount
    
    def test_connection(self) -> bool:
        try:
            with self.get_connection() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    async def test_async_connection(self) -> bool:
        try:
            async with self.get_async_connection() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Async connection test failed: {e}")
            return False
    
    def get_table_info(self) -> Dict[str, Any]:
        try:
            inspector = inspect(self._sync_engine)
            return {
                "tables": inspector.get_table_names(),
                "views": inspector.get_view_names(),
                "schemas": inspector.get_schema_names() if hasattr(inspector, 'get_schema_names') else []
            }
        except Exception as e:
            logger.error(f"Failed to get table info: {e}")
            return {}
    
    def get_connection_info(self) -> Dict[str, Any]:
        return {
            "backend": self.config.backend.value,
            "host": self.config.host,
            "port": self.config.port,
            "database": self.config.database,
            "pool_size": self.config.pool_size,
            "max_overflow": self.config.max_overflow,
            "async_pool_size": self.config.async_pool_size,
            "sync_url": self.config.sync_url.split('@')[0] + '@***',  # Hide credentials
            "async_url": self.config.async_url.split('@')[0] + '@***'
        }
    

    def close(self):
        if self._sync_engine:
            self._sync_engine.dispose()
            logger.info("Sync engine disposed")
    
    async def close_async(self):
        if self._async_engine:
            await self._async_engine.dispose()
            logger.info("Async engine disposed")
    
    async def close_all(self):
        self.close()
        await self.close_async()


def create_database_connector(
    backend: str = "postgresql",
    host: str = "localhost",
    port: Optional[int] = None,
    username: str = "postgres",
    password: str = "password",
    database: str = "fastapi_db",
    **kwargs
) -> DatabaseConnector:
    
    config_dict = {
        "backend": backend,
        "host": host,
        "username": username,
        "password": password,
        "database": database,
        **kwargs
    }
    
    if port is not None:
        config_dict["port"] = port
    
    config = DatabaseConfig(**config_dict)
    return DatabaseConnector(config)

