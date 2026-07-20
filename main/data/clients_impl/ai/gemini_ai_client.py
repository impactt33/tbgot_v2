import logging

from google import genai
from google.genai import types
from tenacity import retry_unless_exception_type

from main.domain.clients import AIClient

logger = logging.getLogger(__name__)

class GeminiAIClient(AIClient[list[types.Content]]):
    def __init__(self, api_key: str):
        self.client = genai.Client(
            api_key=api_key,
            http_options={"base_url": "https://api.proxyapi.ru/google"}  # type: ignore
        )

    async def _generate_content(self, parts: list[types.Part], json_mode: bool) -> types.GenerateContentResponse:
        try:
            response = await self.client.aio.models.generate_content( # TODO: create GenerateContentConfigDict
                model="gemini-2.5-flash-lite",
                contents=[
                    types.Content(role="user", parts=parts) # TODO: add history
                ],
                config=types.GenerateContentConfig(
                    system_instruction="",
                    response_mime_type="application/json" if json_mode else "text/plain",
                    max_output_tokens=2048
                )
            )
        except Exception:
            logger.error(f"Gemini request failed")
            raise

        return response

    @staticmethod
    async def process_to_history(history: list[str]) -> list[types.Content]:
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

    async def ask_text(
        self,
        user_message: str,
        json_mode: bool = False
    ):
        parts = [types.Part(text=user_message)]

        response = await self._generate_content(parts, json_mode)

        text = response.text

        # TODO: processing history

        return text

    async def ask_image(
        self,
        user_message: str,
        images_bytes: list[bytes],
        json_mode: bool = False,
        mime_type: str = "image/jpeg"
    ):
        parts = [types.Part(text=user_message)]

        for image_bytes in images_bytes:
            parts.append(types.Part.from_bytes(data=image_bytes, mime_type=mime_type))

        response = await self._generate_content(parts, json_mode)

        text = response.text

        # TODO: processing history

        return text