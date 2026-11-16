# Процесс: как сделать книжку

Результат: страница-плеер (оригинал слева, перевод справа, подсветка строки
под звук, иллюстрации), mp3, PDF и треки по главам. Всё собирается из
одного `build/data.json`.

```
      источник                       текст + время                  оформление
┌────────────────────┐        ┌──────────────────────┐        ┌────────────────────┐
│ A аудио на языке   │─ASR───>│ sv.json + ru.json    │        │ bible.md (Claude)  │
│   оригинала        │        │ -> build_data.py     │        │ refs (Codex)       │
│ B аудио на другом  │─ASR──┐ │                      │─data──>│ scenes.json (Cl.)  │
│   языке            │      ├>│ text/chNN.txt        │ .json  │ сцены (Codex)      │
│ C только текст /   │──────┘ │ -> tts_build.py      │        │ build_html.py      │
│   своя история     │        │   (озвучка Piper)    │        │ build_pdf.py       │
│ D аудио + готовый  │─ASR───>│ align_literary.py    │        │ split_chapters.py  │
│   перевод          │        │   (оценка, дрейф)    │        │ publish.py         │
└────────────────────┘        └──────────────────────┘        └────────────────────┘
```

| Маршрут | Когда | Синхронизация | Пример |
|---|---|---|---|
| **A** | есть аудиокнига на шведском, перевода нет | точная (перевод сегмент-в-сегмент) | — |
| **B** | аудиокнига есть только на другом языке (польский, английский) | точная (TTS по строкам) | Sandvargen (из польской аудиокниги) |
| **C** | есть только текст, или пишем свою историю | точная (TTS по строкам) | `examples/ella-och-draken` |
| **D** | есть аудио на шведском и уже готовый литературный перевод | оценочная (Гейл—Черч) | Robin |

Если можно выбирать, выбирайте **A** (живой диктор) или **C/B** (точная
синхронизация, полный контроль над текстом). D — только когда перевод уже
есть и переделывать его не хочется.

## 0. Окружение (один раз)

macOS на Apple Silicon, `python3`, `ffmpeg` (`brew install ffmpeg`), Google
Chrome (для PDF), приложение Codex со skill `imagegen` (для иллюстраций),
Claude Code (перевод, библия, сцены, проверка).

```bash
python3 -m venv .venv-tts && .venv-tts/bin/pip install piper-tts pillow     # B, C
python3 -m venv .venv-whisper && .venv-whisper/bin/pip install mlx-whisper  # A, B, D
pip3 install --user pillow   # или пользоваться .venv-tts/bin/python для всех tools/
tools/get_voice.sh sv_SE-nst-medium      # CC0, можно публиковать
tools/get_voice.sh sv_SE-lisa-medium     # приятнее для детей, лицензия не указана -- только личное
```

## 1. Папка книги

```bash
python3 tools/new_book.py my-book --title "Название" --route tts   # -> books/my-book/
```

`books/` в `.gitignore`: личные книги, аудио и картинки в git не попадают.
Исходники кладутся в `books/my-book/source/`. Поля `book.json` —
[FORMATS.md](FORMATS.md).

## 2. Текст и время

### Маршрут A — аудио на языке оригинала

```bash
source .venv-whisper/bin/activate
python3 tools/split_audio.py --input books/my-book/audio.mp3 --outdir books/my-book/build/chunks
python3 tools/transcribe.py --chunks-dir books/my-book/build/chunks --lang sv --out books/my-book/build/sv.json
# Claude: prompts/claude-translate-segments.md -> build/ru.json
python3 tools/build_data.py --sv books/my-book/build/sv.json --ru books/my-book/build/ru.json \
    --title "Название" --out books/my-book/build/data.json
```

Почему нарезка: `whisper-large-v3` на длинном файле теряет или зацикливает
куски речи на границах 30-секундных окон. Куски ~20 сек по реальным паузам
это снимают. После распознавания стоит вычитать `sv.json` (или
`sv.srt`) — правка там дешевле, чем поиск рассинхрона потом.

### Маршрут B — аудио на другом языке

1. Распознать как в A, но `--lang pl` (или другой) -> `build/pl.json`.
   Проверить, не потерял ли Whisper начало глав (у Sandvargen пропали 12 сек
   в главе 13 — дораспознано отдельным куском).
2. Claude: `prompts/claude-text-pairs.md` с источником `build/pl.json` ->
   `text/chNN.txt` (сразу шведский и русский, по предложению на строку).
3. Озвучить: маршрут C, шаг 2.

### Маршрут C — текст или своя история

1. `text/chNN.txt` — пишем сами или через `prompts/claude-text-pairs.md`.
2. Озвучка:
   ```bash
   .venv-tts/bin/python tools/tts_build.py books/my-book   # -> audio.mp3 + build/data.json
   ```
   Голос и скорость — `book.json` -> `tts.voice`, `tts.lengthScale` (1.0
   норма, 1.1–1.2 медленнее, для маленьких детей лучше 1.15). Аудио
   кешируется по предложениям: правка строки -> пересборка за секунды.
   Перед озвучкой послушать пару глав и поправить то, что TTS читает
   плохо (числа, имена, ударения) — прямо в шведской половине строки.

### Маршрут D — аудио + готовый литературный перевод

```bash
# sv.srt -- из transcribe.py (маршрут A, первые два шага) или готовый
python3 tools/align_literary.py --srt books/my-book/build/sv.srt \
    --text books/my-book/source/ru.txt --out books/my-book/build/data.json
```

Перевод: заголовки «Глава N. Название», абзацы через пустую строку. Начало
главы в `.srt` — реплика «Kapitel N…». Если диктор пропустил заголовок
главы (у Robin не было «Kapitel 17»), глава склеится с предыдущей:
ищите длинную паузу между главами (`ffmpeg silencedetect`) и добавляйте
реплику-заголовок вручную. Шведские названия глав, если ASR их исказил —
`book.json` -> `origChapterTitles`.

## 3. Иллюстрации

Подробно — [ILLUSTRATIONS.md](ILLUSTRATIONS.md). Коротко:

1. Claude: библия — персонажи, локации, предметы (`prompts/claude-bible.md`).
2. Codex: по 2–3 варианта референс-листа на каждую группу (`prompts/codex-refs.md`).
3. Человек выбирает, Claude фиксирует (LOCKED).
4. Claude: сцены с якорями и ссылками на референсы (`prompts/claude-scenes.md`).
5. Codex: сцены (`prompts/codex-scenes.md`).
6. Claude: проверка, Codex: перегенерация ошибок (`claude-review.md`, `codex-fix.md`).

## 4. Сборка

```bash
python3 tools/build_html.py books/my-book                  # index.html рядом с audio.mp3
python3 tools/build_pdf.py books/my-book                   # pdf/my-book-parallel.pdf
python3 tools/build_pdf.py books/my-book --mode orig       # книжка только на шведском
python3 tools/build_pdf.py books/my-book --engine pagedjs  # + в шапке страницы глава и таймкод страницы (node/npx)
python3 tools/split_chapters.py books/my-book              # build/tracks/NN - Глава N.mp3 (Yoto и т.п.)
python3 tools/serve.py books/my-book                       # http://localhost:8934/
```

PDF собирать до `build_html.py` (или пересобрать плеер после): плеер сам
находит `pdf/*.pdf` и показывает в шапке кнопки «PDF: SV + RU / SV / RU».

Что класть на сайт или на iPad — только это, остальное сайту не нужно
(`build/data.json` уже встроен в `index.html`):

```
index.html  audio.mp3  illustrations/web/  pdf/
```

Собрать эту папку: `python3 tools/publish.py books/my-book --out ~/site/my-book`
(папка перезаписывается). Сервер должен отдавать mp3 с поддержкой Range
(обычные nginx/Apache/Caddy/GitHub Pages умеют), иначе не работает перемотка.
Через `file://` некоторые браузеры не перематывают большие mp3 — тогда
`tools/serve.py`.

Плеер сам запоминает место (глава, время, прокрутка обеих колонок) в
`localStorage` и открывается там же; кнопка «Ссылка на место» копирует
ссылку вида `index.html#t=1234.5`. Также работает `#ch=5` (начало главы 5).

## 5. Публикация примера

Только для книг, на которые есть права (свой текст, public domain, открытая
лицензия, голос с открытой лицензией). Такие книги живут в `examples/`:

```bash
python3 tools/publish.py examples/my-story   # -> docs/books/my-story/ (+ pdf/) + docs/catalog.json
```

`docs/` — сайт GitHub Pages; главная (`docs/index.html`) рисует список
книг из `catalog.json`.
