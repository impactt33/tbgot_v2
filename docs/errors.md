# Ошибки

> **Главные файлы:**
> [`core/errors/app_error.py`](../core/errors/app_error.py) ·
> [`main/domain/errors/`](../main/domain/errors/) ·
> [`presentation/errors.py`](../main/presentation/errors.py) ·
> [`handlers/error_handlers.py`](../main/presentation/handlers/error_handlers.py) ·
> [`use_cases/ai_guard.py`](../main/domain/use_cases/ai_guard.py)

## Один базовый класс с двумя текстами

```python
class AppError(Exception):
    user_message: str = "Something went wrong. Try again later."

    def __init__(self, detail: str = "", *, user_message: str | None = None) -> None:
        self.detail = detail or type(self).__name__
        if user_message is not None:
            self.user_message = user_message
        super().__init__(self.detail)
```

Два текста на разные аудитории: **`detail` — в лог**, с id и значениями;
**`user_message` — в чат**, без внутренностей. Пользователь никогда не видит
`post_id` и имён классов, а в логе всегда есть, за что зацепиться.

## Обязательное правило

**Любой наследник обязан звать `super().__init__(detail)`.**

```python
class PostNotFoundError(PostError):
    user_message = "Post not found."

    def __init__(self, post_id: int | None = None) -> None:
        self.post_id = post_id
        super().__init__(f"Post (post_id: {post_id!r}) was not found.")   # ← обязательно
```

Забыл — у объекта нет `.detail`, и **обработчик ошибки падает сам** на
`AttributeError`. Пользователь вместо «слишком много фото» видит «Something went
wrong», а в логе — трейс не из того места. На этом уже был баг
(`PostInputTooManyPhotosError`).

## Иерархия

```
AppError
├─ UserError          ─ UserNotFound, UserAlreadyExists, AccessDenied, CannotChangeOwnRole
├─ ChannelError       ─ ChannelNotFound, ChannelMissing, ChannelAlreadyAdded,
│                       ChannelAdding, ChannelRemoving, BotNotMemberOfChannel
├─ PostError          ─ UnsupportedPostType, PostNotFound, PostWasNotCreated,
│                       PostAlreadyPublished, PostNotDraft, PostNotClaimed, PostNotScheduled
├─ QuizTopicError     ─ QuizTopicNotFound, CannotGenerateTopic, InvalidQuizDraft
├─ SourceError        ─ SourceNotFound, NoSourceFound, InvalidSourceDraft
├─ MaterialError      ─ MaterialNotFound, MaterialAlreadyUsed, InvalidMaterialDraft,
│                       StorageChannelNotSet, StorageChannelNotPublic,
│                       StorageChannelUnreachable, MaterialStorage
├─ PostTemplateError  ─ PostTemplateNotFound, ExampleNotFound,
│                       TooManyExamples, NotEnoughExamples
├─ AIClientError      ─ RequestFailed, AnswerIsEmpty, AIClientUnavailable,
│                       AIClientRejected, AIClientUnparsableAnswer, AnswerTooBig
├─ MediaError         ─ MediaDownload
├─ PublisherError     ─ PublishError
└─ (presentation)     ─ TimeInputError, TimeInPastError,
                        PostInputError → Empty / Unsupported / TooLong /
                                         TooManyPhotos / NoPhoto
```

Ошибки презентации живут отдельно, в `main/presentation/errors.py`: они про
пользовательский ввод, а не про домен, и их обычно ловят на месте.

## Осторожно с `from .x import *`

`main/domain/errors/__init__.py` подключает модули звёздочкой, по порядку.
**Одноимённые классы затирают друг друга: побеждает импортированный позже.**

На этом было два бага подряд — дубли `UnsupportedPostTypeError` и
`NoSourceFoundError`. Проигравшая версия становилась недостижимой, а в одном
случае ещё и не звала `super().__init__()`. Оба вычищены.

Профилактика: перед добавлением класса ошибки — `grep -rn "class XError" main/`.

## Обработчик: `error_router`

Пять хендлеров, порядок значим — сверху вниз, первый подошедший выигрывает:

| # | Фильтр | Что делает |
|---|---|---|
| 1 | `AppError` + message | `message.answer(user_message)` |
| 2 | `AppError` + callback | `callback.answer(user_message, show_alert=True)` |
| 3 | любое + callback | «Something went wrong. Try /menu.» алертом |
| 4 | любое + message | то же сообщением |
| 5 | любое | только лог |

`AppError` логируется как `warning` с `detail`; всё остальное — `exception` с
полным трейсом.

Хендлер 3 существует не для красоты: **без ответа кнопка в клиенте крутится
вечно**, и пользователь не видит вообще ничего.

Каждый ответ обёрнут в `try/except TelegramAPIError` — пользователь мог
заблокировать бота, и падать в обработчике ошибок особенно неуместно.

`error_router` включается **первым** в `run.py`.

## Когда ловить на месте, а когда пускать наверх

Правило: **если пользователь может исправить это следующим сообщением — лови на
месте и оставляй состояние.**

```python
# ловим сами: админ просто напишет время ещё раз
except TimeInputError as err:
    await message.answer(err.user_message)
    return

# ловим сами: пусть пришлёт другой пост
except PostInputError as err:
    await message.answer(err.user_message)
    return
```

Отдельный случай — генерация:

```python
except AppError as err:
    await render(callback, err.user_message, retry_keyboard(channel_id, post_type))
    return
```

Здесь `error_router` ответил бы алертом и оставил админа смотреть на
«Generating…» без кнопок. Хендлер вместо этого собирает экран заново с кнопкой
«Try again».

Всё остальное летит наверх — это и есть нормальный путь.

## Ошибки AI как значения

`AIClient` возвращает `AIFailure` (енум), а **не кидает**. Превращение в
исключение — отдельная функция:

```python
def unwrap_ai(result: T | AIFailure) -> T:
    if isinstance(result, AIFailure):
        raise _FAILURE_TO_ERROR[result]()
    return result
```

Смысл: клиент в слое данных ничего не знает про доменные ошибки и просто
сообщает, что произошло. Домен решает, как это назвать. Подробнее —
[ai-and-search.md](ai-and-search.md).
