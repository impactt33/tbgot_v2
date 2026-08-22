from pydantic import BaseModel, Field


class QuizPayload(BaseModel):
    question: str = Field(max_length=300)
    options: list[str] = Field(min_length=2, max_length=12)
    correct_index: int = Field(ge=0)
    explanation: str = Field(max_length=200)
    topic_id: int

class SourcePayload(BaseModel):
    title: str
    text: str
    url: str
    source_title: str