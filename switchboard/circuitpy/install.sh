#!/usr/bin/env bash

CIRCUITPY_DIR=/Volumes/CIRCUITPY

if ! [[ -d "$CIRCUITPY_DIR" ]]
then
  echo "error: CIRCUITPY volume is not mounted" >&2
  exit 1
fi

copy_if_changed() {
  src="$1"
  dst_dir="$2"
  if [[ -z "$dst_dir" ]]; then
    dst="$CIRCUITPY_DIR/$(basename "$1")"
  else
    dst="$CIRCUITPY_DIR/$dst_dir/$(basename "$1")"
  fi

  if ! [[ -f "$dst" ]]; then
    echo "Creating \"$dst\" ..."
    cp "$src" "$dst"
  elif ! diff --brief "$src" "$dst" >/dev/null; then
    echo "Updating \"$dst\" ..."
    cp "$src" "$dst"
  fi
}

copy_if_changed "code.py"
