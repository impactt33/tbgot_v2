import logging

from main.domain.clients import MaterialStorage
from main.domain.entities import MaterialPayload, PostEntity, QuizPayload, SourcePayload
from main.domain.enums import PostType
from main.domain.errors import UnsupportedPostTypeError
from main.domain.services import MaterialService, PostService, QuizTopicService, SourceService

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
        source_service: SourceService,
        material_service: MaterialService,
        material_storage: MaterialStorage
    ):
        self.post_service = post_service
        self.quiz_topic_service = quiz_topic_service
        self.source_service = source_service
        self.material_service = material_service
        self.material_storage = material_storage

    async def __call__(self, post_id: int) -> PostEntity:
        post = await self.post_service.get_by_id(post_id)

        topic_id: int | None = None
        source_id: int | None = None
        material: MaterialPayload | None = None

        match post.post_type:
            case PostType.QUIZ:
                topic_id = QuizPayload.model_validate(post.payload).topic_id
            case PostType.SOURCES:
                source_id = SourcePayload.model_validate(post.payload).source_id
            case PostType.MATERIAL:
                material = MaterialPayload.model_validate(post.payload)
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

        if material is not None and material.material_id is not None:
            removed = await self.material_service.delete_unused(material.material_id)

            if removed is None:
                logger.warning(
                    "Material %s stayed in place after discarding post %s",
                    material.material_id, post_id
                )
            elif not await self.material_storage.remove(
                material.storage_chat_id, material.storage_message_id
            ):
                # Row first, copy second. A copy with no row is invisible junk;
                # a row with no copy would publish a link to nothing.
                logger.warning(
                    "Storage copy %s/%s outlived material %s",
                    material.storage_chat_id, material.storage_message_id, material.material_id
                )

        return deleted