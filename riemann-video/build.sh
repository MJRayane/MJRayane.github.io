#!/usr/bin/env bash
# Rendu complet : 8 scènes en 1080p30, puis assemblage dans riemann.mp4
# Usage : ./build.sh            (4 scènes rendues en parallèle)
set -euo pipefail
cd "$(dirname "$0")"

SCENES=(Scene1Atomes Scene2Chaos Scene3Escalier Scene4Paysage
        Scene5Musique Scene6Quotidien Scene7Dominos Scene8Conclusion)
OUT=media/videos/riemann/1080p30

[ -f data.npz ] || python3 precompute.py          # données mathématiques (≈ 1 min)

# modèle de synthèse vocale Kokoro (voix off), ≈ 350 Mo, téléchargé une fois
mkdir -p modeles
URL=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
for f in kokoro-v1.0.onnx voices-v1.0.bin; do
  [ -f modeles/$f ] || curl -sSL -o modeles/$f $URL/$f
done
python3 lint_subs.py                               # ≤ 12 mots par ligne de sous-titre

# 1) rendu de chaque scène séparément (les scènes 3D sont les plus longues)
mkdir -p logs
printf '%s\n' Scene4Paysage Scene8Conclusion Scene7Dominos Scene1Atomes \
              Scene3Escalier Scene5Musique Scene6Quotidien Scene2Chaos |
  xargs -P 4 -I{} sh -c 'manim -qh --fps 30 riemann.py {} > logs/{}.log 2>&1 && echo "OK {}"'

# 2) assemblage
# La piste audio de chaque scène s'arrête à la dernière phrase : on la complète
# par du silence jusqu'à la durée exacte de la vidéo, sinon la voix prendrait
# de l'avance sur l'image scène après scène.
mkdir -p $OUT/pad
: > concat.txt
for S in "${SCENES[@]}"; do
  D=$(ffprobe -v error -select_streams v:0 -show_entries stream=duration -of csv=p=0 $OUT/$S.mp4)
  ffmpeg -v error -y -i $OUT/$S.mp4 -c:v copy -af "apad,aresample=48000" -c:a aac -b:a 192k -t $D $OUT/pad/$S.mp4
  echo "file '$OUT/pad/$S.mp4'" >> concat.txt
done
ffmpeg -v error -y -f concat -safe 0 -i concat.txt \
       -c:v libx264 -preset slow -crf 20 -pix_fmt yuv420p -r 30 -c:a aac -b:a 160k -ar 48000 -movflags +faststart riemann.mp4

# 3) sous-titres : texte brut + .srt synchronisé
python3 make_subs.py
echo "Terminé : riemann.mp4"
