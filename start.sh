#!/bin/sh
# Запуск из любого текущего каталога. Установка: sh start.sh
set -eu
cd "$(dirname "$0")"
if command -v python3 >/dev/null 2>&1; then
    exec python3 start.py "$@"
elif command -v python3.12 >/dev/null 2>&1; then
    exec python3.12 start.py "$@"
else
    echo 'Python не найден. Установите Python 3.12.' >&2
    exit 1
fi
