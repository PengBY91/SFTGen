"""
任务处理器
负责执行具体的GraphGen任务
"""

import os
import sys
import json
from typing import Dict, Any

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from graphgen.graphgen import GraphGen
from graphgen.models import OpenAIClient, Tokenizer
from graphgen.models.llm.limitter import RPM, TPM
from graphgen.utils import set_logger, logger
from webui.task_manager import task_manager, TaskStatus
from webui.utils import setup_workspace, cleanup_workspace
from backend.schemas import TaskConfig


class TaskProcessor:
    """任务处理器"""
    
    def process_task(self, task_id: str, config: TaskConfig):
        """处理任务的具体逻辑"""
        try:
            # 获取任务信息
            task = task_manager.get_task(task_id)
            if not task:
                raise Exception("任务不存在")
            
            # 更新任务状态为处理中
            task_manager.update_task_status(task_id, TaskStatus.PROCESSING)
            
            # 初始化配置
            graphgen_config = self._build_config(config, task.filepaths)
            env = self._build_env(config)
            
            # 设置工作目录
            log_file, working_dir = setup_workspace(os.path.join("cache", task_id))
            set_logger(log_file, if_stream=True)
            os.environ.update({k: str(v) for k, v in env.items()})
            
            # 初始化 GraphGen
            tokenizer_instance = Tokenizer(config.tokenizer)
            synthesizer_llm_client = OpenAIClient(
                model_name=config.synthesizer_model,
                base_url=config.synthesizer_url,
                api_key=config.api_key,
                request_limit=True,
                rpm=RPM(config.rpm),
                tpm=TPM(config.tpm),
                tokenizer=tokenizer_instance,
            )
            trainee_llm_client = OpenAIClient(
                model_name=config.trainee_model,
                base_url=config.trainee_url,
                api_key=config.trainee_api_key or config.api_key,
                request_limit=True,
                rpm=RPM(config.rpm),
                tpm=TPM(config.tpm),
                tokenizer=tokenizer_instance,
            )
            
            graph_gen = GraphGen(
                working_dir=working_dir,
                tokenizer_instance=tokenizer_instance,
                synthesizer_llm_client=synthesizer_llm_client,
                trainee_llm_client=trainee_llm_client,
            )
            
            graph_gen.clear()
            
            # 处理数据
            graph_gen.insert(read_config=graphgen_config["read"], split_config=graphgen_config["split"])
            
            if graphgen_config["if_trainee_model"]:
                graph_gen.quiz_and_judge(quiz_and_judge_config=graphgen_config["quiz_and_judge"])
            
            # 添加进度回调来实时更新任务状态
            def update_progress(current_count, total_batches):
                if total_batches > 0:
                    # 定期更新进度（每处理10%更新一次）
                    if current_count % max(1, total_batches // 10) == 0:
                        # 尝试从临时文件读取当前已生成的问答对数量
                        temp_file = os.path.join(working_dir, "temp_output.json")
                        if os.path.exists(temp_file):
                            try:
                                with open(temp_file, "r", encoding="utf-8") as f:
                                    temp_data = json.load(f)
                                    temp_count = len(temp_data) if isinstance(temp_data, list) else 0
                                    # 更新任务状态但不改变状态
                                    if temp_count > 0:
                                        task_manager.update_task_status(
                                            task_id,
                                            TaskStatus.PROCESSING,
                                            qa_count=temp_count
                                        )
                            except:
                                pass
            
            # 在生成过程中定期保存临时输出
            graph_gen.generate(
                partition_config=graphgen_config["partition"],
                generate_config=graphgen_config["generate"],
            )
            
            # 保存输出
            output_data = graph_gen.qa_storage.data
            output_file = task_manager.get_task_output_path(task_id)
            
            # 验证输出数据
            if not output_data or len(output_data) == 0:
                raise Exception("数据生成失败：未生成任何问答对。请检查 API key 是否正确，以及 LLM 服务是否可用。")
            
            # 保存完整输出（包含 context 和 graph）
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)
            
            # 计算 token 使用量
            def sum_tokens(client):
                return sum(u["total_tokens"] for u in client.token_usage)
            
            synthesizer_tokens = sum_tokens(graph_gen.synthesizer_llm_client)
            trainee_tokens = (
                sum_tokens(graph_gen.trainee_llm_client)
                if graphgen_config["if_trainee_model"]
                else 0
            )
            total_tokens = synthesizer_tokens + trainee_tokens
            
            # 验证 token 使用量
            if total_tokens == 0:
                raise Exception("数据生成失败：未使用任何 token。请检查 API key 是否正确，以及 LLM 服务是否可用。")
            
            token_usage = {
                "synthesizer_tokens": synthesizer_tokens,
                "trainee_tokens": trainee_tokens,
                "total_tokens": total_tokens
            }
            
            # 计算问答对数量
            qa_count = len(output_data) if output_data else 0
            
            # 更新任务状态为完成
            task_manager.update_task_status(
                task_id,
                TaskStatus.COMPLETED,
                output_file=output_file,
                token_usage=token_usage,
                qa_count=qa_count
            )
            
            # 清理工作目录
            cleanup_workspace(working_dir)
            
        except Exception as e:
            # 更新任务状态为失败
            task_manager.update_task_status(
                task_id,
                TaskStatus.FAILED,
                error_message=str(e)
            )
    
    def _build_config(self, config: TaskConfig, filepaths: list) -> Dict[str, Any]:
        """构建配置字典"""
        method = config.partition_method
        if method == "dfs":
            partition_params = {"max_units_per_community": config.dfs_max_units}
        elif method == "bfs":
            partition_params = {"max_units_per_community": config.bfs_max_units}
        elif method == "leiden":
            partition_params = {
                "max_size": config.leiden_max_size,
                "use_lcc": config.leiden_use_lcc,
                "random_seed": config.leiden_random_seed,
            }
        else:  # ece
            partition_params = {
                "max_units_per_community": config.ece_max_units,
                "min_units_per_community": config.ece_min_units,
                "max_tokens_per_community": config.ece_max_tokens,
                "unit_sampling": config.ece_unit_sampling,
            }
        
        # 支持多文件：使用第一个文件或合并多个文件
        # 这里简化处理，使用第一个文件
        # TODO: 未来可以支持多文件合并处理
        input_file = filepaths[0] if filepaths else ""
        
        # 处理 mode：支持数组格式
        # 如果 mode 是数组，根据情况转换为字符串
        mode = config.mode
        if isinstance(mode, list):
            if len(mode) == 0:
                mode = "aggregated"  # 默认值
            elif len(mode) == 1:
                mode = mode[0]
            else:
                # 如果选择了多个模式，检查是否包含所有4种模式
                all_modes = {"atomic", "multi_hop", "aggregated", "cot"}
                selected_modes = set(mode)
                if selected_modes == all_modes:
                    mode = "all"  # 如果选择了所有模式，使用 "all"
                else:
                    # 如果选择了部分模式，也使用 "all"（因为 GraphGen 目前只支持单个模式或 "all"）
                    # 或者可以提示用户，这里选择使用 "all" 以生成所有模式的数据
                    mode = "all"
        
        mode_ratios = {
            "atomic": float(getattr(config, "qa_ratio_atomic", 25.0)),
            "aggregated": float(getattr(config, "qa_ratio_aggregated", 25.0)),
            "multi_hop": float(getattr(config, "qa_ratio_multi_hop", 25.0)),
            "cot": float(getattr(config, "qa_ratio_cot", 25.0)),
        }

        result = {
            "if_trainee_model": config.if_trainee_model,
            "tokenizer": config.tokenizer,
            "read": {"input_file": input_file},
            "split": {
                "chunk_size": config.chunk_size,
                "chunk_overlap": config.chunk_overlap,
                # 优化配置
                "dynamic_chunk_size": getattr(config, "dynamic_chunk_size", False),
                "enable_extraction_cache": getattr(config, "enable_extraction_cache", True),
                "enable_batch_requests": getattr(config, "enable_batch_requests", True),
                "batch_size": getattr(config, "batch_size", 10),
                "max_wait_time": getattr(config, "max_wait_time", 0.5),
            },
            "search": {"enabled": False},
            "quiz_and_judge": {
                "enabled": config.if_trainee_model,
                "quiz_samples": config.quiz_samples,
                # 批量请求配置
                "enable_batch_requests": getattr(config, "enable_batch_requests", True),
                "batch_size": getattr(config, "batch_size", 10),
                "max_wait_time": getattr(config, "max_wait_time", 0.5),
            },
            "partition": {
                "method": config.partition_method,
                "method_params": partition_params,
            },
            "generate": {
                "mode": mode,
                "data_format": config.data_format,
                # 优化配置
                "use_multi_template": getattr(config, "use_multi_template", True),
                "template_seed": getattr(config, "template_seed", None),
                # 批量请求配置
                "enable_batch_requests": getattr(config, "enable_batch_requests", True),
                "batch_size": getattr(config, "batch_size", 10),
                "max_wait_time": getattr(config, "max_wait_time", 0.5),
                # 生成数量与比例
                "target_qa_pairs": getattr(config, "qa_pair_limit", None),
                "mode_ratios": mode_ratios,
            },
        }
        
        # 记录配置信息用于调试
        qa_limit = getattr(config, "qa_pair_limit", None)
        if qa_limit:
            logger.info(
                "[TaskProcessor] Target QA pairs configured: %d, Mode: %s, Mode ratios: %s",
                qa_limit, mode, mode_ratios
            )
        else:
            logger.info("[TaskProcessor] No QA pair limit configured (unlimited generation)")
        
        return result
    
    def _build_env(self, config: TaskConfig) -> Dict[str, Any]:
        """构建环境变量字典"""
        return {
            "TOKENIZER_MODEL": config.tokenizer,
            "SYNTHESIZER_BASE_URL": config.synthesizer_url,
            "SYNTHESIZER_MODEL": config.synthesizer_model,
            "TRAINEE_BASE_URL": config.trainee_url,
            "TRAINEE_MODEL": config.trainee_model,
            "SYNTHESIZER_API_KEY": config.api_key,
            "TRAINEE_API_KEY": config.trainee_api_key or config.api_key,
            "RPM": config.rpm,
            "TPM": config.tpm,
        }

