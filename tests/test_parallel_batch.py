#!/usr/bin/env python3
"""
测试并行批量处理脚本
演示如何使用多个模型并行处理任务
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from batch_process_parallel import ParallelBatchProcessor, ModelConfig


def test_parallel_processing():
    """测试并行批量处理"""
    print("=" * 80)
    print("测试并行批量处理 - 多模型并行")
    print("=" * 80)
    
    # 配置多个模型
    model_configs = [
        ModelConfig(
            api_key=os.getenv("SYNTHESIZER_API_KEY", "sk-wFHN2ySjUYxCx3LrWAkJEMB11FMxYDvF6DHdye9yVDwIH2no"),
            synthesizer_url="https://api.huiyan-ai.cn/v1",
            synthesizer_model="gpt-4.1-mini-2025-04-14",
            model_id="model_1"
        ),
        ModelConfig(
            api_key=os.getenv("SYNTHESIZER_API_KEY", "sk-wFHN2ySjUYxCx3LrWAkJEMB11FMxYDvF6DHdye9yVDwIH2no"),
            synthesizer_url="https://api.huiyan-ai.cn/v1",
            synthesizer_model="gpt-4.1-mini-2025-04-14",
            model_id="model_2"
        ),
    ]
    
    # 测试文件列表
    test_files = [
        "test_data/sample_input.txt",
        # 可以添加更多测试文件
    ]
    
    # 创建并行处理器
    processor = ParallelBatchProcessor(
        model_configs=model_configs,
        output_dir="test_data/parallel_outputs",
        log_dir="test_data/parallel_logs",
        batch_size=2,  # 每个模型同时处理 2 个任务
        max_workers=4,  # 总共 4 个工作线程
        output_data_type="all",  # 使用 "all" 模式
        output_data_format="Alpaca",
    )
    
    print(f"\n📊 配置信息:")
    print(f"   模型数量: {len(model_configs)}")
    print(f"   Batch size: 2")
    print(f"   最大工作线程数: 4")
    print(f"   测试文件数: {len(test_files)}")
    print(f"   生成模式: all")
    
    # 处理文件
    print("\n🚀 开始并行处理...")
    result = processor.process_batch(test_files)
    
    # 显示结果
    print("\n" + "=" * 80)
    print("处理结果")
    print("=" * 80)
    
    if result["success"]:
        print("✅ 所有文件处理成功!")
    else:
        print(f"⚠️  有 {result['stats']['failed_files']} 个文件处理失败")
    
    print(f"\n📊 统计信息:")
    print(f"   总文件数: {result['stats']['total_files']}")
    print(f"   成功处理: {result['stats']['processed_files']}")
    print(f"   处理失败: {result['stats']['failed_files']}")
    print(f"   总 Token 使用量: {result['stats']['total_tokens']:,}")
    print(f"   总处理时间: {result['stats']['total_time']:.2f}秒")
    
    # 各模型统计
    print(f"\n📈 各模型处理统计:")
    for model_id, model_stat in result['stats']['model_stats'].items():
        print(f"   {model_id}:")
        print(f"     成功: {model_stat['processed']}")
        print(f"     失败: {model_stat['failed']}")
        print(f"     Tokens: {model_stat['tokens']:,}")
    
    # 保存结果
    processor.save_results()
    
    return result["success"]


if __name__ == "__main__":
    try:
        success = test_parallel_processing()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断了处理过程")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

