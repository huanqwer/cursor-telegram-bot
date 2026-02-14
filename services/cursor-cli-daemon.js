#!/usr/bin/env node
// Cursor CLI 任务守护进程
// 监听任务队列，执行 Cursor CLI 命令，发送通知

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

class CursorCLIDaemon {
  constructor() {
    this.taskQueue = [];
    this.isProcessing = false;
    // 守护进程位于 repo/services/，repo 根为上一级
    const repoRoot = path.resolve(__dirname, '..');
    this.logFile = path.join(repoRoot, 'logs/cursor-daemon.log');
    
    // 确保日志目录存在
    const logDir = path.dirname(this.logFile);
    if (!fs.existsSync(logDir)) {
      fs.mkdirSync(logDir, { recursive: true });
    }
  }

  // 添加任务到队列
  addTask(task) {
    this.taskQueue.push(task);
    this.processQueue();
  }

  // 处理任务队列
  async processQueue() {
    if (this.isProcessing || this.taskQueue.length === 0) return;
    
    this.isProcessing = true;
    const task = this.taskQueue.shift();
    
    try {
      await this.executeTask(task);
    } catch (error) {
      this.log(`Error executing task: ${error.message}`);
    } finally {
      this.isProcessing = false;
      this.processQueue(); // 处理下一个任务
    }
  }

  // 执行 Cursor CLI 任务
  async executeTask(task) {
    const { projectPath, taskDescription, model = 'auto', callback } = task;
    
    this.log(`Executing task: ${taskDescription} (model: ${model})`);
    
    const agentPath = process.env.CURSOR_AGENT_PATH || 'agent';
    const args = [
      '--model', model,
      '-p',
      '--force',  // 自动执行，不需要确认
      '--output-format', 'json',
      taskDescription
    ];
    
    // 配置代理环境变量
    const env = {
      ...process.env,
      PATH: process.env.PATH,
      HTTP_PROXY: process.env.HTTP_PROXY || 'http://127.0.0.1:7890',
      HTTPS_PROXY: process.env.HTTPS_PROXY || 'http://127.0.0.1:7890',
      NO_PROXY: 'localhost,127.0.0.1'
    };
    
    // 如果没有指定项目路径，使用项目根目录
    const projectRoot = path.resolve(__dirname, '../..');
    const workingDir = projectPath || projectRoot;
    
    return new Promise((resolve, reject) => {
      const process = spawn(agentPath, args, {
        cwd: workingDir,
        env: env
      });

      let stdout = '';
      let stderr = '';

      process.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      process.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      process.on('close', (code) => {
        const result = {
          code,
          stdout,
          stderr,
          success: code === 0
        };

        this.log(`Task completed with code ${code}`);
        
        if (callback) {
          callback(result);
        }
        
        resolve(result);
      });

      process.on('error', (error) => {
        this.log(`Process error: ${error.message}`);
        reject(error);
      });
    });
  }

  log(message) {
    const timestamp = new Date().toISOString();
    const logMessage = `[${timestamp}] ${message}\n`;
    fs.appendFileSync(this.logFile, logMessage);
    console.log(logMessage.trim());
  }
}

// 如果直接运行，启动守护进程
if (require.main === module) {
  const daemon = new CursorCLIDaemon();
  
  // 监听任务文件（通过文件系统 IPC）
  const projectRoot = path.resolve(__dirname, '../..');
  const taskFile = path.join(projectRoot, 'telegram-bot/tasks/queue.json');
  
  // 确保任务文件存在
  if (!fs.existsSync(taskFile)) {
    fs.writeFileSync(taskFile, '[]');
  }
  
  // 定期检查任务文件
  setInterval(() => {
    try {
      if (fs.existsSync(taskFile)) {
        const content = fs.readFileSync(taskFile, 'utf8');
        if (content.trim()) {
          const tasks = JSON.parse(content);
          if (Array.isArray(tasks) && tasks.length > 0) {
            tasks.forEach(task => daemon.addTask(task));
            fs.writeFileSync(taskFile, '[]'); // 清空队列
          }
        }
      }
    } catch (error) {
      // 忽略错误
    }
  }, 1000);
  
  // 保持进程运行
  process.on('SIGTERM', () => {
    daemon.log('Received SIGTERM, shutting down gracefully');
    process.exit(0);
  });
  
  daemon.log('Cursor CLI Daemon started');
}

module.exports = CursorCLIDaemon;
