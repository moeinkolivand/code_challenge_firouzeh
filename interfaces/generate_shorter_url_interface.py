from abc import ABC, abstractmethod
from pydantic import HttpUrl

class IGenerateShorterUrl(ABC):
    
    @abstractmethod
    def generate(link: str | int) -> str:
        raise NotImplemented("Method Generate Of Interface IGenerateShorterUrl Is Not Implemented")
