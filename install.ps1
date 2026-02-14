# Telegram Bot 一键安装脚本（Windows PowerShell）
# 用法：.\install.ps1

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RepoRoot

Write-Host "=== Telegram Bot 安装 ===" -ForegroundColor Cyan
Write-Host ""

# 1. 检查 Python 或 Node.js
Write-Host "[1/6] 正在检查 Python / Node.js…" -ForegroundColor Yellow
$UsePython = $false
try {
    $py = Get-Command python -ErrorAction SilentlyContinue
    if ($py) {
        Write-Host "  ✓ 已找到 Python: $($py.Source)" -ForegroundColor Green
        $UsePython = $true
    }
} catch {}
if (-not $UsePython) {
    try {
        $node = Get-Command node -ErrorAction SilentlyContinue
        if ($node) {
            Write-Host "  ✓ 已找到 Node.js: $($node.Source)" -ForegroundColor Green
        } else { throw "Not found" }
    } catch {
        Write-Host "  ✗ 未找到 Python 或 Node.js，请先安装其一。" -ForegroundColor Red
        exit 1
    }
}
Write-Host ""

# 2. 创建虚拟环境（Python）
if ($UsePython) {
    Write-Host "[2/6] 正在创建 Python 虚拟环境…" -ForegroundColor Yellow
    Push-Location bot
    python -m venv venv
    Pop-Location
    Write-Host "  ✓ 虚拟环境已创建" -ForegroundColor Green
    Write-Host ""
    Write-Host "[3/6] 正在安装 Python 依赖…" -ForegroundColor Yellow
    & "$RepoRoot\bot\venv\Scripts\pip.exe" install -q -r "$RepoRoot\bot\requirements.txt"
    Write-Host "  ✓ Python 依赖已安装" -ForegroundColor Green
} else {
    Write-Host "[2/6] 跳过 Python 虚拟环境" -ForegroundColor Gray
    Write-Host "[3/6] 正在安装 Node 依赖…" -ForegroundColor Yellow
    Push-Location bot
    npm install --silent
    Pop-Location
    Write-Host "  ✓ Node 依赖已安装" -ForegroundColor Green
}
Write-Host ""

# 4. 配置文件
Write-Host "[4/6] 正在创建配置…" -ForegroundColor Yellow
if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "  ✓ 已复制 .env.example → .env（请编辑 .env 填写 TELEGRAM_BOT_TOKEN）" -ForegroundColor Green
} else {
    Write-Host "  - .env 已存在，跳过" -ForegroundColor Gray
}
if (-not (Test-Path config\bot_config.json)) {
    Copy-Item config\bot_config.example.json config\bot_config.json
    Write-Host "  ✓ 已复制 bot_config.example.json → bot_config.json（请编辑并填写 allowed_user_ids）" -ForegroundColor Green
} else {
    Write-Host "  - config\bot_config.json 已存在，跳过" -ForegroundColor Gray
}
Write-Host ""

# 5. 目录
Write-Host "[5/6] 正在创建 logs、data 目录…" -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path logs, data | Out-Null
Write-Host "  ✓ 完成" -ForegroundColor Green
Write-Host ""

Write-Host "[6/6] 跳过 launchd（仅 macOS）" -ForegroundColor Gray
Write-Host ""

Write-Host "=== 安装完成 ===" -ForegroundColor Cyan
Write-Host "请编辑 .env 填写 TELEGRAM_BOT_TOKEN，编辑 config\bot_config.json 填写 allowed_user_ids。"
Write-Host "启动 Bot：在 bot 目录下执行 .\venv\Scripts\python.exe telegram-bot.py（或 node telegram-bot.js）"
Write-Host ""
