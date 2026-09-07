# Открытые дефекты и план

**Только то, что надо починить.** Описание того, как всё устроено, — в
[README.md](README.md) и файлах по подсистемам.

**HEAD:** `683a2a0`, дерево чистое, совпадает с `origin/master` (7 сентября 2026).
**Head миграций:** `bdf76a3344c2`.
**База для сравнения:** `mypy main/ core/ app/` — 64 ошибки; `pytest` — 4 failed,
8 passed, 3 deselected. Как снимать — [testing.md](testing.md).

Нумерация от исходного ревью, пропуски — закрытые пункты (1, 2, 3, 5, 6, 7, 8,
9, 10, 11 закрыты в `683a2a0`).

## Высокий приоритет

**4. `/menu`, `/admin` и `/start` не сбрасывают FSM.**
Ни один не принимает `FSMContext`. Следующая случайная реплика становится
черновиком с кнопкой «Publish now». Окно — сутки (`FSM_TTL`). Чистят только
`/quit` и инлайн-кнопка `back_to_menu`.
→ [bot-ui.md](bot-ui.md#fsm)

**12. Двойной `callback.answer()` в `ask_for_time`.**
`answer()` стоит первой строкой, и проверка `isinstance(callback.message, Message)`
ниже отвечает во второй раз — ветка «меню устарело» не показывается никогда. То
же внутри `render()`.
→ [bot-ui.md](bot-ui.md#ответить-на-callbackquery-можно-один-раз)

**13. `on_chat_shared` чистит состояние до проверки прав.**
`state.clear()` идёт раньше `get_chat_member`; при отказе админ остаётся без
состояния и без кнопки — тупик.
→ [users-and-channels.md](users-and-channels.md#проверка-прав-при-добавлении)

**14. `AdminProvideRightsState.contact` без fallback.**
На обычный текст вместо контакта бот молчит.

## Клавиатура черновика

**26. `allow_regenerate` объявлен, но не используется.**
`draft_actions_keyboard` принимает флаг и игнорирует его — кнопка Regenerate
рисуется и на `CUSTOM`-посте, хотя хендлер честно передаёт `allow_regenerate=False`.
Со стороны хендлера прикрыто: `regenerate_draft` на `CUSTOM` отвечает
`CANNOT_REGENERATE_TEXT`.

**27. `show_draft_actions` теряет `allow_regenerate`.**
Кнопка «Back» с экрана ввода времени перерисовывает клавиатуру без флага, так что
на `CUSTOM` Regenerate вернётся даже после починки 26. `DraftCB` флага не несёт.
Два пути:
- пронести через `callback_data` — новое поле, значит новый префикс (`npd3`);
  запас по байтам есть (36 из 64);
- вывести на месте: `CUSTOM` — единственный тип без регенерации, `post_type`
  берётся из `post_service.get_by_id(post_id)` прямо в `show_draft_actions`.
  Один лишний SELECT на «Back», зато без миграции клавиатур.

## Миграции

**15. Две ревизии дают разную схему в зависимости от направления.**
`be6bc6812118`: `upgrade` — no-op, `downgrade` сужает CHECK сильнее, чем было на
предыдущей ревизии; оба должны быть `pass`.
`49f8db4f9968`: `downgrade` восстанавливает `('QUIZ','MATERIAL','SOURCES')`, хотя
было `('QUIZ','SOURCES')`, и падает на строках `CUSTOM` — откат головы невозможен
без ручной подготовки.

**16. `channels.channel_id` — скрытый BIGSERIAL.**
Нет `autoincrement=False`, вставка без id молча создаёт канал с `channel_id = 1`.
Подтверждено на живой базе: `default = nextval('channels_channel_id_seq')`.

**17. `186f3cf7cedf` теряет данные.**
`created_at → added_at` сделано add+drop с `server_default=now()` вместо
`alter_column(new_column_name=...)`.

## Конфигурация и инфраструктура

**18.** `DATABASE_ECHO: bool = True` по умолчанию — прод получит SQL-лог с payload постов.

**19.** Шатдаун рвёт ресурсы под работающими хендлерами: `start_polling` не
дожидается задач апдейтов, а `finally` сразу закрывает контейнер и Redis.

**20.** Движок без `pool_pre_ping` — после простоя первый апдейт падает на мёртвом
коннекте.

**21.** `settings.DEBUG`, `APP_HOST`, `APP_PORT`, `DB_MIN_POOL_SIZE`,
`DATABASE_URL` не используются нигде. `setup_logging(log_level="DEBUG")`
захардкожен. `logs/` создаётся относительно cwd.

**22.** `docker-compose.yml`: сервиса бота нет, healthcheck'и никто не потребляет;
том `pgdata` объявлен, но монтируется bind-mount; `max_connections=1000` при
`memory: 512M`.

**23. 4 теста падают.** `tests/conftest.py` без `FakeSourceService`, а
`GenerateSourcePostUseCase.__init__` требует `source_service`.
`test_empty_search_results` нужно три ответа `SearchQueryDraft`.

**24.** `RoleCacheImpl` — заглушка, поэтому SELECT роли на каждый апдейт.

**25.** Нет `[tool.ruff]` в `pyproject.toml` и нет CI — поэтому разъехавшиеся
тесты никто не заметил.

## Мелочи, ждущие решения

**28.** `main/domain/use_cases/generate_material.py` — пустой файл (0 строк).

**29.** `app/di/use_cases.py:12`:
`generate_material_post = provide(GenerateSourcePostUseCase)` — имя провайдера
врёт про содержимое.

**30.** `postgresql_where=cls.used_in_post.is_(None)` даёт по 2 ошибки mypy в
`material_model.py:63`, `source_model.py:41`, `quiz_topic_model.py:42`. Лечится в
трёх местах разом заменой на `sa.text("used_in_post IS NULL")` — DDL получается
идентичный.

**31.** `PostAlreadyPublishedError` остался без единого использования: его место
занял `PostNotDraftError` после введения атомарного захвата. Удалять или нет —
решение владельца.

**32.** `source_errors.py` отдаёт `user_message` по-русски («Не нашёл ни одного
нового ресурса», «Пост получился некорректным»), хотя тексты для пользователя
должны быть английскими.

**33.** `GenerateQuizUseCase._validate` пишет «Longer than 1000 symbols» при
пороге 100.

**34. `channels.storage_channel_id` может указывать на удалённый канал.**
У колонки нет FK — хранилище не постинговый канал и своей строки в `channels`
не имеет, ссылаться не на что. Поэтому удаление канала-хранилища (или потеря
ботом прав в нём) ничем не отслеживается: id остаётся в строке, а обнаружится
это только на `_publish_material` ошибкой `chat not found`, уже после того как
админ собрал пост. Два пути:
- проверять доступность хранилища в момент создания поста с материалом
  (`get_chat` перед началом сбора) — дороже на один вызов, зато отказ приходит
  сразу;
- ловить ошибку при заливке и просить перепривязать хранилище.
Появилось вместе с мастером привязки; до него `storage_channel_id` никем не
заполнялся.

## Оговорка, которую стоит помнить

Дедупликация `UnsupportedPostTypeError` перевела его из `PublisherError` в
`PostError`, то есть сузила старый `except PublisherError`. Широкий
`except Exception` в `PublishPostUseCase` это перекрывает — но если кто-то будет
сужать его обратно, надо помнить про этот класс.

## Посты с материалами

Слой данных готов, этапы 2–5 не начаты, план не согласован. Что именно осталось и
какие вопросы блокируют этап 2 — в [post-type-material.md](post-type-material.md).

## Дальше по плану

1. Тесты на чистые функции: `parse_when`, `in_hours`, `next_day_at`,
   `resolve_preset`, `build_custom_payload`, `tg_length`. Кейсы пишу я сам —
   нужно ТЗ от Claude, потом проверка. Перед этим закрыть пункт 23, чтобы новые
   тесты не приезжали в красный прогон.
2. Тест целостности DI-контейнера и тест скоупов в CI.
3. Видео и документы в собственных постах, включая смешанные альбомы.
4. Канал-хранилище для картинок на случай смены токена (`file_id` привязан к токену).
5. `RoleCache` на Redis.
6. mypy в pre-commit, README.
