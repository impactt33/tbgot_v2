# Как проверять

> **Главные файлы:** [`tests/conftest.py`](../tests/conftest.py) ·
> [`tests/test_generate_quiz.py`](../tests/test_generate_quiz.py) ·
> [`tests/test_generate_source.py`](../tests/test_generate_source.py) ·
> [`tests/test_live_clients.py`](../tests/test_live_clients.py) ·
> [`pyproject.toml`](../pyproject.toml) · [`alembic.ini`](../alembic.ini)

**Главное правило проекта: проверяй утверждения запускаемым кодом, а не по
памяти.** Особенно для SQLAlchemy, aiogram, alembic, dishka, pydantic — их API
меняются.

Для проверок заводи отдельную базу, рабочую не трогай.

## Текущее состояние

```
pytest                    4 failed, 8 passed, 3 deselected
mypy main/ core/ app/     64 ошибки
```

Обе цифры — база для сравнения, а не цель. Прежде чем считать новую ошибку своей,
сними базу на чистом HEAD.

## pytest

```
tests/conftest.py           фейковые клиенты и сервисы
tests/test_generate_quiz.py 8 passed
tests/test_generate_source.py 4 failed  ← дефект 23
tests/test_live_clients.py  3 deselected (маркер live)
```

`asyncio_mode = "auto"`, `addopts = "-m 'not live'"` — живые вызовы Gemini и
Serper по умолчанию исключены, для них нужны ключи и сеть:

```bash
.venv/bin/pytest -m live
```

**4 падения — известные:** `tests/conftest.py` не содержит `FakeSourceService`, а
`GenerateSourcePostUseCase.__init__` его требует; плюс `test_empty_search_results`
нужны три ответа `SearchQueryDraft`. Пункт 23 в [STATE.md](STATE.md) — чинить
перед тем, как писать новые тесты, иначе они приедут в красный прогон.

## Старт диспетчера без сети

Самая дешёвая проверка «ничего не сломалось»: собрать роутеры и контейнер как в
`run.py`, но с `MemoryStorage` и фейковым токеном, и вызвать

```python
await dp.emit_startup(bot=bot)
```

Проходит — значит все аннотации хендлеров резолвятся (PEP 649 проверяет их
именно тут) и все `FromDishka`-ключи есть в контейнере. Ни Postgres, ни Redis не
нужны.

**Без `emit_startup` проверка бессмысленна:** dishka вешает `inject_router`
именно на startup, и без него хендлеры с `FromDishka` падают на
`TypeError: missing required positional arguments`.

## mypy как источник истины

Не подсветка PyCharm.

```bash
.venv/bin/mypy main/ core/ app/
```

Почти все 64 — `no-untyped-def` на хендлерах и `union-attr` на
`Message | InaccessibleMessage | None`.

Базу снимай через отдельный worktree:

```bash
git worktree add /tmp/base HEAD
cp app/.env /tmp/base/app/.env     # без него не импортируется core.config
cd /tmp/base && mypy main/ core/ app/ | tail -1
```

Отдельная известная особенность: `await container.get(X)` типизирован как `Any`,
поэтому присваивание аннотируй явно.

## Живая БД для гонок и транзакций

Отдельный контейнер, рабочая база не трогается:

```bash
docker run --rm -d --name tbgot_scratch_pg \
  -e POSTGRES_USER=test -e POSTGRES_PASSWORD=test -e POSTGRES_DB=test \
  -p 5433:5432 postgres:16
```

Схему поднимай через `Base.metadata.create_all` — мимо миграций, у них свои
дефекты 15–17.

Так проверялись захват поста двумя тапами, отравленная сессия в планировщике и
round-trip репозитория материалов.

## Миграции

```bash
alembic upgrade head
alembic check                      # «No new upgrade operations detected»
```

Круговой прогон обязателен для новой ревизии:

```
head → downgrade -1 → upgrade head
pg_dump --schema-only до и после должны совпасть побайтово
```

Помни: **`include_object` в `migration/env.py` прячет дрейф CHECK** — `alembic
check` не заметит удалённых констрейнтов.

## Размер `callback_data`

Считать **в байтах** на предельных значениях, а не на глаз:

```python
len(DraftCB(action=DraftAction.REGENERATE, post_id=2147483647,
            preview_id=999999, preview_count=10).pack().encode())   # 36 из 64
```

Кириллица — два байта на символ.

## Чек-лист перед «готово»

1. `mypy main/ core/ app/` — не выросло против базы.
2. `pytest` — не выросло против 4 failed.
3. `emit_startup` проходит.
4. Тронул схему — круговой прогон миграций.
5. Тронул `callback_data` — пересчитал байты, при новом поле сменил префикс.
6. `grep -rnE "^from (app|pyasn1|aiohttp)\." main/ core/` молчит.
