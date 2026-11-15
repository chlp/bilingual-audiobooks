# Bilingual Audiobooks — двуязычные книжки для ребёнка

*Bilingual picture audiobooks for kids: Swedish text synced to audio on the
left, translation on the right, consistent illustrations made with
Claude Code + Codex. Docs are in Russian.*

**Примеры: <https://chlp.github.io/bilingual-audiobooks/>**

Инструменты и процесс, чтобы сделать из книги (аудиокниги, текста или своей
истории) страницу-плеер:

- слева шведский текст, справа перевод, по строкам; текущая строка
  подсвечивается под звук в обеих колонках, клик по строке — переход в аудио;
- иллюстрации с одинаковыми героями, местами и предметами по всей книге;
- плеер запоминает место (глава, время, прокрутка) и даёт ссылку на место;
- режим одного языка, скорость, размер шрифта, работает на iPad;
- PDF (параллельный текст или книжка на одном языке) и mp3 по главам (Yoto).

## Как это делается

Подробно — **[guide/PROCESS.md](guide/PROCESS.md)**. Четыре входа, один выход:

| Есть | Что делаем | Синхронизация |
|---|---|---|
| A. Аудиокнига на шведском | Whisper по кускам -> перевод сегмент-в-сегмент | точная |
| B. Аудиокнига на другом языке | Whisper -> шведский + русский по строкам -> озвучка Piper | точная |
| C. Текст или своя история | шведский + русский по строкам -> озвучка Piper | точная |
| D. Шведское аудио + готовый перевод | статистическое выравнивание по длине | оценочная |

Иллюстрации — **[guide/ILLUSTRATIONS.md](guide/ILLUSTRATIONS.md)**: Claude
читает книгу и пишет «библию» (персонажи, локации, предметы), Codex рисует
по несколько вариантов референс-листов, мы выбираем и фиксируем, Claude
расписывает сцены со ссылками на референсы, Codex рисует сцены, Claude
проверяет. Готовые промпты — [prompts/](prompts/).

## Быстрый старт

```bash
git clone https://github.com/chlp/bilingual-audiobooks.git && cd bilingual-audiobooks
python3 -m venv .venv-tts && .venv-tts/bin/pip install piper-tts pillow
tools/get_voice.sh sv_SE-nst-medium

python3 tools/new_book.py my-story --title "Min saga"
# напишите books/my-story/text/ch01.txt (формат -- guide/FORMATS.md),
# поменяйте tts.voice в book.json, если нужен другой голос
.venv-tts/bin/python tools/tts_build.py books/my-story
.venv-tts/bin/python tools/build_html.py books/my-story
.venv-tts/bin/python tools/serve.py books/my-story      # http://localhost:8934/
```

Нужны macOS (для Whisper — Apple Silicon), Python 3, `ffmpeg`, Google
Chrome (PDF), Claude Code и приложение Codex со skill `imagegen`.

## Структура

```
player/template.html   плеер (один на все книги)
tools/                 скрипты: распознавание, озвучка, выравнивание, сборка, PDF, публикация
prompts/               промпты для Claude Code и Codex
guide/                 процесс, иллюстрации, форматы, идеи
examples/<slug>/       открытые книги-примеры (исходники)
docs/                  сайт GitHub Pages: каталог + собранные примеры
books/                 личные книги (в .gitignore)
voices/                голоса Piper (в .gitignore)
```

## Права

Код — MIT. В `examples/` и на сайте — только то, что можно публиковать:
свои тексты, голос Piper NST (CC0). Личные книги (купленные аудиокниги,
их переводы и иллюстрации к ним) держите в `books/`, она не попадает в git.
