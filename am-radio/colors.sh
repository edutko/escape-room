#!/usr/bin/env zsh

say -v Zarvox "blue. white. green. red. yellow." -o colors.aiff && \
ffmpeg -i colors.aiff -af "apad=pad_dur=1" -codec:a libmp3lame colors.mp3 && \
rm -f colors.aiff
