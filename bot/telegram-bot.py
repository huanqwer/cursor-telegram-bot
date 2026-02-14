#!/usr/bin/env python3
"""
安全的 Telegram Bot - Cursor CLI 远程控制
包含完整安全措施：用户认证、输入验证、命令注入防护、代理配置等
"""

import os
import json
import re
import subprocess
import logging
import asyncio
import threading
from datetime import datetime, timedelta
from collections import defaultdict
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest

# 导入项目管理和会话管理模块
from project_manager import (
    get_project_trigger_words,
    get_all_trigger_words,
    get_project_display_list,
    PROJECT_TRIGGER_MAPPING
)
from session_manager import (
    get_user_project,
    set_user_project,
    clear_user_project,
    cleanup_expired_sessions
)

# 加载环境变量
load_dotenv()

# 配置
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
USE_PROXY = os.getenv("USE_PROXY", "true").lower() == "true"
PROXY_URL = os.getenv("PROXY_URL", "http://127.0.0.1:7890")
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "../config/bot_config.json")
LOG_FILE = os.path.join(os.path.dirname(__file__), "../logs/telegram-bot.log")


def _get_project_root():
    """默认项目根路径：环境变量 DEFAULT_PROJECT_ROOT 或 config 的 default_project_root，否则为空"""
    root = os.getenv("DEFAULT_PROJECT_ROOT", "").strip()
    if root:
        return root
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            return (cfg.get("default_project_root") or "").strip()
        except (json.JSONDecodeError, IOError):
            pass
    return ""


def _get_agent_path():
    """Cursor CLI 可执行路径：环境变量 CURSOR_AGENT_PATH 或 config 的 cursor_agent_path，否则为 agent"""
    path = os.getenv("CURSOR_AGENT_PATH", "").strip()
    if path:
        return path
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            return (cfg.get("cursor_agent_path") or "agent").strip() or "agent"
        except (json.JSONDecodeError, IOError):
            pass
    return "agent"


PROJECT_ROOT = _get_project_root()
AGENT_PATH = _get_agent_path()

# 速率限制
RATE_LIMIT = {"max_messages": 5, "window_seconds": 60}
user_message_times = defaultdict(list)

# 项目触发词映射（全局变量，在初始化时填充）
trigger_mapping = {}  # trigger_word -> project_path
all_trigger_words = []  # 所有触发词列表

def init_projects():
    """初始化项目映射"""
    global trigger_mapping, all_trigger_words
    trigger_mapping = get_project_trigger_words()
    all_trigger_words = get_all_trigger_words()
    # 清理过期的会话
    cleanup_expired_sessions()
    logging.info(f"Initialized {len(trigger_mapping)} trigger words for {len(PROJECT_TRIGGER_MAPPING)} projects")
    if not PROJECT_TRIGGER_MAPPING:
        logging.warning("project_trigger_mapping is empty; configure project_trigger_mapping in config/bot_config.json for trigger-word switching")

# 初始化项目映射
init_projects()

# 日志配置
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filemode='a'
)

def load_config():
    """加载配置"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"allowed_user_ids": [], "admin_user_id": None}

def is_user_allowed(user_id):
    """检查用户是否在白名单中"""
    config = load_config()
    return user_id in config.get("allowed_user_ids", [])

def check_rate_limit(user_id):
    """检查速率限制"""
    now = datetime.now()
    user_times = user_message_times[user_id]
    
    # 清理过期记录
    user_times[:] = [
        t for t in user_times 
        if now - t < timedelta(seconds=RATE_LIMIT["window_seconds"])
    ]
    
    if len(user_times) >= RATE_LIMIT["max_messages"]:
        return False
    
    user_times.append(now)
    return True

def validate_task_input(user_input):
    """验证和清理用户输入"""
    # 长度限制
    if len(user_input) > 1000:
        raise ValueError("输入过长（最大 1000 字符）")
    
    # 移除危险字符
    dangerous_chars = [';', '&', '|', '`', '$', '<', '>']
    for char in dangerous_chars:
        if char in user_input:
            raise ValueError(f"禁止使用字符: {char}")
    
    # 检查命令注入模式
    injection_patterns = [
        r'rm\s+-rf',
        r'sudo\s+',
        r'chmod\s+777',
        r'>\s+/dev/',
        r'curl\s+.*\|',
        r'wget\s+.*\|'
    ]
    
    for pattern in injection_patterns:
        if re.search(pattern, user_input, re.IGNORECASE):
            raise ValueError("检测到潜在的危险命令")
    
    return user_input.strip()

def filter_sensitive_info(text):
    """过滤敏感信息"""
    # 过滤可能的 API Key
    text = re.sub(r'sk-[A-Za-z0-9]{32,}', '[API_KEY_FILTERED]', text)
    return text

def extract_trigger_from_message(message, trigger_mapping):
    """
    从消息中提取触发词，支持"切换到"前缀
    
    Args:
        message: 用户消息
        trigger_mapping: 触发词到项目路径的映射字典
        
    Returns:
        tuple: (trigger_word, project_path) 如果匹配，否则返回 None
    """
    message = message.strip()
    
    # 移除"切换到"前缀（如果存在）
    if message.startswith("切换到"):
        message = message[3:].strip()
    
    # 检查是否匹配任何触发词
    if message in trigger_mapping:
        return (message, trigger_mapping[message])
    
    return None

def parse_task_message(message, user_id=None):
    """
    解析任务消息，提取参数
    支持触发词检测和会话记忆
    
    Args:
        message: 用户消息
        user_id: 用户ID（可选）
        
    Returns:
        dict: 任务信息或切换项目标记
    """
    # 1. 检查是否为触发词（支持"切换到"前缀）
    trigger_result = extract_trigger_from_message(message, trigger_mapping)
    if trigger_result:
        trigger_word, project_path = trigger_result
        if user_id:
            set_user_project(user_id, project_path, trigger_word)
        return {"type": "switch_project", "trigger_word": trigger_word, "project_path": project_path}
    
    # 2. 检查是否有记忆的项目
    if user_id:
        user_project = get_user_project(user_id)
        if user_project:
            # 自动添加 --project 参数（如果消息中没有指定）
            if "--project" not in message.lower():
                message = f"--project {user_project['project_path']} {message}"
    
    # 3. 原有解析逻辑
    config = load_config()
    task = {
        "description": "",
        "projectPath": PROJECT_ROOT,
        "model": "auto"
    }
    
    # 提取项目路径
    project_match = re.search(r'--project[:\s]+([^\s]+)', message, re.IGNORECASE)
    if project_match:
        project_spec = project_match.group(1)
        # 检查是否是项目名称（在 allowed_projects 中）
        allowed_projects = config.get("allowed_projects", {})
        if project_spec in allowed_projects:
            task["projectPath"] = allowed_projects[project_spec]
        else:
            # 直接使用路径（可能是完整路径）
            task["projectPath"] = project_spec
    
    # 提取模型
    model_match = re.search(r'--model[:\s]+([^\s]+)', message, re.IGNORECASE)
    if model_match:
        task["model"] = model_match.group(1)
    
    # 提取任务描述（移除参数部分）
    description = message
    description = re.sub(r'--project[:\s]+[^\s]+', '', description, flags=re.IGNORECASE)
    description = re.sub(r'--model[:\s]+[^\s]+', '', description, flags=re.IGNORECASE)
    description = re.sub(r'^(执行任务|任务|do|run)[：:]\s*', '', description, flags=re.IGNORECASE)
    description = description.strip()
    
    task["description"] = description or message
    
    return task

def parse_cursor_output(output_text):
    """解析 Cursor CLI 的 JSON 输出并格式化"""
    try:
        # 尝试解析 JSON
        # Cursor CLI 可能返回多行 JSON，每行一个 JSON 对象
        lines = output_text.strip().split('\n')
        parsed_results = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                json_obj = json.loads(line)
                parsed_results.append(json_obj)
            except json.JSONDecodeError:
                # 如果不是 JSON，保留原始文本
                parsed_results.append({"type": "text", "content": line})
        
        # 查找 result 类型的 JSON 对象
        result_obj = None
        for obj in parsed_results:
            if obj.get("type") == "result":
                result_obj = obj
                break
        
        if result_obj:
            # 提取关键信息
            is_error = result_obj.get("is_error", False)
            result_text = result_obj.get("result", "")
            duration_ms = result_obj.get("duration_ms", 0)
            duration_api_ms = result_obj.get("duration_api_ms", 0)
            
            # 格式化输出
            formatted_output = result_text
            
            # 添加执行时间信息（如果可用）
            if duration_ms > 0:
                duration_sec = duration_ms / 1000
                formatted_output += f"\n\n⏱️ 执行时间: {duration_sec:.2f}秒"
            
            return {
                "success": not is_error,
                "output": formatted_output,
                "raw_output": output_text,
                "is_error": is_error,
                "duration_ms": duration_ms
            }
        else:
            # 如果没有找到 result 对象，返回所有解析的内容
            all_content = "\n".join([
                obj.get("content", str(obj)) if isinstance(obj, dict) else str(obj)
                for obj in parsed_results
            ])
            return {
                "success": True,
                "output": all_content if all_content else output_text,
                "raw_output": output_text,
                "is_error": False
            }
            
    except Exception as e:
        logging.warning(f"Failed to parse JSON output: {e}")
        # 如果解析失败，返回原始输出
        return {
            "success": True,
            "output": output_text,
            "raw_output": output_text,
            "is_error": False
        }

async def execute_cursor_cli(task_description, project_path, model, user_id, username, progress_callback=None):
    """
    安全执行 Cursor CLI，支持增量输出
    
    Args:
        task_description: 任务描述
        project_path: 项目路径（工作目录）
        model: 模型名称
        user_id: 用户ID
        username: 用户名
        progress_callback: 进度回调函数，每30秒调用一次，参数为 (incremental_output, total_output)
    """
    try:
        # 验证输入
        validated_task = validate_task_input(task_description)
        
        # 记录操作
        logging.info(f"User {user_id} ({username}) executing: {validated_task[:100]}")
        logging.info(f"Working directory: {project_path}")
        
        # 执行命令（使用参数列表，防止注入）
        # 注意：不使用 --output-format json，因为 JSON 格式会等到任务完成后才输出
        # 使用默认格式以便实时获取输出
        cmd = [
            AGENT_PATH,
            "--model", model,
            "-p",
            "--force",
            validated_task
        ]
        
        # 配置环境变量（包括代理）
        env = os.environ.copy()
        env["HTTP_PROXY"] = env.get("HTTP_PROXY", "http://127.0.0.1:7890")
        env["HTTPS_PROXY"] = env.get("HTTPS_PROXY", "http://127.0.0.1:7890")
        env["NO_PROXY"] = "localhost,127.0.0.1"
        
        # 使用 Popen 以便实时读取输出（project_path 为空时使用当前目录）
        process = subprocess.Popen(
            cmd,
            cwd=project_path or None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
            bufsize=1  # 行缓冲
        )
        
        stdout_buffer = []
        stderr_buffer = []
        last_sync_time = datetime.now()
        sync_interval = timedelta(seconds=30)  # 30秒同步一次
        last_sent_stdout_len = 0  # 记录上次发送的 stdout 长度
        last_sent_stderr_len = 0  # 记录上次发送的 stderr 长度
        
        # 读取输出的线程函数
        def read_output(pipe, buffer):
            try:
                for line in iter(pipe.readline, ''):
                    if line:
                        buffer.append(line)
                        logging.info(f"CLI output received: {line[:200]}")  # 改为 INFO 级别以便调试
            except Exception as e:
                logging.error(f"Error reading output: {e}")
            finally:
                pipe.close()
        
        # 启动读取线程
        stdout_thread = threading.Thread(target=read_output, args=(process.stdout, stdout_buffer))
        stderr_thread = threading.Thread(target=read_output, args=(process.stderr, stderr_buffer))
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        stdout_thread.start()
        stderr_thread.start()
        
        # 等待进程完成，同时每30秒同步一次增量输出
        start_time = datetime.now()
        while process.poll() is None:
            await asyncio.sleep(1)  # 每秒检查一次
            
            # 检查是否到了同步时间
            now = datetime.now()
            if progress_callback and (now - last_sync_time) >= sync_interval:
                # 获取当前全部输出
                current_stdout = ''.join(stdout_buffer)
                current_stderr = ''.join(stderr_buffer)
                
                # 计算增量部分（只发送新增的内容）
                incremental_stdout = current_stdout[last_sent_stdout_len:]
                incremental_stderr = current_stderr[last_sent_stderr_len:]
                
                # 更新已发送的长度
                last_sent_stdout_len = len(current_stdout)
                last_sent_stderr_len = len(current_stderr)
                
                # 构建增量输出
                incremental_output = ""
                if incremental_stdout:
                    # 对于增量输出，直接使用原始文本（不解析 JSON，因为可能是部分输出）
                    incremental_output = incremental_stdout.strip()
                
                if incremental_stderr:
                    if incremental_output:
                        incremental_output += f"\n\n⚠️ 警告/错误:\n{incremental_stderr.strip()}"
                    else:
                        incremental_output = f"⚠️ 警告/错误:\n{incremental_stderr.strip()}"
                
                # 固定每10秒发送一次消息
                elapsed = (now - start_time).total_seconds()
                try:
                    if incremental_output:
                        # 有新输出，发送新输出
                        incremental_output = filter_sensitive_info(incremental_output)
                        logging.info(f"Sending incremental update after {elapsed:.1f}s, stdout_len={len(incremental_stdout)}, stderr_len={len(incremental_stderr)}")
                        await progress_callback(incremental_output, elapsed)
                    else:
                        # 没有新输出，发送"正在处理中"
                        logging.info(f"No new output after {elapsed:.1f}s, sending progress ping")
                        await progress_callback("⏳ 正在处理中，请稍候...", elapsed)
                except Exception as e:
                    logging.error(f"Error in progress callback: {e}")
                
                last_sync_time = now
        
        # 等待读取线程完成
        stdout_thread.join(timeout=5)
        stderr_thread.join(timeout=5)
        
        # 获取最终输出
        final_stdout = ''.join(stdout_buffer)
        final_stderr = ''.join(stderr_buffer)
        return_code = process.returncode
        
        # 记录结果
        logging.info(f"Task completed with code {return_code}")
        
        # 解析和格式化输出
        # 注意：由于不再使用 --output-format json，输出格式可能不同
        if return_code == 0 and final_stdout:
            # 尝试解析 JSON（如果输出是 JSON 格式）
            try:
                parsed_result = parse_cursor_output(final_stdout)
                # 过滤敏感信息
                parsed_result["output"] = filter_sensitive_info(parsed_result["output"])
                return {
                    "success": parsed_result["success"],
                    "output": parsed_result["output"],
                    "error": filter_sensitive_info(final_stderr) if final_stderr else "",
                    "code": return_code,
                    "duration_ms": parsed_result.get("duration_ms", 0)
                }
            except Exception as e:
                # 如果解析失败，直接使用原始输出
                logging.warning(f"Failed to parse output as JSON, using raw output: {e}")
                return {
                    "success": True,
                    "output": filter_sensitive_info(final_stdout),
                    "error": filter_sensitive_info(final_stderr) if final_stderr else "",
                    "code": return_code,
                    "duration_ms": 0
                }
        else:
            # 执行失败或没有输出
            error_msg = filter_sensitive_info(final_stderr) if final_stderr else "任务执行失败，无错误信息"
            return {
                "success": False,
                "output": "",
                "error": error_msg,
                "code": return_code
            }
        
    except ValueError as e:
        logging.warning(f"Input validation failed: {e}")
        raise
    except subprocess.TimeoutExpired:
        logging.error("Task execution timeout")
        raise Exception("任务执行超时（5分钟）")
    except Exception as e:
        logging.error(f"Execution error: {e}")
        raise

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理消息"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "unknown"
    
    # 检查消息对象是否存在
    if not update.message:
        logging.warning(f"Update without message from user {user_id}")
        return
    
    message_text = update.message.text if update.message.text else ""
    
    # 记录收到的消息
    logging.info(f"Received message from user {user_id} ({username}): {message_text[:100]}")
    
    # 检查消息是否为空
    if not message_text or not message_text.strip():
        logging.warning(f"Empty message from user {user_id}")
        try:
            await update.message.reply_text("❌ 消息内容为空，请发送有效的任务描述")
        except Exception as e:
            logging.error(f"Failed to send reply: {e}")
        return
    
    # 1. 用户认证
    if not is_user_allowed(user_id):
        logging.warning(f"Unauthorized access attempt from user {user_id} ({username})")
        try:
            await update.message.reply_text("❌ 未授权访问\n\n你的 User ID 不在白名单中。请联系管理员添加。")
        except Exception as e:
            logging.error(f"Failed to send unauthorized message: {e}")
        return
    
    # 2. 速率限制
    if not check_rate_limit(user_id):
        logging.info(f"Rate limit exceeded for user {user_id}")
        try:
            await update.message.reply_text("⚠️ 请求过于频繁，请稍后再试\n\n速率限制：每分钟最多 5 条消息")
        except Exception as e:
            logging.error(f"Failed to send rate limit message: {e}")
        return
    
    # 3. 检查是否为触发词（项目切换）
    try:
        parsed = parse_task_message(message_text, user_id)
    except Exception as e:
        logging.warning(f"Task parsing failed: {e}")
        try:
            await update.message.reply_text(f"❌ 解析任务失败: {e}\n\n请检查消息格式是否正确。")
        except Exception as reply_error:
            logging.error(f"Failed to send parsing error reply: {reply_error}")
        return
    
    # 如果是触发词切换操作
    if parsed and parsed.get("type") == "switch_project":
        trigger_word = parsed["trigger_word"]
        project_path = parsed["project_path"]
        try:
            await update.message.reply_text(
                f"✅ 已切换到项目：{trigger_word}\n"
                f"路径：{project_path}\n\n"
                f"后续消息将自动使用此项目。"
            )
        except Exception as e:
            logging.error(f"Failed to send switch confirmation: {e}")
        return
    
    # 4. 检查是否有记忆的项目（如果不是切换操作）
    user_project = get_user_project(user_id)
    if not user_project:
        # 生成项目列表提示
        project_list = "\n".join(get_project_display_list())
        try:
            await update.message.reply_text(
                f"您还没有选择操作哪个项目：\n\n{project_list}\n\n"
                f"请发送触发词切换项目（如：my-todo 或 切换到后端）"
            )
        except Exception as e:
            logging.error(f"Failed to send project list: {e}")
        return
    
    # 5. 解析任务（此时已确保有记忆的项目）
    task = parsed
    
    # 6. 执行任务
    try:
        # 发送执行中消息
        status_message = None
        try:
            status_message = await update.message.reply_text("⏳ 正在执行任务...")
        except Exception as e:
            logging.error(f"Failed to send 'executing' message: {e}")
        
        # 定义进度回调函数，每30秒发送增量输出
        async def progress_callback(incremental_output, elapsed_seconds):
            """进度回调：发送增量输出"""
            try:
                elapsed_min = int(elapsed_seconds // 60)
                elapsed_sec = int(elapsed_seconds % 60)
                elapsed_str = f"{elapsed_min}分{elapsed_sec}秒"
                
                # 限制增量输出长度
                max_incremental_length = 3000
                if len(incremental_output) > max_incremental_length:
                    incremental_output = incremental_output[:max_incremental_length] + "\n\n... (增量内容已截断)"
                
                progress_text = f"📊 进度更新（已执行 {elapsed_str}）\n\n{incremental_output}"
                
                # 发送增量更新
                await update.message.reply_text(progress_text[:4096])
                logging.info(f"Sent progress update to user {user_id} after {elapsed_str}")
            except Exception as e:
                logging.error(f"Error sending progress update: {e}")
        
        result = await execute_cursor_cli(
            task["description"],
            task["projectPath"],
            task["model"],
            user_id,
            username,
            progress_callback=progress_callback
        )
        
        # 5. 发送结果
        if result["success"]:
            output_text = result.get('output', '')
            if not output_text or not output_text.strip():
                output_text = "任务执行成功，但无输出内容。"
            
            # 限制长度（Telegram 消息最大 4096 字符，留出标题空间）
            max_length = 3500
            if len(output_text) > max_length:
                output_text = output_text[:max_length] + "\n\n... (内容已截断，完整内容请查看日志)"
            
            # 添加执行时间信息
            duration_info = ""
            if result.get('duration_ms', 0) > 0:
                duration_sec = result['duration_ms'] / 1000
                duration_info = f"\n⏱️ 执行时间: {duration_sec:.2f}秒"
            
            response = f"✅ 任务完成{duration_info}\n\n{output_text}"
        else:
            error_text = result.get('error', '未知错误')
            if not error_text or not error_text.strip():
                error_text = f"任务执行失败，退出码: {result.get('code', -1)}"
            
            if len(error_text) > 3500:
                error_text = error_text[:3500] + "\n\n... (错误信息已截断)"
            
            response = f"❌ 任务失败 (code: {result.get('code', -1)})\n\n{error_text}"
        
        # 发送消息（Telegram 限制 4096 字符）
        try:
            await update.message.reply_text(response[:4096])
        except Exception as e:
            # 如果消息太长，分段发送
            logging.warning(f"Message too long, splitting: {e}")
            chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
            for i, chunk in enumerate(chunks):
                try:
                    if i == 0:
                        await update.message.reply_text(chunk)
                    else:
                        await update.message.reply_text(f"(续) {chunk}")
                except Exception as chunk_error:
                    logging.error(f"Failed to send chunk {i}: {chunk_error}")
        
    except ValueError as e:
        # 输入验证失败
        logging.warning(f"Input validation failed: {e}")
        try:
            await update.message.reply_text(
                f"❌ 输入验证失败\n\n"
                f"错误: {e}\n\n"
                f"请检查输入内容，确保：\n"
                f"- 不包含危险字符（; & | ` $ < >）\n"
                f"- 不包含危险命令\n"
                f"- 长度不超过 1000 字符"
            )
        except Exception as reply_error:
            logging.error(f"Failed to send validation error reply: {reply_error}")
    except subprocess.TimeoutExpired:
        logging.error("Task execution timeout")
        try:
            await update.message.reply_text(
                "❌ 任务执行超时\n\n"
                "任务执行时间超过 5 分钟，已自动终止。\n"
                "请尝试简化任务或分批执行。"
            )
        except Exception as reply_error:
            logging.error(f"Failed to send timeout message: {reply_error}")
    except Exception as e:
        logging.error(f"Execution error: {e}", exc_info=True)
        try:
            error_msg = str(e)[:1000]  # 限制错误信息长度
            await update.message.reply_text(
                f"❌ 执行错误\n\n"
                f"错误信息: {error_msg}\n\n"
                f"请查看日志文件获取详细信息。"
            )
        except Exception as reply_error:
            logging.error(f"Failed to send error reply: {reply_error}")

def main():
    """主函数"""
    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN 环境变量未设置")
    
    # 配置代理（使用环境变量方式，python-telegram-bot 会自动读取）
    if USE_PROXY:
        os.environ['HTTP_PROXY'] = PROXY_URL
        os.environ['HTTPS_PROXY'] = PROXY_URL
        os.environ['NO_PROXY'] = 'localhost,127.0.0.1'
        logging.info(f"Using proxy via environment: {PROXY_URL}")
    else:
        # 清除代理环境变量
        os.environ.pop('HTTP_PROXY', None)
        os.environ.pop('HTTPS_PROXY', None)
        logging.info("Proxy disabled")
    
    # 创建应用（库会自动读取 HTTP_PROXY/HTTPS_PROXY 环境变量）
    app = Application.builder().token(BOT_TOKEN).build()
    
    # 添加消息处理器（处理所有文本消息）
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    
    logging.info("Bot started, waiting for messages...")
    logging.info(f"Current proxy env: HTTP_PROXY={os.environ.get('HTTP_PROXY', 'None')}")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
