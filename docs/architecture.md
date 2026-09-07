# Архитектура: слои, DI, старт

> **Главные файлы:** [`app/run.py`](../app/run.py) · [`app/container.py`](../app/container.py) ·
> [`app/di/`](../app/di/) · [`core/database/base.py`](../core/database/base.py)
> **Полная карта кода:** [INDEX.md](INDEX.md)

## Слои

| Слой | Пакет | Что внутри | Чего нельзя |
|---|---|---|---|
| Домен | `main/domain/` | сущности, енумы, ABC репозиториев/сервисов/клиентов, доменные ошибки, use cases | импортировать инфраструктуру: ни aiogram, ни SQLAlchemy, ни httpx |
| Данные | `main/data/` | ORM-модели, реализации репозиториев, кэш, исходящие адаптеры | принимать апдейты |
| Презентация | `main/presentation/` | хендлеры, фильтры, клавиатуры, состояния, CallbackData, middleware, разбор ввода | ходить в БД напрямую |
| Composition root | `app/` | провайдеры dishka, контейнер, `run.py`, `scheduler.py` | содержать логику |
| Ядро | `core/` | settings, логирование, `Base`, `AppError` | зависеть от `main/` |

Правило одной фразой: **presentation — входящие апдейты, data — исходящие вызовы.**
`TelegramPublisher` живёт в `data`, а не в `presentation`, именно поэтому: он не
принимает апдейт, он отправляет сообщение.

## Направление зависимостей

Домен объявляет интерфейс, data его реализует, `app/di` их связывает. Ни один
модуль домена не знает имени реализации.

```
main/domain/clients/telegram/publisher.py   Publisher (ABC)
main/data/clients_impl/telegram/…           TelegramPublisher(Publisher)
app/di/clients.py                           provide → Publisher
```

Так же устроены `AIClient`/`GeminiAIClient`, `WebSearchClient`/`SerperWebSearchClient`,
`RoleCache`/`RoleCacheImpl` и все репозитории.

## Три уровня абстракции над данными

Это самая частая путаница, поэтому явно:

**Репозиторий** (`main/data/repositories_impl/`) — один SQL-оператор, никакой
интерпретации. Нет строки — вернул `None`. Не кидает доменных ошибок.

**Сервис** (`main/domain/services_impl/`) — превращает `None` в доменную ошибку и
решает, что «нет строки» означает в этом конкретном месте:

```python
async def get_by_id(self, post_id: int) -> PostEntity:
    post = await self.post_repo.find_by_id(post_id)
    if post is None:
        raise PostNotFoundError(post_id)
    return post
```

**Use case** (`main/domain/use_cases/`) — сценарий из нескольких сервисов и
клиентов, с порядком операций и откатами. Логика вида «сначала удалить пост,
потом тему» живёт здесь, а не в сервисе.

Отсюда конвенция имён: **`find_*` возвращает `None`, `get_*` кидает.**
Исключения перечисляются в докстроке абстрактного метода.

## ORM-объекты не покидают репозиторий

Каждая модель имеет `to_entity()`, и наружу уходит только pydantic-сущность.
Причина практическая: сессия закрывается при выходе из REQUEST-скоупа, а
`lazy="raise"` на связях превращает любое обращение к недогруженной связи в
явную ошибку вместо тихого лишнего SELECT.

## DI: dishka

Контейнер собирается в `app/container.py` из семи провайдеров. Единственное, что
приходит извне, — `Bot`, через `context={Bot: bot}`.

### Скоупы

| Scope.APP (живёт всё время) | Scope.REQUEST (на один апдейт) |
|---|---|
| `Settings` | `AsyncSession` |
| `AsyncEngine`, `async_sessionmaker` | все репозитории |
| `Publisher`, `AIClient`, `WebSearchClient` | все сервисы |
| `httpx.AsyncClient` | все use cases |
| `RoleCache` | |
| `MediaGroupCollector` | |

**`MediaGroupCollector` обязан быть APP.** Части альбома приходят разными
апдейтами; на REQUEST каждая попадёт в свой пустой буфер, и фича молча
выродится в «пост на каждое фото» — без ошибки, без лога.

**REQUEST-скоуп = одна сессия БД.** Отсюда важное следствие для планировщика,
см. [posts.md](posts.md#планировщик).

### `container.get()` типизирован как `Any`

mypy теряет тип дальше по цепочке, поэтому присваивание аннотируется явно:

```python
post_service: PostService = await request_container.get(PostService)
```

## Порядок сборки в `run.py`

```python
dp.include_router(error_router)    # 1
dp.include_router(command_router)  # 2
dp.include_router(menu_router)     # 3
dp.include_router(post_router)     # 4
dp.include_router(admin_router)    # 5

setup_dishka(container=container, router=dp, auto_inject=True)

role_middleware = RoleMiddleware()
dp.message.outer_middleware(role_middleware)
dp.callback_query.outer_middleware(role_middleware)
```

Три решения, которые из кода не выводятся:

1. **`command_router` идёт раньше `post_router`.** Роутеры пробуются по порядку
   регистрации, поэтому `/quit` живёт в `command_router` — иначе его перехватил
   бы хендлер состояния из `post_router`.

2. **`RoleMiddleware` вешается после `setup_dishka` и на конкретные обсерверы**
   (`dp.message`, `dp.callback_query`), а не на `dp.update`. На `dp.update` он
   попал бы в другой REQUEST-контейнер, чем хендлер, и `data["role"]` считался бы
   на одной сессии, а хендлер работал бы на другой.

3. **Планировщик стартует до polling** отдельной задачей и снимается в `finally`.

## Старт и проверка без сети

`setup_dishka` вешает `inject_router` на **startup диспетчера**. В тестовой
обвязке без `await dp.emit_startup(bot=bot)` все хендлеры с `FromDishka` падают на
`TypeError: missing required positional arguments` — см. [testing.md](testing.md).

## PEP 649

Python 3.14 вычисляет аннотации лениво. Ошибка в аннотации хендлера вылезет не
при импорте модуля, а при старте диспетчера. В ORM-моделях по этой же причине
обязателен `from __future__ import annotations`.
