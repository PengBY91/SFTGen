#!/usr/bin/env python3
"""
修复特定任务的状态

这个脚本用于修复因 get_usage() 错误而失败的任务
任务ID: 00dcb594-c26a-4acf-a55d-67b924188518
"""

import os
import sys
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from webui.task_manager import task_manager, TaskStatus


def fix_failed_task(task_id: str):
    """修复失败的评测任务"""
    print(f"开始修复任务: {task_id}")
    
    # 获取任务
    task = task_manager.get_task(task_id)
    if not task:
        print(f"❌ 任务不存在: {task_id}")
        return False
    
    print(f"  任务名称: {task.task_name}")
    print(f"  当前状态: {task.status.value}")
    print(f"  任务类型: {task.task_type}")
    
    if task.task_type != "evaluation":
        print(f"  ❌ 不是评测任务，跳过")
        return False
    
    # 查找评测文件
    # cache_folder 可能包含时间戳前缀，需要查找实际的文件夹
    cache_base = "cache"
    cache_folder = None
    
    # 首先尝试使用 task.cache_folder
    if hasattr(task, 'cache_folder') and task.cache_folder:
        cache_folder = task.cache_folder
    else:
        # 如果没有，搜索 cache 目录下匹配 task_id 的文件夹
        import glob
        pattern = os.path.join(cache_base, f"*{task_id}")
        matching_folders = glob.glob(pattern)
        if matching_folders:
            cache_folder = matching_folders[0]
        else:
            cache_folder = os.path.join(cache_base, task_id)
    
    print(f"  Cache 文件夹: {cache_folder}")
    eval_file = os.path.join(cache_folder, "data", "evaluation", f"{task_id}_eval.json")
    
    if not os.path.exists(eval_file):
        print(f"  ❌ 评测文件不存在: {eval_file}")
        return False
    
    print(f"  ✓ 找到评测文件: {eval_file}")
    
    # 读取评测数据
    try:
        with open(eval_file, 'r', encoding='utf-8') as f:
            eval_data = json.load(f)
        
        eval_count = len(eval_data.get('items', []))
        print(f"  ✓ 评测项数量: {eval_count}")
        
        # 由于无法获取实际的 token 使用量，我们设置为 0
        # 用户可以在任务详情中看到这个任务没有 token 统计
        token_usage = {
            "synthesizer_tokens": 0,
            "synthesizer_input_tokens": 0,
            "synthesizer_output_tokens": 0,
            "trainee_tokens": 0,
            "trainee_input_tokens": 0,
            "trainee_output_tokens": 0,
            "total_tokens": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0
        }
        
        # 更新任务状态为完成
        task_manager.update_task_status(
            task_id,
            TaskStatus.COMPLETED,
            output_file=eval_file,
            token_usage=token_usage,
            qa_count=eval_count
        )
        
        print(f"  ✓ 任务状态已更新为完成")
        print(f"  ✓ 评测项数量: {eval_count}")
        print(f"  ⚠️  Token 使用统计设置为 0（因为无法从失败的任务中获取）")
        
        return True
        
    except Exception as e:
        print(f"  ❌ 修复失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 要修复的任务ID
    task_id = "00dcb594-c26a-4acf-a55d-67b924188518"
    
    print("="*50)
    print("修复失败的评测任务")
    print("="*50)
    print()
    
    success = fix_failed_task(task_id)
    
    print()
    print("="*50)
    if success:
        print("✓ 修复成功！")
        print()
        print("任务现在应该显示为已完成状态。")
        print("注意：Token 使用统计显示为 0，因为无法从失败的任务中获取实际数据。")
    else:
        print("✗ 修复失败")
    print("="*50)
