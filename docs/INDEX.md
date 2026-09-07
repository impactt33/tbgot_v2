# Индекс: куда идти

Точка входа в проект. **Сначала сюда, потом сразу в нужный файл — без `grep` по
всему дереву.** Ссылки ведут и в документацию, и в код.

Пути в коде кликабельны и относительны корню репозитория.

> **KB актуален на:** `f626dc2` · 2026-09-07, **плюс незакоммиченный этап A**
> (мастер канала с привязкой хранилища) в рабочем дереве.
> Закоммитишь — подставь новый sha сюда.
> По этой строке `/kb` понимает, врёт ли документация, а `/kb_update` — какие
> документы править. **Обновлять при каждой правке базы знаний.**

---

## 1. Задача → документ → главные файлы

| Задача | Документ | Главные файлы кода |
|---|---|---|
| Понять слои, DI, старт | [architecture.md](architecture.md) | [`app/run.py`](../app/run.py), [`app/container.py`](../app/container.py), [`app/di/`](../app/di/) |
| Схема БД, миграция | [data-model.md](data-model.md) | [`main/data/models/`](../main/data/models/), [`core/database/base.py`](../core/database/base.py), [`migration/versions/`](../migration/versions/) |
| Статусы поста, публикация, планировщик | [posts.md](posts.md) | [`publish_post.py`](../main/domain/use_cases/publish_post.py), [`post_repo_impl.py`](../main/data/repositories_impl/post_repo_impl.py), [`app/scheduler.py`](../app/scheduler.py), [`telegram_publisher.py`](../main/data/clients_impl/telegram/telegram_publisher.py) |
| Квиз | [post-type-quiz.md](post-type-quiz.md) | [`generate_quiz.py`](../main/domain/use_cases/generate_quiz.py), [`quiz_topic_model.py`](../main/data/models/quiz_topic_model.py) |
| Пост о ресурсе | [post-type-sources.md](post-type-sources.md) | [`generate_source.py`](../main/domain/use_cases/generate_source.py), [`source_model.py`](../main/data/models/source_model.py), [`serper_web_search_client.py`](../main/data/clients_impl/web_search/serper_web_search_client.py) |
| Ручной пост, альбомы | [post-type-custom.md](post-type-custom.md) | [`post_input.py`](../main/presentation/utils/post_input.py), [`media_group.py`](../main/presentation/utils/media_group.py), [`create_custom_post.py`](../main/domain/use_cases/create_custom_post.py) |
| Посты с материалами | [post-type-material.md](post-type-material.md) | [`material_model.py`](../main/data/models/material_model.py), [`material_entity.py`](../main/domain/entities/material_entity.py), [`material_repo_impl.py`](../main/data/repositories_impl/material_repo_impl.py) |
| Отложенная публикация, ввод времени | [scheduling.md](scheduling.md) | [`time_input.py`](../main/presentation/utils/time_input.py), [`schedule_presets.py`](../main/presentation/utils/schedule_presets.py), [`callbacks/schedule.py`](../main/presentation/callbacks/schedule.py) |
| Кнопки, экраны, FSM | [bot-ui.md](bot-ui.md) | [`post_handlers.py`](../main/presentation/handlers/post_handlers.py), [`keyboards/`](../main/presentation/keyboards/), [`callbacks/`](../main/presentation/callbacks/), [`states/`](../main/presentation/states/) |
| Роли, права, каналы | [users-and-channels.md](users-and-channels.md) | [`middlewares/role.py`](../main/presentation/middlewares/role.py), [`admin_panel_handlers.py`](../main/presentation/handlers/admin_panel_handlers.py), [`user_service_impl.py`](../main/domain/services_impl/user_service_impl.py), [`keyboards/channel_setup.py`](../main/presentation/keyboards/channel_setup.py) |
| Обработка ошибок | [errors.md](errors.md) | [`core/errors/app_error.py`](../core/errors/app_error.py), [`main/domain/errors/`](../main/domain/errors/), [`error_handlers.py`](../main/presentation/handlers/error_handlers.py) |
| Gemini, веб-поиск | [ai-and-search.md](ai-and-search.md) | [`gemini_ai_client.py`](../main/data/clients_impl/ai/gemini_ai_client.py), [`ai_guard.py`](../main/domain/use_cases/ai_guard.py) |
| Настройки, логи, запуск | [runtime.md](runtime.md) | [`core/config/settings.py`](../core/config/settings.py), [`core/config/logger.py`](../core/config/logger.py), [`app/run.py`](../app/run.py) |
| Проверить правку | [testing.md](testing.md) | [`tests/`](../tests/), [`pyproject.toml`](../pyproject.toml) |
| Что сломано, что делать дальше | [STATE.md](STATE.md) | — |

---

## 2. Карта кода по слоям

### `app/` — composition root

| Файл | Что внутри | Документ |
|---|---|---|
| [`run.py`](../app/run.py) | сборка Dispatcher, порядок роутеров, middleware, шатдаун | [architecture](architecture.md#порядок-сборки-в-runpy), [runtime](runtime.md#runpy) |
| [`container.py`](../app/container.py) | сборка контейнера dishka | [architecture](architecture.md#di-dishka) |
| [`scheduler.py`](../app/scheduler.py) | цикл отложенных публикаций | [posts](posts.md#планировщик) |
| [`di/config.py`](../app/di/config.py) | `Settings` | [runtime](runtime.md#settings) |
| [`di/database.py`](../app/di/database.py) | engine, sessionmaker, `AsyncSession` (REQUEST) | [architecture](architecture.md#скоупы) |
| [`di/clients.py`](../app/di/clients.py) | `Publisher`, `AIClient`, `WebSearchClient`, `httpx`, `MediaGroupCollector` | [architecture](architecture.md#скоупы) |
| [`di/repositories.py`](../app/di/repositories.py) | все репозитории (REQUEST) | [architecture](architecture.md) |
| [`di/services.py`](../app/di/services.py) | все сервисы (REQUEST) | [architecture](architecture.md) |
| [`di/use_cases.py`](../app/di/use_cases.py) | все use cases (REQUEST) | [architecture](architecture.md) |
| [`di/cache.py`](../app/di/cache.py) | `RoleCache` (APP) | [users-and-channels](users-and-channels.md#кэш-ролей) |

### `core/` — ядро

| Файл | Что внутри | Документ |
|---|---|---|
| [`config/settings.py`](../core/config/settings.py) | все переменные окружения, `user_tz`, URL-свойства | [runtime](runtime.md#settings) |
| [`config/logger.py`](../core/config/logger.py) | `setup_logging`, три хендлера, ротация | [runtime](runtime.md#логирование) |
| [`database/base.py`](../core/database/base.py) | `Base`, `naming_convention` | [data-model](data-model.md#конвенции) |
| [`errors/app_error.py`](../core/errors/app_error.py) | `AppError` с `detail` и `user_message` | [errors](errors.md) |

### `main/domain/` — домен

**Сущности** ([`entities/`](../main/domain/entities/))

| Файл | Классы |
|---|---|
| [`payloads.py`](../main/domain/entities/payloads.py) | `QuizPayload`, `SourcePayload`, `CustomPayload`, `MaterialPayload` |
| [`post_entity.py`](../main/domain/entities/post_entity.py) | `PostEntity`, `PostCreateEntity` |
| [`channel_entity.py`](../main/domain/entities/channel_entity.py) | `ChannelEntity`, `ChannelAddEntity` |
| [`user_entity.py`](../main/domain/entities/user_entity.py) | `UserEntity`, `NewUserEntity`, `UserCreateEntity` |
| [`quiz_topic_entity.py`](../main/domain/entities/quiz_topic_entity.py) | `QuizTopicEntity`, `QuizTopicAddEntity` |
| [`source_entity.py`](../main/domain/entities/source_entity.py) | `SourceEntity`, `AddSourceEntity` |
| [`material_entity.py`](../main/domain/entities/material_entity.py) | `MaterialEntity`, `AddMaterialEntity` |

**Енумы** ([`enums/`](../main/domain/enums/))

[`post_status.py`](../main/domain/enums/post_status.py) `PostStatus` ·
[`post_type.py`](../main/domain/enums/post_type.py) `PostType` ·
[`user_role.py`](../main/domain/enums/user_role.py) `UserRole` ·
[`channel_action.py`](../main/domain/enums/channel_action.py) `ChannelAction` ·
[`failures/ai_answer_failures.py`](../main/domain/enums/failures/ai_answer_failures.py) `AIFailure`

**Use cases** ([`use_cases/`](../main/domain/use_cases/))

| Файл | Класс | Документ |
|---|---|---|
| [`publish_post.py`](../main/domain/use_cases/publish_post.py) | `PublishPostUseCase`, `PreviewPostUseCase` | [posts](posts.md) |
| [`discard_draft.py`](../main/domain/use_cases/discard_draft.py) | `DiscardDraftUseCase` | [posts](posts.md#discard_draft-против-delete_draft) |
| [`generate_quiz.py`](../main/domain/use_cases/generate_quiz.py) | `GenerateQuizUseCase` | [post-type-quiz](post-type-quiz.md) |
| [`generate_source.py`](../main/domain/use_cases/generate_source.py) | `GenerateSourcePostUseCase` | [post-type-sources](post-type-sources.md) |
| [`create_custom_post.py`](../main/domain/use_cases/create_custom_post.py) | `CreateCustomPostUseCase` | [post-type-custom](post-type-custom.md) |
| [`change_user_role.py`](../main/domain/use_cases/change_user_role.py) | `ChangeUserRoleUseCase` | [users-and-channels](users-and-channels.md) |
| [`ai_guard.py`](../main/domain/use_cases/ai_guard.py) | `unwrap_ai` | [ai-and-search](ai-and-search.md) |
| [`generate_material.py`](../main/domain/use_cases/generate_material.py) | **пустой файл** | [STATE](STATE.md) п. 28 |

**Интерфейсы и реализации** — попарно, ABC в `domain`, impl рядом:

| Сущность | ABC репозитория | Impl репозитория | ABC сервиса | Impl сервиса |
|---|---|---|---|---|
| Пост | [`post_repo.py`](../main/domain/repositories/post_repo.py) | [`post_repo_impl.py`](../main/data/repositories_impl/post_repo_impl.py) | [`post_service.py`](../main/domain/services/post_service.py) | [`post_service_impl.py`](../main/domain/services_impl/post_service_impl.py) |
| Канал | [`channel_repo.py`](../main/domain/repositories/channel_repo.py) | [`channel_repo_impl.py`](../main/data/repositories_impl/channel_repo_impl.py) | [`channel_service.py`](../main/domain/services/channel_service.py) | [`channel_service_impl.py`](../main/domain/services_impl/channel_service_impl.py) |
| Пользователь | [`user_repo.py`](../main/domain/repositories/user_repo.py) | [`user_repo_impl.py`](../main/data/repositories_impl/user_repo_impl.py) | [`user_service.py`](../main/domain/services/user_service.py) | [`user_service_impl.py`](../main/domain/services_impl/user_service_impl.py) |
| Тема квиза | [`quiz_topic_repo.py`](../main/domain/repositories/quiz_topic_repo.py) | [`quiz_topic_repo_impl.py`](../main/data/repositories_impl/quiz_topic_repo_impl.py) | [`quiz_topic_service.py`](../main/domain/services/quiz_topic_service.py) | [`quiz_topic_service_impl.py`](../main/domain/services_impl/quiz_topic_service_impl.py) |
| Ресурс | [`source_repo.py`](../main/domain/repositories/source_repo.py) | [`source_repo_impl.py`](../main/data/repositories_impl/source_repo_impl.py) | [`source_service.py`](../main/domain/services/source_service.py) | [`source_service_impl.py`](../main/domain/services_impl/source_service_impl.py) |
| Материал | [`material_repo.py`](../main/domain/repositories/material_repo.py) | [`material_repo_impl.py`](../main/data/repositories_impl/material_repo_impl.py) | [`material_service.py`](../main/domain/services/material_service.py) | [`material_service_impl.py`](../main/domain/services_impl/material_service_impl.py) |

**Клиенты** — ABC в `domain/clients/`, реализация в `data/clients_impl/`:

| Интерфейс | Реализация | Документ |
|---|---|---|
| [`clients/telegram/publisher.py`](../main/domain/clients/telegram/publisher.py) `Publisher` | [`telegram_publisher.py`](../main/data/clients_impl/telegram/telegram_publisher.py) | [posts](posts.md#публикация-в-telegram) |
| [`clients/ai/ai_client.py`](../main/domain/clients/ai/ai_client.py) `AIClient` | [`gemini_ai_client.py`](../main/data/clients_impl/ai/gemini_ai_client.py) | [ai-and-search](ai-and-search.md) |
| [`clients/web_search/web_search_client.py`](../main/domain/clients/web_search/web_search_client.py) `WebSearchClient` | [`serper_web_search_client.py`](../main/data/clients_impl/web_search/serper_web_search_client.py) | [ai-and-search](ai-and-search.md#serper) |
| [`cache/role_cache.py`](../main/domain/cache/role_cache.py) `RoleCache` | [`role_cache_impl.py`](../main/data/cache_impl/role_cache_impl.py) — **заглушка** | [users-and-channels](users-and-channels.md#кэш-ролей) |

**Ошибки** ([`errors/`](../main/domain/errors/)) — по файлу на группу, см. [errors.md](errors.md#иерархия):

[`post_errors.py`](../main/domain/errors/post_errors.py) ·
[`channel_errors.py`](../main/domain/errors/channel_errors.py) ·
[`user_errors.py`](../main/domain/errors/user_errors.py) ·
[`quiz_topics_errors.py`](../main/domain/errors/quiz_topics_errors.py) ·
[`source_errors.py`](../main/domain/errors/source_errors.py) ·
[`material_errors.py`](../main/domain/errors/material_errors.py) ·
[`ai_client_errors.py`](../main/domain/errors/ai_client_errors.py) ·
[`publisher_errors.py`](../main/domain/errors/publisher_errors.py) ·
[`web_search_errors.py`](../main/domain/errors/web_search_errors.py)

### `main/data/` — данные

**ORM-модели** ([`models/`](../main/data/models/))

| Файл | Таблица | Документ |
|---|---|---|
| [`post_model.py`](../main/data/models/post_model.py) | `posts` | [data-model](data-model.md#posts) |
| [`channel_model.py`](../main/data/models/channel_model.py) | `channels` | [data-model](data-model.md#channels) |
| [`user_model.py`](../main/data/models/user_model.py) | `users` | [data-model](data-model.md#users) |
| [`quiz_topic_model.py`](../main/data/models/quiz_topic_model.py) | `quiz_topics` | [data-model](data-model.md) |
| [`source_model.py`](../main/data/models/source_model.py) | `sources` | [data-model](data-model.md) |
| [`material_model.py`](../main/data/models/material_model.py) | `materials` | [post-type-material](post-type-material.md#таблица-materials-по-полям) |

### `main/presentation/` — презентация

**Хендлеры** ([`handlers/`](../main/presentation/handlers/)) — порядок включения в `run.py` значим:

| Файл | Роутер | Что обслуживает |
|---|---|---|
| [`error_handlers.py`](../main/presentation/handlers/error_handlers.py) | `error_router` | пять обработчиков ошибок, [errors](errors.md#обработчик-error_router) |
| [`command_handlers.py`](../main/presentation/handlers/command_handlers.py) | `command_router` | `/start`, `/menu`, `/admin`, `/self_info`, `/quit` |
| [`menu_handlers.py`](../main/presentation/handlers/menu_handlers.py) | `menu_router` | возврат в корневое меню |
| [`post_handlers.py`](../main/presentation/handlers/post_handlers.py) | `post_router` | генерация, черновик, расписание, ручной пост, отложенные |
| [`admin_panel_handlers.py`](../main/presentation/handlers/admin_panel_handlers.py) | `admin_router` | права, добавление и удаление канала |

**Клавиатуры** ([`keyboards/`](../main/presentation/keyboards/))

[`main_menu.py`](../main/presentation/keyboards/main_menu.py) корневое и админское меню ·
[`post.py`](../main/presentation/keyboards/post.py) каналы, типы, действия черновика, пресеты, `SUPPORTED_POST_TYPES` ·
[`scheduled.py`](../main/presentation/keyboards/scheduled.py) список отложенных ·
[`add_channel.py`](../main/presentation/keyboards/add_channel.py) `request_chat`, два пикера и их `request_id` ·
[`channel_setup.py`](../main/presentation/keyboards/channel_setup.py) список каналов и экран хранилища ·
[`roles.py`](../main/presentation/keyboards/roles.py) выбор роли

**CallbackData** ([`callbacks/`](../main/presentation/callbacks/)) — таблица префиксов в [bot-ui.md](bot-ui.md#callbackdata)

[`menu.py`](../main/presentation/callbacks/menu.py) `MenuCB` ·
[`post.py`](../main/presentation/callbacks/post.py) `ChannelCB`, `GenerateCB`, `DraftCB` ·
[`schedule.py`](../main/presentation/callbacks/schedule.py) `ScheduleCB` ·
[`scheduled.py`](../main/presentation/callbacks/scheduled.py) `ScheduledCB` ·
[`custom_post.py`](../main/presentation/callbacks/custom_post.py) `CustomChannelCB` ·
[`channel_setup.py`](../main/presentation/callbacks/channel_setup.py) `SetupChannelCB`, `StorageCB`, `StorageAction`

**Утилиты** ([`utils/`](../main/presentation/utils/))

| Файл | Что | Документ |
|---|---|---|
| [`time_input.py`](../main/presentation/utils/time_input.py) | `parse_when`, `in_hours`, `next_day_at`, `format_local` | [scheduling](scheduling.md#parse_when) |
| [`schedule_presets.py`](../main/presentation/utils/schedule_presets.py) | `resolve_preset`, `PRESET_TITLES` | [scheduling](scheduling.md) |
| [`post_input.py`](../main/presentation/utils/post_input.py) | `build_custom_payload`, `tg_length` | [post-type-custom](post-type-custom.md#разбор-ввода-build_custom_payload) |
| [`media_group.py`](../main/presentation/utils/media_group.py) | `MediaGroupCollector` | [post-type-custom](post-type-custom.md#альбомы-mediagroupcollector) |
| [`callback_view.py`](../main/presentation/utils/callback_view.py) | `render` | [bot-ui](bot-ui.md#render) |

**Прочее**

[`middlewares/role.py`](../main/presentation/middlewares/role.py) `RoleMiddleware` ·
[`filters/roles.py`](../main/presentation/filters/roles.py) `HasAccessFilter`, `IsAdminFilter` ·
[`states/`](../main/presentation/states/) все `StatesGroup` и `BOT_STATES` ·
[`errors.py`](../main/presentation/errors.py) ошибки ввода

---

## 3. Где объявлено — быстрый поиск

| Ищу | Файл |
|---|---|
| `PostStatus`, `PostType` | [`main/domain/enums/`](../main/domain/enums/) |
| форма `payload` любого типа поста | [`entities/payloads.py`](../main/domain/entities/payloads.py) |
| `claim_for_publishing`, `claim_scheduled`, `mark_failed` | [`post_repo_impl.py`](../main/data/repositories_impl/post_repo_impl.py) |
| как пост превращается в сообщение канала | [`telegram_publisher.py`](../main/data/clients_impl/telegram/telegram_publisher.py) |
| какие типы постов предлагаются в меню | `SUPPORTED_POST_TYPES` в [`keyboards/post.py`](../main/presentation/keyboards/post.py) |
| все тексты для пользователя | константы вверху [`post_handlers.py`](../main/presentation/handlers/post_handlers.py) |
| промпты к Gemini | константы `_SYSTEM`, `_*_PROMPT` в [`generate_quiz.py`](../main/domain/use_cases/generate_quiz.py), [`generate_source.py`](../main/domain/use_cases/generate_source.py) |
| лимиты Telegram (1024 / 4096 / 10) | [`post_input.py`](../main/presentation/utils/post_input.py) |
| список групп состояний | `BOT_STATES` в [`states/__init__.py`](../main/presentation/states/__init__.py) |
| `request_id` пикеров каналов | `POSTING_REQUEST_ID`, `STORAGE_REQUEST_ID` в [`keyboards/add_channel.py`](../main/presentation/keyboards/add_channel.py) |
| `naming_convention` | [`core/database/base.py`](../core/database/base.py) |
| порядок роутеров | [`app/run.py`](../app/run.py) |
| head миграций | [`bdf76a3344c2`](../migration/versions/bdf76a3344c2_materials_table_and_storage_channel.py) |
| настройки mypy, pytest | [`pyproject.toml`](../pyproject.toml) |

---

## 4. Точки входа

| Что | Файл |
|---|---|
| Запуск бота | [`app/run.py`](../app/run.py) → `main()` |
| Планировщик | [`app/scheduler.py`](../app/scheduler.py) → `run_scheduler()` |
| Alembic | [`migration/env.py`](../migration/env.py), [`alembic.ini`](../alembic.ini) |
| Тесты | [`tests/`](../tests/), фикстуры в [`conftest.py`](../tests/conftest.py) |
| Инфраструктура | [`docker-compose.yml`](../docker-compose.yml) |
