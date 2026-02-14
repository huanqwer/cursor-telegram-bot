#!/bin/bash

# 服务监控脚本
# 检查 Cursor CLI Daemon 的运行状态

# 获取脚本所在目录的父目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_FILE="$PROJECT_ROOT/telegram-bot/logs/monitor.log"
CURSOR_SERVICE="com.cursor.cli.daemon"

# 确保日志目录存在
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

check_service() {
    local service=$1
    if launchctl list | grep -q "$service"; then
        local status=$(launchctl list | grep "$service" | awk '{print $1}')
        if [ "$status" != "0" ]; then
            log "WARNING: Service $service is not running properly (status: $status)"
            return 1
        else
            log "OK: Service $service is running"
            return 0
        fi
    else
        log "ERROR: Service $service is not loaded"
        return 1
    fi
}

# 检查 Cursor CLI Daemon
if ! check_service "$CURSOR_SERVICE"; then
    log "Attempting to restart Cursor CLI Daemon..."
    launchctl start "$CURSOR_SERVICE"
fi

log "Health check completed"
