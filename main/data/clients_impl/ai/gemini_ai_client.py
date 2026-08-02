import logging
from typing import TypeVar

import httpx
from google import genai
from google.genai import types
from google.genai import errors as genai_errors
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from main.domain.clients import AIClient
from main.domain.enums.ai_answer_failures import AIFailure

logger = logging.getLogger(__name__)

TModel = TypeVar("TModel", bound=BaseModel)

_RETRYABLE_NETWORK = (httpx.TimeoutException, httpx.NetworkError)
_UNAVAILABLE_ERRORS = (genai_errors.ServerError, *_RETRYABLE_NETWORK)

def _is_retryable(exc: BaseException) -> bool:
    """Retry only accidental errors."""
    if isinstance(exc, _RETRYABLE_NETWORK):
        return True
    if isinstance(exc, genai_errors.ServerError):
        return True
    return isinstance(exc, genai_errors.APIError) and exc.code == 429


class GeminiAIClient(AIClient):
    def __init__(self, api_key: str):
        self.client = genai.Client(
            api_key=api_key,
            http_options={"base_url": "https://api.proxyapi.ru/google"}  # type: ignore
        )

    @staticmethod
    def process_to_history( # TODO: в будушем посмотреть как парситься история, чтобы не было двух последних user
        prompt: str,
        *,
        history: list[str] | None = None,
        images: list[bytes] | None = None,
        mime_type: str = "image/jpeg"
    ) -> list[types.Content]:
        gemini_history = []
        role = "user"

        if history is not None:
            for content in history:
                gemini_history.append(
                    types.Content(role=role, parts=[types.Part(text=content)])
                )

                role = "model" if role == "user" else "user"

        parts = [types.Part(text=prompt)]

        if images is not None:
            for image in images:
                parts.append(types.Part.from_bytes(data=image, mime_type=mime_type))

        gemini_history.append(
            types.Content(role="user", parts=parts)
        )

        return gemini_history

    # noinspection PyTypeChecker
    @retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10), # type: ignore
        reraise=True
    )
    async def _generate_content(
        self,
        content: list[types.Content],
        *,
        generate_config: types.GenerateContentConfig
    ) -> types.GenerateContentResponse:
        return await self.client.aio.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=content,
            config=generate_config
        )

    async def _call(
        self,
        prompt: str,
        images: list[bytes] | None = None,
        history: list[str] | None = None,
        *,
        config: types.GenerateContentConfig,
        mime_type: str = "image/jpeg"
    ) -> types.GenerateContentResponse | AIFailure:
        gemini_history = self.process_to_history(prompt, images=images, mime_type=mime_type, history=history)

        try:
            return await self._generate_content(gemini_history, generate_config=config)
        except genai_errors.ClientError:
            logger.exception("Gemini rejected the request")
            return AIFailure.REJECTED
        except _UNAVAILABLE_ERRORS:
            logger.exception("Gemini is unavailable")
            return AIFailure.UNAVAILABLE
        except Exception:
            logger.exception("Unexpected Gemini failure")
            return AIFailure.UNAVAILABLE

    async def ask_text(self, prompt: str, *, system: str | None = None) -> str | AIFailure:
        generate_config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="text/plain",
            max_output_tokens=2048,
            thinking_config=types.ThinkingConfig(thinking_budget=0)
        )

        response = await self._call(prompt, config=generate_config)

        if isinstance(response, AIFailure):
            return response

        if not response.text:
            logger.error("Gemini request failed")
            return AIFailure.EMPTY

        return response.text # type: ignore

    async def ask_structured(
        self,
        prompt: str,
        schema: type[TModel],
        *,
        system: str | None = None
    ) -> TModel | AIFailure:
        generate_config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_schema=schema,
            max_output_tokens=8192,
            thinking_config=types.ThinkingConfig(thinking_budget=0)
        )

        response = await self._call(prompt, config=generate_config)

        if isinstance(response, AIFailure):
            return response

        parsed = response.parsed
        if not isinstance(parsed, schema):
            logger.error("Gemini returned unprocessable payload: %s", parsed)
            return AIFailure.UNPARSEABLE

        return parsed

    async def ask_image(
        self,
        prompt: str,
        images: list[bytes],
        *,
        system: str | None = None,
        mime_type: str = "image/jpeg"
    ) -> str | AIFailure:
        generate_config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="text/plain",
            max_output_tokens=4096,
            thinking_config=types.ThinkingConfig(thinking_budget=0)
        )
        response = await self._call(prompt, images=images, mime_type=mime_type, config=generate_config)

        if isinstance(response, AIFailure):
            return response

        if not response.text:
            logger.error("Gemini request failed")
            return AIFailure.EMPTY

        return response.text # type: ignore