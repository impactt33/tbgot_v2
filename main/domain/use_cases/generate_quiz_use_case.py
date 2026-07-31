from pydantic import BaseModel, Field

from main.domain.clients import AIClient


class QuizDraft(BaseModel):
    """Schema that AI must return."""
    title: str = Field(description="Text from 100 to 300 symbols about history of topic from prompt.")
    options: list[str] = Field(min_length=2, max_length=4, description="Realistic answers for question, but only 1 right.")
    correct_index: int = Field(description="Index of correct answer, starting from 0.")

PROMPT = """Составь квиз из {count} вопросов по теме «{topic}».
Используй следующий контекст:

{context}
"""

class GenerateQuizUseCase:
    def __init__(
        self,
        ai_client: AIClient
    ):
        self.ai_client = ai_client