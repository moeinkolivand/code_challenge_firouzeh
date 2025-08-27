from contextlib import asynccontextmanager
from fastapi import FastAPI
from configs import settings
from infrastructure import Initilizer
from infrastructure import DatabaseConnector
from infrastructure.cache.redis import RedisConnector
from apies.shortener.router import generator_router
configurations = settings.Settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db_connection = Initilizer.create_database_connector()
    app.state.redis_connection = Initilizer.create_redis_connector()
    print("Application startup complete: Connections bound to app.state")
    
    yield
    app.state.db_connection.close()
    app.state.redis_connection.close()


app = FastAPI(
    title=configurations.PROJECT_NAME,
    version=configurations.VERSION,
    description="FastAPI application with SQLAlchemy, Pydantic, and Redis",
    lifespan=lifespan
)

app.include_router(generator_router)


@app.get("/health")
async def health():
    db : DatabaseConnector = app.state.db_connection
    redis: RedisConnector = app.state.redis_connection
    return {
        "db": db.test_connection(),
        "redis": redis.ping()
    }

