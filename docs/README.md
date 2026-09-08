# Документация

Телеграм-бот для автопостинга в канал о дизайне.

## Навигация — через [INDEX.md](INDEX.md)

Там три вещи, которых нет здесь: таблица «задача → документ → **файлы кода**»,
полная карта проекта по слоям со ссылками на каждый модуль и раздел «где
объявлено» для быстрого поиска. **Начинай с него, а не с перебора файлов.**

## Что где

| Документ | О чём |
|---|---|
| [INDEX.md](INDEX.md) | карта проекта и ссылки на код |
| [STATE.md](STATE.md) | открытые дефекты и план — **только они**, без описаний |
| [architecture.md](architecture.md) | слои, DI, скоупы, порядок сборки |
| [data-model.md](data-model.md) | таблицы, конвенции, грабли миграций |
| [posts.md](posts.md) | статусы поста, захват, публикация, планировщик |
| [post-type-quiz.md](post-type-quiz.md) | тип `QUIZ` |
| [post-type-sources.md](post-type-sources.md) | тип `SOURCES` |
| [post-type-custom.md](post-type-custom.md) | тип `CUSTOM`, альбомы |
| [post-type-material.md](post-type-material.md) | тип `MATERIAL`: сбор, генерация, публикация |
| [material-storage.md](material-storage.md) | копия файла в канале-хранилище, таблица `materials` |
| [generated-markup.md](generated-markup.md) | проверка HTML, который написала модель |
| [post-templates.md](post-templates.md) | примеры и инструкция на пару (канал, тип) |
| [scheduling.md](scheduling.md) | отложенная публикация, ввод времени |
| [bot-ui.md](bot-ui.md) | экраны, кнопки, CallbackData, FSM |
| [users-and-channels.md](users-and-channels.md) | роли, права, подключение каналов |
| [errors.md](errors.md) | `AppError`, обработчики, конвенции |
| [ai-and-search.md](ai-and-search.md) | Gemini, Serper |
| [runtime.md](runtime.md) | настройки, логи, запуск, окружение |
| [testing.md](testing.md) | как проверять правку |

Формат работы, конвенции кода и грабли — в [../CLAUDE.md](../CLAUDE.md).

Навигация и обновление этой базы знаний — скиллы `/kb` и `/kb_update`,
они живут в `~/.claude/skills/` и в репозиторий не входят.

## Правило

**Если документ разошёлся с кодом — верен код.** Документы описывают намерение и
решения, которые из кода не выводятся; факты проверяй запуском.

## Схема одного цикла

```
Telegram update
  → Dispatcher (роутеры: error, command, menu, post, admin)
  → RoleMiddleware кладёт data["role"]
  → фильтр HasAccessFilter / IsAdminFilter
  → хендлер (presentation) ← FromDishka: use case, service
      → use case (domain)
          → service (domain) → repo (data) → Postgres
          → client (data) → Gemini / Serper / Telegram
  → ответ в чат
```

Плюс независимая петля: `run_scheduler` каждые 60 секунд забирает созревшие посты
и публикует их мимо диспетчера.
