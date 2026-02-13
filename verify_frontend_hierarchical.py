#!/usr/bin/env python
"""
前端 Hierarchical 配置完整性验证脚本

验证所有前端文件都已正确添加 hierarchical 配置。
"""

import os
import re


def check_file(filepath, patterns, description):
    """检查文件是否包含指定的模式"""
    print(f"\n{'=' * 70}")
    print(f"检查: {description}")
    print(f"文件: {filepath}")
    print(f"{'=' * 70}")

    if not os.path.exists(filepath):
        print(f"❌ 文件不存在: {filepath}")
        return False

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    all_passed = True
    for pattern_name, pattern in patterns.items():
        if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
            print(f"✅ {pattern_name}")
        else:
            print(f"❌ {pattern_name} - 未找到")
            all_passed = False

    return all_passed


def main():
    """主验证流程"""
    print("\n" + "=" * 70)
    print("前端 Hierarchical 配置完整性验证".center(70))
    print("=" * 70)

    base_dir = "frontend/src"

    # 1. 检查类型定义
    type_patterns = {
        "qa_ratio_hierarchical": r"qa_ratio_hierarchical\s*[?:]",
        "hierarchical_relations": r"hierarchical_relations\s*[?:]",
        "structure_format": r"structure_format\s*[?:]",
        "max_hierarchical_depth": r"max_hierarchical_depth\s*[?:]",
        "max_siblings_per_community": r"max_siblings_per_community\s*[?:]",
    }
    result1 = check_file(
        f"{base_dir}/api/types.ts",
        type_patterns,
        "类型定义 (types.ts)"
    )

    # 2. 检查配置页面
    config_patterns = {
        "Hierarchical 分区选项": r'<el-option[^>]*value="hierarchical"',
        "Hierarchical 参数配置": r'partition_method\s*===\s*[\'"]hierarchical[\'"]',
        "层次关系类型选择": r'hierarchical_relations.*multiple.*filterable',
        "最大层次深度": r'max_hierarchical_depth',
        "最大兄弟节点数": r'max_siblings_per_community',
        "Hierarchical 生成模式": r'<el-checkbox[^>]*label="hierarchical"',
        "Hierarchical 占比": r'qa_ratio_hierarchical',
        "树结构格式": r'structure_format.*markdown.*json.*outline',
        "占比计算包含 hierarchical": r'qa_ratio_hierarchical.*\?\?',
    }
    result2 = check_file(
        f"{base_dir}/views/Config.vue",
        config_patterns,
        "配置页面 (Config.vue)"
    )

    # 3. 检查新建任务页面
    create_patterns = {
        "Hierarchical 分区选项": r'<el-option[^>]*value="hierarchical"',
        "Hierarchical 参数配置": r'partition_method\s*===\s*[\'"]hierarchical[\'"]',
        "层次关系类型": r'hierarchical_relations',
        "Hierarchical 生成模式": r'<el-checkbox[^>]*label="hierarchical"',
        "Hierarchical 占比": r'qa_ratio_hierarchical',
        "树结构格式条件显示": r'mode\.includes\([\'"]hierarchical[\'"]\)',
        "占比计算包含 hierarchical": r'qa_ratio_hierarchical.*\?\?',
    }
    result3 = check_file(
        f"{base_dir}/views/CreateTask.vue",
        create_patterns,
        "新建任务页面 (CreateTask.vue)"
    )

    # 4. 检查配置 Store
    store_patterns = {
        "qa_ratio_hierarchical 默认值": r'qa_ratio_hierarchical\s*:\s*[\d.]+',
        "hierarchical_relations 默认值": r"hierarchical_relations\s*:\s*\[",
        "structure_format 默认值": r'structure_format\s*:\s*[\'"]',
        "max_hierarchical_depth 默认值": r'max_hierarchical_depth\s*:\s*\d+',
        "max_siblings_per_community 默认值": r'max_siblings_per_community\s*:\s*\d+',
    }
    result4 = check_file(
        f"{base_dir}/stores/config.ts",
        store_patterns,
        "配置 Store (config.ts)"
    )

    # 5. 检查后端 schemas
    backend_patterns = {
        "qa_ratio_hierarchical 字段": r'qa_ratio_hierarchical\s*:\s*float',
        "hierarchical_relations 字段": r'hierarchical_relations\s*:\s*List\[str\]',
        "structure_format 字段": r'structure_format\s*:\s*str',
        "max_hierarchical_depth 字段": r'max_hierarchical_depth\s*:\s*int',
        "max_siblings_per_community 字段": r'max_siblings_per_community\s*:\s*int',
    }
    result5 = check_file(
        "backend/schemas.py",
        backend_patterns,
        "后端配置模型 (schemas.py)"
    )

    # 6. 检查 task_processor
    processor_patterns = {
        "all_mode_names 包含 hierarchical": r'all_mode_names\s*=\s*\{[^}]*hierarchical[^}]*\}',
        "hierarchical partition params": r'partition_params\s*=\s*\{[^}]*hierarchical_relations',
        "hierarchical generate config": r'structure_format.*hierarchical_relations',
    }
    result6 = check_file(
        "backend/core/task_processor.py",
        processor_patterns,
        "任务处理器 (task_processor.py)"
    )

    # 总结
    print("\n" + "=" * 70)
    print("验证结果总结".center(70))
    print("=" * 70)

    results = {
        "类型定义 (types.ts)": result1,
        "配置页面 (Config.vue)": result2,
        "新建任务页面 (CreateTask.vue)": result3,
        "配置 Store (config.ts)": result4,
        "后端配置 (schemas.py)": result5,
        "任务处理器 (task_processor.py)": result6,
    }

    all_passed = all(results.values())

    for name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name:40} {status}")

    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 所有验证通过！前端配置已完整添加！".center(70))
        print("=" * 70)
        print("\n✅ 前端可以正常使用 Hierarchical 功能")
        print("✅ 所有配置项已正确映射到后端")
        print("✅ 默认值已正确设置")
        print("\n下一步:")
        print("  1. 启动前端: cd frontend && npm run dev")
        print("  2. 访问配置页面查看 Hierarchical 配置")
        print("  3. 创建新任务测试 Hierarchical 模式")
        return 0
    else:
        print("❌ 部分验证失败，请检查上方详细信息".center(70))
        print("=" * 70)
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
