#!/bin/bash

# Telegram Bot 安全测试脚本
# 用于在只有一个 Telegram 账号的情况下进行安全测试

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_FILE="$REPO_ROOT/config/bot_config.json"
BACKUP_FILE="$REPO_ROOT/config/bot_config.json.backup"

echo "=== Telegram Bot 安全测试 ==="
echo ""

# 备份配置文件
if [ ! -f "$BACKUP_FILE" ]; then
    cp "$CONFIG_FILE" "$BACKUP_FILE"
    echo "✅ 已备份配置文件"
fi

# 获取当前 User ID
CURRENT_USER_ID=$(python3 -c "import json; print(json.load(open('$CONFIG_FILE'))['allowed_user_ids'][0])" 2>/dev/null)
echo "当前 User ID: $CURRENT_USER_ID"
echo ""

echo "请选择测试场景："
echo "1. 测试未授权访问（临时移除白名单）"
echo "2. 测试速率限制（设置为每分钟1条）"
echo "3. 测试输入验证（危险字符）"
echo "4. 测试命令注入防护"
echo "5. 恢复原始配置"
echo "6. 查看当前配置"
echo ""
read -p "请选择 (1-6): " choice

case $choice in
    1)
        echo ""
        echo "=== 测试未授权访问 ==="
        echo "临时移除你的 User ID  from 白名单..."
        python3 << EOF
import json
config = json.load(open('$CONFIG_FILE'))
config['allowed_user_ids'] = []
json.dump(config, open('$CONFIG_FILE', 'w'), indent=2, ensure_ascii=False)
print("✅ 已移除白名单")
print("现在发送消息给 Bot，应该收到'❌ 未授权访问'")
EOF
        echo ""
        echo "⚠️  测试完成后，请选择选项 5 恢复配置"
        ;;
    2)
        echo ""
        echo "=== 测试速率限制 ==="
        echo "设置速率限制为每分钟1条消息..."
        python3 << EOF
import json
config = json.load(open('$CONFIG_FILE'))
config['rate_limit']['max_messages'] = 1
config['rate_limit']['window_seconds'] = 60
json.dump(config, open('$CONFIG_FILE', 'w'), indent=2, ensure_ascii=False)
print("✅ 速率限制已设置为每分钟1条")
print("现在快速发送2条消息，第二条应该收到'⚠️ 请求过于频繁'")
EOF
        echo ""
        echo "⚠️  测试完成后，请选择选项 5 恢复配置"
        ;;
    3)
        echo ""
        echo "=== 测试输入验证 ==="
        echo "请在 Telegram 中发送以下测试消息："
        echo ""
        echo "1. 测试危险字符:"
        echo "   ls; rm -rf /"
        echo ""
        echo "2. 测试命令注入:"
        echo "   test && echo hello"
        echo ""
        echo "3. 测试超长输入:"
        echo "   $(python3 -c "print('a' * 1001)")"
        echo ""
        echo "预期结果：应该收到'❌ 输入验证失败'"
        ;;
    4)
        echo ""
        echo "=== 测试命令注入防护 ==="
        echo "请在 Telegram 中发送以下测试消息："
        echo ""
        echo "1. rm -rf /tmp/test"
        echo "2. sudo ls"
        echo "3. chmod 777 /etc"
        echo ""
        echo "预期结果：应该收到'❌ 输入验证失败: 检测到潜在的危险命令'"
        ;;
    5)
        echo ""
        echo "=== 恢复原始配置 ==="
        if [ -f "$BACKUP_FILE" ]; then
            cp "$BACKUP_FILE" "$CONFIG_FILE"
            echo "✅ 配置已恢复"
        else
            echo "❌ 备份文件不存在"
        fi
        ;;
    6)
        echo ""
        echo "=== 当前配置 ==="
        cat "$CONFIG_FILE" | python3 -m json.tool
        ;;
    *)
        echo "无效选择"
        exit 1
        ;;
esac

echo ""
echo "提示：Bot 需要重启才能应用配置更改（除了输入验证测试）"
echo "重启命令：pkill -f telegram-bot.py && cd $REPO_ROOT/bot && source venv/bin/activate && nohup python3 telegram-bot.py > /tmp/telegram-bot-startup.log 2>&1 &"
