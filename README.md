# Cursor Telegram Bot

**通过 Telegram 远程控制 Cursor CLI，实现远程 AI 编程与手机遥控编程。**

- 开源地址：**[https://github.com/huanqwer/cursor-telegram-bot](https://github.com/huanqwer/cursor-telegram-bot)**
- 功能：在 Telegram 中发送任务描述，Bot 调用本机 Cursor CLI（`agent`）执行，并返回结果；支持触发词切换项目、会话记忆、长任务进度推送、代理、白名单与速率限制。

适用于：**远程 Cursor CLI**、**Telegram Bot Cursor 编程**、**遥控编程**、**手机控制 AI 编程**、remote cursor cli、telegram cursor programming、remote AI coding。

## 快速开始

1. **克隆仓库**
   ```bash
   git clone https://github.com/huanqwer/cursor-telegram-bot.git
   cd cursor-telegram-bot
   ```

2. **一键安装**
   - **macOS / Linux**：`./install.sh`
   - **Windows**：`.\install.ps1`

3. **配置**：编辑 `.env` 填写 `TELEGRAM_BOT_TOKEN`，编辑 `config/bot_config.json` 填写 `allowed_user_ids`（你的 Telegram User ID）。详见下方配置说明。

4. **启动**：`./scripts/start-bot.sh`（Mac/Linux）或在 `bot` 目录下运行 `python3 telegram-bot.py` / `node telegram-bot.js`。

## 目录结构

```
telegram-bot/
├── bot/                    # Telegram Bot 代码
│   ├── telegram-bot.py    # Python 版本
│   ├── telegram-bot.js    # Node.js 版本
│   ├── requirements.txt   # Python 依赖
│   ├── package.json       # Node.js 依赖
│   └── venv/              # Python 虚拟环境（如果使用）
├── skills/                 # 核心组件
│   ├── cursor-task-handler.js
│   ├── cursor-cli-executor.js
│   └── cursor-status-monitor.js
├── services/              # 守护进程服务（可选）
│   └── cursor-cli-daemon.js
├── scripts/               # 工具脚本
│   ├── monitor-services.sh
│   ├── install-services.sh
│   └── start-bot.sh
├── config/                # 配置文件
│   ├── bot_config.json    # Bot 配置（用户白名单等）
│   ├── cursor-projects.json
│   └── com.telegram.bot.plist  # launchd 配置（可选）
├── tasks/                 # 任务队列（如果使用守护进程）
│   └── queue.json
└── logs/                  # 日志文件
    └── (自动生成)
```

## 启动 Bot（安装与配置完成后）

**Python 版本**：
```bash
cd bot
source venv/bin/activate  # 如果使用虚拟环境
python3 telegram-bot.py
```

**Node.js 版本**：
```bash
cd bot
node telegram-bot.js
```

**或使用启动脚本**：
```bash
./scripts/start-bot.sh
```

### 在 Telegram 中使用

1. 在 Telegram 中找到你的 Bot
2. 发送任务消息，例如：
   - "列出项目根目录的文件"
   - "创建一个新函数 --model opus-4.6-thinking"
   - "分析代码结构 --project /path/to/project"

### 查看日志

```bash
tail -f logs/telegram-bot.log
```

## 配置

### 环境变量（`.env` 文件）

复制 `.env.example` 为 `.env` 并填写，切勿将 `.env` 提交到版本控制。包含：
- `TELEGRAM_BOT_TOKEN`: Bot Token（必填）
- `USE_PROXY`: 是否使用代理（默认 `true`）
- `PROXY_URL`: 代理地址（默认 `http://127.0.0.1:7890`）
- `DEFAULT_PROJECT_ROOT`: 默认项目路径（可选）
- `CURSOR_AGENT_PATH`: Cursor CLI 可执行路径（可选，默认 `agent`）

### Bot 配置（`config/bot_config.json`）

复制 `config/bot_config.example.json` 为 `config/bot_config.json` 并填写。包含：
- `allowed_user_ids`: 允许使用的 Telegram User ID 列表
- `rate_limit`: 速率限制配置
- `allowed_projects`: 项目名称到路径的映射
- `project_trigger_mapping`: 触发词到项目的映射（可选）
- `default_project_root`: 默认项目路径（可选）

## 代理配置

**默认启用代理**（使用 Clash: `http://127.0.0.1:7890`）

如果不需要代理，在 `.env` 文件中设置：
```
USE_PROXY=false
```

## 任务格式

- **基本格式**：`任务描述`
- **指定模型**：`任务描述 --model opus-4.6-thinking`
- **指定项目**：`任务描述 --project /path/to/project`

## 配置后台运行（可选）

### 使用 launchd（macOS）

```bash
# 复制 plist 文件（需先用 install 脚本将 REPO_ROOT 替换为实际安装路径）
cp config/com.telegram.bot.plist ~/Library/LaunchAgents/

# 加载服务
launchctl load ~/Library/LaunchAgents/com.telegram.bot.plist

# 启动服务
launchctl start com.telegram.bot
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

## 日志

- Bot 日志：`logs/telegram-bot.log`
- 标准输出：`logs/telegram-bot.out.log`
- 错误输出：`logs/telegram-bot.err.log`

## 故障排查

### Bot 无响应

- 检查 Token 是否正确：确认 `.env` 中已填写 `TELEGRAM_BOT_TOKEN`
- 检查网络连接
- 查看日志：`tail -f logs/telegram-bot.log`

### 提示"未授权访问"

- 检查 `bot_config.json` 中的 `allowed_user_ids` 是否包含你的 User ID
- 确认 User ID 是数字格式

### 任务执行失败

- 检查 Cursor CLI 是否正常：`agent --version`
- 检查代理配置：`lsof -i :7890`
- 查看日志文件中的错误信息

### 代理连接失败

- 确认 Clash 代理正在运行：`lsof -i :7890`
- 如果不需要代理，设置 `USE_PROXY=false`
- 测试代理连接：`curl -x http://127.0.0.1:7890 https://api.telegram.org`

## 安全措施

- ✅ 用户白名单验证
- ✅ 输入验证和清理
- ✅ 命令注入防护
- ✅ Bot Token 保护（环境变量）
- ✅ 速率限制（默认每分钟5条消息）
- ✅ 敏感信息过滤
- ✅ 超时控制（5分钟）
- ✅ 日志记录

## 发布前检查（维护者）

推送或公开发布前，建议使用**另一款 AI**（不同模型/产品）对仓库做一次交叉检查：请其全文搜索可能的敏感信息（如 Telegram Bot Token、User ID、个人绝对路径），根据反馈再排查，确认无遗漏后再推送。

## License

Apache-2.0. 反馈与贡献欢迎提交至 [GitHub](https://github.com/huanqwer/cursor-telegram-bot)。
