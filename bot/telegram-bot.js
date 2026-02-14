#!/usr/bin/env node
/**
 * 安全的 Telegram Bot - Cursor CLI 远程控制
 * 包含完整安全措施：用户认证、输入验证、命令注入防护、代理配置等
 */

const { Telegraf } = require('telegraf');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
require('dotenv').config();

const BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
const USE_PROXY = process.env.USE_PROXY !== 'false';
const PROXY_URL = process.env.PROXY_URL || 'http://127.0.0.1:7890';
const CONFIG_FILE = path.join(__dirname, '../config/bot_config.json');
const LOG_FILE = path.join(__dirname, '../logs/telegram-bot.log');

function loadConfigSync() {
    if (fs.existsSync(CONFIG_FILE)) {
        try {
            return JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8'));
        } catch (e) {}
    }
    return { allowed_user_ids: [], admin_user_id: null };
}
const _config = loadConfigSync();
const PROJECT_ROOT = (process.env.DEFAULT_PROJECT_ROOT || _config.default_project_root || '').trim();
const AGENT_PATH = (process.env.CURSOR_AGENT_PATH || _config.cursor_agent_path || 'agent').trim() || 'agent';

// 速率限制
const rateLimit = new Map();
const RATE_LIMIT = { maxMessages: 5, windowMs: 60000 };

// 日志函数
function log(message) {
    const timestamp = new Date().toISOString();
    const logMessage = `[${timestamp}] ${message}\n`;
    fs.appendFileSync(LOG_FILE, logMessage);
    console.log(logMessage.trim());
}

function loadConfig() {
    if (fs.existsSync(CONFIG_FILE)) {
        return JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8'));
    }
    return { allowed_user_ids: [], admin_user_id: null };
}

function isUserAllowed(userId) {
    const config = loadConfig();
    return config.allowed_user_ids.includes(userId);
}

function checkRateLimit(userId) {
    const now = Date.now();
    const userTimes = rateLimit.get(userId) || [];
    
    // 清理过期记录
    const validTimes = userTimes.filter(t => now - t < RATE_LIMIT.windowMs);
    
    if (validTimes.length >= RATE_LIMIT.maxMessages) {
        return false;
    }
    
    validTimes.push(now);
    rateLimit.set(userId, validTimes);
    return true;
}

function validateTaskInput(input) {
    if (input.length > 1000) {
        throw new Error('输入过长（最大 1000 字符）');
    }
    
    const dangerousChars = [';', '&', '|', '`', '$', '<', '>'];
    for (const char of dangerousChars) {
        if (input.includes(char)) {
            throw new Error(`禁止使用字符: ${char}`);
        }
    }
    
    const injectionPatterns = [
        /rm\s+-rf/i,
        /sudo\s+/i,
        /chmod\s+777/i,
        />\s+\/dev\//i,
        /curl\s+.*\|/i,
        /wget\s+.*\|/i
    ];
    
    for (const pattern of injectionPatterns) {
        if (pattern.test(input)) {
            throw new Error('检测到潜在的危险命令');
        }
    }
    
    return input.trim();
}

function filterSensitiveInfo(text) {
    return text.replace(/sk-[A-Za-z0-9]{32,}/g, '[API_KEY_FILTERED]');
}

function parseTaskMessage(message) {
    const task = {
        description: '',
        projectPath: PROJECT_ROOT,
        model: 'auto'
    };
    
    // 提取项目路径
    const projectMatch = message.match(/--project[:\s]+([^\s]+)/i);
    if (projectMatch) {
        task.projectPath = projectMatch[1];
    }
    
    // 提取模型
    const modelMatch = message.match(/--model[:\s]+([^\s]+)/i);
    if (modelMatch) {
        task.model = modelMatch[1];
    }
    
    // 提取任务描述（移除参数部分）
    let description = message
        .replace(/--project[:\s]+[^\s]+/gi, '')
        .replace(/--model[:\s]+[^\s]+/gi, '')
        .replace(/^(执行任务|任务|do|run)[：:]\s*/i, '')
        .trim();
    
    task.description = description || message;
    
    return task;
}

function executeCursorCLI(taskDescription, projectPath, model) {
    return new Promise((resolve, reject) => {
        try {
            const validatedTask = validateTaskInput(taskDescription);
            
            log(`Executing task: ${validatedTask.substring(0, 100)}`);
            
            const cmd = spawn(AGENT_PATH, [
                '--model', model,
                '-p',
                '--force',
                '--output-format', 'json',
                validatedTask
            ], {
                cwd: projectPath || undefined,
                env: {
                    ...process.env,
                    HTTP_PROXY: process.env.HTTP_PROXY || 'http://127.0.0.1:7890',
                    HTTPS_PROXY: process.env.HTTPS_PROXY || 'http://127.0.0.1:7890',
                    NO_PROXY: 'localhost,127.0.0.1'
                }
            });
            
            let stdout = '';
            let stderr = '';
            
            cmd.stdout.on('data', (data) => {
                stdout += data.toString();
            });
            
            cmd.stderr.on('data', (data) => {
                stderr += data.toString();
            });
            
            cmd.on('close', (code) => {
                log(`Task completed with code ${code}`);
                resolve({
                    success: code === 0,
                    output: filterSensitiveInfo(stdout),
                    error: filterSensitiveInfo(stderr),
                    code: code
                });
            });
            
            cmd.on('error', (error) => {
                log(`Process error: ${error.message}`);
                reject(error);
            });
            
            // 5分钟超时
            setTimeout(() => {
                cmd.kill();
                reject(new Error('任务执行超时（5分钟）'));
            }, 300000);
            
        } catch (error) {
            reject(error);
        }
    });
}

// 创建 Bot 实例
const botOptions = {};
if (USE_PROXY) {
    botOptions.telegram = {
        agent: require('https').globalAgent,
        webhookReply: false
    };
    log(`Using proxy: ${PROXY_URL}`);
} else {
    log('Proxy disabled');
}

const bot = new Telegraf(BOT_TOKEN, botOptions);

bot.on('text', async (ctx) => {
    const userId = ctx.from.id;
    const username = ctx.from.username || 'unknown';
    const messageText = ctx.message.text;
    
    // 用户认证
    if (!isUserAllowed(userId)) {
        log(`Unauthorized access from user ${userId}`);
        return ctx.reply('❌ 未授权访问');
    }
    
    // 速率限制
    if (!checkRateLimit(userId)) {
        return ctx.reply('⚠️ 请求过于频繁，请稍后再试');
    }
    
    // 解析任务
    let task;
    try {
        task = parseTaskMessage(messageText);
    } catch (error) {
        return ctx.reply(`❌ 解析任务失败: ${error.message}`);
    }
    
    // 执行任务
    try {
        await ctx.reply('⏳ 正在执行任务...');
        
        const result = await executeCursorCLI(
            task.description,
            task.projectPath,
            task.model
        );
        
        const response = result.success
            ? `✅ 任务完成\n\n${result.output.substring(0, 3500)}`
            : `❌ 任务失败 (code: ${result.code})\n\n${result.error.substring(0, 3500)}`;
        
        await ctx.reply(response);
        
    } catch (error) {
        await ctx.reply(`❌ 错误: ${error.message}`);
        log(`Error: ${error.message}`);
    }
});

// 启动 Bot
bot.launch().then(() => {
    log('Bot started');
}).catch((error) => {
    log(`Bot startup error: ${error.message}`);
    process.exit(1);
});

// 优雅关闭
process.once('SIGINT', () => bot.stop('SIGINT'));
process.once('SIGTERM', () => bot.stop('SIGTERM'));
