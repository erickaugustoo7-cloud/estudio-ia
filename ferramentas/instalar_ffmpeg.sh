#!/usr/bin/env bash
# Instala ffmpeg/ffprobe no runner sem depender só do apt (os espelhos do Ubuntu às vezes travam ou falham).
set -u
if command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null; then echo "ffmpeg já disponível"; exit 0; fi
for t in 1 2; do
  if timeout 240 sudo apt-get update -q && timeout 300 sudo apt-get install -y -q ffmpeg; then echo "ffmpeg via apt"; exit 0; fi
  echo "apt falhou (tentativa $t)"; sleep 10
done
echo "usando build estático"
mkdir -p /tmp/ffs && cd /tmp/ffs
curl -fsSL --retry 3 -o ff.tar.xz https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz
tar -xf ff.tar.xz --strip-components=1
sudo cp ffmpeg ffprobe /usr/local/bin/
ffmpeg -version | head -1
