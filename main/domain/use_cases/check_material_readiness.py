from main.domain.entities import ChannelEntity
from main.domain.enums import PostType
from main.domain.errors import PostTemplateError, StorageChannelNotSetError
from main.domain.services import PostTemplateService


class CheckMaterialReadinessUseCase:
    """Whether a material post can be started in a channel, and if not, why.

    Two things have to be in place before anything is forwarded: a bound
    storage channel, and a template with at least MIN_EXAMPLES examples. The
    start of the material flow refuses on either, and the reminders list shows
    the same reason on the channel's button instead of hiding the channel.
    """

    def __init__(self, template_service: PostTemplateService):
        self.template_service = template_service

    async def __call__(self, channel: ChannelEntity) -> None:
        """Raises StorageChannelNotSetError, PostTemplateNotFoundError,
        NotEnoughExamplesError."""
        if channel.storage_channel_id is None:
            raise StorageChannelNotSetError(channel.channel_id)

        # Only the check happens here; generation fetches the template again.
        await self.template_service.get_for_generation(channel.channel_id, PostType.MATERIAL)

    async def find_problem(
        self, channel: ChannelEntity
    ) -> StorageChannelNotSetError | PostTemplateError | None:
        """The error the call would raise, handed back instead. None when ready."""
        try:
            await self(channel)
        except (StorageChannelNotSetError, PostTemplateError) as problem:
            return problem

        return None
