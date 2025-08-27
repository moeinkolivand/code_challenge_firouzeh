from infrastructure.cache.redis import RedisConnector, create_redis_connector
from infrastructure.databases.postgres import DatabaseConnector, create_database_connector


__all__ = [
    'Initilizer'
]

class Initilizer:
    @staticmethod
    def create_database_connector() -> DatabaseConnector:
        return create_database_connector(
            host="postgres"
        )
        

    @staticmethod
    def create_redis_connector() -> RedisConnector:
        return create_redis_connector(
            host="redis"
        )
