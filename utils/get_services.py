from fastapi import Depends
from infrastructure.databases.postgres import DatabaseConnector
from services.url_shortener.url_shortener_generator import UrlShortenerGenerator
from services.url_shortener.url_shorterner_service import UrlShortenerService
from utils.get_connections import get_db_connector

def get_url_shortener_service(
    db_connector: DatabaseConnector = Depends(get_db_connector)
) -> UrlShortenerService:
    return UrlShortenerService(
        shortener_algorim=UrlShortenerGenerator,
        db_connector=db_connector
    )
