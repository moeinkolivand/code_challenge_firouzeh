from fastapi import Request
from infrastructure.cache.redis import RedisConnector
from infrastructure.databases.postgres import DatabaseConnector

def get_db_connector(request: Request) -> DatabaseConnector:
    return request.app.state.db_connection

def get_redis_connector(request: Request) -> RedisConnector:
    return request.app.state.redis_connection
