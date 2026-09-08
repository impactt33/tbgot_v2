# Тип поста: MATERIAL (в работе)

**Статус: сделаны этап 1 (слой данных) и этап 2 целиком — привязка хранилища и
шаблоны постов. Этапы 3–5 не начаты.** Постов этого типа бот пока не создаёт.

> **Главные файлы:**
> [`models/material_model.py`](../main/data/models/material_model.py) ·
> [`entities/material_entity.py`](../main/domain/entities/material_entity.py) ·
> [`errors/material_errors.py`](../main/domain/errors/material_errors.py) ·
> [`repositories/material_repo.py`](../main/domain/repositories/material_repo.py) +
> [impl](../main/data/repositories_impl/material_repo_impl.py) ·
> [`services/material_service.py`](../main/domain/services/material_service.py) +
> [impl](../main/domain/services_impl/material_service_impl.py)
> **Рядом:** `MaterialPayload` в [`entities/payloads.py`](../main/domain/entities/payloads.py) ·
> `storage_channel_id` в [`channel_model.py`](../main/data/models/channel_model.py) ·
> `set_storage_channel` в [`channel_service_impl.py`](../main/domain/services_impl/channel_service_impl.py) ·
> миграция [`bdf76a3344c2`](../migration/versions/bdf76a3344c2_materials_table_and_storage_channel.py)

## Задача

Пост вида:

```
название
описание
ссылка на пост в хранилище
```

Материал (обычно PDF или архив) лежит в **чужом** публичном канале. Ссылаться
прямо на чужой пост нельзя — он может исчезнуть. Значит, нужна своя копия: бот
перезаливает файл в **канал-хранилище**, принадлежащий владельцу бота, и
публикует ссылку на неё.

## Почему админ пересылает файл вручную

Всё автоматическое проверено и не работает. Бота в чужой канал добавить нельзя —
каналы не принадлежат владельцу бота, а добавить бота может только админ канала.
Дальше:

- `copyMessage` / `forwardMessage` из чужого канала → `Bad Request: message to
  copy not found` на шести разных `message_id`. Контроль на несуществующем канале
  даёт **другую** ошибку (`chat not found`), то есть дело в доступе, а не в
  существовании поста.
- **Метода вступления в Bot API нет.** Из 181 метода есть `leave_chat`,
  `join_chat` — нет.
- Читающих методов тоже нет: ни `getMessage`, ни `getChatHistory`.
- `getFile` принимает `file_id`, а он приходит только в апдейте из чата, где бот
  состоит. Свой Bot API-сервер снимает лимиты 20/50 МБ, но ходит с **теми же
  правами**.
- Публичная веб-версия `t.me` отдаёт фото и видео прямыми ссылками на
  `cdn*.telesco.pe`, но **не документы**: у постов с файлами в разметке нет ни
  одного класса контента, только «Please open Telegram to view this post».

Отсюда принятая схема: **админ пересылает материал боту в личку.** Это не
автоматизация аккаунта, а человек в своём клиенте.

Из пересланного сообщения бот получает сразу всё:

| Что | Откуда | Зачем |
|---|---|---|
| `document.file_id` | сообщение | перезалить в хранилище |
| `document.file_unique_id` | сообщение | дедупликация |
| `forward_origin.chat` + `.message_id` | `MessageOriginChannel` | источник заполняется сам |

Перезалив идёт по `file_id`, файл не скачивается — лимиты 20 и 50 МБ не
задействованы.

## Хранилище обязано быть публичным

Ссылка на пост в приватном канале имеет вид `t.me/c/<shifted_id>/<msg>` и
открывается **только у участников этого канала**. Подписчик основного канала
нажмёт кнопку и не получит ничего. Поэтому мастер привязки обязан отклонять
канал без `username` — `StorageChannelNotPublicError`.

## `channels.storage_channel_id`

`BigInteger`, nullable, **без FK**. Хранилище — не постинговый канал и своей
строки в `channels` не имеет, ссылаться не на что. Nullable — новостному каналу
материалы не нужны.

Правится через `ChannelService.set_storage_channel(channel_id, storage_channel_id)`;
`None` отвязывает.

## Таблица `materials` по полям

```python
id              Integer PK              # int4, как posts.id и sources.id
channel_id      BigInteger FK→channels CASCADE
file_unique_id  String(127)

source_chat_id     BigInteger  null
source_username    String(63)  null
source_message_id  BigInteger  null

storage_chat_id     BigInteger
storage_message_id  BigInteger

created_at    DateTime(tz) server_default=now()
used_in_post  Integer FK→posts SET NULL
```

**`id` — `Integer`, а не `BigInteger`,** как `posts.id` и `sources.id`. Держи в
голове граблю: `posts.id` это int4, а `channels.channel_id` — BigInteger;
подстановка id канала туда, где ждут id поста, даёт `OverflowError`, обратная
пройдёт молча.

**`channel_id`** — постинговый канал, для которого материал взят. Не хранилище и
не источник. `CASCADE`: удалили канал — материалы под него уезжают следом. Из-за
этого поля дедупликация получается **по каналу**, а не глобальная: один файл
можно взять в два разных канала (проверено).

**`file_unique_id`** — ключ дедупликации. Не `file_id`, хотя качать и
перепощивать умеет только он. Из документации Bot API:

> **file_id**: «can be used to download or reuse the file»
> **file_unique_id**: «is supposed to be the same over time and for different
> bots. **Can't be used to download or reuse the file**»

Нам нужно сравнивать, а не качать: `file_unique_id` переживает смену токена,
`file_id` — нет. Сам `file_id` в таблице **не хранится вообще** — он нужен ровно
один раз, в момент заливки в хранилище. `String(127)` с запасом: реальные
значения короче, документированного максимума нет.

**`source_*` — три nullable-поля,** провенанс из `forward_origin`. Nullable,
потому что `forward_origin` это union из четырёх вариантов, и канал несёт только
один. `MessageOriginHiddenUser` содержит `['type', 'date', 'sender_user_name']` —
ни чата, ни id; такое приезжает, когда источник скрывает пересылки. Будь поля
`NOT NULL`, такой материал нельзя было бы принять вовсе. Отдельно
`source_username` nullable ещё и потому, что `Chat.username` в aiogram это
`str | None`.

`String(63)` — как `channels.username`. `BigInteger` для id сообщения — как
`posts.telegram_message_id`.

**`storage_chat_id` + `storage_message_id`** — координаты нашей копии, не
nullable. Эта пара и есть долговечный хендл вместо `file_id`: она не зависит от
токена, потому что сообщение физически лежит в канале. Материал без копии в
хранилище публиковать нечего.

**`used_in_post`** — `NULL` значит «свободен». `ON DELETE SET NULL`, как у
`sources` и `quiz_topics`: удалили пост — материал возвращается в оборот.
Отсюда же работает `delete_unused`, который удаляет только строку с
`used_in_post IS NULL`.

### Констрейнты

**`uq_channel_material_file (channel_id, file_unique_id)`** — механизм
дедупликации на уровне БД. Он важнее проверки в коде: `add_material` делает
`ON CONFLICT DO NOTHING` по этому индексу, то есть проверка и вставка — один
оператор. «Сначала SELECT, потом INSERT» пропустил бы два одновременных пересыла.

`None` из репозитория означает конфликт, сервис превращает его в
`MaterialAlreadyUsedError`.

**`ix_materials_unused`** — частичный индекс по `used_in_post IS NULL`,
скопирован с `ix_sources_unused`. **Сейчас не нужен:** материалы выбираются
пересылкой, а не запросом «найди свободный», как у источников. Если запрос
«покажи незадействованные материалы канала» не появится — индекс стоит выкинуть,
это лишняя запись при каждом INSERT и UPDATE.

Это же место даёт +2 ошибки mypy на `postgresql_where=cls.used_in_post.is_(None)`
— та же жалоба, что в `source_model.py:41` и `quiz_topic_model.py:42`.

## Payload

```python
class MaterialPayload(BaseModel):
    title: str
    description: str
    storage_chat_id: int
    storage_message_id: int
    storage_username: str

    @property
    def url(self) -> str:
        return f"https://t.me/{self.storage_username}/{self.storage_message_id}"
```

Ссылка **замораживается на момент создания черновика**: при публикации ничего не
резолвится, лишних запросов нет. Поэтому `storage_username` лежит в payload, а не
берётся из `channels` — иначе публикация зависела бы от того, не переименовали ли
хранилище.

## Ошибки

| Ошибка | Когда |
|---|---|
| `MaterialNotFoundError` | нет строки по id |
| `MaterialAlreadyUsedError` | файл уже брали для этого канала |
| `StorageChannelNotSetError` | у канала не привязано хранилище |
| `StorageChannelNotPublicError` | у хранилища нет `username` |

## Что уже проверено

- `PostType.MATERIAL` **уже разрешён** констрейнтом:
  `ck_posts_posttype CHECK (post_type IN ('QUIZ','MATERIAL','SOURCES','CUSTOM'))`
  — миграция под тип поста не нужна.
- `head → downgrade → head` даёт побайтово равную схему (`pg_dump --schema-only`),
  `alembic check` — «No new upgrade operations detected».
- Round-trip репозитория на живом Postgres: привязка и отвязка хранилища,
  дедупликация, пересылка со скрытым источником, `mark_used`, `delete_unused`,
  `ON DELETE SET NULL` при удалении поста.

## Этап 2 — сделано

**Привязка хранилища.** Мастер канала спрашивает хранилище сразу после
подключения канала, плюс отдельный вход «Set up channel» для каналов,
добавленных раньше. Пикер отсекает приватные каналы флагом `chat_has_username`,
права проверяются через `get_chat_member`, пропуск — нормальный исход.
Подробности — [users-and-channels.md](users-and-channels.md#мастер-канала).

**Шаблоны постов.** Таблица `post_templates` хранит 3–5 реальных постов канала
и свободную инструкцию на пару **(канал, тип поста)**. Сводить примеры в
описанный «шаблон» решено не пробовать: модель получает их как есть и
абстрагирует сама, каждый раз. Админка для наполнения готова, к генерации ещё не
подключено — `get_for_generation` ждёт вызова из `CreateMaterialPostUseCase`.
Всё устройство — в [post-templates.md](post-templates.md).

Таблица общая для всех типов, но подключать её будем сначала только к
`MATERIAL`: иначе одна задача трогает работающие `generate_quiz` и
`generate_source`.

## Этапы 3-5 — не начаты

3. **Приём материала:** `MaterialPostState` (картинки с описанием → документ),
   дедупликация по `file_unique_id` **до** заливки, заливка в хранилище.
4. **Тип поста:** `CreateMaterialPostUseCase` (он же зовёт
   `PostTemplateService.get_for_generation`), `TelegramPublisher._publish_material`,
   ветки `MATERIAL` в `discard_draft` (удалить пост в хранилище и строку
   `materials`) и `regenerate_draft` (регенерировать нечего, как `CUSTOM`),
   добавить в `SUPPORTED_POST_TYPES`.
5. `allow_regenerate=False` для `MATERIAL` — упирается в пункты 26–27
   [STATE.md](STATE.md).

## Что выяснилось при планировании

**Ссылка идёт в тексте, не в кнопке.** Проверено: `SendMediaGroup` вообще не
имеет `reply_markup`, в отличие от `SendPhoto`, `SendMessage` и `SendDocument`.
У поста с двумя и более картинками кнопки быть не может, иначе вёрстка зависела
бы от числа картинок.

**`MaterialPayload` придётся расширить `photo_file_ids`.** Пост — это картинки,
описание и ссылка, а текст при картинках едет подписью, где лимит **1024**
UTF-16 единицы, а не 4096. Модель надо ограничивать при генерации, иначе
публикация упадёт уже после того, как файл уехал в хранилище.

**Генерация — последним шагом, после заливки.** Текст ссылается на материал, а
ссылка существует, только когда файл уже в хранилище. Сгенерировать раньше —
значит либо перегенерировать, либо запрещать модели упоминать ссылку.

**Придётся скачивать картинки.** Gemini нужны байты, `file_id` не подойдёт:
`Bot.download(file, destination=None)` вернёт `BinaryIO` в памяти. Это первое
место в проекте, где файл действительно скачивается, — оговорка в
`payloads.py` про «ничего не скачиваем» для `MATERIAL` перестанет быть верной.
`AIClient.ask_image` при этом возвращает `str` и не используется нигде, а
`ask_structured` картинок не принимает: интерфейс надо расширять.

**Открытый вопрос:** поддерживать ли `video`/`audio` кроме `document`. Разбор
отличается только именем поля, а вот `_publish_material` придётся ветвить по
типу, чтобы перезаливать нужным методом.

## Мусор рядом

`main/domain/use_cases/generate_material.py` — пустой файл. В `app/di/use_cases.py`
провайдер `generate_material_post = provide(GenerateSourcePostUseCase)` — имя
врёт про содержимое. Оба числятся в [STATE.md](STATE.md).
