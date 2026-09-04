import logging

from main.domain.entities import PostEntity, QuizPayload, SourcePayload
from main.domain.enums import PostType
from main.domain.errors import UnsupportedPostTypeError
from main.domain.services import PostService, QuizTopicService, SourceService

logger = logging.getLogger(__name__)

class DiscardDraftUseCase:
    """Returns unpublished post: 'Discard' or 'Regenerate'.

    Order matters. quiz_topics.used_in_post is set to ON DELETE SET NULL,
    so we first delete the post (freeing up the topic) and only then the topic itself.
    The reverse order would leave a reference to a non-existent topic in the payload.

    Discard also removes the topic row, so the topic returns to the pool and
    can be offered again. Regenerate goes through delete_draft instead and
    keeps the row, so the same topic is reused for the new question.
    """

    def __init__(
        self,
        post_service: PostService,
        quiz_topic_service: QuizTopicService,
        source_service: SourceService
    ):
        self.post_service = post_service
        self.quiz_topic_service = quiz_topic_service
        self.source_service = source_service

    async def __call__(self, post_id: int) -> PostEntity:
        post = await self.post_service.get_by_id(post_id)

        topic_id: int | None = None
        source_id: int | None = None

        match post.post_type:
            case PostType.QUIZ:
                topic_id = QuizPayload.model_validate(post.payload).topic_id
            case PostType.SOURCES:
                source_id = SourcePayload.model_validate(post.payload).source_id
            case PostType.CUSTOM:
                # nothing behind a hand-written post: no topic row, no source row.
                pass
            case _:
                raise UnsupportedPostTypeError(post.post_type)

        deleted = await self.post_service.delete_draft(post_id)

        if topic_id is not None:
            topic = await self.quiz_topic_service.delete_unused(topic_id)
            if topic is None:
                logger.warning("Topic %s stayed in place after discarding post %s", topic_id, post_id)

        if source_id is not None:
            source = await self.source_service.delete_unused(source_id)
            if source is None:
                logger.warning("Source %s stayed in place after discarding post %s", source_id, post_id)

        return deleted