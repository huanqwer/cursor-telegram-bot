#!/usr/bin/env node
// 任务解析器
// 解析 Telegram 消息中的任务描述，提取参数

/**
 * 解析任务消息，提取任务描述和参数
 * @param {string} message - Telegram 消息内容
 * @returns {Object} 解析后的任务对象
 */
function parseTaskMessage(message) {
  const task = {
    description: '',
    projectPath: process.env.DEFAULT_PROJECT_ROOT || '/path/to/your/project',
    model: 'auto',
    autoExecute: true
  };

  // 移除多余的空格和换行
  const cleanMessage = message.trim().replace(/\s+/g, ' ');

  // 提取项目路径（如果指定）
  const projectMatch = cleanMessage.match(/--project[:\s]+([^\s]+)/i);
  if (projectMatch) {
    task.projectPath = projectMatch[1];
  }

  // 提取模型（如果指定）
  const modelMatch = cleanMessage.match(/--model[:\s]+([^\s]+)/i);
  if (modelMatch) {
    task.model = modelMatch[1];
  }

  // 提取任务描述（移除参数部分）
  let description = cleanMessage
    .replace(/--project[:\s]+[^\s]+/gi, '')
    .replace(/--model[:\s]+[^\s]+/gi, '')
    .trim();

  // 如果消息以特定命令开头，移除命令前缀
  const commandPrefixes = [
    /^执行任务[：:]\s*/i,
    /^任务[：:]\s*/i,
    /^do[：:]\s*/i,
    /^run[：:]\s*/i
  ];

  for (const prefix of commandPrefixes) {
    if (prefix.test(description)) {
      description = description.replace(prefix, '').trim();
      break;
    }
  }

  task.description = description || cleanMessage;

  return task;
}

/**
 * 验证任务参数
 * @param {Object} task - 任务对象
 * @returns {Object} 验证结果 {valid: boolean, errors: string[]}
 */
function validateTask(task) {
  const errors = [];

  if (!task.description || task.description.trim().length === 0) {
    errors.push('Task description is required');
  }

  if (task.projectPath && !require('fs').existsSync(task.projectPath)) {
    errors.push(`Project path does not exist: ${task.projectPath}`);
  }

  const validModels = ['auto', 'opus-4.6-thinking', 'sonnet-4.5-thinking', 'gpt-5.3-codex', 'gpt-5.2'];
  if (task.model && !validModels.includes(task.model)) {
    errors.push(`Invalid model: ${task.model}. Valid models: ${validModels.join(', ')}`);
  }

  return {
    valid: errors.length === 0,
    errors
  };
}

module.exports = {
  parseTaskMessage,
  validateTask
};
