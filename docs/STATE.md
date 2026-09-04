# Состояние проекта

Обновляется по ходу работы. Если расходится с кодом — верен код, а файл надо
поправить. Проверяй запуском, прежде чем чинить что-то из списка ниже.

**HEAD на момент обновления:** `be3ca62 bugfix;` + незакоммиченные правки
(4 сентября 2026)
**Head миграций:** `49f8db4f9968`

## Бот запускается

Диспетчер собирается ровно как в `run.py` (те же роутеры, `setup_dishka`,
`RoleMiddleware`), `await dp.emit_startup(bot=bot)` проходит: `OK`. Значит все
аннотации хендлеров резолвятся и все `FromDishka`-ключи есть в контейнере.
Проверка не требует ни Postgres, ни Redis — `MemoryStorage` и фейковый токен.

## Открытые дефекты

Найдены ревью четырьмя агентами по слоям плюс прогоном сценария через настоящий
`Dispatcher` с фейковой Telegram-сессией. Все подтверждены запуском.

### Исправлено

1. ~~**`MediaGroupCollector` не импортирован** в `post_handlers.py`~~ — **закрыто.**
   Импорт добавлен, `main/presentation/utils/__init__.py` реэкспортирует
   `MediaGroupCollector`, `tg_length`, `build_custom_payload` и перечисляет их
   в `__all__`. `emit_startup` проходит.

2. ~~**`discard_draft.py`: `else` считает, что всё не-QUIZ это SOURCES**~~ — **закрыто.**
   Ветвление переведено на `match` с явным `case PostType.CUSTOM` и
   `case _: raise UnsupportedPostTypeError(...)`.
   Промежуточная версия правки содержала `UnsupportedPostTypeError(post.post_type)`
   **без `raise`** — выражение, а не оператор: объект создавался и умирал, `match`
   завершался штатно, управление уходило на `delete_draft`. На посте `MATERIAL`
   пост удалялся молча, без исключения. Проверено запуском до и после.

3. ~~**`regenerate_draft`: та же ошибка, теряется пост**~~ — **закрыто, но описание
   было неверным.** `model_validate` стоял **до** `delete_draft`, пост не терялся:
   на `CUSTOM` вылетал `ValidationError` до удаления, черновик оставался в БД.
   Реальных дефектов было два, оба исправлены:
   - `else` вместо `match` — теперь `match` с `case PostType.CUSTOM` (алерт
     `CANNOT_REGENERATE_TEXT`, константа перестала быть мёртвой) и `case _: raise`;
   - `await callback.answer()` стоял **первой строкой** хендлера и съедал
     единственный ответ, поэтому алерт из `app_error_in_callback` не доходил
     (это дефект №12). Перенесён после всего, что может ответить алертом.

8. ~~**`preview_count` мёртв**~~ — **закрыто.** Поле ехало в `DraftCB`/`ScheduleCB`
   и нигде не читалось; превью альбома из N сообщений чистилось на одно.
   Причина в `TelegramPublisher._publish_custom`: альбом уходит одним
   `send_media_group`, наружу возвращается только `messages[0].message_id`,
   а остальные id идут подряд. Что сделано:
   - новый хелпер `_delete_preview(bot, chat_id, preview_id, preview_count)`
     удаляет `preview_id … preview_id + count - 1`; `_cleanup` и `_cleanup_preview`
     принимают `preview_count` и зовут его;
   - счётчик читается во всех пяти точках: `publish_draft`, `discard_draft`,
     `regenerate_draft`, `schedule_at_preset`, `receive_time` (последняя — из FSM
     data, туда `preview_count` теперь кладётся в `ask_for_time`);
   - счётчик перестал теряться при пересадке между клавиатурами:
     `schedule_preset_keyboard` и `back_to_draft_keyboard` принимают и проносят
     `preview_count`, `show_draft_actions`/`schedule_draft`/`ask_for_time` его
     передают.
   Размер `callback_data` после правки — максимум **36 байт из 64**
   (`npd2:regenerate:2147483647:999999:10`), новых полей не добавлялось.

### Побочно исправлено

- **Дубль `UnsupportedPostTypeError`** в `post_errors.py` и `publisher_errors.py`.
  Та же болезнь, что дефект №11, только на другом имени: `errors/__init__.py`
  подключает `post_errors` пятой строкой, `publisher_errors` — седьмой, поздний
  перетирал раннего. Побеждала publisher-версия; post-версия была недостижима и
  **не звала `super().__init__()`** — то есть дефект №9 на ней же. Оставлена одна
  версия в `post_errors.py`, с `super().__init__(detail)`. `telegram_publisher.py`
  импортирует имя из пакета, а не из модуля, поэтому правки не потребовал.
  Из `publisher_errors.py` убран ставший ненужным импорт `PostType`.
- **`PostAlreadyPublishedError` остался без единого использования.** Его
  единственное место было в `PublishPostUseCase`, где проверку `status is
  PUBLISHED` заменил атомарный захват (дефект 7): теперь на второй тап летит
  `PostNotDraftError` с текстом «already published or publishing now», который
  покрывает оба случая. Класс не удалял — решай сам, нужен ли он.
- **`source_errors.py` отдаёт `user_message` по-русски** («Не нашёл ни одного
  нового ресурса», «Пост получился некорректным»), а CLAUDE.md требует, чтобы
  тексты для пользователя были по-английски. Не трогал: это не дефект логики.

### Кластер публикации — закрыт

Проверялся на отдельном Postgres в Docker (порт 5433, рабочая база не тронута).
Оба дефекта сперва воспроизведены на живой БД, потом проверены после правки.

5. ~~**Пост залипает в `PUBLISHING` без падения бота.**~~ — **закрыто.**
   `PublishPostUseCase` ловил только `PublisherError`, а `model_validate` внутри
   публикатора кидает `ValidationError` — мимо обоих `except`. Теперь
   `except Exception`, и `mark_failed` зовётся на чём угодно. Отдельно:
   `_mark_failed` не даёт своей ошибке заслонить исходную — логирует и
   пробрасывает первую (`propagated exception is the original one: ValueError`).
   **Оговорка:** дедупликация `UnsupportedPostTypeError` (см. «Побочно
   исправлено») перевела его из `PublisherError` в `PostError`, то есть сузила
   старый `except PublisherError`. Широкий `except Exception` это перекрывает.

6. ~~**Планировщик открывает один REQUEST-скоуп на всю пачку.**~~ — **закрыто.**
   Воспроизведено: пост A валит `IntegrityError`, пост B на той же сессии
   получает `InFailedSQLTransactionError` и остаётся в `PUBLISHING`.
   `run_scheduler` разбит на `_claim_due` (один скоуп на пачку — это один
   statement) и `_publish` (скоуп на пост). Выход из скоупа закрывает сессию,
   следующий пост начинает с чистой. После правки: `post A -> FAILED,
   post B -> PUBLISHED, scopes opened: 2`.
   Плюс тот самый недостающий `rollback()`: `mark_failed` вызывается уже после
   аварии, то есть сессия может быть в aborted-состоянии, и его собственный
   UPDATE умирал бы вместе с ней. Теперь `PostRepoImpl.mark_failed` начинает с
   `await self.session.rollback()` — без этого пост A оставался в `PUBLISHING`
   даже при скоупе на пост (проверено, это был первый прогон).

7. ~~**`mark_published` без фильтра по статусу и без атомарного захвата.**~~ —
   **закрыто.** Воспроизведено: два одновременных тапа «Publish now» оба
   проходили проверку `status is PUBLISHED` и публиковали — `posts actually sent
   to the channel: 2`. Плюс пост, уже забранный планировщиком в `PUBLISHING`,
   эту проверку тоже проходил.
   Добавлен `PostRepo.claim_for_publishing`: `DRAFT/SCHEDULED -> PUBLISHING`
   одним `UPDATE ... RETURNING`, проверка и смена статуса в одном statement.
   `PublishPostUseCase.__call__` (ручной путь) захватывает сам, а планировщик
   зовёт `publish_claimed(post)` — `claim_due` уже перевёл пост в `PUBLISHING`.
   `mark_published` получил `.where(status == PUBLISHING)` и новую ошибку
   `PostNotClaimedError` (иначе `PostNotFoundError` врал бы в логе).
   После правки: `tap 2: refused`, `sent to the channel: 1`, а на посте в
   `PUBLISHING` — `refused ... | publisher called: 0`, то есть до Telegram дело
   не доходит вообще.

9. ~~**`PostInputTooManyPhotosError` не зовёт `super().__init__()`**~~ —
   **закрыто.** Воспроизведено: `except PostInputError` падал сам на
   `AttributeError: ... has no attribute 'detail'`, и админ вместо «слишком
   много фото» видел «Something went wrong». Добавлен `super().__init__(detail)`.
   Оговорка: `ALBUM_LIMIT = 10` совпадает с лимитом Telegram, так что ветка,
   скорее всего, недостижима — но чинилась одной строкой.

10. ~~**Утечка в `MediaGroupCollector`**~~ — **закрыто.** `try/finally` вокруг
    `asyncio.sleep`, `pop` в `finally`. Было после отмены:
    `buckets left: {'g2': [300, 301]}`, стало `buckets left: {}`, при этом
    `CancelledError` по-прежнему пробрасывается, а обычный путь не изменился.

11. ~~**Дубль `NoSourceFoundError`**~~ — **закрыто.** Версия из `post_errors.py`
    была недостижима (побеждал `source_errors`, он импортируется позже) и нигде
    не использовалась — удалена. Ушли обе ошибки mypy.

### Высокий приоритет

4. **`/menu`, `/admin` и `/start` не сбрасывают FSM.** Ни один из трёх не
   принимает `FSMContext`. Следующая случайная реплика становится черновиком с
   кнопкой «Publish now». Окно — сутки (`FSM_TTL` в `run.py`). Чистят только
   `/quit` и инлайн-кнопка `back_to_menu`. `/start` в прошлой редакции файла
   упомянут не был.
12. **Двойной `callback.answer()`** в `ask_for_time` и внутри `render()` → ветка
    «меню устарело» не показывается никогда. (В `regenerate_draft` и
    `ask_for_custom_post` — см. пункт 3, там исправлено.)
13. **`on_chat_shared` чистит состояние до проверки прав** — при отказе тупик.
14. **`AdminProvideRightsState.contact` без fallback** — на текст бот молчит.

### Клавиатура черновика

26. **`allow_regenerate` объявлен в `draft_actions_keyboard`, но в теле не
    используется** — кнопка Regenerate рисуется и на `CUSTOM`-посте, хотя
    `post_handlers.py` в кастомной ветке честно передаёт `allow_regenerate=False`.
    Пока не трогаем — решение за владельцем. Со стороны хендлера уже прикрыто:
    `regenerate_draft` на `CUSTOM` отвечает `CANNOT_REGENERATE_TEXT`.
27. **`show_draft_actions` теряет `allow_regenerate`.** Кнопка «Back» с экрана
    ввода времени перерисовывает клавиатуру черновика без флага, так что на
    `CUSTOM` Regenerate вернётся даже после починки пункта 26. `DraftCB` этого
    флага не несёт. Два пути:
    - пронести флаг через `callback_data` — новое поле, значит новый префикс
      (`npd3`), как уже делалось ради `preview_count`; запас по байтам есть
      (36 из 64);
    - не носить, а выводить: `CUSTOM` — единственный тип без регенерации,
      `post_type` берётся из `post_service.get_by_id(post_id)` прямо в
      `show_draft_actions`. Один лишний SELECT на нажатие «Back», зато без
      миграции клавиатур.

### Миграции

15. **Две ревизии дают разную схему в зависимости от направления.**
    `be6bc6812118`: `upgrade` — no-op, `downgrade` сужает CHECK сильнее, чем было
    на предыдущей ревизии; оба должны быть `pass`.
    `49f8db4f9968`: `downgrade` восстанавливает `('QUIZ','MATERIAL','SOURCES')`,
    хотя было `('QUIZ','SOURCES')`, и падает на строках `CUSTOM` — откат головы
    невозможен без ручной подготовки.
16. **`channels.channel_id` — скрытый BIGSERIAL.** Нет `autoincrement=False`,
    вставка без id молча создаёт канал с `channel_id = 1`.
17. **`186f3cf7cedf` теряет данные:** `created_at → added_at` сделано add+drop
    с `server_default=now()` вместо `alter_column(new_column_name=...)`.

### Конфигурация и инфраструктура

18. `DATABASE_ECHO: bool = True` по умолчанию — прод получит SQL-лог с payload постов.
19. Шатдаун рвёт ресурсы под работающими хендлерами: `start_polling` не дожидается
    задач апдейтов, а `finally` сразу закрывает контейнер и Redis.
20. Движок без `pool_pre_ping` — после простоя первый апдейт падает на мёртвом коннекте.
21. `settings.DEBUG`, `APP_HOST`, `APP_PORT`, `DB_MIN_POOL_SIZE`, `DATABASE_URL`
    не используются нигде. `setup_logging(log_level="DEBUG")` захардкожен.
    `logs/` создаётся относительно cwd.
22. `docker-compose.yml`: сервиса бота нет, healthcheck'и никто не потребляет;
    том `pgdata` объявлен, но монтируется bind-mount; `max_connections=1000`
    при `memory: 512M`.
23. **4 теста падают:** `tests/conftest.py` без `FakeSourceService`, а
    `GenerateSourcePostUseCase.__init__` требует `source_service`.
    `test_empty_search_results` нужно три ответа `SearchQueryDraft`.
    Прогон: `4 failed, 8 passed, 3 deselected`.
24. `RoleCacheImpl` — заглушка, поэтому SELECT роли на каждый апдейт.
25. Нет `[tool.ruff]` в `pyproject.toml` и нет CI — поэтому разъехавшиеся тесты
    никто не заметил.

## Проверено и работает — не переделывать

Порядок роутеров и хендлеров правильный. `/quit` матчится на всех группах состояний.
`callback_data` — максимум 36 байт из 64. Все скоупы DI верны, все REQUEST-ключи
резолвятся. `RoleMiddleware` и хендлер получают один и тот же контейнер.
`claim_scheduled` с `FOR UPDATE SKIP LOCKED` корректен. `ChannelAction` из Redis
приводится обратно правильно. Круговой прогон миграций head → ревизия → head даёт
равную схему в 11 случаях из 11. Домен не импортирует инфраструктуру, ORM-объекты
за репозиторий не утекают.

## Как проверять

- **Старт диспетчера без сети:** собрать роутеры и контейнер как в `run.py`, но с
  `MemoryStorage` и фейковым токеном, и вызвать `await dp.emit_startup(bot=bot)`.
  Без `emit_startup` dishka не вешает `inject_router`, и хендлеры с `FromDishka`
  падают на `TypeError: missing required positional arguments`.
- **mypy как источник истины, но с базой для сравнения.** По всему проекту
  (`mypy main/ core/ app/`) сейчас **62 ошибки против 65 на чистом `HEAD`**, почти
  все — `no-untyped-def` на хендлерах и `union-attr` на
  `Message | InaccessibleMessage | None`. Прежде чем считать новую ошибку своей,
  снимай базу через `git worktree add <tmp> HEAD` (не забудь скопировать туда
  `app/.env`, без него не импортируется `core.config`).
- **`dishka`-контейнер типизирован как `Any`:** `await container.get(PostService)`
  возвращает `Any`, и `mypy` теряет тип дальше по цепочке. Аннотируй присваивание
  явно — `post_service: PostService = await request_container.get(PostService)`.
- **Живая БД для проверки гонок и транзакций.** Отдельный контейнер на порту 5433,
  схема через `Base.metadata.create_all` (мимо миграций, у них свои дефекты
  15-17), рабочая база не трогается:
  `docker run --rm -d --name tbgot_scratch_pg -e POSTGRES_USER=test
  -e POSTGRES_PASSWORD=test -e POSTGRES_DB=test -p 5433:5432 postgres:16`
- **Размер `callback_data`** — считать в байтах на предельных значениях
  (`post_id = 2147483647`, `preview_count = 10`), а не на глаз.

## Посты с материалами (в работе)

Материалы лежат в **чужих** публичных каналах, добавить туда бота нельзя. Поэтому
достать файл автоматически невозможно — проверено:

- `copyMessage`/`forwardMessage` из чужого канала → `Bad Request: message to copy
  not found` на шести разных `message_id`; контроль на несуществующем канале даёт
  другую ошибку (`chat not found`), то есть дело в доступе, а не в существовании.
- Метода вступления в Bot API нет: из 181 метода есть `leave_chat`, `join_chat` —
  нет. Бота в чужой канал может добавить только его админ.
- Читающих методов тоже нет: ни `getMessage`, ни `getChatHistory`.
- `getFile` принимает `file_id`, а он приходит только в апдейте из чата, где бот
  состоит. Свой Bot API-сервер снимает лимиты 20/50 МБ, но ходит с теми же правами.
- Публичная веб-версия `t.me` отдаёт **фото и видео** (прямые ссылки на
  `cdn*.telesco.pe`), но **не документы**: у постов с файлами в разметке нет ни
  одного класса контента, только «Please open Telegram to view this post».
  У канала при этом `has_protected_content` не выставлен — значит дело в типе
  контента, а не в настройках канала.

**Принятая схема: админ пересылает материал боту.** Это не автоматизация аккаунта,
а человек в своём клиенте. Из пересланного сообщения бот получает сразу всё:
`document.file_id` для перепубликации, `document.file_unique_id` для
дедупликации и `forward_origin` (`MessageOriginChannel.chat` + `.message_id`) —
источник заполняется сам, вставлять ссылки руками не надо. Перепост идёт по
`file_id`, файл не скачивается, лимиты 20 и 50 МБ не задействованы.

Формат поста: `название \n описание \n ссылка на пост в хранилище`.

**Хранилище обязано быть публичным.** Ссылка на приватный канал имеет вид
`t.me/c/<shifted_id>/<msg>` и открывается только у его участников — у подписчика
основного канала кнопка молча не сработает. Мастер привязки должен отклонять
канал без `username` (`StorageChannelNotPublicError`).

### Этап 1 — схема данных: сделано

- `channels.storage_channel_id` — `BigInteger`, nullable, **без FK**: хранилище не
  постинговый канал и своей строки в `channels` не имеет. Nullable ради каналов,
  которым материалы не нужны (новостные).
- Таблица `materials` по образцу `sources`: `file_unique_id` как ключ
  дедупликации (он, в отличие от `file_id`, переживает смену токена),
  `source_chat_id`/`source_username`/`source_message_id` **nullable** — канал может
  скрывать пересылки, тогда приезжает `MessageOriginHiddenUser` без чата,
  `storage_chat_id`/`storage_message_id`, `used_in_post` с `ON DELETE SET NULL`,
  `UniqueConstraint(channel_id, file_unique_id)`.
- `MaterialEntity`/`AddMaterialEntity`, `MaterialPayload` (ссылка собирается
  свойством `url`, при публикации ничего не резолвится), `MaterialRepo` + impl,
  `MaterialService` + impl, ошибки, провайдеры dishka,
  `ChannelService.set_storage_channel`.
- Миграция `bdf76a3344c2`. **Миграция для `PostType.MATERIAL` не нужна** — он уже
  разрешён констрейнтом: `ck_posts_posttype CHECK (post_type IN ('QUIZ',
  'MATERIAL', 'SOURCES', 'CUSTOM'))`, проверено на живой базе.
- Проверено: `head → downgrade → head` даёт побайтово равную схему
  (`pg_dump --schema-only`), `alembic check` — «No new upgrade operations
  detected», round-trip репозитория на живом Postgres (привязка и отвязка
  хранилища, дедупликация, пересылка со скрытым источником, `mark_used`,
  `delete_unused`, `ON DELETE SET NULL` при удалении поста).
- **mypy 62 → 64.** Обе новые ошибки — в `material_model.py:63`, на
  `postgresql_where=cls.used_in_post.is_(None)`. Это ровно тот же паттерн и та же
  жалоба, что уже есть в `source_model.py:41` и `quiz_topic_model.py:42`: внутри
  `declared_attr.directive` mypy видит `int | None` вместо дескриптора. Оставил
  как у соседей, чтобы не разъезжаться стилем. Лечится в трёх местах разом заменой
  на `sa.text("used_in_post IS NULL")` — DDL получается идентичный.

### Этапы 2-5 — не начаты

2. Привязка хранилища в мастере добавления канала: `request_chat`, проверки «бот
   админ», `can_post_messages` и наличие `username`, кнопка Skip, отдельная
   перепривязка.
3. Приём материала: `MaterialPostState` (материал → название → описание),
   хендлер на пересланный документ, дедупликация, заливка в хранилище.
4. Тип поста `MATERIAL`: `CreateMaterialPostUseCase`,
   `TelegramPublisher._publish_material`, ветки `MATERIAL` в `discard_draft`
   (удалить пост в хранилище и строку `materials`) и `regenerate_draft`
   (регенерировать нечего, как `CUSTOM`), `SUPPORTED_POST_TYPES`.
5. `allow_regenerate=False` для `MATERIAL` — упирается в пункты 26-27.

**Открыто:** ссылка в тексте или в кнопке (сделано в тексте, по последнему
описанию); поддерживать ли `video`/`audio` кроме `document`.

## Дальше по плану

1. Тесты на чистые функции: `parse_when`, `in_hours`, `next_day_at`,
   `resolve_preset`, `build_custom_payload`, `tg_length`. Кейсы пишу я сам —
   нужно ТЗ от Claude, потом проверка. Перед этим стоит закрыть пункт 23, чтобы
   новые тесты не приезжали в красный прогон.
2. Тест целостности DI-контейнера и тест скоупов в CI.
3. Видео и документы в собственных постах, включая смешанные альбомы.
4. Канал-хранилище для картинок на случай смены токена (`file_id` привязан к токену).
5. `RoleCache` на Redis.
6. mypy в pre-commit, README.
