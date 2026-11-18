#!/usr/bin/env bash
# Instala ffmpeg/ffprobe no runner: build estático primeiro (rápido e não depende dos espelhos do Ubuntu), apt como reserva.
set -u
if command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null; then echo "ffmpeg já disponível"; exit 0; fi
mkdir -p /tmp/ffs && cd /tmp/ffs
if curl -fsSL --retry 3 --max-time 180 -o ff.tar.xz https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz \
   && tar -xf ff.tar.xz --strip-components=1 && sudo cp ffmpeg ffprobe /usr/local/bin/; then
  ffmpeg -version | head -1; exit 0
fi
echo "build estático falhou — tentando apt"
for t in 1 2; do
  if timeout 240 sudo apt-get update -q && timeout 300 sudo apt-get install -y -q ffmpeg; then echo "ffmpeg via apt"; exit 0; fi
  echo "apt falhou (tentativa $t)"; sleep 10
done
exit 1
