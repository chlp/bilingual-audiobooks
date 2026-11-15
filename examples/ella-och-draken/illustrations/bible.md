# Библия иллюстраций: Ella och den blå draken

Статус: **DRAFT** — референсы ещё не выбраны. После выбора вариантов статус
каждого элемента меняется на `LOCKED`, а описание больше не правится (иначе
картинки разойдутся с уже нарисованными).

Всё, что повторяется в книге больше одного раза, описано здесь один раз и
получает свой референс-лист. Сцены (`scenes.json`) ссылаются на эти листы по
`id`, а не описывают внешность заново.

## Стиль (общий для всех картинок)

```
children's picture book illustration, soft gouache and colored pencil, warm muted palette,
gentle textured paper, expressive faces, Swedish countryside, late summer
```

Негатив: `text, letters, watermark, extra fingers, deformed hands, photorealistic, 3d render, scary`.
Формат сцен: 3:2, горизонтальный.

## Персонажи — лист `refs/characters.png`

| id | Кто | Главы | Описание для промпта |
|---|---|---|---|
| `ella` | Элла, 6 лет | 1–3 | `Ella, a 6-year-old girl with two red braids, freckles, round face, yellow raincoat-style jacket over a blue-and-white striped shirt, green rubber boots` |
| `bulle` | Булле, пёс | 1–3 | `Bulle, a small brown short-haired dog with one white ear, red collar, curly tail` |
| `morfar` | дедушка Свен | 2–3 | `Morfar Sven, a tall thin grandfather with a short white beard, red-and-white striped knitted hat, grey wool sweater, brown corduroy trousers` |
| `mamma` | мама Эллы | 1–2 | `Ella's mother, a woman in her thirties with a red bun hairstyle, green cardigan, jeans` |

Эпизодические (без листа, описываются в сцене): почтальон.

## Локации — по листу на каждую

| id | Где | Главы | Описание | Лист |
|---|---|---|---|---|
| `loc-stuga` | красный домик дедушки у озера | 2–3 | `a small red Swedish wooden cottage with white corner boards, a green front door, a three-step wooden porch, an old apple tree beside it, a shiny lake behind` | `refs/loc-stuga.png` |
| `loc-kulle` | холм за домиком | 2–3 | `a grassy hill behind the cottage with one big round grey boulder on top, view over the lake and the red cottage below` | `refs/loc-kulle.png` |
| `loc-ellas-hus` | жёлтый дом Эллы в городе | 1 | `a yellow two-storey town house with a white front door and a brass mail slot` | — (одна сцена, лист не нужен) |

## Предметы

| id | Что | Главы | Описание | Лист |
|---|---|---|---|---|
| `prop-drake` | синий воздушный змей | 1–3 | `a diamond-shaped blue kite with a smiling yellow sun painted in the middle and a long yellow ribbon tail with small bows` | `refs/prop-drake.png` |
| `prop-stege` | деревянная лестница | 3 | эпизодический, описывается в сцене | — |

## Правила для сцен

- Каждый персонаж, локация и предмет из таблиц — **строго как на референсе**.
- Если в сцене кого-то НЕТ — написать явно (`Morfar is NOT in this scene`):
  генератор любит дорисовывать знакомых персонажей.
- Возраст детей держать: 6 лет — маленький ребёнок, не подросток.
