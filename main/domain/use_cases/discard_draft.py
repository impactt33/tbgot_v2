import logging

from main.domain.entities import PostEntity, QuizPayload
from main.domain.enums import PostType
from main.domain.services import PostService, QuizTopicService

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

    def __init__(self, post_service: PostService, quiz_topic_service: QuizTopicService):
        self.post_service = post_service
        self.quiz_topic_service = quiz_topic_service

    async def __call__(self, post_id: int) -> PostEntity:
        post = await self.post_service.get_by_id(post_id)

        topic_id: int | None = (
            QuizPayload.model_validate(post.payload).topic_id
            if post.post_type is PostType.QUIZ
            else None
        )

        deleted = await self.post_service.delete_draft(post_id)

        if topic_id is not None:
            topic = await self.quiz_topic_service.delete_unused(topic_id)
            if topic is None:
                logger.warning("Topic %s stayed in place after discarding post %s", topic_id, post_id)

        return deleted