#!/usr/bin/env node
// 状态监控器
// 监控 Cursor CLI 执行状态，解析输出中的关键信息

/**
 * 解析 Cursor CLI 输出，识别任务状态
 * @param {string} output - CLI 输出内容
 * @returns {Object} 解析后的状态信息
 */
function parseCursorOutput(output) {
  const status = {
    completed: false,
    error: false,
    needsConfirmation: false,
    progress: [],
    summary: ''
  };

  const lowerOutput = output.toLowerCase();

  // 检查任务完成状态
  if (lowerOutput.includes('completed') || 
      lowerOutput.includes('done') || 
      lowerOutput.includes('success') ||
      lowerOutput.includes('finished')) {
    status.completed = true;
  }

  // 检查错误状态
  if (lowerOutput.includes('error') || 
      lowerOutput.includes('failed') || 
      lowerOutput.includes('exception') ||
      lowerOutput.includes('fatal')) {
    status.error = true;
  }

  // 检查是否需要确认
  if (lowerOutput.includes('approve') || 
      lowerOutput.includes('confirm') || 
      lowerOutput.includes('review') ||
      lowerOutput.includes('permission')) {
    status.needsConfirmation = true;
  }

  // 提取进度信息
  const progressMatches = output.match(/(?:progress|step|working|processing)[:\s]+(.+)/gi);
  if (progressMatches) {
    status.progress = progressMatches.map(m => m.trim());
  }

  // 生成摘要（取前 200 个字符）
  status.summary = output.substring(0, 200).replace(/\n/g, ' ').trim();

  return status;
}

/**
 * 检查任务是否完成
 * @param {Object} result - 任务执行结果
 * @returns {boolean} 是否完成
 */
function isTaskCompleted(result) {
  if (!result || result.code === undefined) {
    return false;
  }

  // 退出码为 0 通常表示成功
  if (result.code === 0) {
    return true;
  }

  // 即使退出码非 0，如果输出中包含完成标记，也认为完成
  const status = parseCursorOutput(result.stdout || result.stderr || '');
  return status.completed;
}

/**
 * 检查任务是否有错误
 * @param {Object} result - 任务执行结果
 * @returns {boolean} 是否有错误
 */
function hasTaskError(result) {
  if (!result) {
    return true;
  }

  if (result.code !== 0) {
    return true;
  }

  const status = parseCursorOutput(result.stdout || result.stderr || '');
  return status.error;
}

module.exports = {
  parseCursorOutput,
  isTaskCompleted,
  hasTaskError
};
