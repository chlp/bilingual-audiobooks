# Codex: сцены по референсам

```
Прочитай AGENTS.md, books/<slug>/illustrations/bible.md и scenes.json.

Для каждой сцены из scenes.json, у которой ещё нет файла (список:
python3 tools/illustrations_status.py books/<slug>), сгенерируй картинку:
- прикрепи как референсы все файлы refs/<id>.png из поля refs сцены;
- промпт = STYLE из библии + "Use the attached reference sheets strictly for
  the recurring characters, locations and objects (faces, hair, clothes,
  colors, shapes); create a new scene:" + prompt сцены + "Landscape 3:2.
  No text, letters or watermark.";
- сохрани в books/<slug>/illustrations/<file> (PNG).

Генерируй по главам. После каждой главы собери контакт-лист
python3 tools/contact_sheet.py books/<slug>/illustrations/chNN/*.png -o /tmp/chNN.png --cols 3,
посмотри его и сам перегенерируй сцены с явными ошибками: лишний или
пропавший персонаж, другая внешность/одежда, чем на референсе, текст на
картинке, лишние пальцы. В конце перечисли, что перегенерировал и почему.
```
