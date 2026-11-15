# Форматы файлов

## book.json

Все пути — относительно папки книги. Голос (`tts.voice`) ищется сначала в
папке книги, потом в корне репозитория.

| Поле | По умолчанию | Что |
|---|---|---|
| `slug` | имя папки | ключ в `localStorage` и URL на сайте |
| `title`, `subtitle` | `slug`, — | шапка плеера, вкладка, каталог |
| `route` | — | `asr` (A), `tts` (B/C), `literary` (D) — для людей |
| `origLang`, `transLang` | `sv`, `ru` | языки |
| `origLabel`, `transLabel` | `Svenska`, `Русский` | заголовки колонок |
| `origShort`, `transShort` | `SV`, `RU` | переключатель языков |
| `audio` | `audio.mp3` | аудио книги |
| `data` | `build/data.json` | см. ниже |
| `text` | `text` | папка `chNN.txt` (маршруты B/C) |
| `illustrations` | `illustrations` | см. ILLUSTRATIONS.md |
| `out` | `index.html` | страница плеера |
| `footerHint` | подсказка про клики | подвал плеера |
| `origChapterTitles` | — | `{"1": "Vilse i centrum"}` — ручные названия глав оригинала |
| `tts.voice` | `voices/sv_SE-lisa-medium.onnx` | голос Piper |
| `tts.lengthScale` | `1.08` | скорость, больше — медленнее |
| `tts.cache` | `build/tts_cache` | кеш озвучки |
| `cover`, `about` | — | карточка в каталоге сайта |

## text/chNN.txt (маршруты B, C)

```
@Åsa Lind. Sandvargen och sanna påhitt. ||| Оса Линд. Песчаный Волк и правдивые выдумки.
Kapitel 1. Sanna påhitt ||| Глава 1. Правдивые выдумки

Zackarina bodde i ett hus vid havet. ||| Закарина жила в доме у моря.
– En sån mus kan man ju inte äga, sa Zackarina. ||| — Такую мышку ведь нельзя иметь, — сказала Закарина.

Nästa stycke. ||| Следующий абзац.
```

- Одна строка = одно предложение (или реплика) = одна строка в плеере и
  один кусок озвучки. Ровно один разделитель `|||`.
- Первая строка без `@` — заголовок главы. `@` — вступление (название
  книги), озвучивается перед заголовком.
- Пустая строка — новый абзац (длиннее пауза в озвучке, отступ в плеере).
- Строки на `#` — комментарии, не озвучиваются.
- Номер главы берётся из имени файла.

## sv.json / ru.json (маршрут A)

```json
[{"start": 9.92, "end": 14.15, "text": "Zackarina bodde i ett hus vid havet."}, ...]
```

`ru.json` — той же длины, с теми же `start`/`end`.

## build/data.json

Единый вход для плеера, PDF и нарезки по главам.

```json
{
  "duration": 5881.5,
  "cues": [{"start": 0.0, "end": 2.96, "text": "…", "para": 1}],
  "chapters": [{
    "index": 0, "ruNum": 1,
    "svTitle": "Sanna påhitt", "ruTitle": "Правдивые выдумки", "svRawTitle": "Kapitel 1. Sanna påhitt",
    "timeStart": 0.0, "timeEnd": 412.3,
    "cueStart": 0, "cueEnd": 98,
    "titleLines": 2,
    "ruLines": [{"text": "…", "start": 0.0, "end": 2.96, "para": 0, "svStart": 0, "svEnd": 0}]
  }]
}
```

- `cues` — реплики оригинала с точным временем (`para` — номер абзаца, если
  известен).
- `ruLines` — строки перевода (имя поля историческое, язык любой).
  `svStart`/`svEnd` — **глобальные** индексы `cues`, которым соответствует
  строка (при 1:1 совпадают).
- `cueStart`/`cueEnd` — диапазон `cues` главы, `cueEnd` не включается.
- `titleLines` — сколько первых строк главы — заголовок/вступление (PDF
  печатает их отдельно).
- `ruNum` — настоящий номер главы из книги, не порядковый индекс.

## illustrations/scenes.json

См. [ILLUSTRATIONS.md](ILLUSTRATIONS.md), шаг 4. Для простых случаев
вместо него можно `images.json` — тот же список, только `chapter`, `file`,
`anchor`/`anchorOrig`, `pos`.

## docs/catalog.json

Список карточек книг на сайте, пишет `tools/publish.py`.
