# Шаблоны постов: примеры и инструкция

Как канал заставляет модель писать в своей манере. Хранится на **пару
(канал, тип поста)**, наполняется руками через админку, читается генерацией.

> **Главные файлы:**
> [`models/post_template_model.py`](../main/data/models/post_template_model.py) ·
> [`entities/post_template_entity.py`](../main/domain/entities/post_template_entity.py) ·
> [`errors/post_template_errors.py`](../main/domain/errors/post_template_errors.py) ·
> [`repositories/post_template_repo.py`](../main/domain/repositories/post_template_repo.py) +
> [impl](../main/data/repositories_impl/post_template_repo_impl.py) ·
> [`services/post_template_service.py`](../main/domain/services/post_template_service.py) +
> [impl](../main/domain/services_impl/post_template_service_impl.py)
> **Интерфейс:** [`callbacks/templates.py`](../main/presentation/callbacks/templates.py) ·
> [`keyboards/templates.py`](../main/presentation/keyboards/templates.py) ·
> блок «POST TEMPLATES» в [`admin_panel_handlers.py`](../main/presentation/handlers/admin_panel_handlers.py)
> **Миграция:** [`a3f1c9d20e57`](../migration/versions/a3f1c9d20e57_post_templates_table.py)

**Статус: слой данных и админка сделаны, к генерации не подключено.**
`get_for_generation` написан и ждёт вызова из `GenerateMaterialPostUseCase` —
это [этап 3 в post-type-material.md](post-type-material.md).

## Зачем и почему именно примеры

Модель должна писать так, как пишет конкретный канал. Способа два.

**Свести примеры в описание** («короткие абзацы, эмодзи в начале, хештеги в
конце») — и подставлять описание. Отвергнуто:

- дистилляция односторонняя: что модель при сведении не заметила, потеряно
  навсегда, и обнаружится это через десяток кривых постов;
- нужная абстракция зависит от задачи — для поста с одной картинкой важна
  длина, для обзора структура, а сводка пишется заранее и вслепую;
- сводку нечем проверить. Пять реальных постов владелец канала читает глазами и
  знает, что они хорошие.

**Отдать примеры как есть** — принято. Модель абстрагирует сама, каждый раз, с
задачей перед глазами. Цена — две-три тысячи токенов на запрос.

## Что хранится

| Поле | Что это |
|---|---|
| `examples: list[str]` | 3–5 реальных постов канала этого типа, Telegram HTML как есть |
| `instruction: str \| None` | свободный текст владельца канала |

Ключ — **пара (канал, тип поста)**, а не канал целиком: квиз и пост о ресурсе в
одном канале пишутся по-разному.

`instruction` в промпте идёт **после** блока примеров: примеры показывают,
инструкция правит, а вес у того, что ближе к концу, больше.

## Границы

Объявлены в [`services/post_template_service.py`](../main/domain/services/post_template_service.py):

```python
MIN_EXAMPLES = 3
MAX_EXAMPLES = 5
MAX_INSTRUCTION_LENGTH = 1024
TEMPLATE_POST_TYPES = (PostType.MATERIAL, PostType.QUIZ, PostType.SOURCES)
```

**Минимум жёсткий.** Меньше трёх — генерация отказывает
(`NotEnoughExamplesError`), а не деградирует молча: по двум примерам модель
ловит не манеру канала, а случайное совпадение этих двух постов, и результат
хуже, чем вообще без примеров.

**`CUSTOM` в `TEMPLATE_POST_TYPES` нет:** такой пост пишет человек, генерации
там нет и шаблонировать нечего.

## Таблица `post_templates`

```python
id           Integer PK
channel_id   BigInteger FK→channels CASCADE
post_type    enum(16) CHECK
examples     JSONB   server_default '[]'::jsonb
instruction  Text    null
created_at   timestamptz now()
updated_at   timestamptz now(), onupdate now()
```

**Почему JSONB, а не отдельная таблица примеров.** Примеры читаются всегда
целиком, их максимум пять, и по содержимому их никто не ищет — вторая таблица
дала бы только джойн. Плата: пример адресуется **позицией в массиве**, а не
собственным id. Это терпимо, потому что оба пишущих запроса — один оператор
каждый, а экран перерисовывается после каждого действия.

**`uq_post_templates_channel_id_post_type`** — имя задано руками. Конвенция
строит `uq` из первой колонки (`uq_%(table_name)s_%(column_0_name)s`) и дала бы
`uq_post_templates_channel_id`, скрыв половину ключа от того, кто смотрит `\d` в
psql. Явное имя конвенцию перебивает — она применяется только к безымянным
ограничениям.

**`ck_post_templates_posttype`** — имя от **имени енума**, не от колонки. Это
общая грабля проекта, см. [data-model.md](data-model.md#грабли-миграций).

Отдельного индекса по `(channel_id, post_type)` нет: UNIQUE уже создаёт его под
собой.

## Три запроса репозитория

Все три — по одному оператору, ничего не читается в Python и обратно.

### `add_example` — upsert с потолком

```sql
INSERT INTO post_templates (channel_id, post_type, examples)
VALUES (..., ..., jsonb_build_array($1))
ON CONFLICT ON CONSTRAINT uq_post_templates_channel_id_post_type
DO UPDATE SET examples = post_templates.examples || excluded.examples,
              updated_at = now()
WHERE jsonb_array_length(post_templates.examples) < $2
RETURNING ...
```

Отдельного действия «создать шаблон» в интерфейсе нет: строка возникает от
первого же примера. Строки нет — отрабатывает `INSERT` с массивом из одного
элемента; строка есть — `DO UPDATE` дописывает тот же массив к существующему.
Значение упомянуто один раз и переиспользуется через `excluded` — это строка,
которую Postgres собирался вставить.

Альтернатива «SELECT, потом INSERT или UPDATE» — два похода в базу и окно между
ними: два одновременных нажатия оба увидели бы «строки нет».

**Потолок висит на `WHERE` ветки `DO UPDATE`.** Примеров уже пять — ветка не
выполняется, `RETURNING` пуст, репозиторий возвращает `None`, сервис кидает
`TooManyExamplesError`. Ветке `INSERT` проверка не нужна: свежий массив всегда
из одного элемента.

### `remove_example` — удаление по позиции

```sql
UPDATE post_templates
SET examples = examples - $index, updated_at = now()
WHERE channel_id = ... AND post_type = ...
  AND $index >= 0
  AND jsonb_array_length(examples) > $index
RETURNING ...
```

**Две ловушки, обе проверены запуском.**

`$index` объявлен как `sa.bindparam("index", index, type_=sa.Integer)`. Без
явного типа SQLAlchemy приводит правый операнд к типу левого и компилирует
`examples - $index::JSONB`, а оператора `jsonb - jsonb` в Postgres нет вовсе.
Есть три разных: `jsonb - integer` (элемент массива по позиции),
`jsonb - text` (ключ объекта), `jsonb - text[]`. Нужен первый.

`$index >= 0` — потому что **Postgres считает отрицательные позиции с конца**, и
`-1` удалил бы последний пример, а не промахнулся. Проверка длины от этого не
спасает: для `-1` она истинна.

### `set_instruction` — тот же upsert без условия

Возвращает `PostTemplateEntity | None` не потому, что `None` возможен — у
`DO UPDATE` тут нет `WHERE`, строка приходит всегда. Просто `session.scalar`
типизирован как `T | None`, и вместо `cast` взята конвенция проекта:
наблюдение внизу, интерпретация наверху. Сервис превращает `None` в
`PostTemplateNotFoundError`, как `MaterialRepo.mark_used`.

## Ошибки

| Ошибка | Когда |
|---|---|
| `PostTemplateNotFoundError` | шаблона нет вовсе |
| `ExampleNotFoundError` | кнопка удаления указывает мимо массива |
| `TooManyExamplesError` | примеров уже `MAX_EXAMPLES` |
| `NotEnoughExamplesError` | примеров меньше `MIN_EXAMPLES`, генерация отказана |

`NotEnoughExamplesError` кидается **только на генерации**, не при наполнении
шаблона: админ имеет право оставить шаблон недобранным и вернуться позже.

## Экраны

```
Bot management → Set up channel → канал ─┬─ Bind / Unbind storage
                                         ├─ Post templates
                                         └─ Done / Skip
                                                ↓
                            • MATERIAL (3/5)   ○ QUIZ (1/5)   ○ SOURCES (0/5)
                                                ↓
                            экран шаблона ─┬─ Add example       → ждём сообщение
                                           ├─ Remove example    → список примеров
                                           ├─ Set instruction   → ждём текст
                                           ├─ Clear instruction
                                           └─ Back
```

Кружок закрашен при `count >= MIN_EXAMPLES` — он отмечает не «что-то есть», а
«этим уже можно генерировать».

Кнопки прячутся по состоянию: «Add example» пропадает на полном шаблоне,
«Remove example» и «Clear instruction» — когда убирать нечего.

### CallbackData

| Класс | Префикс | Несёт | Худшая упаковка |
|---|---|---|---|
| `TemplateTypesCB` | `tpt` | `channel_id` | 18 байт |
| `TemplateCB` | `tpl` | `action`, `channel_id`, `post_type` | 35 байт |
| `TemplateRemoveExampleCB` | `tprmx` | `channel_id`, `post_type`, `index` | 31 байт |

Удаление вынесено в свой класс, а не в ещё один `TemplateAction`: индекс не
имеет смысла ни для одной другой кнопки, а поле, добавленное в `TemplateCB`,
сломало бы распаковку всех кнопок, уже лежащих в чатах, — и молча, потому что
`.filter()` глотает `TypeError`.

### Приём примера

Хендлер `on_example_received` берёт `message.html_text` — он одинаково собирает
HTML и из `text`, и из `caption`, поэтому пример можно и переслать из канала, и
напечатать руками. Форматирование сохраняется: модели нужен именно тот вид, в
котором пост выйдет.

**Картинки не трогаем.** Присланный пост почти всегда с фото, но хранится только
текст. Части альбома, кроме первой, приходят отдельными апдейтами без подписи —
у них `html_text` пуст, и они отбрасываются молча, по признаку
`media_group_id is not None`. Иначе бот отвечал бы «тут нет текста» по разу на
каждое фото.

Длина считается через `tg_length`, то есть в UTF-16 code units, и сверяется с
`TEXT_LIMIT = 4096`: пост длиннее — это, скорее всего, два поста.

### Пара (канал, тип) в FSM

Кнопки носят её в `callback_data`, но у сообщения callback'а нет, поэтому перед
ожиданием ввода пара кладётся в FSM data. `PostType` — обычный `Enum`, а данные
FSM уезжают через `json.dumps`, так что кладётся `post_type.value`; обратно
Redis отдаёт строку в любом случае, и `_template_target` приводит её через
`PostType(raw)`. Сравнение через `is` без этого ломается — общая грабля,
см. [bot-ui.md](bot-ui.md#енумы-из-redis-возвращаются-строками).

Потеря пары — не ошибка, а истёкший TTL: `_template_target` возвращает `None`,
бот отправляет админа в меню.

### Почему в списке примеров длина, а не превью

`examples_keyboard` подписывает кнопки как `Remove #1 (120 chars)`. Превью не
показывается по двум причинам: примеры хранятся как Telegram HTML, и у половины
постов фрагмент начнётся с `<b>`; плюс у бота глобально `parse_mode=HTML`, так
что любой показ содержимого требует экранирования. По той же причине
`_template_view` прогоняет инструкцию через `html_decoration.quote` — её пишет
человек, и одинокий `<` сломал бы весь экран.

Нормальный просмотр текста примеров — в плане, см. [STATE.md](STATE.md).

## Как это ляжет в промпт (этап D)

Примеры пойдут **блоком в системную инструкцию**, а не чередующимися ходами
user/model. Few-shot по-настоящему — это пары «вход → выход», а входов у нас
нет: из каких фотографий и какого сырого текста родился пост в примерах,
неизвестно. Фальшивые ходы «якобы ты это ответила на якобы вот это» — вранье
модели о её же истории.

Три вещи придётся сказать явно, иначе будет плохо:

1. **Примеры — образец формы, не источник содержания.** Без этого модель тащит
   из них факты и целые фразы. Самый частый способ испортить few-shot.
2. **Разметка в примерах — Telegram HTML,** и ответ должен быть в ней же,
   разрешёнными тегами. Модель увидит `<b>` и `<a href>` прямо в образцах, и
   надо сказать, что это формат вывода, а не мусор.
3. **Пример — пост целиком,** вместе с заголовочной строкой: генерация отдаёт
   структуру (`title` + `description`), и соответствие нужно объяснить.

## Что проверено запуском

- `alembic upgrade head` → `downgrade -1` → `upgrade`; `alembic check` молчит.
- Схема в psql: имена `uq_post_templates_channel_id_post_type`,
  `ck_post_templates_posttype`, `fk_post_templates_channel_id_channels` — как
  задумано.
- Репозиторий на живом Postgres: пять `add_example` подряд растят массив,
  шестой возвращает `None`; `remove_example` по валидному индексу удаляет, по
  индексу за границей и по `-1` не трогает ничего; после удаления снова можно
  добавить; `set_instruction` сохраняет примеры и создаёт строку с пустым
  массивом, если инструкция — первое, что задали.
- `callback_data`: 35 байт из 64 в худшем случае.
- `mypy` — 64, база не сдвинулась; `pytest` — 4 failed / 8 passed / 3 deselected,
  та же база (дефект 23).

Живьём в Telegram экраны **не проверялись**.
