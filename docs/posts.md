# Пост: жизненный цикл, публикация, планировщик

> **Главные файлы:**
> [`use_cases/publish_post.py`](../main/domain/use_cases/publish_post.py) ·
> [`use_cases/discard_draft.py`](../main/domain/use_cases/discard_draft.py) ·
> [`repositories_impl/post_repo_impl.py`](../main/data/repositories_impl/post_repo_impl.py) ·
> [`services_impl/post_service_impl.py`](../main/domain/services_impl/post_service_impl.py) ·
> [`app/scheduler.py`](../app/scheduler.py) ·
> [`clients_impl/telegram/telegram_publisher.py`](../main/data/clients_impl/telegram/telegram_publisher.py)
> **Рядом:** [`enums/post_status.py`](../main/domain/enums/post_status.py) ·
> [`errors/post_errors.py`](../main/domain/errors/post_errors.py) ·
> [`models/post_model.py`](../main/data/models/post_model.py)

## Статусы

```
                    ┌──────────────── unschedule ─────────────┐
                    ▼                                         │
  (создан) ─────► DRAFT ──── schedule ────────────────────► SCHEDULED
                    │                                         │
                    │ claim_for_publishing        claim_scheduled (планировщик)
                    │ claim_for_publishing                     │
                    └──────────────► PUBLISHING ◄──────────────┘
                                      │      │
                          mark_published    mark_failed
                                      ▼      ▼
                                 PUBLISHED  FAILED
```

`DRAFT` и `SCHEDULED` можно удалить (`delete_draft`), `PUBLISHED` — нельзя, это
записано в `WHERE` самого DELETE.

**`PUBLISHING` — статус-ловушка.** Его не выбирает ни один запрос: ни
`claim_scheduled` (берёт `SCHEDULED`), ни `find_scheduled`, ни `delete_draft`.
Пост, застрявший в `PUBLISHING`, не подберёт никто. Отсюда все меры ниже.

## Захват: почему `claim_for_publishing`

Публикация всегда идёт **claim → send → mark**.

Раньше было «прочитать статус, проверить, опубликовать» — три отдельных
оператора. Между проверкой и публикацией успевал вклиниться второй тап или
планировщик, и пост уходил в канал дважды (воспроизводилось: `posts actually
sent to the channel: 2`).

Сейчас проверка и смена статуса — **один оператор**:

```python
update(Post)
.where(Post.id == post_id, Post.status.in_((PostStatus.DRAFT, PostStatus.SCHEDULED)))
.values(status=PostStatus.PUBLISHING)
.returning(Post)
```

Postgres на READ COMMITTED, разблокировавшись после чужого коммита, перепроверяет
`WHERE` уже по новой версии строки. Второй тап не находит ни одной строки,
получает `None`, сервис поднимает `PostNotDraftError` — и до Telegram дело не
доходит вообще.

**Два входа в публикацию:**

```python
async def __call__(self, post_id):          # ручной путь: захватываем здесь
    post = await self.post_service.claim_for_publishing(post_id)
    return await self.publish_claimed(post)

async def publish_claimed(self, post):      # путь планировщика: уже захвачено
```

Планировщик зовёт `publish_claimed`, потому что `claim_due` перевёл посты в
`PUBLISHING` ещё в пачке. Второй раз захватывать нечего.

`claim_scheduled` — та же идея на пачку, плюс `FOR UPDATE SKIP LOCKED` в
подзапросе: несколько экземпляров бота не подерутся за одни и те же строки.

`mark_published` фильтрует по `status == PUBLISHING`. Не нашёл — значит строку
поменял кто-то мимо захвата, и это `PostNotClaimedError`, отдельная ошибка,
чтобы в логе не врало `PostNotFoundError`.

## Почему `except Exception`, а не `except PublisherError`

```python
try:
    message_id = await self.publisher.publish(post, post.channel_id)
except Exception:
    await self._mark_failed(post.id)
    raise
```

`TelegramPublisher` кидает `PublishError` только на `TelegramAPIError`. Но внутри
него сначала идёт `model_validate` payload'а, а это `ValidationError` — мимо
любого `except PublisherError`. Пост оставался в `PUBLISHING` навсегда.

`_mark_failed` отдельным методом с собственным `try`: **бухгалтерия не должна
заслонять исходную ошибку.** Если и `mark_failed` упал, наверх летит первое
исключение, а второе уходит в лог.

## `mark_failed` начинается с `rollback()`

```python
async def mark_failed(self, post_id: int) -> PostEntity | None:
    await self.session.rollback()
    ...
```

Неочевидно, но обязательно. `mark_failed` вызывается **после** того, как что-то
уже упало. Если упал SQL-оператор, транзакция в aborted-состоянии, и любой
следующий оператор на этой сессии умирает на `InFailedSQLTransactionError` — в
том числе сам этот UPDATE. Без `rollback()` пост остаётся в `PUBLISHING`.

Сессию выдаёт dishka на REQUEST-скоуп, репозиторий работает в её рамках, и
`rollback()` отменяет незакоммиченное **в этой же сессии**. Все остальные методы
репозитория коммитят сами, так что откатывать чужую полезную работу нечего.

## Планировщик

`app/scheduler.py`, цикл раз в 60 секунд, две функции — и это разделение
принципиально:

```python
async def run_scheduler(container, interval=60):
    while True:
        for post in await _claim_due(container):   # один скоуп на пачку
            await _publish(container, post)         # скоуп на каждый пост
        await asyncio.sleep(interval)
```

**`_claim_due` — один скоуп на пачку,** потому что это один оператор.

**`_publish` — скоуп на пост.** Скоуп это сессия; провалившийся оператор
отравляет сессию, и все следующие посты пачки умерли бы на
`InFailedSQLTransactionError` вместо публикации. Выход из скоупа закрывает
сессию, следующий пост начинает с чистой.

Воспроизводилось так: пост A валит `IntegrityError` → пост B на той же сессии
остаётся в `PUBLISHING`. После правки: `post A → FAILED, post B → PUBLISHED,
scopes opened: 2`.

Обе функции ловят `Exception` и логируют: **упавший тик не должен убить цикл.**

## `discard_draft` против `delete_draft`

Две разные операции, и их путают:

| | `delete_draft` (сервис) | `DiscardDraftUseCase` |
|---|---|---|
| что делает | удаляет строку поста | удаляет пост **и** освобождающую его тему/ресурс |
| когда | Regenerate | Discard |
| зачем | тема нужна для новой попытки | тема возвращается в общий пул |

Порядок внутри `DiscardDraftUseCase` важен: `used_in_post` объявлен
`ON DELETE SET NULL`, поэтому **сначала удаляется пост** (тем самым освобождая
тему), и только потом сама тема. В обратном порядке в payload осталась бы ссылка
на несуществующую строку.

Ветвление — только `match` с явным `case _`:

```python
match post.post_type:
    case PostType.QUIZ:    topic_id = QuizPayload.model_validate(post.payload).topic_id
    case PostType.SOURCES: source_id = SourcePayload.model_validate(post.payload).source_id
    case PostType.CUSTOM:  pass          # за ручным постом нет ни темы, ни ресурса
    case _:                raise UnsupportedPostTypeError(post.post_type)
```

На `else` наступали трижды: `CUSTOM` проваливался в ветку `SOURCES`. Отдельно —
`raise` обязателен: выражение `UnsupportedPostTypeError(post.post_type)` без
`raise` создаёт объект и молча идёт дальше, пост при этом удаляется.

## Публикация в Telegram

`TelegramPublisher.publish` — единственная точка, знающая, как выглядит каждый
тип поста в канале:

| Тип | Метод API | Заметка |
|---|---|---|
| `QUIZ` | `send_poll(type=QUIZ)` | анонимный, с `explanation` |
| `SOURCES` | `send_message` | ссылка через `LinkPreviewOptions`, не в тексте |
| `CUSTOM` | `send_message` / `send_photo` / `send_media_group` | см. [post-type-custom.md](post-type-custom.md) |
| `MATERIAL` | — | ещё не реализовано |

`TelegramAPIError` заворачивается в `PublishError`; всё остальное летит наверх
как есть и ловится широким `except` в use case.

`PreviewPostUseCase` — тот же `publisher.publish`, но `chat_id` = id админа.
Превью и публикация проходят один и тот же код, поэтому «в превью выглядело
иначе» невозможно by design.
