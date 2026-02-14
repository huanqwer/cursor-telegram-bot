#!/bin/bash

# 安装 launchd 服务的脚本

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"

echo "Installing Cursor CLI services..."

# 创建 LaunchAgents 目录（如果不存在）
mkdir -p "$LAUNCH_AGENTS_DIR"

# 安装守护进程服务
echo "Installing Cursor CLI Daemon..."
cp "$PROJECT_ROOT/telegram-bot/config/com.cursor.cli.daemon.plist" \
   "$LAUNCH_AGENTS_DIR/com.cursor.cli.daemon.plist"

# 加载服务
echo "Loading services..."
launchctl load "$LAUNCH_AGENTS_DIR/com.cursor.cli.daemon.plist" 2>/dev/null || \
launchctl load -w "$LAUNCH_AGENTS_DIR/com.cursor.cli.daemon.plist"

echo "Services installed successfully!"
echo ""
echo "To start services:"
echo "  launchctl start com.cursor.cli.daemon"
echo ""
echo "To check status:"
echo "  launchctl list | grep com.cursor"
echo ""
echo "To view logs:"
echo "  tail -f $PROJECT_ROOT/telegram-bot/logs/cursor-daemon.log"
