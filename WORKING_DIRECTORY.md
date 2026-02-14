# Cursor CLI 工作目录切换指南

## 概述

Cursor CLI 的工作目录决定了命令在哪个项目路径下执行。Telegram Bot 支持通过多种方式切换工作目录。

## 切换方式

### 方式 1: 在消息中指定项目路径（推荐）

在发送任务消息时，使用 `--project` 参数指定项目路径：

```
--project /path/to/your/project 添加新功能
```

或者使用简写：

```
--project my-todo 添加新功能
```

**注意**：如果使用项目名称（如 `my-todo`），Bot 会在 `bot_config.json` 的 `allowed_projects` 中查找对应的完整路径。

### 方式 2: 修改配置文件

编辑 `config/bot_config.json`，在 `allowed_projects` 中添加或修改项目路径：

```json
{
  "allowed_projects": {
    "my-project": "/path/to/your/my-project",
    "other-project": "/path/to/your/other-project"
  }
}
```

然后在消息中使用项目名称：

```
--project other-project 执行任务
```

### 方式 3: 修改默认项目路径

在 `.env` 中设置 `DEFAULT_PROJECT_ROOT=/path/to/your/project`，或在 `config/bot_config.json` 中设置 `default_project_root` 字段。未设置时默认工作目录为空（使用当前目录或需通过 `--project` / 触发词指定）。

## 代码实现

工作目录的切换在 `execute_cursor_cli` 函数中通过 `subprocess.Popen` 的 `cwd` 参数实现：

```python
process = subprocess.Popen(
    cmd,
    cwd=project_path,  # 这里设置工作目录
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    env=env,
    bufsize=1
)
```

`project_path` 的值来自 `parse_task_message` 函数的解析结果。

## 解析逻辑

`parse_task_message` 函数按以下顺序确定项目路径：

1. **检查消息中的 `--project` 参数**
   - 如果找到，使用指定的路径
   - 如果路径是项目名称，在 `allowed_projects` 中查找完整路径

2. **使用默认路径**
   - 如果没有指定 `--project`，使用环境变量 `DEFAULT_PROJECT_ROOT` 或 config 中的 `default_project_root`

## 示例

### 示例 1: 使用完整路径

```
--project /path/to/your/project 添加用户登录功能
```

### 示例 2: 使用项目名称

```
--project my-todo 修复bug
```

### 示例 3: 不指定项目（使用默认）

```
添加新功能
```

## 安全考虑

1. **路径验证**：Bot 会验证项目路径是否在 `allowed_projects` 白名单中
2. **路径规范化**：建议使用绝对路径，避免相对路径带来的安全问题
3. **权限检查**：确保 Bot 进程有权限访问指定的项目目录

## 常见问题

### Q: 如何添加新项目到白名单？

A: 编辑 `config/bot_config.json`，在 `allowed_projects` 中添加新项目：

```json
{
  "allowed_projects": {
    "my-project": "/path/to/your/my-project",
    "new-project": "/path/to/your/new-project"
  }
}
```

### Q: 可以使用相对路径吗？

A: 不建议。使用绝对路径更安全可靠。如果必须使用相对路径，确保路径相对于 Bot 的工作目录。

### Q: 工作目录切换后需要重启 Bot 吗？

A: 不需要。工作目录在每次任务执行时动态设置，无需重启 Bot。

### Q: 如何查看当前使用的项目路径？

A: 查看 Bot 日志文件 `logs/telegram-bot.log`，每次执行任务时会记录工作目录。

## 相关文件

- `bot/telegram-bot.py`: Bot 主程序，包含工作目录切换逻辑
- `config/bot_config.json`: 配置文件，包含允许的项目路径列表
- `WORKING_DIRECTORY.md`: 本文档
