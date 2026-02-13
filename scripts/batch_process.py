#!/usr/bin/env python3
"""
GraphGen 批量处理脚本
提供简单的 Python API 来批量处理数据生成任务
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from tqdm import tqdm
from dotenv import load_dotenv

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from graphgen_cli import GraphGenCLI


class BatchProcessor:
    """批量处理器类"""
    
    def __init__(
        self,
        api_key: str,
        synthesizer_url: str = "https://api.huiyan-ai.cn/v1",
        synthesizer_model: str = "gpt-4.1-mini-2025-04-14",
        trainee_url: Optional[str] = None,
        trainee_model: Optional[str] = None,
        trainee_api_key: Optional[str] = None,
        use_trainee_model: bool = False,
        output_dir: str = "tasks/outputs",
        log_dir: str = "logs",
        **kwargs
    ):
        """
        初始化批量处理器
        
        Args:
            api_key: API Key (必需)
            synthesizer_url: Synthesizer API URL
            synthesizer_model: Synthesizer 模型名称
            trainee_url: Trainee API URL (如果使用 trainee 模型)
            trainee_model: Trainee 模型名称 (如果使用 trainee 模型)
            trainee_api_key: Trainee API Key (如果使用 trainee 模型)
            use_trainee_model: 是否使用 Trainee 模型
            output_dir: 输出目录
            log_dir: 日志目录
            **kwargs: 其他配置参数
                - output_data_type: 输出数据类型，可选 "atomic", "multi_hop", "aggregated", "all"
                  "all" 模式会同时使用所有四种生成模式（atomic, aggregated, multi_hop, cot），
                  生成更多数据但消耗更多 token
        """
        self.api_key = api_key
        self.synthesizer_url = synthesizer_url
        self.synthesizer_model = synthesizer_model
        self.trainee_url = trainee_url or "https://api.siliconflow.cn/v1"
        self.trainee_model = trainee_model or "Qwen/Qwen2.5-7B-Instruct"
        self.trainee_api_key = trainee_api_key or api_key
        self.use_trainee_model = use_trainee_model
        self.output_dir = Path(output_dir)
        self.log_dir = Path(log_dir)
        
        # 创建输出和日志目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 默认配置参数
        self.config = {
            "chunk_size": kwargs.get("chunk_size", 1024),
            "chunk_overlap": kwargs.get("chunk_overlap", 100),
            "tokenizer": kwargs.get("tokenizer", "cl100k_base"),
            "output_data_type": kwargs.get("output_data_type", "aggregated"),  # 可选: atomic, multi_hop, aggregated, all
            "output_data_format": kwargs.get("output_data_format", "Alpaca"),
            "quiz_samples": kwargs.get("quiz_samples", 2),
            "bidirectional": kwargs.get("bidirectional", True),
            "expand_method": kwargs.get("expand_method", "max_tokens"),
            "max_extra_edges": kwargs.get("max_extra_edges", 5),
            "max_tokens": kwargs.get("max_tokens", 256),
            "max_depth": kwargs.get("max_depth", 2),
            "edge_sampling": kwargs.get("edge_sampling", "max_loss"),
            "isolated_node_strategy": kwargs.get("isolated_node_strategy", "ignore"),
            "loss_strategy": kwargs.get("loss_strategy", "only_edge"),
            "rpm": kwargs.get("rpm", 1000),
            "tpm": kwargs.get("tpm", 50000),
        }
        
        # 初始化 CLI
        self.cli = GraphGenCLI()
        
        # 统计信息
        self.stats = {
            "total_files": 0,
            "processed_files": 0,
            "failed_files": 0,
            "total_tokens": 0,
            "total_time": 0,
            "file_results": []
        }
        
        # 设置日志
        self._setup_logging()
    
    def _setup_logging(self):
        """设置日志"""
        log_file = self.log_dir / f"batch_process_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"批量处理日志文件: {log_file}")
    
    def process_file(
        self,
        file_path: Union[str, Path],
        output_file: Optional[Union[str, Path]] = None
    ) -> Dict[str, Any]:
        """
        处理单个文件
        
        Args:
            file_path: 输入文件路径
            output_file: 输出文件路径 (可选，默认自动生成)
            
        Returns:
            处理结果字典，包含 success, output_file, tokens_used, processing_time 等信息
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            error_msg = f"文件不存在: {file_path}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "file_path": str(file_path),
                "error_msg": error_msg
            }
        
        # 确定输出文件路径
        if output_file is None:
            base_name = file_path.stem
            output_file = self.output_dir / f"{base_name}_graphgen_output.jsonl"
        else:
            output_file = Path(output_file)
        
        start_time = time.time()
        
        try:
            # 创建命名空间对象来模拟 argparse.Namespace
            class Args:
                pass
            
            args = Args()
            args.use_trainee_model = self.use_trainee_model
            args.synthesizer_url = self.synthesizer_url
            args.synthesizer_model = self.synthesizer_model
            args.trainee_url = self.trainee_url
            args.trainee_model = self.trainee_model
            args.api_key = self.api_key
            args.trainee_api_key = self.trainee_api_key
            args.input_file = str(file_path)
            args.output_file = str(output_file)
            
            # 设置配置参数
            for key, value in self.config.items():
                setattr(args, key, value)
            
            # 处理文件
            self.logger.info(f"开始处理文件: {file_path}")
            result = self.cli.process_single_file(str(file_path), args)
            
            # 如果成功，移动输出文件到指定位置
            if result["success"] and result["output_file"]:
                if Path(result["output_file"]).exists() and result["output_file"] != str(output_file):
                    import shutil
                    shutil.move(result["output_file"], output_file)
                    result["output_file"] = str(output_file)
            
            processing_time = time.time() - start_time
            result["processing_time"] = processing_time
            
            if result["success"]:
                self.logger.info(
                    f"✅ 文件处理成功: {file_path} -> {result['output_file']} "
                    f"(tokens: {result['tokens_used']}, 时间: {processing_time:.2f}秒)"
                )
            else:
                self.logger.error(f"❌ 文件处理失败: {file_path} - {result.get('error_msg', '未知错误')}")
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = str(e)
            self.logger.error(f"处理文件时发生异常: {file_path} - {error_msg}")
            return {
                "success": False,
                "file_path": str(file_path),
                "error_msg": error_msg,
                "processing_time": processing_time
            }
    
    def process_batch(
        self,
        file_paths: List[Union[str, Path]],
        output_dir: Optional[Union[str, Path]] = None,
        continue_on_error: bool = True
    ) -> Dict[str, Any]:
        """
        批量处理多个文件
        
        Args:
            file_paths: 文件路径列表
            output_dir: 输出目录 (可选，默认使用初始化时的 output_dir)
            continue_on_error: 遇到错误时是否继续处理其他文件
            
        Returns:
            批量处理结果字典，包含统计信息和每个文件的处理结果
        """
        if output_dir:
            self.output_dir = Path(output_dir)
            self.output_dir.mkdir(parents=True, exist_ok=True)
        
        batch_start_time = time.time()
        self.stats = {
            "total_files": len(file_paths),
            "processed_files": 0,
            "failed_files": 0,
            "total_tokens": 0,
            "total_time": 0,
            "file_results": []
        }
        
        self.logger.info("=" * 80)
        self.logger.info("开始批量处理")
        self.logger.info(f"文件数量: {len(file_paths)}")
        self.logger.info(f"输出目录: {self.output_dir}")
        self.logger.info("=" * 80)
        
        # 测试 API 连接
        self.logger.info("测试 API 连接...")
        if not self.cli.test_api_connection(self.synthesizer_url, self.api_key, self.synthesizer_model):
            self.logger.error("Synthesizer API 连接失败")
            return {
                "success": False,
                "error": "API 连接失败",
                "stats": self.stats
            }
        
        if self.use_trainee_model:
            if not self.cli.test_api_connection(self.trainee_url, self.trainee_api_key, self.trainee_model):
                self.logger.error("Trainee API 连接失败")
                return {
                    "success": False,
                    "error": "Trainee API 连接失败",
                    "stats": self.stats
                }
        
        # 处理文件
        with tqdm(total=len(file_paths), desc="批量处理", unit="文件") as pbar:
            for file_path in file_paths:
                result = self.process_file(file_path)
                self.stats["file_results"].append(result)
                
                if result["success"]:
                    self.stats["processed_files"] += 1
                    self.stats["total_tokens"] += result.get("tokens_used", 0)
                else:
                    self.stats["failed_files"] += 1
                    if not continue_on_error:
                        self.logger.error("遇到错误，停止批量处理")
                        break
                
                pbar.update(1)
                pbar.set_postfix({
                    "成功": self.stats["processed_files"],
                    "失败": self.stats["failed_files"]
                })
        
        # 计算总时间
        self.stats["total_time"] = time.time() - batch_start_time
        
        # 打印总结
        self.logger.info("=" * 80)
        self.logger.info("批量处理完成")
        self.logger.info(f"总文件数: {self.stats['total_files']}")
        self.logger.info(f"成功处理: {self.stats['processed_files']}")
        self.logger.info(f"处理失败: {self.stats['failed_files']}")
        self.logger.info(f"总 token 使用量: {self.stats['total_tokens']}")
        self.logger.info(f"总处理时间: {self.stats['total_time']:.2f}秒")
        if self.stats["processed_files"] > 0:
            avg_time = self.stats["total_time"] / self.stats["processed_files"]
            self.logger.info(f"平均处理时间: {avg_time:.2f}秒/文件")
        self.logger.info("=" * 80)
        
        return {
            "success": self.stats["failed_files"] == 0,
            "stats": self.stats
        }
    
    def process_from_list(
        self,
        list_file: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
        continue_on_error: bool = True
    ) -> Dict[str, Any]:
        """
        从文件列表中读取文件路径并批量处理
        
        Args:
            list_file: 包含文件路径列表的文本文件 (每行一个路径)
            output_dir: 输出目录
            continue_on_error: 遇到错误时是否继续处理其他文件
            
        Returns:
            批量处理结果字典
        """
        list_file = Path(list_file)
        
        if not list_file.exists():
            error_msg = f"文件列表不存在: {list_file}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
        
        # 读取文件列表
        with open(list_file, 'r', encoding='utf-8') as f:
            file_paths = [
                line.strip() for line in f 
                if line.strip() and not line.startswith('#')
            ]
        
        self.logger.info(f"从文件列表读取到 {len(file_paths)} 个文件路径")
        
        return self.process_batch(file_paths, output_dir, continue_on_error)
    
    def process_directory(
        self,
        directory: Union[str, Path],
        pattern: str = "*.txt",
        output_dir: Optional[Union[str, Path]] = None,
        continue_on_error: bool = True,
        recursive: bool = False
    ) -> Dict[str, Any]:
        """
        处理目录中的所有匹配文件
        
        Args:
            directory: 目录路径
            pattern: 文件匹配模式 (例如 "*.txt", "*.json")
            output_dir: 输出目录
            continue_on_error: 遇到错误时是否继续处理其他文件
            recursive: 是否递归搜索子目录
            
        Returns:
            批量处理结果字典
        """
        directory = Path(directory)
        
        if not directory.exists():
            error_msg = f"目录不存在: {directory}"
            self.logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
        
        # 查找匹配的文件
        if recursive:
            file_paths = list(directory.rglob(pattern))
        else:
            file_paths = list(directory.glob(pattern))
        
        # 过滤出文件 (排除目录)
        file_paths = [f for f in file_paths if f.is_file()]
        
        # 过滤支持的文件类型
        valid_extensions = ['.txt', '.json', '.jsonl', '.csv']
        file_paths = [
            f for f in file_paths 
            if f.suffix.lower() in valid_extensions
        ]
        
        self.logger.info(f"在目录 {directory} 中找到 {len(file_paths)} 个匹配文件")
        
        return self.process_batch(file_paths, output_dir, continue_on_error)
    
    def save_results(self, output_file: Optional[Union[str, Path]] = None):
        """
        保存处理结果到 JSON 文件
        
        Args:
            output_file: 输出文件路径 (可选，默认自动生成)
        """
        if output_file is None:
            output_file = self.output_dir / f"batch_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        else:
            output_file = Path(output_file)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"处理结果已保存到: {output_file}")
        return output_file


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="GraphGen 批量处理脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:

  # 处理单个文件
  python batch_process.py -i input.txt -k your_api_key

  # 批量处理多个文件
  python batch_process.py -b file1.txt file2.json file3.csv -k your_api_key

  # 从文件列表批量处理
  python batch_process.py -l file_list.txt -k your_api_key

  # 处理目录中的所有文件
  python batch_process.py -d data/ -k your_api_key

  # 使用配置文件
  python batch_process.py -c config.json -b file1.txt file2.txt
        """
    )
    
    # 输入参数组 - 互斥选择
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("-i", "--input-file", help="单个输入文件路径")
    input_group.add_argument("-b", "--batch-files", nargs='+', help="批量处理多个文件路径")
    input_group.add_argument("-l", "--file-list", help="包含文件路径列表的文本文件")
    input_group.add_argument("-d", "--directory", help="处理目录中的所有匹配文件")
    input_group.add_argument("-c", "--config", help="配置文件路径 (JSON 格式)")
    
    # API 配置
    parser.add_argument("-k", "--api-key", 
                      default=os.getenv("SYNTHESIZER_API_KEY", ""),
                      help="API Key (默认从环境变量 SYNTHESIZER_API_KEY 读取)")
    
    # 输出配置
    parser.add_argument("-o", "--output-dir", 
                      default="tasks/outputs",
                      help="输出目录 (默认: tasks/outputs)")
    
    # 模型配置
    parser.add_argument("--use-trainee-model", action="store_true", 
                      help="使用 Trainee 模型")
    parser.add_argument("--synthesizer-url", 
                      default=os.getenv("SYNTHESIZER_BASE_URL", "https://api.huiyan-ai.cn/v1"),
                      help="Synthesizer API URL")
    parser.add_argument("--synthesizer-model", 
                      default=os.getenv("SYNTHESIZER_MODEL", "gpt-4.1-mini-2025-04-14"),
                      help="Synthesizer 模型名称")
    
    # 其他配置参数
    parser.add_argument("--chunk-size", type=int, default=1024, help="文本块大小")
    parser.add_argument("--chunk-overlap", type=int, default=100, help="文本块重叠大小")
    parser.add_argument("--max-tokens", type=int, default=256, help="最大 token 数")
    parser.add_argument("--max-depth", type=int, default=2, help="最大深度")
    
    # 目录处理选项
    parser.add_argument("--pattern", default="*.txt", help="文件匹配模式 (用于 -d 选项)")
    parser.add_argument("--recursive", action="store_true", help="递归搜索子目录 (用于 -d 选项)")
    
    args = parser.parse_args()
    
    # 验证 API Key
    if not args.api_key:
        print("❌ 错误: 未提供 API Key")
        print("请通过以下方式之一提供 API Key:")
        print("1. 命令行参数: -k your_api_key")
        print("2. 环境变量: SYNTHESIZER_API_KEY=your_api_key")
        sys.exit(1)
    
    # 加载环境变量
    load_dotenv()
    
    # 如果使用配置文件
    if args.config:
        with open(args.config, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 从配置文件创建处理器
        processor = BatchProcessor(**config)
        
        # 处理文件
        if "file_paths" in config:
            result = processor.process_batch(config["file_paths"])
        elif "list_file" in config:
            result = processor.process_from_list(config["list_file"])
        elif "directory" in config:
            result = processor.process_directory(
                config["directory"],
                pattern=config.get("pattern", "*.txt"),
                recursive=config.get("recursive", False)
            )
        else:
            print("❌ 配置文件中必须包含 file_paths, list_file 或 directory 之一")
            sys.exit(1)
    else:
        # 创建处理器
        processor = BatchProcessor(
            api_key=args.api_key,
            synthesizer_url=args.synthesizer_url,
            synthesizer_model=args.synthesizer_model,
            use_trainee_model=args.use_trainee_model,
            output_dir=args.output_dir,
            chunk_size=args.chunk_size,
            chunk_overlap=args.chunk_overlap,
            max_tokens=args.max_tokens,
            max_depth=args.max_depth,
        )
        
        # 处理文件
        if args.input_file:
            result = processor.process_file(args.input_file)
        elif args.batch_files:
            result = processor.process_batch(args.batch_files)
        elif args.file_list:
            result = processor.process_from_list(args.file_list)
        elif args.directory:
            result = processor.process_directory(
                args.directory,
                pattern=args.pattern,
                recursive=args.recursive
            )
    
    # 保存结果
    processor.save_results()
    
    # 退出
    if result.get("success", False):
        print("🎉 批量处理完成!")
        sys.exit(0)
    else:
        print("💥 批量处理完成，但有文件处理失败")
        sys.exit(1)


if __name__ == "__main__":
    main()

