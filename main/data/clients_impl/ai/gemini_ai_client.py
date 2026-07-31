import logging
from typing import TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed, wait_exponential

from main.domain.clients import AIClient

logger = logging.getLogger(__name__)

TModel = TypeVar("TModel", bound=BaseModel)

class GeminiGenerateConfig(BaseModel):
    system_instruction: str | None = None
    response_mime_type: str = "plain/text"
    response_schema: BaseModel | None = None
    max_output_tokens: int = 4096
    thinking_config: types.ThinkingConfig = types.ThinkingConfig(thinking_budget=0)


class GeminiAIClient(AIClient):
    def __init__(self, api_key: str):
        self.client = genai.Client(
            api_key=api_key,
            http_options={"base_url": "https://api.proxyapi.ru/google"}  # type: ignore
        )

    @staticmethod
    def process_to_history(history: list[str]) -> list[types.Content]:
        gemini_history = []

        if history is None:
            return gemini_history

        role = "user"

        for content in history:
            gemini_history.append(
                types.Content(role=role, parts=[types.Part(text=content)])
            )

            role = "model" if role == "user" else "user"

        return gemini_history

    @retry(
        retry=retry_if_exception_type((TimeoutError, ConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    async def _generate_content(
        self,
        content: list[types.Content],
        generate_config: types.GenerateContentConfig
    ) -> types.GenerateContentResponse | None:
        try:
            response = await self.client.aio.models.generate_content( # TODO: create GenerateContentConfigDict
                model="gemini-2.5-flash-lite",
                contents=content,
                config=generate_config
            )
        except Exception as exc:
            logger.exception("Failed to generate content: %s", exc)
            return None

        return response

    async def ask_structured(
        self,
        prompt: str,
        schema: type[TModel],
        *,
        system: str | None = None
    ) -> TModel | None:
        generate_config = GeminiGenerateConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=schema,
            max_output_tokens=4096,
            thinking_config=types.ThinkingConfig(thinking_budget=0)
        )

        content = self.process_to_history([prompt])
        config = types.GenerateContentConfig(**generate_config.model_dump())

        response = await self._generate_content(content, config)

        if response is None:
            logger.exception("Gemini request failed")
            return response

        parsed = response.parsed
        if not isinstance(parsed, schema):
            logger.exception("Gemini returned unprocessable payload: %s", parsed)

        return parsed

    async def ask_text(self, prompt: str, *, system: str | None = None) -> str | None:
        generate_config = GeminiGenerateConfig(
            system_instruction=system,
            response_mime_type="text/plain",
            max_output_tokens=2048,
            thinking_config=types.ThinkingConfig(thinking_budget=0)
        )

        content = self.process_to_history([prompt])
        config = types.GenerateContentConfig(**generate_config.model_dump())

        response = await self._generate_content(content, config)

        if response is None:
            logger.exception("Gemini request failed")
            return response

        return response.text

    async def ask_image(self, prompt: str, images: list[bytes], *, mime_type: str = "image/jpeg") -> str | None:
        ...