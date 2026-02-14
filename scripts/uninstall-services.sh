#!/bin/bash

# 卸载 launchd 服务的脚本

LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"

echo "Uninstalling Cursor CLI services..."

# 停止并卸载服务
echo "Stopping and unloading services..."

launchctl stop com.cursor.cli.daemon 2>/dev/null
launchctl unload "$LAUNCH_AGENTS_DIR/com.cursor.cli.daemon.plist" 2>/dev/null

launchctl stop com.cursor.monitor 2>/dev/null
launchctl unload "$LAUNCH_AGENTS_DIR/com.cursor.monitor.plist" 2>/dev/null

# 删除 plist 文件
echo "Removing plist files..."
rm -f "$LAUNCH_AGENTS_DIR/com.cursor.cli.daemon.plist"
rm -f "$LAUNCH_AGENTS_DIR/com.cursor.monitor.plist"

echo "Services uninstalled successfully!"
