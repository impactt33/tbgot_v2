from main.domain.cache import RoleCache
from main.domain.entities import UserEntity
from main.domain.enums import UserRole
from main.domain.services import UserService


class ChangeUserRoleUseCase:
    """Change user role and reset cache."""

    def __init__(self, user_service: UserService, role_cache: RoleCache):
        self.user_service = user_service
        self.role_cache = role_cache

    async def __call__(
        self,
        actor_telegram_id: int,
        target_telegram_id: int,
        new_role: UserRole
    ) -> UserEntity:
        user = await self.user_service.change_user_role(
            actor_telegram_id,
            target_telegram_id,
            new_role
        )
        await self.role_cache.invalidate(target_telegram_id)
        return user