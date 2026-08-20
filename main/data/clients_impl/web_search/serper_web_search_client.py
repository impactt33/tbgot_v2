import logging

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from main.domain.clients import SearchResult, WebSearchClient
from main.domain.errors import WebSearchError

logger = logging.getLogger(__name__)

_SEARCH_URL = "https://google.serper.dev/search"

class SerperWebSearchClient(WebSearchClient):
    def __init__(self, api_key: str, http_client: httpx.AsyncClient):
        self.api_key = api_key
        self.http_client = http_client

    # noinspection PyTypeChecker
    @retry(
        retry=retry_if_exception_type((
            httpx.TimeoutException,
            httpx.NetworkError
        )),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        raraise=True
    )
    async def _request(self, query: str, *, limit: int = 5) -> dict:
        response = await self.http_client.post(
            _SEARCH_URL,
            headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
            json={"q": query, "num": limit}
        )
        response.raise_for_status()
        return response.json()

    async def search(self, query: str, *, limit: int = 5) -> list[SearchResult]:
        try:
            payload = await self._request(query, limit=limit)
        except Exception as exc:
            logger.error(f"Error occurred by SerperClient: {exc}")
            raise WebSearchError(f"serper request failed: {exc}") from exc

        results: list[SearchResult] = []
        for item in payload.get("organic", [])[:limit]:
            link, title = item.get("link"), item.get("title")
            if not link or not title:
                continue
            results.append(
                SearchResult(title=title, url=link, snippet=item.get("snippet", ""))
            )

        return results