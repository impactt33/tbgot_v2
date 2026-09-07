# Тип поста: SOURCES

> **Главные файлы:**
> [`use_cases/generate_source.py`](../main/domain/use_cases/generate_source.py) ·
> [`models/source_model.py`](../main/data/models/source_model.py) ·
> [`repositories_impl/source_repo_impl.py`](../main/data/repositories_impl/source_repo_impl.py) ·
> [`clients_impl/web_search/serper_web_search_client.py`](../main/data/clients_impl/web_search/serper_web_search_client.py)
> **Рядом:** `SourcePayload` в [`entities/payloads.py`](../main/domain/entities/payloads.py) ·
> `_publish_source` в [`telegram_publisher.py`](../main/data/clients_impl/telegram/telegram_publisher.py) ·
> [`errors/source_errors.py`](../main/domain/errors/source_errors.py)

Пост о полезном ресурсе: заголовок, 2–4 предложения, ссылка. Ссылка **не в
тексте**, а в превью — `LinkPreviewOptions(prefer_large_media=True,
show_above_text=True)`, поэтому пост в канале выглядит как карточка.

## Payload

```python
class SourcePayload(BaseModel):
    title: str
    text: str
    url: str
    source_title: str
    source_id: int | None = None
```

`source_id` **опционален**, в отличие от `QuizPayload.topic_id`. Отсюда лишняя
проверка в `regenerate_draft`:

```python
case PostType.SOURCES:
    source_id = SourcePayload.model_validate(post.payload).source_id
    if source_id is not None:
        source = await source_service.find_by_id(source_id)
```

## Сценарий

```
__call__
├─ ресурс не передан? → _pick_new_source
│   ├─ find_unused(limit=1) — недоиспользованный ресурс? берём
│   └─ иначе до 3 попыток:
│       ├─ ask_structured(SearchQueryDraft) — придумай поисковый запрос
│       ├─ web_search.search(query, limit=5)
│       └─ _claim_first_free — вставляем результаты по очереди,
│           первый, что вставился, наш
├─ ask_structured(SourceDraft) по title/url/snippet
├─ _validate
├─ create_draft
└─ mark_used(source.id, post.id)
```

## «Вставка выигрывает гонку»

Ключевой приём, стоит понять:

```python
for result in results:
    source = await self.source_service.add_source(AddSourceEntity(...))
    if source is not None:
        return source, result.snippet or _NO_SNIPPET
return None
```

Мы **не спрашиваем** «этот url уже использован?», а сразу пытаемся вставить.
`ON CONFLICT DO NOTHING` по `uq_channel_source_url` вернёт `None`, если url уже
занят. Одним оператором и проверили, и застолбили: две параллельные генерации не
уведут один ресурс.

Побочный эффект — строка появляется в БД **до** того, как пост написан. Если
генерация упадёт дальше, останется `sources` с `used_in_post IS NULL` — и её
подберёт `find_unused` в следующий раз. Это описано прямо в докстроке
`_pick_new_source`: «A row left over from a generation that died halfway is
reused first: the url is already burned in uq_channel_source_url».

## Два обращения к модели плюс поиск

| Шаг | Схема | Что просим |
|---|---|---|
| 1 | `SearchQueryDraft` | поисковый запрос, английский, 3–6 слов |
| 2 | Serper | 5 органических результатов |
| 3 | `SourceDraft` | заголовок ≤ 100 и текст ≤ 700 по title/url/snippet |

Промпт явно требует «Ссылку в текст не вставляй — она будет отдельно», потому что
ссылка уходит в `LinkPreviewOptions`, а не в тело.

`_validate` минимальный: непустые `title` и `text` после `strip()`. Остальное
держит схема.

## Serper

`SerperWebSearchClient` — `POST https://google.serper.dev/search`, `httpx` из
APP-скоупа с таймаутом 30 с, `tenacity` — 3 попытки с экспоненциальной паузой на
`TimeoutException` и `NetworkError`.

Результаты без `link` или `title` молча пропускаются: у Serper в `organic`
попадаются блоки без ссылки. Любая ошибка запроса заворачивается в
`WebSearchError`.

## Известное расхождение с конвенцией

`source_errors.py` отдаёт `user_message` **по-русски** («Не нашёл ни одного
нового ресурса», «Пост получился некорректным»), тогда как остальной бот говорит
с пользователем по-английски. Числится в [STATE.md](STATE.md), логику не ломает.
