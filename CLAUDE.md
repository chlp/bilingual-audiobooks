# Bilingual Audiobooks — инструкции для Claude Code

Репозиторий: инструменты и процесс для двуязычных (SV/RU) книжек-плееров с
иллюстрациями для ребёнка. Процесс — `guide/PROCESS.md`, иллюстрации —
`guide/ILLUSTRATIONS.md`, форматы — `guide/FORMATS.md`, промпты — `prompts/`.

## Правила

- Личные книги — только `books/<slug>/` (в `.gitignore`). Ничего из
  `books/` не коммитить и не копировать в `examples/` или `docs/`:
  купленные аудиокниги, их тексты, переводы и иллюстрации к ним
  публиковать нельзя. `examples/` и `docs/` — только своё/открытое.
  Собранные личные книги идут в `web/` (тоже `.gitignore`):
  `python3 tools/publish.py books/<slug>`.
- Не править сгенерированное: `build/data.json`, `index.html`,
  `illustrations/web/`, `docs/`, `web/` — пересобирать скриптами
  (страница списка книг — шаблон `player/catalog.html`).
- Перевод сегмент-в-сегмент (маршрут A) сохраняет длину и таймкоды 1:1.
- Картинки рисует Codex, не Claude. Роль Claude: библия (`bible.md`),
  сцены (`scenes.json`), проверка, готовые промпты для Codex по шаблонам
  из `prompts/`. Промпт для Codex отдавать пользователю целиком, в блоке
  кода, с подставленным `<slug>`.
- После фиксации референсов (`bible.md` — LOCKED) описания в библии не
  менять; новые повторяющиеся элементы — новым референсом.
- Плеер один — `player/template.html`, общий для всех книг; книжные
  особенности — через `book.json`, не форком шаблона.

## Проверка изменений

```bash
python3 -m py_compile tools/*.py
.venv-tts/bin/python tools/tts_build.py examples/ella-och-draken
.venv-tts/bin/python tools/build_html.py examples/ella-och-draken
python3 tools/illustrations_status.py examples/ella-och-draken
python3 tools/build_pdf.py examples/ella-och-draken
```

Плеер проверять в браузере через `tools/serve.py`: подсветка, клик по строке,
восстановление места после перезагрузки, «Ссылка на место», режим одного
языка, ширина телефона.

## Окружение

`.venv-tts/` (piper-tts, pillow), `.venv-whisper/` (mlx-whisper), голоса в
`voices/` (`tools/get_voice.sh`). Скрипты без piper/whisper (`build_html.py`
и т.п.) требуют только Pillow — удобно запускать через `.venv-tts/bin/python`.
