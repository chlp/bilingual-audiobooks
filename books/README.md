# books/ — личные книги

Всё в этой папке, кроме этого файла, в `.gitignore`. Одна книга — одна
папка, создаётся `python3 tools/new_book.py <slug> --title "…"`.

```
books/<slug>/
  book.json          настройки (guide/FORMATS.md)
  source/            исходники: mp3/mp4, расшифровки, готовые переводы
  text/chNN.txt      пары «оригинал ||| перевод» (маршруты B, C)
  build/             data.json, куски аудио, кеш TTS, треки по главам (на сайт не нужно)
  pdf/               PDF (build_pdf.py); плеер ссылается на них из шапки
  illustrations/     bible.md, refs/, scenes.json, chNN/, web/
  audio.mp3          аудио книги
  index.html         плеер; на сайт: index.html + audio.mp3 + illustrations/web/ + pdf/
                     (tools/publish.py books/<slug> --out <папка>)
  extras/            всё прочее (Yoto, старые версии)
```
