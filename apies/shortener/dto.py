from pydantic import BaseModel, HttpUrl

__all__ = [
    'URLInputDto',
    'URLResponseDto'
]

class URLInputDto(BaseModel):
    url: HttpUrl  


class URLResponseDto(BaseModel):
    url: str
