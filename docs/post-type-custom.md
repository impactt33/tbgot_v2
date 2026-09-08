# Тип поста: CUSTOM (ручной пост и альбомы)

> **Главные файлы:**
> [`utils/post_input.py`](../main/presentation/utils/post_input.py) — `build_custom_payload`,
> рядом с ним живёт `build_material_input` для [материалов](post-type-material.md) ·
> [`utils/media_group.py`](../main/presentation/utils/media_group.py) ·
> [`use_cases/create_custom_post.py`](../main/domain/use_cases/create_custom_post.py) ·
> `_publish_custom` в [`telegram_publisher.py`](../main/data/clients_impl/telegram/telegram_publisher.py)
> **Хендлеры:** `receive_custom_album`, `receive_custom_post`, `_store_custom_post` в
> [`post_handlers.py`](../main/presentation/handlers/post_handlers.py)
> **Рядом:** `CustomPayload` в [`entities/payloads.py`](../main/domain/entities/payloads.py) ·
> [`presentation/errors.py`](../main/presentation/errors.py) ·
> [`callbacks/custom_post.py`](../main/presentation/callbacks/custom_post.py)

Админ пишет пост сам, бот только проверяет и сохраняет. Ни модели, ни поиска.

## Payload

```python
class CustomPayload(BaseModel):
    html_text: str
    photo_file_ids: list[str] = Field(default_factory=list)
```

**Хранится готовый HTML, а не текст + entities.** Форматирование в Telegram
живёт отдельно от текста — координатами в UTF-16, — и собирать его обратно при
каждой публикации незачем. `message.html_text` делает это один раз, причём
одинаково для `text` и для `caption`.

**Фото хранятся как `file_id`.** Telegram уже держит файл; Bot API принимает
`file_id` строкой везде, где принимает загрузку. Скачивать нечего, лимит 20 МБ не
задействован. Оговорка: **`file_id` привязан к токену бота** — при смене токена
сохранённые id перестанут резолвиться, и отложенные посты не опубликуются.
Долговечный вариант — канал-хранилище и `copy_message`, он записан в план.

## Разбор ввода: `build_custom_payload`

Вынесен из хендлера, чтобы правила читались и тестировались без диспетчера.
Принимает **список** сообщений: одиночный пост — список из одного.

```
пусто                       → PostInputEmptyError
фото                        → берём part.photo[-1].file_id   (список идёт от
                              меньшего к большему, последний — оригинал)
не фото внутри альбома      → PostInputUnsupportedError
не фото и не текст          → PostInputUnsupportedError
> 10 фото                   → PostInputTooManyPhotosError
ни фото, ни видимого текста → PostInputEmptyError
длиннее лимита              → PostInputTooLongError
```

Лимиты — телеграмные: **1024 для подписи к фото, 4096 для сообщения**, 10 фото в
альбоме. Порог зависит от того, есть ли фото: текст, уехавший в подпись,
получает вчетверо меньше места.

### `tg_length`

```python
def tg_length(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2
```

Telegram считает длину в **UTF-16 code units**, а не в символах Python. Эмодзи
вне BMP занимает две единицы, поэтому пост, набитый ими, упирается в лимит
раньше, чем показывает `len()`.

### Подпись ищется по всем частям

```python
captioned = next((p for p in parts if (p.caption or p.text)), None)
```

Подпись несёт ровно одна часть альбома, но **не обязательно первая** — порядок
апдейтов не гарантирован.

## Альбомы: `MediaGroupCollector`

Проблема: **у Telegram нет события «альбом получен»**. Приходит по апдейту на
фото, связаны они только общим `media_group_id`, и количества в них нет. Узнать,
что альбом кончился, можно единственным способом — подождать и увидеть, что
больше ничего не пришло.

```python
async def collect(self, message: Message) -> list[Message] | None:
    group_id = message.media_group_id
    if group_id is None:
        return [message]

    if group_id in self._groups:      # не первый: кладём и уходим
        self._groups[group_id].append(message)
        return None

    self._groups[group_id] = [message]   # первый: становимся ждущим
    try:
        await asyncio.sleep(self._settle_delay)   # 1.0 с
    finally:
        parts = self._groups.pop(group_id, [])

    parts.sort(key=lambda part: part.message_id)
    return parts
```

Разделение ролей: **хендлер первого апдейта ждёт и возвращает весь альбом,
остальные молча складывают своё сообщение и возвращают `None`.** Ожидание
остаётся внутри того хендлера, который потом и ответит пользователю, — никакой
фоновой задаче не надо лезть обратно в диспетчер.

`try/finally` вокруг `sleep` — не украшение. `sleep` это точка отмены; на
шатдауне без `finally` буфер остался бы висеть навсегда, и повторный
`media_group_id` попал бы в мёртвый. Проверялось: после отмены было
`buckets left: {'g2': [300, 301]}`, стало `{}`, при этом `CancelledError`
по-прежнему пробрасывается.

Хранение в памяти — сознательно: группа оседает за секунду, перезапуск посреди
альбома стоит переотправки, а не потерянного поста.

**Скоуп обязан быть APP.** На REQUEST каждая часть попала бы в свой пустой
буфер, и фича молча выродилась бы в «пост на каждое фото».

### Порядок регистрации хендлеров

```python
@post_router.message(CustomPostState.waiting_for_post, F.media_group_id)
async def receive_custom_album(...)

@post_router.message(CustomPostState.waiting_for_post)
async def receive_custom_post(...)
```

Альбомный **обязан** стоять первым. aiogram пробует хендлеры в порядке
регистрации, а у второго нет контент-фильтра — стоя первым, он проглотил бы
каждую часть альбома по отдельности.

`F.media_group_id` пропускает только апдейты, у которых поле непустое.
Проверка `group_id is None` внутри коллектора при таком фильтре недостижима —
она страховка на случай вызова из другого места.

## Публикация

`TelegramPublisher._publish_custom` разветвляется по числу фото:

| Фото | Метод | Возвращает |
|---|---|---|
| 0 | `send_message` | `message_id` |
| 1 | `send_photo(caption=…)` | `message_id` |
| 2+ | `send_media_group` | `messages[0].message_id` |

В альбоме подпись несёт только первый элемент — Telegram показывает её под всей
группой. `media` аннотирован как `list[MediaUnion]`, а не `list[InputMediaPhoto]`:
`list` инвариантен, и второе не подошло бы по типу.

## `preview_count`: почему альбом чистится неправильно без него

`send_media_group` — один вызов, наружу приходит только `messages[0].message_id`.
Остальные id идут **подряд**. Поэтому превью альбома из N сообщений нельзя
удалить одним `delete_message`:

```python
async def _delete_preview(bot, chat_id, preview_id, preview_count=1):
    if preview_id is None:
        return
    for offset in range(max(preview_count, 1)):
        await _delete(bot, chat_id, preview_id + offset)
```

Счётчик считается как `max(len(payload.photo_file_ids), 1)`, едет в `DraftCB` и
`ScheduleCB` и читается в пяти точках: `publish_draft`, `discard_draft`,
`regenerate_draft`, `schedule_at_preset`, `receive_time` (последняя — из FSM
data). Клавиатуры `schedule_preset_keyboard` и `back_to_draft_keyboard` его
проносят, иначе он терялся бы при переходе на экран времени и обратно.

## Regenerate у CUSTOM нет

За ручным постом ничего не стоит: ни темы, ни ресурса. Хендлер отвечает алертом
`CANNOT_REGENERATE_TEXT`, а `_store_custom_post` рисует клавиатуру с
`allow_regenerate=False`.

**Известный дефект:** сам `draft_actions_keyboard` флаг `allow_regenerate`
объявляет, но в теле не использует — кнопка рисуется всё равно. Прикрыто со
стороны хендлера. Пункты 26–27 в [STATE.md](STATE.md).

## Use case

`CreateCustomPostUseCase` делает ровно две вещи: проверяет, что канал ещё
существует, и создаёт черновик. Проверка не лишняя — канал могли отключить, пока
админ печатал.
