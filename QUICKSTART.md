# Telegram Bot 快速开始

## 前提条件

- ✅ Telegram Bot 已创建：在 [@BotFather](https://t.me/BotFather) 创建 Bot，将获得的 **Token** 填入 `.env` 的 `TELEGRAM_BOT_TOKEN`
- ✅ Telegram User ID 已获取：通过 [@userinfobot](https://t.me/userinfobot) 等获取你的 **User ID**，填入 `config/bot_config.json` 的 `allowed_user_ids`
- ✅ 已运行一键安装脚本（或手动复制 `.env.example` → `.env`、`config/bot_config.example.json` → `config/bot_config.json` 并编辑）

## 启动 Bot

### 方法 1: Python 版本（推荐）

```bash
cd bot   # 进入项目目录下的 bot 目录

# 如果使用虚拟环境
source venv/bin/activate

# 启动 Bot
python3 telegram-bot.py
```

### 方法 2: Node.js 版本

```bash
cd bot
node telegram-bot.js
```

### 方法 3: 使用启动脚本

```bash
./scripts/start-bot.sh
```

## 测试 Bot

1. 在 Telegram 中找到你的 Bot
2. 发送 `/start` 或任意消息
3. Bot 应该回复"⏳ 正在执行任务..."然后返回结果

**示例消息**：
- "列出项目根目录的文件"
- "创建一个新函数 --model opus-4.6-thinking"
- "分析代码结构 --project /path/to/project"

## 查看日志

```bash
# Bot 日志（在项目根目录下执行）
tail -f logs/telegram-bot.log

# 标准输出
tail -f logs/telegram-bot.out.log

# 错误输出
tail -f logs/telegram-bot.err.log
```

## 配置后台运行（可选）

### 使用 launchd（macOS）

```bash
# 复制 plist 文件（需先用 install.sh 或手动替换 plist 中的 REPO_ROOT 为实际安装路径）
cp config/com.telegram.bot.plist ~/Library/LaunchAgents/

# 加载服务
launchctl load ~/Library/LaunchAgents/com.telegram.bot.plist

# 启动服务
launchctl start com.telegram.bot

# 检查状态
launchctl list | grep com.telegram.bot
```

### 使用 PM2（Node.js）

```bash
npm install -g pm2
cd bot
pm2 start telegram-bot.js --name telegram-bot
pm2 save
pm2 startup
```

### 使用 screen

```bash
screen -S telegram-bot
cd bot
python3 telegram-bot.py
# 按 Ctrl+A 然后 D 退出 screen
```

## 停止 Bot

### 前台运行
- 按 `Ctrl+C`

### launchd 服务
```bash
launchctl stop com.telegram.bot
launchctl unload ~/Library/LaunchAgents/com.telegram.bot.plist
```

### PM2
```bash
pm2 stop telegram-bot
pm2 delete telegram-bot
```

## 检查系统状态

```bash
./check-status.sh
```

## 常见问题

### Bot 无法启动

1. 检查依赖是否安装：
   - Python: `pip3 list | grep python-telegram-bot`
   - Node.js: `npm list telegraf`

2. 检查 Token 是否正确：确认 `.env` 中已填写 `TELEGRAM_BOT_TOKEN`

3. 检查日志文件中的错误信息

### Bot 无响应

1. 检查 Clash 代理是否运行：`lsof -i :7890`
2. 如果不需要代理，设置 `USE_PROXY=false` 在 `.env` 文件中
3. 查看日志：`tail -f logs/telegram-bot.log`

### 提示"未授权访问"

- 检查 `bot_config.json` 中的 `allowed_user_ids` 是否包含你的 Telegram User ID（数字格式）
