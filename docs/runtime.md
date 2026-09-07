# Настройки, логи, запуск

> **Главные файлы:**
> [`core/config/settings.py`](../core/config/settings.py) ·
> [`core/config/logger.py`](../core/config/logger.py) ·
> [`app/run.py`](../app/run.py) ·
> [`docker-compose.yml`](../docker-compose.yml) ·
> [`pyproject.toml`](../pyproject.toml) ·
> [`app/di/database.py`](../app/di/database.py)

## Settings

`pydantic-settings`, читает `app/.env` (в `.gitignore`). **Экземпляр создаётся на
уровне модуля:**

```python
settings = Settings()
```

Отсюда практическое следствие: **без `app/.env` не импортируется `core.config`**,
а значит падает почти всё, включая тестовую обвязку и `mypy` в отдельном
worktree. Скопировать `.env` — первое, что делаешь в свежей копии.

### Обязательные переменные

```
BOT_TOKEN
GEMINI_API_KEY
SERPER_API_KEY
DB_HOST  DB_PORT  DB_USER  DB_PASSWORD  DB_NAME
REDIS_HOST  REDIS_PORT  REDIS_DB
```

### С дефолтами

| Переменная | Дефолт | Заметка |
|---|---|---|
| `DATABASE_ECHO` | `True` | **в проде надо `False`** — иначе SQL-лог с payload постов |
| `DB_MIN_POOL_SIZE` | 1 | не используется |
| `DB_MAX_POOL_SIZE` | 10 | `pool_size` движка |
| `USER_TIMEZONE` | `Europe/Moscow` | валидируется через `ZoneInfo` |
| `APP_HOST` / `APP_PORT` / `DEBUG` | `0.0.0.0` / 8080 / False | не используются |

Неиспользуемые поля — пункт 21 в [STATE.md](STATE.md), там же `DATABASE_ECHO`
(пункт 18).

### Свойства-URL

```python
DATABASE_URL             # postgresql://…      (нигде не используется)
SQLALCHEMY_DATABASE_URL  # postgresql+asyncpg://…  ← движок берёт это
REDIS_URL                # redis://host:port/db
user_tz                  # ZoneInfo
```

## Логирование

`setup_logging` через `dictConfig`, три обработчика:

| Handler | Уровень | Куда |
|---|---|---|
| `console` | из аргумента | stdout, короткий формат |
| `app_file` | DEBUG | `logs/app.log`, ротация в полночь UTC, 14 дней |
| `error_file` | ERROR | `logs/errors.log`, ротация в полночь UTC, 30 дней |

Файловый формат включает `funcName:lineno` — по логу видно место.

Приглушены: `aiogram` до INFO, `sqlalchemy.engine`, `aiohttp`, `asyncio` до
WARNING.

**Два подвоха.** Вызов захардкожен: `setup_logging(log_level="DEBUG")` в `run.py`,
`settings.DEBUG` не участвует. И `logs/` создаётся **относительно cwd** — запуск
из другого каталога рассыплет логи по файловой системе.

## `run.py`

```python
storage = RedisStorage.from_url(settings.REDIS_URL, state_ttl=FSM_TTL, data_ttl=FSM_TTL)
bot = Bot(token=..., default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=storage)

dp.include_router(error_router)     # порядок значим
dp.include_router(command_router)
dp.include_router(menu_router)
dp.include_router(post_router)
dp.include_router(admin_router)

container = create_container(bot)
setup_dishka(container=container, router=dp, auto_inject=True)

role_middleware = RoleMiddleware()          # после setup_dishka
dp.message.outer_middleware(role_middleware)
dp.callback_query.outer_middleware(role_middleware)

scheduler_task = asyncio.create_task(run_scheduler(container))

try:
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
finally:
    scheduler_task.cancel()
    ...
    await container.close()
    await storage.close()
    await bot.session.close()
```

`FSM_TTL` — сутки. `parse_mode=HTML` по умолчанию: `CustomPayload.html_text`
хранится готовым HTML.

`drop_pending_updates=True` — накопленные за простой апдейты выбрасываются, а не
разгребаются пачкой.

**Известный дефект шатдауна:** `start_polling` не дожидается задач апдейтов, а
`finally` сразу закрывает контейнер и Redis — ресурсы рвутся под работающими
хендлерами. Пункт 19 в [STATE.md](STATE.md). Там же пункт 20: у движка нет
`pool_pre_ping`, поэтому после простоя первый апдейт падает на мёртвом коннекте.

## Окружение

- **Нужен Python 3.14.0 финальный, не rc.** `uv python install 3.14` ставит rc2, на
  котором pydantic 2.13 падает при импорте любой модели:
  `TypeError: _eval_type() got an unexpected keyword argument 'prefer_fwd_module'`.
- **Docker-демона может не быть.** Тогда Postgres поднимается напрямую (`initdb`
  под пользователем `postgres`, порт 5430), Redis — `redis-server --port 6379`.
- Зависимости и настройки инструментов — в `pyproject.toml`. mypy: `python_version
  3.14`, плагин pydantic, `disallow_untyped_defs`, `warn_return_any`,
  `warn_unused_ignores`; `migration.versions.*` исключены.
- **`[tool.ruff]` в `pyproject.toml` нет**, CI нет. Пункт 25 в [STATE.md](STATE.md).

## `docker-compose.yml`

Только Postgres и Redis, **сервиса самого бота нет** — он запускается локально.
Известные проблемы: healthcheck'и никто не потребляет, том `pgdata` объявлен, но
монтируется bind-mount, `max_connections=1000` при `memory: 512M`. Пункт 22.

## Профилактика мусорных импортов

PyCharm любит автоимпорты. Домен не должен видеть `app/`:

```bash
grep -rnE "^from (app|pyasn1|aiohttp)\." main/ core/   # должно молчать
```
