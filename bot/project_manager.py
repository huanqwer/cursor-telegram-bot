#!/usr/bin/env python3
"""
项目触发词映射管理模块
从 config/bot_config.json 的 project_trigger_mapping 读取项目与触发词映射；
若未配置则返回空映射。
"""

import os
import json
import logging

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "../config/bot_config.json")

# 从配置加载的映射，结构: { project_name: { "path": str, "triggers": [str] } }
# 若配置缺失或为空则为 {}
def _load_project_trigger_mapping():
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get("project_trigger_mapping") or {}
    except (json.JSONDecodeError, IOError) as e:
        logging.warning(f"Failed to load project_trigger_mapping from config: {e}")
        return {}

PROJECT_TRIGGER_MAPPING = _load_project_trigger_mapping()


def get_project_trigger_words():
    """
    返回触发词到项目路径的映射字典

    Returns:
        dict: {trigger_word: project_path} 格式的字典
    """
    trigger_mapping = {}
    for project_name, project_info in PROJECT_TRIGGER_MAPPING.items():
        project_path = project_info.get("path", "")
        for trigger in project_info.get("triggers", []):
            trigger_mapping[trigger] = project_path
    return trigger_mapping


def get_all_trigger_words():
    """
    返回所有触发词列表

    Returns:
        list: 所有触发词的列表
    """
    all_triggers = []
    for project_info in PROJECT_TRIGGER_MAPPING.values():
        all_triggers.extend(project_info.get("triggers", []))
    return all_triggers


def get_project_info_by_trigger(trigger_word):
    """
    根据触发词获取项目信息

    Args:
        trigger_word: 触发词

    Returns:
        tuple: (project_name, project_path) 或 None
    """
    for project_name, project_info in PROJECT_TRIGGER_MAPPING.items():
        if trigger_word in project_info.get("triggers", []):
            return (project_name, project_info.get("path", ""))
    return None


def get_project_display_list():
    """
    获取用于显示的项目列表（包含所有触发词）

    Returns:
        list: 格式化的项目列表字符串
    """
    display_list = []
    for project_name, project_info in PROJECT_TRIGGER_MAPPING.items():
        triggers_str = "、".join(project_info.get("triggers", []))
        display_list.append(f"- {triggers_str} -> {project_info.get('path', '')}")
    return display_list
