# books/ — личные книги

Всё в этой папке, кроме этого файла, в `.gitignore`. Одна книга — одна
папка, создаётся `python3 tools/new_book.py <slug> --title "…"`.

```
books/<slug>/
  book.json          настройки (guide/FORMATS.md)
  source/            исходники: mp3/mp4, расшифровки, готовые переводы
  text/chNN.txt      пары «оригинал ||| перевод» (маршруты B, C)
  build/             data.json, куски аудио, кеш TTS, PDF, треки по главам
  illustrations/     bible.md, refs/, scenes.json, chNN/, web/
  audio.mp3          аудио книги
  index.html         плеер (рядом с audio.mp3 и illustrations/web/)
  extras/            всё прочее (Yoto, старые версии)
```
