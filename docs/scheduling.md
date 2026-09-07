# Отложенная публикация

> **Главные файлы:**
> [`utils/time_input.py`](../main/presentation/utils/time_input.py) ·
> [`utils/schedule_presets.py`](../main/presentation/utils/schedule_presets.py) ·
> [`callbacks/schedule.py`](../main/presentation/callbacks/schedule.py) ·
> [`callbacks/scheduled.py`](../main/presentation/callbacks/scheduled.py) ·
> [`keyboards/scheduled.py`](../main/presentation/keyboards/scheduled.py) ·
> `schedule_preset_keyboard` в [`keyboards/post.py`](../main/presentation/keyboards/post.py)
> **Хендлеры:** блок SCHEDULE в
> [`post_handlers.py`](../main/presentation/handlers/post_handlers.py) ·
> **Как публикуется:** [`app/scheduler.py`](../app/scheduler.py)

## Два экрана

**Пресеты.** Пять кнопок с уже посчитанным временем плюс «Enter date and time»
плюс «Back»:

```
In an hour · 07.09.2026 16:30
In two hours · 07.09.2026 17:30
In three hours · 07.09.2026 18:30
Tomorrow morning (10:00) · 08.09.2026 10:00
Tomorrow evening (19:00) · 08.09.2026 19:00
Enter date and time
Back
```

**Ручной ввод.** Состояние `CreatePostState.waiting_for_time`, три формата,
выход по «Back» или `/quit`.

## Пресеты не носят время в `callback_data`

Важное решение. `ScheduleCB` несёт **имя** пресета, а не timestamp:

```python
class ScheduleCB(CallbackData, prefix="nps2"):
    preset: SchedulePreset
    post_id: int
    preview_id: int
    preview_count: int = 1
```

Время считается заново в хендлере — `resolve_preset(callback_data.preset,
settings.user_tz)`. Иначе кнопка, полежавшая в чате полчаса, поставила бы
публикацию в прошлое: подпись «In an hour» осталась бы прежней, а час уже прошёл.

Подпись на кнопке при этом считается при отрисовке, поэтому она честная в момент
показа и может разойтись с фактом при позднем нажатии. Это осознанный компромисс:
расхождение максимум на минуты, а гарантия «время всегда в будущем» — жёсткая.

## Часовые пояса

**В БД всё в UTC**, колонка `timestamptz`, планировщик сравнивает с `func.now()`.
Локальная зона (`settings.USER_TIMEZONE`, по умолчанию `Europe/Moscow`) живёт
ровно в двух местах: при разборе ввода и при выводе.

```python
parse_when(text, tz)  →  aware datetime в UTC
format_local(when, tz)  →  "25.12.2026 18:00"
```

`Settings` валидирует зону на старте: неизвестное имя — `ValueError` при импорте
`core.config`, а не загадочное поведение в рантайме.

## `parse_when`

Три формата, оба регэкспа `fullmatch`:

| Ввод | Правило |
|---|---|
| `18:00` | сегодня; если уже прошло — завтра |
| `25.12 18:00` | текущий год; если дата прошла — следующий год |
| `25.12.2026 18:00` | ровно как написано, без переносов |

Год переносится **только когда он не указан явно**: написал `25.12.2020 18:00` —
получишь `TimeInPastError`, а не тихий перенос на 2021.

`MIN_LEAD = 1 минута`. Время ближе — `TimeInPastError`: планировщик ходит раз в
60 секунд, ставить публикацию на «через 5 секунд» бессмысленно.

**`now` передаётся параметром** во все функции — так они остаются чистыми и
тестируемыми без подмены системных часов. Это же относится к `in_hours`,
`next_day_at`, `resolve_preset`.

### Несуществующее локальное время

```python
def _at(day, hour, minute, tz):
    local = datetime(day.year, day.month, day.day, hour, minute, tzinfo=tz)
    if local.astimezone(UTC).astimezone(tz) != local:
        raise TimeInputError(f"Local time does not exist in {tz}: {local}")
    return local
```

Круговой прогон через UTC ловит час, пропущенный при переводе стрелок. Для
Москвы сейчас неактуально, но зона настраиваемая.

Отдельно `_date` ловит `31.02` — `date()` кидает `ValueError`, он заворачивается
в `TimeInputError` с человеческим текстом.

## Ошибки ввода — не ошибки приложения

```python
try:
    when = parse_when(message.text or "", settings.user_tz)
except TimeInputError as err:
    await message.answer(err.user_message)
    return          # состояние НЕ сбрасывается
```

Хендлер ловит `TimeInputError` сам и **оставляет состояние открытым**: админ
просто пишет время ещё раз. До `error_router` это не доходит. Тот же приём — в
разборе ручного поста.

А вот `AppError` от `post_service.schedule` (например, пост уже опубликован)
состояние сбрасывает и возвращает в меню — повторять ввод бессмысленно.

## Список отложенных

`show_scheduled` → `find_scheduled()` (limit 20, сортировка по `scheduled_at`) →
по строке на пост:

```
Cancel · 08.09.2026 10:00 · QUIZ · Название канала
```

Нажатие отменяет публикацию: `unschedule` переводит `SCHEDULED → DRAFT` и
обнуляет `scheduled_at`.

**Гонка обработана явно.** Между отрисовкой списка и нажатием планировщик мог
забрать пост:

```python
try:
    await post_service.unschedule(callback_data.post_id)
except PostNotScheduledError as err:
    await callback.answer(err.user_message, show_alert=True)
else:
    await callback.answer("Publication cancelled, the post is back to drafts.")

await _render_scheduled(...)   # список перерисовывается в обоих случаях
```

`unschedule` фильтрует по `status == SCHEDULED`, поэтому «отменить» уже
публикующийся пост нельзя — вернётся `None` и поднимется ошибка.

## Что дальше

Как отложенный пост доходит до канала — в [posts.md](posts.md#планировщик).
