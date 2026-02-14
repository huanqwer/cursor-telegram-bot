#!/usr/bin/env node
// 测试任务处理器的脚本

const { parseTaskMessage, validateTask } = require('../skills/cursor-task-handler');

console.log('Testing Task Handler...\n');

// 测试用例
const testCases = [
  '执行任务：列出当前目录的文件',
  '任务：创建一个新的工具函数 --model opus-4.6-thinking',
  'do: 分析代码结构 --project /path/to/your/project',
  '列出文件 --model sonnet-4.5-thinking',
  '简单的任务描述'
];

testCases.forEach((message, index) => {
  console.log(`\nTest Case ${index + 1}: "${message}"`);
  const task = parseTaskMessage(message);
  console.log('Parsed task:', JSON.stringify(task, null, 2));
  
  const validation = validateTask(task);
  console.log('Validation:', validation.valid ? '✅ Valid' : '❌ Invalid');
  if (!validation.valid) {
    console.log('Errors:', validation.errors);
  }
});

console.log('\nAll tests completed!');
