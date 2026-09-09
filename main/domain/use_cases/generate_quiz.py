import logging

from pydantic import BaseModel, Field

from main.domain.clients import AIClient
from main.domain.entities import (
    PostCreateEntity,
    PostEntity,
    PostTemplateEntity,
    QuizTopicAddEntity,
    QuizTopicEntity,
)
from main.domain.enums import PostType
from main.domain.errors import CannotGenerateTopicError, InvalidQuizDraftError
from main.domain.services import PostService, PostTemplateService, QuizTopicService
from main.domain.use_cases.ai_guard import unwrap_ai
from main.domain.use_cases.html_guard import ALLOWED_TAGS_HINT, strip_tags, visible_length
from main.domain.use_cases.markup_repair import ask_with_valid_markup
from main.domain.use_cases.template_prompt import instruction_block, manner_block

logger = logging.getLogger(__name__)

_MAX_TOPIC_ATTEMPTS = 3

# Telegram's own limits for a poll, counted in visible text.
_QUESTION_LIMIT = 300
_DESCRIPTION_LIMIT = 1024
_OPTION_LIMIT = 100
_EXPLANATION_LIMIT = 200
# Not a consequence of the length: the Bot API allows at most two line feeds in
# an explanation, whatever its size.
_EXPLANATION_LINE_FEEDS = 2


_SYSTEM = (
    "Ты — редактор телеграм-канала о графическом и продуктовом дизайне. "
    "Пишешь по-русски, кратко и по делу, без канцелярита и восклицательных знаков."
)

_TOPIC_PROMPT = """Придумай одну новую тему для короткого квиза о дизайне.

Темы, которые уже были — их использовать нельзя:
{used_topics}
{instruction}
Тема должна быть узкой и конкретной, не «основы типографики», а например «правило внутреннего и внешнего»."""

_QUIZ_PROMPT = """Составь один вопрос для квиза по теме «{topic}».

Вопрос должен проверять понимание, а не запоминание термина.
Неверные варианты сделай правдоподобными — такими, которые выберет человек, знающий тему поверхностно.
{manner}
Требования к ответу:
- question: вопрос обычным текстом, без разметки, до {question_limit} символов;
- description: тело поста в разметке Telegram HTML, до {description_limit} символов
  видимого текста. Разрешены только теги {allowed_tags}, символы < > & вне тегов
  пиши как &lt; &gt; &amp;. Можно оставить пустым, если сказать нечего;
- options: варианты ответа обычным текстом, без разметки, до {option_limit} символов каждый;
- explanation: пояснение в разметке Telegram HTML, до {explanation_limit} символов
  видимого текста и не больше двух переносов строки."""

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
    # Raw caps, tags included: what matters is the visible text, and a limit
    # tight enough for that would reject well-formatted answers. The real
    # thresholds live in _validate.
    description: str = Field(
        default="",
        max_length=1500,
        description="Тело поста в разметке Telegram HTML. Можно оставить пустым",
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
        max_length=400,
        description="Почему верен именно этот вариант, в разметке Telegram HTML",
    )

class GenerateQuizRequest(BaseModel):
    channel_id: int
    topic: QuizTopicEntity | None = None

class GenerateQuizUseCase:
    def __init__(
        self,
        ai_client: AIClient,
        quiz_topic_service: QuizTopicService,
        post_service: PostService,
        template_service: PostTemplateService
    ):
        self.ai_client = ai_client
        self.quiz_topic_service = quiz_topic_service
        self.post_service = post_service
        self.template_service = template_service

    async def __call__(self, request: GenerateQuizRequest) -> PostEntity:
        # Read once and used by both prompts: the topic is picked with the
        # owner's instruction in mind, the post is written with the examples.
        template = await self.template_service.find(request.channel_id, PostType.QUIZ)

        if request.topic is None:
            topic = await self._pick_new_topic(request.channel_id, template)
            logger.info("Quiz topic for channel %s: %r", request.channel_id, topic.topic)
        else:
            topic = request.topic

        draft = await ask_with_valid_markup(
            self.ai_client,
            _QUIZ_PROMPT.format(
                topic=topic.topic,
                manner=manner_block(template),
                question_limit=_QUESTION_LIMIT,
                description_limit=_DESCRIPTION_LIMIT,
                option_limit=_OPTION_LIMIT,
                explanation_limit=_EXPLANATION_LIMIT,
                allowed_tags=ALLOWED_TAGS_HINT,
            ),
            QuizDraft,
            fields=("description", "explanation"),
            system=_SYSTEM,
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

    async def _pick_new_topic(
        self, channel_id: int, template: PostTemplateEntity | None
    ) -> QuizTopicEntity:
        unused_topic = await self.quiz_topic_service.find_unused(channel_id, limit=1)
        if unused_topic:
            return unused_topic[0]

        used = await self.quiz_topic_service.get_topic_names(channel_id)
        used_block = "\n".join(f"- {t}" for t in used) or "(пока ни одной)"

        for attempt in range(1, _MAX_TOPIC_ATTEMPTS + 1):
            idea = unwrap_ai(
                await self.ai_client.ask_structured(
                    _TOPIC_PROMPT.format(
                        used_topics=used_block,
                        instruction=instruction_block(template),
                    ),
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
        if any(visible_length(o) > _OPTION_LIMIT for o in options):
            raise InvalidQuizDraftError(f"An option is longer than {_OPTION_LIMIT} characters.")

        # Markup is guaranteed by markup_repair; these are the size limits it
        # knows nothing about, measured the way Telegram measures them.
        if visible_length(draft.description) > _DESCRIPTION_LIMIT:
            raise InvalidQuizDraftError(
                f"Description is longer than {_DESCRIPTION_LIMIT} characters."
            )
        if visible_length(draft.explanation) > _EXPLANATION_LIMIT:
            raise InvalidQuizDraftError(
                f"Explanation is longer than {_EXPLANATION_LIMIT} characters."
            )
        if strip_tags(draft.explanation).count("\n") > _EXPLANATION_LINE_FEEDS:
            raise InvalidQuizDraftError(
                f"Explanation has more than {_EXPLANATION_LINE_FEEDS} line feeds."
            )