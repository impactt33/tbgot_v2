from abc import ABC, abstractmethod

from pydantic import BaseModel


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str


class WebSearchClient(ABC):
    @abstractmethod
    async def search(self, query: str, *, limit: int = 5) -> list[SearchResult]:
        """Empty list -> nothing was found. Transport Error -> WebSearchError."""