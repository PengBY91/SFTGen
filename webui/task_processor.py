"""
任务处理器
负责执行具体的文件处理任务
"""

import os
import tempfile
import threading
import time
from typing import Dict, Any, Optional
import json

from graphgen.graphgen import GraphGen
from graphgen.models import OpenAIClient, Tokenizer
from graphgen.models.llm.limitter import RPM, TPM
from graphgen.utils import set_logger
from webui.utils import cleanup_workspace, setup_workspace
from webui.task_manager import task_manager, TaskStatus, TaskInfo
from webui.base import WebuiParams


class TaskProcessor:
    """任务处理器"""
    
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.processing_threads: Dict[str, threading.Thread] = {}
    
    def start_task(self, task_id: str, params: WebuiParams) -> bool:
        """启动任务处理"""
        if task_id in self.processing_threads:
            return False  # 任务已在处理中
        
        # 更新任务状态为处理中
        task_manager.update_task_status(task_id, TaskStatus.PROCESSING)
        
        # 创建处理线程
        thread = threading.Thread(
            target=self._process_task,
            args=(task_id, params),
            daemon=True
        )
        self.processing_threads[task_id] = thread
        thread.start()
        return True
    
    def _process_task(self, task_id: str, params: WebuiParams):
        """处理任务的具体逻辑"""
        task = task_manager.get_task(task_id)
        if not task:
            return
        
        try:
            # 设置工作目录
            log_file, working_dir = setup_workspace(os.path.join(self.root_dir, "cache", task_id))
            set_logger(log_file, if_stream=True)
            
            # 构建配置
            config = self._build_config(params)
            env = self._build_env(params)
            
            # 初始化 GraphGen
            graph_gen = GraphGen(working_dir=working_dir, config=config)
            graph_gen.clear()
            
            # 设置 LLM 客户端
            tokenizer_instance = Tokenizer(config.get("tokenizer", "cl100k_base"))
            synthesizer_llm_client = OpenAIClient(
                model_name=env.get("SYNTHESIZER_MODEL", ""),
                base_url=env.get("SYNTHESIZER_BASE_URL", ""),
                api_key=env.get("SYNTHESIZER_API_KEY", ""),
                request_limit=True,
                rpm=RPM(env.get("RPM", 1000)),
                tpm=TPM(env.get("TPM", 50000)),
                tokenizer=tokenizer_instance,
            )
            
            trainee_llm_client = OpenAIClient(
                model_name=env.get("TRAINEE_MODEL", ""),
                base_url=env.get("TRAINEE_BASE_URL", ""),
                api_key=env.get("TRAINEE_API_KEY", ""),
                request_limit=True,
                rpm=RPM(env.get("RPM", 1000)),
                tpm=TPM(env.get("TPM", 50000)),
                tokenizer=tokenizer_instance,
            )
            
            graph_gen = GraphGen(
                working_dir=working_dir,
                tokenizer_instance=tokenizer_instance,
                synthesizer_llm_client=synthesizer_llm_client,
                trainee_llm_client=trainee_llm_client,
            )
            
            # 处理数据
            graph_gen.insert(read_config=config["read"], split_config=config["split"])
            
            if config["if_trainee_model"]:
                graph_gen.quiz_and_judge(quiz_and_judge_config=config["quiz_and_judge"])
            
            graph_gen.generate(
                partition_config=config["partition"],
                generate_config=config["generate"],
            )
            
            # 保存输出
            output_data = graph_gen.qa_storage.data
            output_file = task_manager.get_task_output_path(task_id)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            # 计算 token 使用量
            def sum_tokens(client):
                return sum(u["total_tokens"] for u in client.token_usage)
            
            synthesizer_tokens = sum_tokens(graph_gen.synthesizer_llm_client)
            trainee_tokens = (
                sum_tokens(graph_gen.trainee_llm_client)
                if config["if_trainee_model"]
                else 0
            )
            
            token_usage = {
                "synthesizer_tokens": synthesizer_tokens,
                "trainee_tokens": trainee_tokens,
                "total_tokens": synthesizer_tokens + trainee_tokens
            }
            
            # 更新任务状态为完成
            task_manager.update_task_status(
                task_id, 
                TaskStatus.COMPLETED,
                output_file=output_file,
                token_usage=token_usage
            )
            
        except Exception as e:
            # 更新任务状态为失败
            task_manager.update_task_status(
                task_id,
                TaskStatus.FAILED,
                error_message=str(e)
            )
        
        finally:
            # 清理工作目录
            if 'working_dir' in locals():
                cleanup_workspace(working_dir)
            
            # 移除处理线程记录
            if task_id in self.processing_threads:
                del self.processing_threads[task_id]
    
    def _build_config(self, params: WebuiParams) -> Dict[str, Any]:
        """构建配置字典"""
        # 根据分区方法构建参数
        method = params.partition_method
        if method == "dfs":
            partition_params = {
                "max_units_per_community": params.dfs_max_units,
            }
        elif method == "bfs":
            partition_params = {
                "max_units_per_community": params.bfs_max_units,
            }
        elif method == "leiden":
            partition_params = {
                "max_size": params.leiden_max_size,
                "use_lcc": params.leiden_use_lcc,
                "random_seed": params.leiden_random_seed,
            }
        else:  # ece
            partition_params = {
                "max_units_per_community": params.ece_max_units,
                "min_units_per_community": params.ece_min_units,
                "max_tokens_per_community": params.ece_max_tokens,
                "unit_sampling": params.ece_unit_sampling,
            }
        
        return {
            "if_trainee_model": params.if_trainee_model,
            "read": {"input_file": params.upload_file},
            "split": {
                "chunk_size": params.chunk_size,
                "chunk_overlap": params.chunk_overlap,
            },
            "search": {"enabled": False},
            "quiz_and_judge": {
                "enabled": params.if_trainee_model,
                "quiz_samples": params.quiz_samples,
            },
            "partition": {
                "method": params.partition_method,
                "method_params": partition_params,
            },
            "generate": {
                "mode": params.mode,
                "data_format": params.data_format,
            },
        }
    
    def _build_env(self, params: WebuiParams) -> Dict[str, Any]:
        """构建环境变量字典"""
        return {
            "TOKENIZER_MODEL": params.tokenizer,
            "SYNTHESIZER_BASE_URL": params.synthesizer_url,
            "SYNTHESIZER_MODEL": params.synthesizer_model,
            "TRAINEE_BASE_URL": params.trainee_url,
            "TRAINEE_MODEL": params.trainee_model,
            "SYNTHESIZER_API_KEY": params.api_key,
            "TRAINEE_API_KEY": params.trainee_api_key,
            "RPM": params.rpm,
            "TPM": params.tpm,
        }
    
    def is_task_processing(self, task_id: str) -> bool:
        """检查任务是否正在处理中"""
        return task_id in self.processing_threads
    
    def get_processing_tasks(self) -> list:
        """获取正在处理的任务列表"""
        return list(self.processing_threads.keys())
