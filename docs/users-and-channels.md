# Пользователи, роли и каналы

> **Главные файлы:**
> [`middlewares/role.py`](../main/presentation/middlewares/role.py) ·
> [`handlers/admin_panel_handlers.py`](../main/presentation/handlers/admin_panel_handlers.py) ·
> [`services_impl/user_service_impl.py`](../main/domain/services_impl/user_service_impl.py) ·
> [`services_impl/channel_service_impl.py`](../main/domain/services_impl/channel_service_impl.py) ·
> [`cache_impl/role_cache_impl.py`](../main/data/cache_impl/role_cache_impl.py) ·
> [`keyboards/add_channel.py`](../main/presentation/keyboards/add_channel.py) ·
> [`keyboards/channel_setup.py`](../main/presentation/keyboards/channel_setup.py)
> **Рядом:** [`callbacks/channel_setup.py`](../main/presentation/callbacks/channel_setup.py) ·
> [`enums/user_role.py`](../main/domain/enums/user_role.py) ·
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

## Мастер канала

Три входа, один и тот же экран настройки в конце:

```
Add channel      → пикер (id=1) → права → канал записан → экран канала
Remove channel   → пикер (id=1) → канал удалён
Set up channel   → список каналов (• привязано / ○ нет) → экран канала
```

Добавление и удаление по-прежнему различаются данными состояния
(`state.update_data(action=ChannelAction.ADD | REMOVE)`), но экран канала
после добавления открывается сразу: **админ, который только что подключил
канал, — единственный, кто знает, зачем канал нужен.** Отдельный вход
«Set up channel» существует ради каналов, добавленных раньше: спрашивать
хранилище только при добавлении означало бы, что у старых каналов его не будет
никогда.

### Два пикера, а не один

```python
POSTING_REQUEST_ID = 1
STORAGE_REQUEST_ID = 2
```

`request_chat` возвращает `chat_shared` с тем `request_id`, который был в кнопке.
Пикеры разведены по id **и** по состоянию (`waiting_for_channel` против
`waiting_for_storage`), поэтому кнопка, забытая в чате с прошлого шага, не
подставит канал не в тот шаг.

```python
# постинговый канал
KeyboardButtonRequestChat(
    request_id=POSTING_REQUEST_ID,
    chat_is_channel=True, bot_is_member=True,
    request_title=True, request_username=True,
)

# хранилище — плюс одна строка
    chat_has_username=True,
```

**`chat_has_username=True` — фильтр на стороне Telegram.** Ссылка на пост в
приватном канале имеет вид `t.me/c/<id>/<msg>` и открывается только у его
участников, так что приватное хранилище бесполезно. С этим флагом такие каналы
в пикере просто не показываются, и админ не может выбрать негодный.

Серверная проверка `if not shared.username` всё равно осталась: фильтр в
пикере — это UI, а `chat_shared` может прийти от старой кнопки. Тогда летит
`StorageChannelNotPublicError`.

`bot_administrator_rights` в пикере **не используется**: у него 11 обязательных
булевых полей ради одного `can_post_messages`, а `get_chat_member` мы зовём в
любом случае.

### Проверка прав — общий хелпер

```python
async def _bot_can_post(bot: Bot, chat_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, bot.id)
    except TelegramBadRequest:
        raise BotNotMemberOfChannelError() from None
    return isinstance(member, ChatMemberAdministrator) and bool(member.can_post_messages)
```

`bot_is_member=True` гарантирует только членство, но не право писать. Проверка
идёт **до** записи в БД — и для постингового канала, и для хранилища.

### Состояние переживает отказ

Раньше `state.clear()` стоял до проверки прав, и при отказе админ оставался в
тупике: кнопка пикера ещё в чате, но нажатие уже никуда не ведёт. Теперь
состояние сбрасывается **только на успешном исходе**:

- отказ по правам, `BotNotMemberOfChannelError`, `ChannelAlreadyAddedError`,
  `StorageChannelNotPublicError` — состояние живо, админ чинит права и жмёт
  кнопку снова;
- канал записан / удалён / хранилище привязано — `state.clear()`.

Это был дефект 13.

### Экран канала

```
[Bind storage]      → пикер id=2 → проверки → set_storage_channel(id)
[Rebind storage]    → то же, если хранилище уже привязано
[Unbind storage]    → set_storage_channel(None)
[Post templates]    → примеры и инструкция, см. post-templates.md
[Skip] / [Done]     → выход в меню
```

**Пропуск — нормальный исход, а не отказ:** новостной канал материалов не
публикует и хранилища не требует, `storage_channel_id` для того и nullable.

Отдельная проверка — хранилище не может совпадать с постинговым каналом, иначе
файл упал бы прямо в ленту.

`channel_id` едет в `StorageCB`, а не лежит в FSM: экран достижим и сразу после
добавления канала, и из списка настройки, и ни один путь не должен зависеть от
того, уцелело ли состояние между ними.

### Дубли

`add_channel` в репозитории — `ON CONFLICT DO NOTHING`, `None` означает «уже
есть», сервис поднимает `ChannelAlreadyAddedError`. Никаких предварительных
SELECT.

Удаление канала уносит по `CASCADE` его `quiz_topics`, `sources` и `materials`, а
посты — тоже `CASCADE`, включая опубликованные.

**Открытый дефект:** `storage_channel_id` объявлен **без FK**, поэтому удаление
канала-хранилища ничем не отслеживается — id остаётся в строке, а обнаружится
это только при заливке материала. Пункт 34 в [STATE.md](STATE.md).
