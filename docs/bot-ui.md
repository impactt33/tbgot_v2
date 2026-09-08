# Интерфейс бота: экраны, кнопки, состояния

> **Главные файлы:**
> [`callbacks/`](../main/presentation/callbacks/) ·
> [`keyboards/`](../main/presentation/keyboards/) ·
> [`states/`](../main/presentation/states/) ·
> [`filters/roles.py`](../main/presentation/filters/roles.py) ·
> [`utils/callback_view.py`](../main/presentation/utils/callback_view.py)
> **Хендлеры:** [`post_handlers.py`](../main/presentation/handlers/post_handlers.py) ·
> [`menu_handlers.py`](../main/presentation/handlers/menu_handlers.py) ·
> [`command_handlers.py`](../main/presentation/handlers/command_handlers.py) ·
> [`admin_panel_handlers.py`](../main/presentation/handlers/admin_panel_handlers.py)

## Карта экранов

```
/start ─ регистрация, роль NONE → отбой
/menu ─┬─ Create post      → канал → тип ─┬─ Quiz / Sources → генерация → черновик
       │                                  └─ Material → картинки → файл → черновик
       ├─ Add created post → канал → «пришли пост»    → черновик
       ├─ Scheduled posts  → список, тап отменяет
       └─ Bot management (только ADMIN)
            ├─ Provide rights → контакт → роль
            ├─ Add channel    → request_chat → экран канала
            ├─ Set up channel → список каналов → экран канала
            └─ Remove channel → request_chat

экран канала ─┬─ Bind / Rebind storage → request_chat (только публичные)
              ├─ Unbind storage        → отвязать
              ├─ Post templates        → типы постов
              └─ Skip / Done           → в меню

типы постов ─ • MATERIAL (3/5) / ○ QUIZ (1/5) / ○ SOURCES (0/5)
                 ↓
экран шаблона ─┬─ Add example       → ждём сообщение
               ├─ Remove example    → список примеров, тап удаляет
               ├─ Set instruction   → ждём текст
               ├─ Clear instruction
               └─ Back

материал ─┬─ шаг 1: пост с картинками (альбом собирается целиком)
          └─ шаг 2: документ → заливка в хранилище → генерация → превью

черновик ─┬─ Publish now  → в канал, всё чистится
          ├─ Schedule     → пресеты ─┬─ пресет → готово
          │                          └─ ручной ввод → время
          ├─ Regenerate   → заново (кроме CUSTOM)
          └─ Discard      → пост и тема/ресурс удалены
```

Команды: `/start`, `/menu`, `/admin`, `/self_info`, `/quit`.

## CallbackData

| Класс | Префикс | Несёт |
|---|---|---|
| `MenuCB` | `menu` | `action` |
| `ChannelCB` | `npc` | `channel_id` → экран типа |
| `CustomChannelCB` | `cpc` | `channel_id` → сразу ждём пост |
| `GenerateCB` | `npg` | `channel_id`, `post_type` |
| `DraftCB` | `npd2` | `action`, `post_id`, `preview_id`, `preview_count` |
| `ScheduleCB` | `nps2` | `preset`, `post_id`, `preview_id`, `preview_count` |
| `ScheduledCB` | `sch` | `action`, `post_id` |
| `SetupChannelCB` | `stc` | `channel_id` → экран настройки канала |
| `StorageCB` | `stg` | `action`, `channel_id` |
| `TemplateTypesCB` | `tpt` | `channel_id` → список типов |
| `TemplateCB` | `tpl` | `action`, `channel_id`, `post_type` |
| `TemplateRemoveExampleCB` | `tprmx` | `channel_id`, `post_type`, `index` |

`ChannelCB` и `CustomChannelCB` разделены намеренно: первая ведёт на выбор типа,
вторая — сразу в ожидание сообщения.

`SetupChannelCB` и `StorageCB` разведены по префиксам не для красоты: у них
разное число полей, и общий префикс означал бы, что `.filter()` одного класса
ловит кнопки другого и падает на распаковке.

По той же причине удаление примера вынесено в `TemplateRemoveExampleCB`, а не в
ещё один `TemplateAction`: индекс не нужен ни одной другой кнопке, а лишнее поле
в `TemplateCB` обрушило бы распаковку всех уже разосланных кнопок. Худшая
упаковка из трёх — `tpl:list_ex:-1001962556344:MATERIAL`, 35 байт из 64.

### Лимит 64 БАЙТА, не символа

Кириллица — по два байта на символ, поэтому русские подписи в `callback_data`
недопустимы. Считать надо на предельных значениях:

```
npd2:regenerate:2147483647:999999:10   → 36 байт из 64
```

### Добавил поле — меняй префикс

**Самая коварная грабля интерфейса.** Новое поле в CallbackData ломает разбор
кнопок, уже лежащих в чате: `unpack` кидает `TypeError`, но `.filter()` его
**ловит и возвращает `False`**. Падения нет, ошибки в логе нет — кнопка просто
молчит.

Поэтому при добавлении `preview_count` префиксы стали `npd2` и `nps2`: под новым
префиксом старые кнопки просто ни с чем не совпадают, вместо того чтобы тихо
умирать.

### Ответить на CallbackQuery можно один раз

Второй `callback.answer()` не дойдёт. Отсюда правило: **всё, что может ответить
алертом, идёт до первого `answer()`.**

Так устроен `regenerate_draft`: сначала `match` по типу поста (ветка `CUSTOM`
отвечает алертом и выходит), и только потом `await callback.answer()`.

Дефект того же рода ещё открыт в `ask_for_time`: `callback.answer()` стоит первым,
и ветка «меню устарело» не показывается никогда — пункт 12 в [STATE.md](STATE.md).

## `render`

Единственный способ перерисовать экран:

```python
async def render(callback, text, markup=None):
    if not isinstance(callback.message, Message):
        await callback.answer("This menu is too old, send /menu again.", show_alert=True)
        return
    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest as exc:
        if "message is not modified" not in str(exc):
            raise
```

Две вещи, которые он закрывает:

1. **`callback.message` это `Message | InaccessibleMessage | None`.** Telegram
   прячет тело сообщений старше 48 часов, и редактировать становится нечего.
2. **Перерисовка того же самого — не ошибка,** но Telegram отвечает
   `TelegramBadRequest: message is not modified`. Глушится по подстроке; всё
   остальное пробрасывается.

## FSM

Состояний намеренно мало — **всё, что можно, сделано кнопками**:

```python
class AdminProvideRightsState(StatesGroup):
    contact = State()
    role = State()

class AdminChannelActionState(StatesGroup):
    waiting_for_channel = State()
    waiting_for_storage = State()

class CreatePostState(StatesGroup):
    waiting_for_time = State()

class TemplateState(StatesGroup):
    waiting_for_example = State()
    waiting_for_instruction = State()

class CustomPostState(StatesGroup):
    waiting_for_post = State()

class MaterialPostState(StatesGroup):
    waiting_for_post = State()
    waiting_for_document = State()
```

`TemplateState` — единственная группа, которой нужна не только «что ждём», но и
«для чего»: пара (канал, тип поста) кладётся в data, потому что у сообщения нет
`callback_data`, откуда её взять. Разбирает её `_template_target` в
[`admin_panel_handlers.py`](../main/presentation/handlers/admin_panel_handlers.py).

`MaterialPostState` копит данные между двумя шагами: `channel_id` кладётся на
входе, `photo_file_ids` и `description` — после первого сообщения, и всё это
нужно на втором. Ошибка генерации состояние **не сбрасывает**: если заливка
прошла, а генерация упала, тот же файл переиспользуется на повторной отправке.

### Порядок регистрации решает

В `post_router` два места, где порядок обязателен, и оба про отсутствующий
фильтр:

```
receive_material_album      ← F.media_group_id
receive_material_post       ← без контент-фильтра: первым съел бы части альбома
receive_material_document   ← F.document
receive_material_not_document ← без фильтра: первым съел бы документы
```

Второй случай — не оптимизация, а лекарство от молчания бота: без
`receive_material_not_document` присланный вместо файла стикер не совпал бы ни с
одним хендлером, и админ не узнал бы, что от него всё ещё чего-то ждут. Ровно
эта дыра числится дефектами 14 и 35 в [STATE.md](STATE.md).

Разведение типов постов сделано **фильтрами, а не порядком**: у `generate_post`
стоит `F.post_type != PostType.MATERIAL`, у `ask_for_material_post` —
`F.post_type == PostType.MATERIAL`. Условия взаимоисключающие, так что порядок
между ними ни на что не влияет.

Хранилище — **Redis**, TTL сутки (`FSM_TTL` в `run.py`). Кнопки состояния не
требуют: `post_id` и `preview_id` едут в `callback_data`, поэтому между
апдейтами ничего помнить не надо.

### Енумы из Redis возвращаются строками

`RedisStorage` сериализует `data` через `json.dumps`, поэтому сравнение через
`is` ломается. Нужно приведение обратно:

```python
raw_action = data.get("action")
action = ChannelAction(raw_action)
```

### `/quit`

Живёт в `command_router`, который включается **раньше** `post_router`, — иначе
хендлер состояния перехватил бы команду. Фильтр `StateFilter(*BOT_STATES)`
означает, что вне состояния `/quit` молчит.

`BOT_STATES` в `states/__init__.py` — единственный список всех групп; добавил
группу — впиши сюда, иначе `/quit` из неё не выйдет.

**Открытый дефект:** `/menu`, `/admin` и `/start` состояние **не** сбрасывают —
ни один не принимает `FSMContext`. Следующая случайная реплика станет черновиком
с кнопкой «Publish now». Окно — сутки. Пункт 4 в [STATE.md](STATE.md).

## Фильтры ролей

```python
class HasAccessFilter(Filter):
    async def __call__(self, event, role: UserRole = UserRole.NONE) -> bool:
        return role is not UserRole.NONE

class IsAdminFilter(Filter):
    async def __call__(self, event, role: UserRole = UserRole.NONE) -> bool:
        return role is UserRole.ADMIN
```

Вешаются на роутер целиком, а не на отдельные хендлеры:

```python
post_router.message.filter(HasAccessFilter())
post_router.callback_query.filter(HasAccessFilter())
```

Роль берётся из `data["role"]`, который кладёт `RoleMiddleware` — см.
[users-and-channels.md](users-and-channels.md).

## Чистка сообщений

Черновик оставляет в чате два сообщения: превью (одно или несколько) и панель
кнопок. После действия обычно надо убрать оба:

| Хелпер | Что убирает |
|---|---|
| `_delete(bot, chat_id, id)` | одно сообщение по id, глушит ошибку |
| `_delete_preview(...)` | превью, возможно из нескольких сообщений подряд |
| `_drop(message)` | сообщение, объект которого ещё на руках |
| `_cleanup_preview(...)` | только превью, кнопки остаются |
| `_cleanup(...)` | превью **и** кнопки |

`_cleanup_preview` нужен именно для Regenerate: старое превью уходит, а панель
остаётся, чтобы экран не мигал.

Все удаления глушат `TelegramAPIError`: сообщение могли удалить руками, и падать
из-за этого незачем.

## Тексты

Все строки для пользователя — константами в начале модуля хендлеров, **по-английски**
(конвенция проекта). Промпты к Gemini — по-русски.
