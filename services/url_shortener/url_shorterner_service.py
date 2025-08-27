from pydantic import BaseModel

from infrastructure.databases.postgres import DatabaseConnector
from models.url_shortener import UrlShorter
from repository.url_shortener_repository import UrlShorterRepository

__all__ = [
    "UrlShortenerService"
]


from typing import Type
from interfaces.generate_shorter_url_interface import IGenerateShorterUrl


class UrlShortenerService:
    def __init__(self, shortener_algorim: Type[IGenerateShorterUrl], db_connector: Type[DatabaseConnector]):
        self.shortener = shortener_algorim
        self.repository = UrlShorterRepository(db_connector)
        
    def generate_url_shortener(self, url: str | Type[BaseModel]) -> str:
        url_shortener: UrlShorter = self.repository.create(url)
        shorted_link: str | int = self.shortener.generate(url_shortener.id)
        url_shortener = self.repository.update(url_id=url_shortener.id, shorted_url=shorted_link)

        return url_shortener.shorted_url
    
    def get_real_link(self, url: str | Type[BaseModel]):
        return self.repository.get_by_shorted_url(url)

