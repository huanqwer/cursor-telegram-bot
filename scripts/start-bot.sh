#!/bin/bash

# Telegram Bot 启动脚本（默认加代理，一键启动）

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOT_DIR="$SCRIPT_DIR/../bot"
USE_PROXY=true
PROXY_URL="${PROXY_URL:-http://127.0.0.1:7890}"
RUN_BACKGROUND=false

# 解析参数
for arg in "$@"; do
    case "$arg" in
        --no-proxy)   USE_PROXY=false ;;
        --background|-b) RUN_BACKGROUND=true ;;
        --help|-h)
            echo "Usage: $0 [--no-proxy] [--background|-b]"
            echo "  --no-proxy    不设置代理（默认会设置 HTTP_PROXY/HTTPS_PROXY）"
            echo "  --background  后台运行（nohup），日志输出到 /tmp/telegram-bot-startup.log"
            echo "  --help        显示此帮助"
            exit 0
            ;;
    esac
done

cd "$BOT_DIR" || exit 1

# 默认加代理（访问 Telegram API）
if [ "$USE_PROXY" = true ]; then
    export HTTP_PROXY="${HTTP_PROXY:-$PROXY_URL}"
    export HTTPS_PROXY="${HTTPS_PROXY:-$PROXY_URL}"
    echo "Using proxy: $HTTP_PROXY"
fi

_run_bot() {
    if [ -d "venv" ] && command -v python3 &> /dev/null; then
        echo "Starting Bot with Python (virtual environment)..."
        source venv/bin/activate
        exec python3 telegram-bot.py
    elif command -v python3 &> /dev/null; then
        echo "Starting Bot with Python..."
        exec python3 telegram-bot.py
    elif command -v node &> /dev/null; then
        echo "Starting Bot with Node.js..."
        exec node telegram-bot.js
    else
        echo "Error: Neither Python3 nor Node.js found"
        exit 1
    fi
}

if [ "$RUN_BACKGROUND" = true ]; then
    echo "Starting Bot in background (nohup)..."
    nohup env \
        USE_PROXY="$USE_PROXY" \
        PROXY_URL="$PROXY_URL" \
        HTTP_PROXY="${HTTP_PROXY:-$PROXY_URL}" \
        HTTPS_PROXY="${HTTPS_PROXY:-$PROXY_URL}" \
        bash -c 'cd "$0" && if [ "$1" = true ]; then export HTTP_PROXY="$2" HTTPS_PROXY="$2"; fi && if [ -d venv ]; then . venv/bin/activate; fi && exec python3 telegram-bot.py' \
        "$BOT_DIR" "$USE_PROXY" "$PROXY_URL" >> /tmp/telegram-bot-startup.log 2>&1 &
    echo "PID: $!"
    echo "Log: tail -f /tmp/telegram-bot-startup.log"
else
    _run_bot
fi
