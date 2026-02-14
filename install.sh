#!/usr/bin/env bash
# Telegram Bot 一键安装脚本（macOS / Linux）
# 用法：./install.sh

set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

echo "=== Telegram Bot 安装 ==="
echo ""

# 1. 检查 Python3 或 Node.js
echo "[1/6] 正在检查 Python3 / Node.js…"
if command -v python3 &>/dev/null; then
    echo "  ✓ 已找到 Python3: $(python3 --version)"
    USE_PYTHON=true
elif command -v node &>/dev/null; then
    echo "  ✓ 已找到 Node.js: $(node --version)"
    USE_PYTHON=false
else
    echo "  ✗ 未找到 Python3 或 Node.js，请先安装其一。"
    exit 1
fi
echo ""

# 2. 创建 Python 虚拟环境（若使用 Python）
if [ "$USE_PYTHON" = true ]; then
    echo "[2/6] 正在创建 Python 虚拟环境…"
    (cd bot && python3 -m venv venv)
    echo "  ✓ 虚拟环境已创建"
    echo ""
    echo "[3/6] 正在安装 Python 依赖…"
    (cd bot && ./venv/bin/pip install -q -r requirements.txt)
    echo "  ✓ Python 依赖已安装"
else
    echo "[2/6] 跳过 Python 虚拟环境（使用 Node.js）"
    echo "[3/6] 正在安装 Node 依赖…"
    (cd bot && npm install --silent)
    echo "  ✓ Node 依赖已安装"
fi
echo ""

# 4. 配置文件
echo "[4/6] 正在创建配置…"
if [ ! -f .env ]; then
    cp .env.example .env
    echo "  ✓ 已复制 .env.example → .env（请编辑 .env 填写 TELEGRAM_BOT_TOKEN）"
else
    echo "  - .env 已存在，跳过"
fi
if [ ! -f config/bot_config.json ]; then
    cp config/bot_config.example.json config/bot_config.json
    echo "  ✓ 已复制 config/bot_config.example.json → config/bot_config.json（请编辑并填写 allowed_user_ids 等）"
else
    echo "  - config/bot_config.json 已存在，跳过"
fi
echo ""

# 5. 目录
echo "[5/6] 正在创建 logs、data 目录…"
mkdir -p logs data
echo "  ✓ 完成"
echo ""

# 6. 可选 launchd
echo "[6/6] 是否安装 launchd 服务（macOS 开机自启）？[y/N]"
read -r INSTALL_LAUNCHD
if [[ "$INSTALL_LAUNCHD" =~ ^[yY] ]]; then
    PLIST_DEST="$HOME/Library/LaunchAgents/com.telegram.bot.plist"
    sed "s|REPO_ROOT|$REPO_ROOT|g" config/com.telegram.bot.plist > "$PLIST_DEST"
    echo "  ✓ 已安装 $PLIST_DEST（请执行 launchctl load $PLIST_DEST 并 launchctl start com.telegram.bot）"
else
    echo "  - 跳过 launchd"
fi
echo ""

echo "=== 安装完成 ==="
echo "请编辑 .env 填写 TELEGRAM_BOT_TOKEN，编辑 config/bot_config.json 填写 allowed_user_ids（你的 Telegram User ID）。"
echo "启动 Bot：./scripts/start-bot.sh"
echo ""
