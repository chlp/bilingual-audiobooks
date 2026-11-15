#!/bin/sh
# Скачивает голос Piper в voices/ (папка в .gitignore).
#   tools/get_voice.sh sv_SE-lisa-medium
#   tools/get_voice.sh sv_SE-nst-medium
# Список голосов: https://huggingface.co/rhasspy/piper-voices/tree/main
set -eu
name="${1:?имя голоса, например sv_SE-lisa-medium}"
lang_region="${name%%-*}"                 # sv_SE
rest="${name#*-}"; voice="${rest%-*}"; quality="${rest##*-}"
lang="${lang_region%%_*}"                 # sv
base="https://huggingface.co/rhasspy/piper-voices/resolve/main/$lang/$lang_region/$voice/$quality"
dir="$(cd "$(dirname "$0")/.." && pwd)/voices"
mkdir -p "$dir"
for f in "$name.onnx" "$name.onnx.json" "MODEL_CARD"; do
  out="$dir/$f"; [ "$f" = MODEL_CARD ] && out="$dir/$name.MODEL_CARD"
  curl -fL --progress-bar -o "$out" "$base/$f"
done
echo "voices/$name.onnx"
