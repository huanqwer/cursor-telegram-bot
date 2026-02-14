#!/usr/bin/env python3
"""
会话状态管理模块
管理用户的项目选择记忆，支持自动过期（第二天0点后失效）
"""

import os
import json
import logging
from datetime import datetime, date
from threading import Lock

# 数据文件路径
DATA_DIR = os.path.join(os.path.dirname(__file__), "../data")
SESSION_FILE = os.path.join(DATA_DIR, "user_sessions.json")

# 文件锁，用于多线程安全
_file_lock = Lock()


def ensure_data_dir():
    """确保数据目录存在"""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR, exist_ok=True)


def load_sessions():
    """加载用户会话数据"""
    ensure_data_dir()
    if not os.path.exists(SESSION_FILE):
        return {}
    
    try:
        with _file_lock:
            with open(SESSION_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logging.error(f"Failed to load sessions: {e}")
        return {}


def save_sessions(sessions):
    """保存用户会话数据"""
    ensure_data_dir()
    try:
        with _file_lock:
            with open(SESSION_FILE, 'w', encoding='utf-8') as f:
                json.dump(sessions, f, indent=2, ensure_ascii=False)
    except IOError as e:
        logging.error(f"Failed to save sessions: {e}")


def is_expired(date_str):
    """
    检查日期是否过期（第二天0点后失效）
    
    Args:
        date_str: 日期字符串，格式为 "YYYY-MM-DD"
        
    Returns:
        bool: True 表示已过期，False 表示未过期
    """
    try:
        session_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        today = date.today()
        
        # 如果会话日期是今天，未过期
        if session_date == today:
            return False
        
        # 如果会话日期是昨天或更早，已过期
        return session_date < today
    except ValueError as e:
        logging.error(f"Invalid date format: {date_str}, error: {e}")
        return True  # 格式错误视为过期


def get_user_project(user_id):
    """
    获取用户当前选择的项目
    
    Args:
        user_id: 用户ID（字符串或整数）
        
    Returns:
        dict: 包含 project_path, trigger_word, date 的字典，如果不存在或已过期返回 None
    """
    user_id_str = str(user_id)
    sessions = load_sessions()
    
    if user_id_str not in sessions:
        return None
    
    session = sessions[user_id_str]
    
    # 检查是否过期
    if is_expired(session.get("date", "")):
        # 清除过期会话
        clear_user_project(user_id)
        return None
    
    return session


def set_user_project(user_id, project_path, trigger_word):
    """
    设置用户选择的项目
    
    Args:
        user_id: 用户ID（字符串或整数）
        project_path: 项目路径
        trigger_word: 触发词
    """
    user_id_str = str(user_id)
    sessions = load_sessions()
    
    sessions[user_id_str] = {
        "project_path": project_path,
        "trigger_word": trigger_word,
        "date": date.today().strftime("%Y-%m-%d")
    }
    
    save_sessions(sessions)
    logging.info(f"User {user_id_str} switched to project: {project_path} (trigger: {trigger_word})")


def clear_user_project(user_id):
    """
    清除用户项目选择
    
    Args:
        user_id: 用户ID（字符串或整数）
    """
    user_id_str = str(user_id)
    sessions = load_sessions()
    
    if user_id_str in sessions:
        del sessions[user_id_str]
        save_sessions(sessions)
        logging.info(f"Cleared project selection for user {user_id_str}")


def cleanup_expired_sessions():
    """清理所有过期的会话"""
    sessions = load_sessions()
    expired_users = []
    
    for user_id, session in sessions.items():
        if is_expired(session.get("date", "")):
            expired_users.append(user_id)
    
    if expired_users:
        for user_id in expired_users:
            del sessions[user_id]
        save_sessions(sessions)
        logging.info(f"Cleaned up {len(expired_users)} expired sessions")
