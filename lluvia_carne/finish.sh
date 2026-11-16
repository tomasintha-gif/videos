#!/bin/bash
# finish.sh "Title": loudness gain to -14 LUFS + -1 dBFS limiter, encode, QA
set -e
cd "$(dirname "$0")"
I=$(ffmpeg -hide_banner -i out/mix.wav -af ebur128 -f null - 2>&1 | grep -E "^\s+I:" | tail -1 | awk '{print $2}')
G=$(python3 -c "print(-14.0 - ($I))")
echo "integrated $I LUFS -> gain $G dB"
ffmpeg -y -loglevel error -i out/mix.wav -af "volume=${G}dB,alimiter=limit=0.891:level=disabled" -ar 48000 out/master.wav
ffmpeg -y -loglevel error -framerate 30 -i out/frames/f%05d.jpg -i out/master.wav -map 0:v -map 1:a \
  -c:v libx264 -preset slow -crf 17 -pix_fmt yuv420p -color_range tv -colorspace bt709 -color_primaries bt709 -color_trc bt709 \
  -c:a aac -b:a 192k -shortest -movflags +faststart -metadata title="$1" out/final_hq.mp4
ffmpeg -y -loglevel error -i out/final_hq.mp4 -c:v libx264 -preset slow -crf 23 -c:a copy -movflags +faststart out/lluvia_de_carne.mp4
echo "--- QA"
ffmpeg -hide_banner -i out/final_hq.mp4 -vf "freezedetect=n=0.001:d=0.4,blackdetect=d=0.1" -af ebur128 -f null - 2>&1 | grep -E "freeze_duration|black_start|^\s+I:|Peak:" | tail -6
ffprobe -v error -show_entries format=duration -of csv=p=0 out/final_hq.mp4
ffmpeg -y -loglevel error -i out/final_hq.mp4 -vf "fps=1/3,scale=180:-1,tile=10x2" -frames:v 1 out/qa_sheet.jpg
