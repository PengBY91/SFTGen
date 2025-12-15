#!/usr/bin/env python3
"""
修复已有评测任务的文件命名问题

用法:
    python scripts/fix_evaluation_files.py [task_id]
    
    如果不提供 task_id，则修复所有评测任务
    如果提供 task_id，则只修复指定任务
"""

import os
import sys
import json
import shutil
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from webui.task_manager import task_manager, TaskStatus


def fix_evaluation_files(target_task_id=None):
    """修复评测任务的文件命名
    
    Args:
        target_task_id: 如果指定，则只修复该任务；否则修复所有任务
    """
    if target_task_id:
        print(f"开始修复任务: {target_task_id}")
    else:
        print("开始扫描所有评测任务...")
    
    # 获取所有任务
    tasks = task_manager.get_all_tasks()
    if not tasks:
        print("没有找到任何任务")
        return
    
    fixed_count = 0
    error_count = 0
    
    for task in tasks:
        # 如果指定了目标任务，只处理该任务
        if target_task_id and task.task_id != target_task_id:
            continue
        
        # 只处理评测任务
        if task.task_type != "evaluation":
            continue
        
        # 只处理已完成的任务
        if task.status != TaskStatus.COMPLETED:
            print(f"跳过任务 {task.task_id} (状态: {task.status.value})")
            continue
        
        print(f"\n处理任务: {task.task_id}")
        print(f"  任务名称: {task.task_name}")
        
        # 获取缓存文件夹
        cache_folder = task.cache_folder if hasattr(task, 'cache_folder') else f"cache/{task.task_id}"
        eval_dir = os.path.join(cache_folder, "data", "evaluation")
        
        if not os.path.exists(eval_dir):
            print(f"  ❌ 评测目录不存在: {eval_dir}")
            error_count += 1
            continue
        
        # 查找所有 JSON 文件
        eval_files = [f for f in os.listdir(eval_dir) if f.endswith('.json')]
        
        if not eval_files:
            print(f"  ❌ 未找到评测文件")
            error_count += 1
            continue
        
        # 期望的文件名
        expected_filename = f"{task.task_id}_eval.json"
        expected_path = os.path.join(eval_dir, expected_filename)
        
        # 如果期望的文件已存在，跳过
        if os.path.exists(expected_path):
            print(f"  ✓ 文件已存在: {expected_filename}")
            continue
        
        # 找到实际的评测文件（通常是第一个）
        source_filename = eval_files[0]
        source_path = os.path.join(eval_dir, source_filename)
        
        try:
            # 复制文件
            shutil.copy2(source_path, expected_path)
            print(f"  ✓ 已复制:")
            print(f"    源文件: {source_filename}")
            print(f"    目标文件: {expected_filename}")
            
            # 验证文件内容
            with open(expected_path, 'r', encoding='utf-8') as f:
                eval_data = json.load(f)
                item_count = len(eval_data.get('items', []))
                print(f"    评测项数量: {item_count}")
            
            fixed_count += 1
            
        except Exception as e:
            print(f"  ❌ 复制失败: {e}")
            error_count += 1
    
    print("\n" + "="*50)
    print(f"修复完成！")
    print(f"  成功修复: {fixed_count} 个任务")
    print(f"  失败/跳过: {error_count} 个任务")
    print("="*50)


if __name__ == "__main__":
    try:
        # 解析命令行参数
        target_task_id = None
        if len(sys.argv) > 1:
            target_task_id = sys.argv[1]
            print(f"目标任务ID: {target_task_id}\n")
        
        fix_evaluation_files(target_task_id)
    except KeyboardInterrupt:
        print("\n\n操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
