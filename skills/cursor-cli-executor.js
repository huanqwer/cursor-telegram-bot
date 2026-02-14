#!/usr/bin/env node
// CLI 执行器
// 调用 Cursor CLI 执行任务，实时捕获输出流

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

/**
 * 执行 Cursor CLI 任务
 * @param {Object} options - 执行选项
 * @param {string} options.taskDescription - 任务描述
 * @param {string} [options.projectPath] - 项目路径
 * @param {string} [options.model] - 模型名称
 * @param {Function} [options.onOutput] - 输出回调函数
 * @returns {Promise<Object>} 执行结果
 */
async function executeCursorCLI(options) {
  const {
    taskDescription,
    projectPath = process.env.DEFAULT_PROJECT_ROOT || '/path/to/your/project',
    model = 'auto',
    onOutput
  } = options;

  const agentPath = process.env.CURSOR_AGENT_PATH || 'agent';
  const args = [
    '--model', model,
    '-p',
    '--force',
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

  return new Promise((resolve, reject) => {
    const process = spawn(agentPath, args, {
      cwd: projectPath,
      env: env
    });

    let stdout = '';
    let stderr = '';
    let outputBuffer = '';

    process.stdout.on('data', (data) => {
      const text = data.toString();
      stdout += text;
      outputBuffer += text;

      // 如果提供了回调函数，实时调用
      if (onOutput) {
        try {
          // 尝试解析 JSON 输出
          const lines = outputBuffer.split('\n').filter(l => l.trim());
          for (const line of lines) {
            try {
              const json = JSON.parse(line);
              onOutput(json);
            } catch (e) {
              // 不是 JSON，作为文本输出
              onOutput({ type: 'text', content: line });
            }
          }
          outputBuffer = '';
        } catch (e) {
          // 忽略解析错误
        }
      }
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
      resolve(result);
    });

    process.on('error', (error) => {
      reject(error);
    });
  });
}

module.exports = {
  executeCursorCLI
};
