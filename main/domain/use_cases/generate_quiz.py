import logging

from pydantic import BaseModel, Field

from main.domain.clients import AIClient
from main.domain.entities import PostCreateEntity, PostEntity, QuizTopicAddEntity
from main.domain.enums import PostType
from main.domain.errors import CannotGenerateTopicError, InvalidQuizDraftError
from main.domain.services import PostService, QuizTopicService
from main.domain.use_cases.ai_guard import unwrap_ai

logger = logging.getLogger(__name__)

_MAX_TOPIC_ATTEMPTS = 3


_SYSTEM = (
    "Ты — редактор телеграм-канала о графическом и продуктовом дизайне. "
    "Пишешь по-русски, кратко и по делу, без канцелярита и восклицательных знаков."
)

_TOPIC_PROMPT = """Придумай одну новую тему для короткого квиза о дизайне.

Темы, которые уже были — их использовать нельзя:
{used_topics}

Тема должна быть узкой и конкретной, не «основы типографики», а например «правило внутреннего и внешнего»."""

_QUIZ_PROMPT = """Составь один вопрос для квиза по теме «{topic}».

Вопрос должен проверять понимание, а не запоминание термина.
Неверные варианты сделай правдоподобными — такими, которые выберет человек, знающий тему поверхностно."""

class TopicDraft(BaseModel):
    topic: str = Field(
        max_length=255,
        description="Тема квиза, 3-7 слов, без кавычек и точки в конце"
    )

class QuizDraft(BaseModel):
    question: str = Field(
        max_length=300,
        description="Вопрос, одно предложение, без вариантов ответа внутри",
    )
    options: list[str] = Field(
        min_length=2,
        max_length=4,
        description="Варианты ответа, каждый до 100 символов. Ровно один верный",
    )
    correct_index: int = Field(
        ge=0, le=3, description="Индекс верного варианта в options, считая с нуля"
    )
    explanation: str = Field(
        max_length=200, description="Почему верен именно этот вариант"
    )

class GenerateQuizRequest(BaseModel):
    channel_id: int

class GenerateQuizUseCase:
    def __init__(
        self,
        ai_client: AIClient,
        quiz_topic_service: QuizTopicService,
        post_service: PostService
    ):
        self.ai_client = ai_client
        self.quiz_topic_service = quiz_topic_service
        self.post_service = post_service

    async def __call__(self, request: GenerateQuizRequest) -> PostEntity:
        topic = await self._pick_new_topic(request.channel_id)
        logger.info("Quiz topic for channel %s: %r", request.channel_id, topic.topic)

        draft = unwrap_ai(
            await self.ai_client.ask_structured(
                _QUIZ_PROMPT.format(topic=topic.topic),
                QuizDraft,
                system=_SYSTEM
            )
        )

        self._validate(draft)

        post = await self.post_service.create_draft(
            PostCreateEntity(
                channel_id=request.channel_id,
                post_type=PostType.QUIZ,
                payload={**draft.model_dump(), "topic_id": topic.id}
            )
        )
        await self.quiz_topic_service.mark_used(topic.id, post.id)
        return post

    async def _pick_new_topic(self, channel_id: int):
        used = await self.quiz_topic_service.get_topic_names(channel_id)
        used_block = "\n".join(f"- {t}" for t in used) or "(пока ни одной)"

        for attempt in range(1, _MAX_TOPIC_ATTEMPTS + 1):
            idea = unwrap_ai(
                await self.ai_client.ask_structured(
                    _TOPIC_PROMPT.format(used_topics=used_block),
                    TopicDraft,
                    system=_SYSTEM
                )
            )
            topic = await self.quiz_topic_service.add_topic(
                QuizTopicAddEntity(channel_id=channel_id, topic=idea.topic.strip())
            )
            if topic is not None:
                return topic
            logger.info("Попытка %s: тема %r уже была", attempt, idea.topic)

        raise CannotGenerateTopicError(channel_id=channel_id)

    @staticmethod
    def _validate(draft: QuizDraft) -> None:
        options = [o.strip() for o in draft.options]
        if any(not o for o in options):
            raise InvalidQuizDraftError("Empty answer variant.")
        if len(set(options)) != len(options):
            raise InvalidQuizDraftError("Answers are duplicated.")
        if draft.correct_index >= len(options):
            raise InvalidQuizDraftError(
                f"correct_index={draft.correct_index} out of range ({len(options)} variants)"
            )
        if any(len(o) > 100 for o in options):
            raise InvalidQuizDraftError("Longer than 1000 symbols.")