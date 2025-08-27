from fastapi import APIRouter, Depends
from apies.shortener.dto import URLInputDto, URLResponseDto
from services.url_shortener.url_shorterner_service import UrlShortenerService
from utils.get_services import get_url_shortener_service

generator_router = APIRouter(prefix="/api")

@generator_router.post("/generator", response_model=URLResponseDto)
async def generate_shorten_link(url: URLInputDto, service: UrlShortenerService = Depends(get_url_shortener_service)):
    generated_id = service.generate_url_shortener(str(url.url))
    return URLResponseDto(url=generated_id)


@generator_router.get("/generator/{shorted_url}", response_model=URLResponseDto)
async def generate_shorten_link(shorted_url: str, service: UrlShortenerService = Depends(get_url_shortener_service)):
    url_shorterner = service.get_real_link(shorted_url)
    return URLResponseDto(url=url_shorterner.original_url)
