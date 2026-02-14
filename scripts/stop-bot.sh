#!/bin/bash

# Telegram Bot 停止脚本

# 查找并结束 Bot 进程（优先 Python，再 Node）
stopped=0

if ps aux | grep -E "[t]elegram-bot\.py" >/dev/null 2>&1; then
    echo "Stopping Python Bot..."
    pkill -f "telegram-bot\.py" 2>/dev/null && stopped=1
fi

if ps aux | grep -E "[t]elegram-bot\.js" >/dev/null 2>&1; then
    echo "Stopping Node.js Bot..."
    pkill -f "telegram-bot\.js" 2>/dev/null && stopped=1
fi

if [ "$stopped" = 1 ]; then
    echo "Bot stopped."
else
    echo "Bot is not running."
fi
