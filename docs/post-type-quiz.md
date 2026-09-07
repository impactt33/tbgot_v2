# Тип поста: QUIZ

> **Главные файлы:**
> [`use_cases/generate_quiz.py`](../main/domain/use_cases/generate_quiz.py) ·
> [`models/quiz_topic_model.py`](../main/data/models/quiz_topic_model.py) ·
> [`services_impl/quiz_topic_service_impl.py`](../main/domain/services_impl/quiz_topic_service_impl.py) ·
> [`repositories_impl/quiz_topic_repo_impl.py`](../main/data/repositories_impl/quiz_topic_repo_impl.py)
> **Рядом:** `QuizPayload` в [`entities/payloads.py`](../main/domain/entities/payloads.py) ·
> `_publish_quiz` в [`telegram_publisher.py`](../main/data/clients_impl/telegram/telegram_publisher.py) ·
> [`errors/quiz_topics_errors.py`](../main/domain/errors/quiz_topics_errors.py)

Публикуется как нативный опрос Telegram (`send_poll` с `type=QUIZ`): вопрос,
2–4 варианта, один верный, пояснение.

## Payload

```python
class QuizPayload(BaseModel):
    question: str        # ≤ 300
    options: list[str]   # 2..12
    correct_index: int   # ≥ 0
    explanation: str     # ≤ 200
    topic_id: int        # ссылка на строку quiz_topics
```

`topic_id` — то, ради чего payload вообще связан с таблицей: по нему
`discard_draft` находит тему и возвращает её в пул, а `regenerate_draft` —
переиспользует.

## Зачем таблица тем

Модель не помнит, о чём уже спрашивали. `quiz_topics` — это внешняя память:
список тем канала, который подставляется в промпт как «вот это использовать
нельзя», плюс `UniqueConstraint(channel_id, topic)`, который ловит повтор, даже
если модель промпт проигнорировала.

## Сценарий

```
__call__
├─ тема не передана? → _pick_new_topic
│   ├─ find_unused(limit=1) — есть недоиспользованная? берём её
│   └─ иначе до 3 попыток:
│       ├─ ask_structured(TopicDraft) — придумай тему, вот использованные
│       └─ add_topic → None значит дубль, пробуем ещё
│                    → 3 неудачи = CannotGenerateTopicError
├─ ask_structured(QuizDraft) по этой теме
├─ _validate(draft)
├─ create_draft(payload = draft + topic_id)
└─ mark_used(topic.id, post.id)
```

**Сначала `find_unused`.** Это подбор мусора за собой: если прошлая генерация
умерла между `add_topic` и `create_draft`, тема осталась висеть с
`used_in_post IS NULL`. Брать её первой дешевле, чем ходить в модель.

**`add_topic` возвращает `None` на конфликте**, а не кидает: репозиторий делает
`ON CONFLICT DO NOTHING` по `(channel_id, topic)`, проверка и вставка в одном
операторе. Гонка между двумя генерациями невозможна — вставка выигрывает.

**`mark_used` после `create_draft`,** иначе `used_in_post` некуда писать: поста
ещё нет.

## Две модели ответа

Gemini вызывается дважды, обе схемы — pydantic, отдаются в `response_schema`:

```python
class TopicDraft(BaseModel):
    topic: str = Field(max_length=255, description="Тема квиза, 3-7 слов…")

class QuizDraft(BaseModel):
    question: str
    options: list[str] = Field(min_length=2, max_length=4)
    correct_index: int = Field(ge=0, le=3)
    explanation: str
```

Обрати внимание на расхождение: `QuizDraft.options` допускает 2–4 варианта, а
`QuizPayload.options` — до 12. Первая — ограничение для модели, вторая — предел
Telegram. Ужимать `QuizPayload` до 4 не надо, это запас на будущее.

## Что не ловит pydantic

`_validate` — ручные проверки поверх схемы, потому что модель может вернуть
формально валидный, но бессмысленный квиз:

- пустой вариант после `strip()`;
- дубли вариантов;
- `correct_index` за пределами фактического списка;
- вариант длиннее 100 символов (лимит Telegram на строку опроса).

Всё это — `InvalidQuizDraftError`, наследник `AppError`, то есть долетит до
пользователя понятным текстом.

Мелочь: сообщение последней проверки говорит «Longer than 1000 symbols», а порог
100. Косметика, но чинить — не забыть про обе цифры.

## Regenerate

`regenerate_draft` достаёт `topic_id` из payload, грузит тему и передаёт её в
`GenerateQuizRequest(topic=...)`. Тогда `_pick_new_topic` не вызывается вовсе:
тема та же, вопрос новый.
