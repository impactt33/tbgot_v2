from pydantic import BaseModel

from main.domain.entities import CustomPayload, PostCreateEntity, PostEntity
from main.domain.enums import PostType
from main.domain.services import ChannelService, PostService

class CreateCustomPostRequest(BaseModel):
    channel_id: int
    payload: CustomPayload

class CreateCustomPostUseCase:
    """Store a post the admin wrote himself as a draft.

   No AI and no search: the content arrives finished. The channel is still
   looked up, so a post cannot be attached to a channel that was disconnected
   while the admin was typing.
   """

    def __init__(self, post_service: PostService, channel_service: ChannelService):
        self.post_service = post_service
        self.channel_service = channel_service

    async def __call__(self, request: CreateCustomPostRequest) -> PostEntity:
        await self.channel_service.get_channel_by_id(request.channel_id)

        return await self.post_service.create_draft(
            PostCreateEntity(
                channel_id=request.channel_id,
                post_type=PostType.CUSTOM,
                payload=request.payload.model_dump()
            )
        )