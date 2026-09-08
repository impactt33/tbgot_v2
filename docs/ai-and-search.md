# Gemini и веб-поиск

> **Главные файлы:**
> [`clients_impl/ai/gemini_ai_client.py`](../main/data/clients_impl/ai/gemini_ai_client.py) ·
> [`clients_impl/web_search/serper_web_search_client.py`](../main/data/clients_impl/web_search/serper_web_search_client.py) ·
> [`use_cases/ai_guard.py`](../main/domain/use_cases/ai_guard.py)
> **Интерфейсы:** [`clients/ai/ai_client.py`](../main/domain/clients/ai/ai_client.py) ·
> [`clients/telegram/media_downloader.py`](../main/domain/clients/telegram/media_downloader.py) +
> [impl](../main/data/clients_impl/telegram/telegram_media_downloader.py) ·
> [`clients/web_search/web_search_client.py`](../main/domain/clients/web_search/web_search_client.py) ·
> [`enums/failures/ai_answer_failures.py`](../main/domain/enums/failures/ai_answer_failures.py) ·
> провайдеры в [`app/di/clients.py`](../app/di/clients.py)

## Интерфейс

```python
class AIClient(ABC):
    async def ask_text(self, prompt, *, system=None) -> str | AIFailure
    async def ask_structured(
        self, prompt, schema: type[TModel], *,
        system=None, images: list[bytes] | None = None, mime_type="image/jpeg"
    ) -> TModel | AIFailure
```

**Картинки принимает `ask_structured`, отдельного `ask_image` нет.** Он был —
возвращал `str`, не использовался нигде и успел разойтись с собственным ABC
(в интерфейсе не было `system`). После того как структурный ответ научился
изображениям, он стал дублем и удалён.

`images` и `mime_type` — только по имени, после `*`: картинки редкий случай, и
голый список третьим позиционным аргументом читался бы как часть промпта.
`mime_type` один на весь список — фотографии Telegram всегда JPEG, смешивать
нечего.

## Провал как значение, а не исключение

Ключевое решение слоя. Клиент возвращает `str | AIFailure`, где

```python
class AIFailure(Enum):
    UNAVAILABLE   # сеть, 5xx, всё непонятное
    REJECTED      # 4xx: модель отказалась
    EMPTY         # ответ пустой
    UNPARSEABLE   # не разобрался в схему
```

Клиент живёт в слое данных и не должен знать доменных ошибок. Перевод — одной
функцией в домене:

```python
_FAILURE_TO_ERROR = {
    AIFailure.UNAVAILABLE: AIClientUnavailable,
    AIFailure.REJECTED:    AIClientRejected,
    AIFailure.EMPTY:       AnswerIsEmptyError,
    AIFailure.UNPARSEABLE: AIClientUnparsableAnswer,
}

def unwrap_ai(result: T | AIFailure) -> T:
    if isinstance(result, AIFailure):
        raise _FAILURE_TO_ERROR[result]()
    return result
```

В use case это выглядит так — вызов завёрнут прямо в месте использования:

```python
draft = unwrap_ai(await self.ai_client.ask_structured(prompt, QuizDraft, system=_SYSTEM))
```

Побочная польза: mypy после `unwrap_ai` видит `QuizDraft`, а не `QuizDraft | AIFailure`.

## Структурированный ответ

`ask_structured` отдаёт Gemini pydantic-схему как `response_schema` и просит
`application/json`. Проверка на выходе строгая:

```python
parsed = response.parsed
if not isinstance(parsed, schema):
    return AIFailure.UNPARSEABLE
```

Это единственный способ получить от модели данные, а не текст. Все описания
полей (`Field(description=...)`) уезжают в схему и **работают как часть
промпта** — потому они и написаны по-русски и подробно.

## Retry

`tenacity`, 3 попытки, экспоненциальная пауза 1→10 с, `reraise=True`. Повторяем
**только случайное**:

```python
def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError)):
        return True
    if isinstance(exc, genai_errors.ServerError):
        return True
    return isinstance(exc, genai_errors.APIError) and exc.code == 429
```

`ClientError` (4xx кроме 429) не повторяется: если модель отказала, второй
одинаковый запрос отказа не отменит.

## Настройки генерации

- модель `gemini-2.5-flash-lite`;
- `thinking_config=ThinkingConfig(thinking_budget=0)` — рассуждения выключены,
  задачи короткие;
- `max_output_tokens`: 2048 текст, 8192 структура;
- ходит через прокси: `base_url="https://api.proxyapi.ru/google"`.

## `process_to_history`

Собирает `list[types.Content]`, чередуя роли `user`/`model`. Сейчас `history`
никем не передаётся — все вызовы одноходовые. В коде висит `TODO` про два
подряд идущих `user` в конце: при непустой истории последний элемент добавляется
как `user` независимо от того, чем история кончилась.

**Картинки кладутся в `parts` после текста.** Google для одиночного изображения
советует обратный порядок. Не меняли: без живой генерации это подгонка вслепую,
но это первое, что стоит попробовать, если описания к материалам выйдут мимо.

## Откуда берутся байты картинок

Модели нельзя передать `file_id` — Gemini принимает либо инлайновые байты, либо
URI из своего Files API. Телеграмная ссылка на файл содержит **токен бота прямо
в пути**, так что отдавать её Google (да ещё через прокси) нельзя ни при каких
обстоятельствах. Значит, байты проходят через бота.

`MediaDownloader` — интерфейс в домене, `TelegramMediaDownloader` — реализация:

```python
async def download(self, file_id: str) -> bytes
async def download_many(self, file_ids: list[str]) -> list[bytes]
```

`Bot.download(file_id)` с `destination=None` отдаёт `BinaryIO` в памяти, на диск
ничего не пишется. Фотография максимального размера — обычно 100–400 КБ, три
штуки инлайном ≈ 1 МБ; до лимита `getFile` в 20 МБ далеко.

**Ретраи здесь хитрее, чем кажется.** `Bot.download` — это два вызова, и падают
они по-разному: `get_file` идёт через сессию aiogram и даёт
`TelegramNetworkError`, а сама закачка ходит в `api.telegram.org` напрямую через
`aiohttp` без обёртки — оборвавшийся поток прилетит как `aiohttp.ClientError`,
который не наследует ни `OSError`, ни `TimeoutError`. Поэтому в предикате
`_is_retryable` есть явный `aiohttp`. `TelegramBadRequest` (кривой `file_id`) не
повторяется.

`download_many` собирает через `asyncio.gather(return_exceptions=True)`: обычный
`gather` пробрасывает первую ошибку сразу, оставляя соседние загрузки работать
без присмотра.

Живой мультимодальный вызов проверялся синтетическим PNG, собранным на `zlib` —
прокси инлайновые байты пропускает, `response_schema` работает вместе с
картинками.

## Промпты

Живут константами рядом с use case, **по-русски** — это конвенция проекта.
Общий системный промпт у квизов и ресурсов один и тот же:

> Ты — редактор телеграм-канала о графическом и продуктовом дизайне. Пишешь
> по-русски, кратко и по делу, без канцелярита и восклицательных знаков.

## Serper

```python
POST https://google.serper.dev/search
headers: X-API-KEY
json: {"q": query, "num": limit}
```

`httpx.AsyncClient` — из APP-скоупа, один на всё приложение, таймаут 30 с. Та же
политика retry (таймаут и сеть, 3 попытки).

Разбор терпимый: элементы `organic` без `link` или `title` пропускаются молча —
в выдаче попадаются блоки без ссылки. Любая ошибка запроса заворачивается в
`WebSearchError`.

`SearchResult` — простая сущность домена: `title`, `url`, `snippet`.

## Ключи

`GEMINI_API_KEY` и `SERPER_API_KEY` — в `app/.env`, обязательные поля
`Settings`. Без них не импортируется `core.config`.

Живые вызовы вынесены в `tests/test_live_clients.py` под маркером `live`, который
по умолчанию исключён (`addopts = "-m 'not live'"`) — см. [testing.md](testing.md).

## Проверка того, что модель написала

Ответ в свободной форме проверять нечем, а вот разметку — можно и нужно:
`ask_structured` гарантирует форму, но не то, что HTML внутри поля валиден.
Этим занимается [generated-markup.md](generated-markup.md).
