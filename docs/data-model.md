# Схема данных и миграции

> **Главные файлы:** [`main/data/models/`](../main/data/models/) ·
> [`core/database/base.py`](../core/database/base.py) ·
> [`migration/versions/`](../migration/versions/) · [`migration/env.py`](../migration/env.py)
> **Модели:** [`post_model.py`](../main/data/models/post_model.py) ·
> [`channel_model.py`](../main/data/models/channel_model.py) ·
> [`user_model.py`](../main/data/models/user_model.py) ·
> [`quiz_topic_model.py`](../main/data/models/quiz_topic_model.py) ·
> [`source_model.py`](../main/data/models/source_model.py) ·
> [`material_model.py`](../main/data/models/material_model.py) ·
> [`post_template_model.py`](../main/data/models/post_template_model.py)

Head миграций — `a3f1c9d20e57`.

## Таблицы

```
users                     кто пользуется ботом
channels ─┬─ quiz_topics     темы квизов, по одной на канал
          ├─ sources         ресурсы, о которых уже писали
          ├─ materials       файлы, залитые в канал-хранилище
          └─ post_templates  примеры и инструкция на (канал, тип поста)
posts                     все посты: черновики, отложенные, опубликованные
```

### `users`

| Колонка | Тип | Заметка |
|---|---|---|
| `id` | int4 PK | внутренний |
| `telegram_id` | bigint unique index | тот, что приходит в апдейте |
| `username` | varchar(63) null | может отсутствовать |
| `role` | enum(16) CHECK | `ADMIN` / `USER` / `NONE`, дефолт `NONE` |
| `created_at`, `updated_at` | timestamptz | `updated_at` с `onupdate=func.now()` |

### `channels`

| Колонка | Тип | Заметка |
|---|---|---|
| `channel_id` | bigint PK | id канала из Telegram, вида `-1001962556344` |
| `username` | varchar(63) unique index | у приватного канала `NULL` |
| `title` | varchar(255) null | |
| `storage_channel_id` | bigint null | канал-хранилище, **без FK** |
| `added_at` | timestamptz | |

`storage_channel_id` без внешнего ключа намеренно: хранилище — не постинговый
канал и своей строки в `channels` не имеет. Nullable — новостному каналу
хранилище не нужно. Подробности в [post-type-material.md](post-type-material.md).

Связи `quiz_topics`, `sources`, `materials` — все с `cascade="all, delete-orphan"`,
`passive_deletes=True` и **`lazy="raise"`**.

### `posts`

| Колонка | Тип | Заметка |
|---|---|---|
| `id` | **int4** PK | не bigint, см. граблю ниже |
| `channel_id` | bigint FK→channels CASCADE, index | |
| `post_type` | enum(16) CHECK | `QUIZ` / `MATERIAL` / `SOURCES` / `CUSTOM` |
| `status` | enum(16) CHECK | дефолт `DRAFT`, см. [posts.md](posts.md) |
| `payload` | JSONB | форма зависит от `post_type` |
| `telegram_message_id` | bigint null | id опубликованного сообщения |
| `created_at` | timestamptz | |
| `scheduled_at`, `published_at` | timestamptz null | |

Частичный индекс `ix_posts_due` по `scheduled_at WHERE status = 'SCHEDULED'` —
под запрос планировщика.

**`payload` — единственное нетипизированное место в схеме.** Валидируется
pydantic-моделями из `main/domain/entities/payloads.py`: `QuizPayload`,
`SourcePayload`, `CustomPayload`, `MaterialPayload`. Схема БД про их форму ничего
не знает, поэтому `model_validate` может упасть на любой существующей строке —
это учтено в `PublishPostUseCase` (см. [posts.md](posts.md)).

### `quiz_topics` и `sources` — один шаблон

Обе устроены одинаково, отсюда легко читать третью, `materials`:

| | `quiz_topics` | `sources` |
|---|---|---|
| уникальность | `(channel_id, topic)` | `(channel_id, url)` |
| частичный индекс | `ix_quiz_topics_unused` | `ix_sources_unused` |
| `used_in_post` | int4 FK→posts **SET NULL** | то же |

Смысл `used_in_post`: **`NULL` значит «свободно»**. Пост удалили — строка
возвращается в оборот, а не удаляется вместе с ним. На этом построены и
`find_unused` (взять свободное), и `delete_unused` (убрать только незанятое).

`ON DELETE SET NULL`, а не `CASCADE`, — сознательно: тема или ресурс переживают
свой пост.

### `materials`

Разобрана по полям в [post-type-material.md](post-type-material.md).

### `post_templates`

| Колонка | Тип | Заметка |
|---|---|---|
| `id` | int4 PK | |
| `channel_id` | bigint FK→channels CASCADE | |
| `post_type` | enum(16) CHECK | `ck_post_templates_posttype` |
| `examples` | jsonb, `server_default '[]'::jsonb` | 3–5 постов как есть, Telegram HTML |
| `instruction` | text null | свободный текст владельца канала |
| `created_at`, `updated_at` | timestamptz | `updated_at` с `onupdate=func.now()` |

`uq_post_templates_channel_id_post_type` — **имя задано руками.** Конвенция
строит `uq` из первой колонки и дала бы `uq_post_templates_channel_id`, скрыв
половину ключа. Явное имя конвенцию перебивает: она применяется только к
безымянным ограничениям. Отдельного индекса по паре нет — UNIQUE создаёт его сам.

Массив вместо отдельной таблицы примеров, три однооператорных запроса и грабли
`jsonb - integer` — в [post-templates.md](post-templates.md#таблица-post_templates).

## Конвенции

**`naming_convention` в `Base`.** Имена индексов, констрейнтов и ключей
генерируются по шаблону, руками их писать не надо:

```python
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
```

**Енум-колонки — всегда так:**

```python
SAEnum(PostType, native_enum=False, length=16, create_constraint=True)
```

`native_enum=False` значит `VARCHAR + CHECK` вместо нативного типа Postgres:
добавить значение — это правка CHECK, а не `ALTER TYPE`.

**`from __future__ import annotations`** обязателен в каждой ORM-модели (PEP 649).
Связи по этой же причине объявляются под `if TYPE_CHECKING`.

## Грабли миграций

- **Голое имя в `drop_constraint` / `create_check_constraint`.** Передавать
  `"poststatus"`, а не `"ck_posts_poststatus"` — конвенция накрутит второй
  префикс и получится `ck_posts_ck_posts_poststatus`.
- **Имя CHECK идёт от имени енума, а не от колонки.** Колонка `status`,
  констрейнт `ck_posts_poststatus`. На этом был баг «column post_status does not exist».
- **Смена типа колонки с дефолтом:** DROP DEFAULT → ALTER TYPE … USING →
  SET DEFAULT → DROP TYPE. Autogenerate так не умеет, пишется руками.
- **`include_object` в `migration/env.py` прячет весь дрейф CHECK.** Можно
  дропнуть все констрейнты руками — `alembic check` промолчит.
- **`posts.id` это int4, а `channels.channel_id` — BigInteger.** Подстановка id
  канала туда, где ждут id поста, даёт `OverflowError`; обратная пройдёт молча и
  испортит данные. Поэтому `used_in_post` во всех трёх таблицах — `Integer`.

Три ревизии с известными дефектами (`be6bc6812118`, `49f8db4f9968`,
`186f3cf7cedf`, `channels.channel_id` как скрытый BIGSERIAL) перечислены в
[STATE.md](STATE.md).

## Как добавить таблицу

1. Модель в `main/data/models/`, реэкспорт в `models/__init__.py`.
2. Сущности в `main/domain/entities/` — отдельно `XEntity` (читаем) и
   `AddXEntity` (пишем, без `id` и `created_at`).
3. ABC репозитория, реализация, ABC сервиса, реализация.
4. Провайдеры в `app/di/repositories.py` и `app/di/services.py`.
5. Ошибки в `main/domain/errors/`, реэкспорт.
6. `alembic revision --autogenerate`, потом **прочитать глазами**.
7. Проверить круговым прогоном: `head → downgrade → head` должен дать
   побайтово равный `pg_dump --schema-only`.
