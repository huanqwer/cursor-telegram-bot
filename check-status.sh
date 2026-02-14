#!/bin/bash
# 检查系统状态脚本

echo "=== Telegram Bot 系统状态检查 ==="
echo ""

echo "1. Cursor CLI:"
if command -v agent &> /dev/null; then
    echo "   ✅ 已安装: $(agent --version)"
else
    echo "   ❌ 未安装"
fi

echo ""
echo "2. Launchd 服务:"
if launchctl list | grep -q "com.cursor.cli.daemon"; then
    echo "   ✅ Cursor CLI Daemon: 运行中"
else
    echo "   ❌ Cursor CLI Daemon: 未运行"
fi

echo ""
echo "3. 代理配置:"
if lsof -i :7890 &> /dev/null; then
    echo "   ✅ Clash 代理运行在端口 7890"
else
    echo "   ⚠️  Clash 代理未检测到（端口 7890）"
fi

echo ""
echo "4. 日志文件:"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." 2>/dev/null && pwd)"
LOG_DAEMON="${REPO_ROOT:-.}/logs/cursor-daemon.log"
if [ -f "$LOG_DAEMON" ]; then
    echo "   ✅ 守护进程日志存在"
    echo "   最近日志:"
    tail -3 "$LOG_DAEMON" 2>/dev/null | sed 's/^/      /'
else
    echo "   ⚠️  守护进程日志不存在（服务可能未运行）"
fi

echo ""
echo "=== 检查完成 ==="
