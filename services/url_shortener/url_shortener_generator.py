from interfaces.generate_shorter_url_interface import IGenerateShorterUrl
from services.url_shortener.url_shortener_generator_helper import encode_base62


class UrlShortenerGenerator(IGenerateShorterUrl):
    
    def generate(link: str | int) -> str:
        return encode_base62(link)
