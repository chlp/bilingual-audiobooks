# Готовые промпты

Копируйте в нужную сессию, заменив `<slug>` на папку книги (`books/<slug>` или
`examples/<slug>`). Порядок шагов — в [guide/PROCESS.md](../guide/PROCESS.md).

| Файл | Кто выполняет | Шаг |
|---|---|---|
| [claude-text-pairs.md](claude-text-pairs.md) | Claude Code | текст -> `text/chNN.txt` (маршруты B, C) |
| [claude-translate-segments.md](claude-translate-segments.md) | Claude Code | `sv.json` -> `ru.json` (маршрут A) |
| [claude-bible.md](claude-bible.md) | Claude Code | библия иллюстраций: персонажи, локации, предметы |
| [codex-refs.md](codex-refs.md) | Codex (imagegen) | варианты референс-листов |
| [claude-scenes.md](claude-scenes.md) | Claude Code | выбор сцен -> `scenes.json` |
| [codex-scenes.md](codex-scenes.md) | Codex (imagegen) | сцены по зафиксированным референсам |
| [claude-review.md](claude-review.md) | Claude Code | проверка картинок, список на перегенерацию |
| [codex-fix.md](codex-fix.md) | Codex (imagegen) | перегенерация отдельных сцен |
