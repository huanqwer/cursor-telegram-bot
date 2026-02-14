#!/usr/bin/env node
// 测试守护进程的脚本

const CursorCLIDaemon = require('../services/cursor-cli-daemon');
const fs = require('fs');
const path = require('path');

console.log('Testing Cursor CLI Daemon...\n');

const daemon = new CursorCLIDaemon();

// 测试任务
const testTask = {
  projectPath: '/path/to/your/project',
  taskDescription: '列出当前目录的前 5 个文件',
  model: 'auto',
  callback: (result) => {
    console.log('\n=== Task Result ===');
    console.log('Success:', result.success);
    console.log('Code:', result.code);
    console.log('Stdout length:', result.stdout.length);
    console.log('Stderr length:', result.stderr.length);
    if (result.stdout) {
      console.log('\nOutput preview:');
      console.log(result.stdout.substring(0, 500));
    }
  }
};

console.log('Adding test task to queue...');
daemon.addTask(testTask);

// 等待任务完成
setTimeout(() => {
  console.log('\nTest completed. Check logs for details.');
  process.exit(0);
}, 30000); // 等待 30 秒
