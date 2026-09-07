# Пользователи, роли и каналы

> **Главные файлы:**
> [`middlewares/role.py`](../main/presentation/middlewares/role.py) ·
> [`handlers/admin_panel_handlers.py`](../main/presentation/handlers/admin_panel_handlers.py) ·
> [`services_impl/user_service_impl.py`](../main/domain/services_impl/user_service_impl.py) ·
> [`services_impl/channel_service_impl.py`](../main/domain/services_impl/channel_service_impl.py) ·
> [`cache_impl/role_cache_impl.py`](../main/data/cache_impl/role_cache_impl.py) ·
> [`keyboards/add_channel.py`](../main/presentation/keyboards/add_channel.py)
> **Рядом:** [`enums/user_role.py`](../main/domain/enums/user_role.py) ·
> [`filters/roles.py`](../main/presentation/filters/roles.py) ·
> [`use_cases/change_user_role.py`](../main/domain/use_cases/change_user_role.py) ·
> [`models/user_model.py`](../main/data/models/user_model.py) ·
> [`models/channel_model.py`](../main/data/models/channel_model.py)

## Роли

```python
class UserRole(str, Enum):
    ADMIN = "ADMIN"   # всё, включая управление
    USER  = "USER"    # создание и публикация постов
    NONE  = "NONE"    # ничего, дефолт при первом /start
```

Новый пользователь получает `NONE` и текст «попроси админа выдать права».
Повысить может только `ADMIN`, и **не себе**: `change_user_role` первым делом
проверяет `actor_telegram_id == target_telegram_id` и кидает
`CannotChangeOwnRoleError`. Смысл — не дать последнему админу случайно разжаловать
себя и запереть бота.

## `RoleMiddleware`

Роль считается **один раз на апдейт** и кладётся в `data["role"]`, откуда её
берут и фильтры, и хендлеры.

```python
tg_user = data.get("event_from_user")
if tg_user is None or tg_user.is_bot:
    data["role"] = UserRole.NONE
    return await handler(event, data)

container = data[CONTAINER_NAME]
cache = await container.get(RoleCache)
role = await cache.get(tg_user.id)
if role is None:
    user_service = await container.get(UserService)
    role = await user_service.get_role(tg_user.id)
    await cache.set(tg_user.id, role)
data["role"] = role
```

Три вещи здесь неочевидны:

1. **Контейнер берётся из `data[CONTAINER_NAME]`,** а не создаётся свой. Это тот
   же REQUEST-контейнер, что достанется хендлеру, — то есть та же сессия БД.

2. **Регистрация после `setup_dishka` и на конкретных обсерверах.** На
   `dp.update` middleware попал бы в другой REQUEST-контейнер, чем хендлер.

3. **`get_role` возвращает `NONE`, а не `None`,** для незарегистрированного:
   `SELECT role WHERE telegram_id = ?` не нашёл строки → `UserRole.NONE`. Поэтому
   апдейт от неизвестного отсекается фильтром, а не падает.

### `/start` и роль

`command_start` берёт роль **не из middleware, а из результата
`get_or_create_user`**:

```python
# role from Middleware read before this handler ran, means it is empty
if new_user.user.role is UserRole.NONE:
```

Причина: при самом первом `/start` middleware отработал **до** того, как строка
появилась, и положил `NONE`. Свежесозданный пользователь всё равно `NONE`, но
проверка честная и не сломается, если дефолт когда-нибудь поменяется.

## Кэш ролей

`RoleCacheImpl` — **заглушка**: `get` всегда `None`, `set` и `invalidate` ничего
не делают. Значит `SELECT` роли идёт на **каждый апдейт**. Интерфейс и точки
инвалидации уже расставлены, так что перевод на Redis — замена одного класса.

`ChangeUserRoleUseCase` существует ровно ради инвалидации:

```python
user = await self.user_service.change_user_role(...)
await self.role_cache.invalidate(target_telegram_id)
```

Сейчас вызов холостой, но когда кэш станет настоящим, забытая инвалидация
означала бы, что разжалованный админ остаётся админом до истечения TTL.

Пункт 24 в [STATE.md](STATE.md).

## Выдача прав

```
Provide rights → AdminProvideRightsState.contact
   админ шлёт контакт  → find_by_telegram_id
                       → не зарегистрирован? «That user has not registered yet.»
                       → state.update_data(contact=id), state → role
   выбор роли (inline) → ChangeUserRoleUseCase
                       → state.clear(), возврат в меню
                       → уведомить пользователя
```

Уведомление обёрнуто отдельно, потому что **пользователь мог заблокировать
бота**:

```python
except TelegramForbiddenError:
    await callback.message.answer("Role was provided, but user blocked the bot.")
except TelegramAPIError:
    logger.exception(...)
```

Роль при этом уже выдана — сбой уведомления не откатывает операцию.

Клавиатура ролей — единственная на «сырых» строках (`provide_role_ADMIN`), а не
на CallbackData-фабрике. Историческое, работает через `F.data.startswith`.

**Открытый дефект:** у `AdminProvideRightsState.contact` нет fallback-хендлера —
на обычный текст вместо контакта бот молчит. Пункт 14 в [STATE.md](STATE.md).

## Добавление и удаление канала

Один хендлер на оба действия, различаются данными состояния:

```
Add channel / Remove channel
   → state = AdminChannelActionState.waiting_for_channel
   → state.update_data(action=ChannelAction.ADD | REMOVE)
   → ReplyKeyboard с request_chat
   → on_chat_shared
```

### `request_chat`

```python
KeyboardButtonRequestChat(
    request_id=1,
    chat_is_channel=True,
    bot_is_member=True,
    request_title=True,
    request_username=True,
)
```

Телеграм сам показывает **только каналы, где бот уже состоит**, и присылает
обратно `chat_id`, `title`, `username`. Ни парсить ссылки, ни спрашивать id
руками не нужно.

`request_id=1` захардкожен и сверяется в хендлере (`if shared.request_id != 1:
return`) — на случай, если в чате осталась кнопка от другого запроса.

### Проверка прав при добавлении

```python
member = await bot.get_chat_member(shared.chat_id, bot.id)
if not (isinstance(member, ChatMemberAdministrator) and member.can_post_messages):
    → «grant this permission and try again»
```

`bot_is_member=True` гарантирует только членство, но не право писать. Проверка
делается **до** записи в БД, чтобы не завести канал, в который нельзя постить.

`TelegramBadRequest` от `get_chat_member` → `BotNotMemberOfChannelError`.

### Дубли

`add_channel` в репозитории — `ON CONFLICT DO NOTHING`, `None` означает «уже
есть», сервис поднимает `ChannelAlreadyAddedError`. Никаких предварительных
SELECT.

Удаление канала уносит по `CASCADE` его `quiz_topics`, `sources` и `materials`, а
посты — тоже `CASCADE`, включая опубликованные.

**Открытый дефект:** `on_chat_shared` делает `state.clear()` **до** проверки
прав, поэтому при отказе админ остаётся без состояния и без кнопки — тупик.
Пункт 13 в [STATE.md](STATE.md).

## Хранилище

Отдельного шага в мастере пока нет: `ChannelService.set_storage_channel` написан,
но никем не вызывается. Это этап 2 в [post-type-material.md](post-type-material.md).
