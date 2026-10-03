#!/usr/bin/env bash

if [ -z "$1" ]; then
  echo "" 2>&1
  exit 1
fi

in="$1"
out_dir="$(dirname "$1")"
out="$(basename "$1" .mp3).wav"

if [ -d "/var/lib/asterisk/sounds/custom" ]; then
  out_dir="/var/lib/asterisk/sounds/custom"
fi

ffmpeg -i "$in" -ar 8000 -ac 1 "$out_dir"/"$out"

if [ "$out_dir" == "/var/lib/asterisk/sounds/custom" ]; then
  sudo chown asterisk: "$out_dir"/"$out"
  sudo chmod 0664 "$out_dir"/"$out"
fi
