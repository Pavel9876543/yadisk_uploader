#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -x ".venv/bin/python" ]; then
  echo "Не найдено окружение .venv."
  echo "Создайте его командой: /usr/bin/python3 -m venv --system-site-packages .venv"
  exit 1
fi

if [ -z "${QT_QPA_PLATFORM:-}" ]; then
  if [ -n "${WAYLAND_DISPLAY:-}" ] && [ -z "${DISPLAY:-}" ]; then
    export QT_QPA_PLATFORM=wayland
  else
    export QT_QPA_PLATFORM=xcb
  fi
fi

if [ "${QT_QPA_PLATFORM}" != "offscreen" ] \
  && [ -z "${DISPLAY:-}" ] \
  && [ -z "${WAYLAND_DISPLAY:-}" ]; then
  echo "Не найден графический дисплей."
  echo "Для Termux:X11 запустите X-сервер и выполните: export DISPLAY=:0"
  exit 1
fi

exec .venv/bin/python app/main.py
