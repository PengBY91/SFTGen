#!/usr/bin/env python3
"""
迁移旧版本任务输出文件到新版本存储位置

将 tasks/outputs/ 中的文件迁移到 cache/{task_id}/data/ 结构中
"""

import os
import sys
import json
import shutil
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from webui.task_manager import task_manager


def migrate_task_outputs():
    """迁移所有旧版本的任务输出文件"""
    print("="*60)
    print("迁移旧版本任务输出文件到新存储位置")
    print("="*60)
    print()
    
    # 旧输出目录
    old_outputs_dir = "tasks/outputs"
    if not os.path.exists(old_outputs_dir):
        print(f"❌ 旧输出目录不存在: {old_outputs_dir}")
        return
    
    # 获取所有任务
    tasks = task_manager.get_all_tasks()
    if not tasks:
        print("❌ 没有找到任何任务")
        return
    
    print(f"找到 {len(tasks)} 个任务")
    print()
    
    migrated_count = 0
    skipped_count = 0
    error_count = 0
    
    for task in tasks:
        task_id = task.task_id
        task_name = task.task_name or "未命名"
        
        # 只处理 SFT 任务（评测任务的输出文件名不同）
        if task.task_type == "evaluation":
            continue
        
        # 查找旧输出文件
        # 旧文件可能是 {task_id}_output.jsonl 或 {task_id}_output.json
        old_file_jsonl = os.path.join(old_outputs_dir, f"{task_id}_output.jsonl")
        old_file_json = os.path.join(old_outputs_dir, f"{task_id}_output.json")
        
        old_file = None
        if os.path.exists(old_file_jsonl):
            old_file = old_file_jsonl
        elif os.path.exists(old_file_json):
            old_file = old_file_json
        
        if not old_file:
            # 没有找到旧输出文件，跳过
            continue
        
        print(f"处理任务: {task_name} ({task_id})")
        print(f"  旧文件: {old_file}")
        
        # 确定新的存储位置
        # 如果任务有 cache_folder，使用它；否则创建新的
        if hasattr(task, 'cache_folder') and task.cache_folder:
            cache_folder = task.cache_folder
        else:
            # 创建新的 cache 文件夹（不带时间戳，因为是迁移的旧任务）
            cache_folder = os.path.join("cache", task_id)
        
        # 新文件位置
        new_data_dir = os.path.join(cache_folder, "data")
        os.makedirs(new_data_dir, exist_ok=True)
        
        # 新文件名统一为 .json
        new_file = os.path.join(new_data_dir, f"{task_id}_output.json")
        
        # 检查新文件是否已存在
        if os.path.exists(new_file):
            print(f"  ⚠️  新文件已存在，跳过: {new_file}")
            skipped_count += 1
            continue
        
        try:
            # 直接复制文件，保持原格式
            # JSONL 格式也是有效的，不需要转换
            shutil.copy2(old_file, new_file)
            print(f"  ✓ 已复制: {new_file}")
            
            # 验证文件是否可读
            try:
                file_size = os.path.getsize(new_file)
                print(f"    文件大小: {file_size} 字节")
            except Exception as e:
                print(f"    ⚠️  无法获取文件大小: {e}")
            
            # 更新任务的 output_file 路径（如果需要）
            if not hasattr(task, 'output_file') or not task.output_file or not os.path.exists(task.output_file):
                # 更新任务的 cache_folder 和 output_file
                task.cache_folder = cache_folder
                task.output_file = new_file
                task_manager.save_tasks()
                print(f"  ✓ 已更新任务元数据")
            
            migrated_count += 1
            
        except Exception as e:
            print(f"  ❌ 迁移失败: {e}")
            error_count += 1
        
        print()
    
    print("="*60)
    print("迁移完成！")
    print(f"  成功迁移: {migrated_count} 个文件")
    print(f"  跳过: {skipped_count} 个文件（已存在）")
    print(f"  失败: {error_count} 个文件")
    print("="*60)
    print()
    print("注意事项：")
    print("1. 旧文件仍保留在 tasks/outputs/ 中，未被删除")
    print("2. 如果确认迁移成功，可以手动删除旧文件")
    print("3. 新文件位于 cache/{task_id}/data/{task_id}_output.json")


if __name__ == "__main__":
    try:
        migrate_task_outputs()
    except KeyboardInterrupt:
        print("\n\n操作已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
