"""
任务处理器
负责执行具体的KGE-Gen任务
"""

import os
import sys
import json
import shutil
from typing import Dict, Any
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from graphgen.graphgen import GraphGen
from graphgen.models import OpenAIClient, Tokenizer
from graphgen.models.llm.limitter import RPM, TPM
from graphgen.utils import set_logger, logger
from webui.task_manager import task_manager, TaskStatus
from webui.utils import setup_workspace
from backend.schemas import TaskConfig


class TaskProcessor:
    """任务处理器"""
    
    def process_task(self, task_id: str, config: TaskConfig):
        """处理任务的具体逻辑"""
        cache_folder = None
        working_dir = None
        log_file = None
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
            
            # 设置工作目录（文件夹名称前面加上时间戳）
            time_prefix = datetime.now().strftime("%Y%m%d_%H%M%S")
            cache_folder = os.path.join("cache", f"{time_prefix}-{task_id}")
            log_file, working_dir = setup_workspace(cache_folder)
            
            # 确保日志文件目录存在
            log_dir = os.path.dirname(log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            
            # 强制重新配置 logger，确保使用新的日志文件
            set_logger(log_file, if_stream=True, force=True)
            logger.info(f"[TaskProcessor] 任务 {task_id} 开始处理，日志文件: {log_file}")
            
            # 保存日志文件路径，用于后续保留日志
            self._current_log_file = log_file
            os.environ.update({k: str(v) for k, v in env.items()})
            
            # 初始化 KGE-Gen
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
            
            # 处理多个文件：循环处理每个文件，累积到知识图谱中
            filepaths = task.filepaths if task.filepaths else []
            if not filepaths:
                raise Exception("任务没有关联的文件")
            
            logger.info(f"[TaskProcessor] 开始处理 {len(filepaths)} 个文件")
            for idx, filepath in enumerate(filepaths, 1):
                if not os.path.exists(filepath):
                    logger.warning(f"[TaskProcessor] 文件不存在，跳过: {filepath}")
                    continue
                
                logger.info(f"[TaskProcessor] 正在处理文件 {idx}/{len(filepaths)}: {filepath}")
                # 为每个文件创建读取配置
                file_read_config = {"input_file": filepath}
                # 对每个文件调用 insert，知识图谱会累积所有文件的内容
                graph_gen.insert(read_config=file_read_config, split_config=graphgen_config["split"])
            
            logger.info(f"[TaskProcessor] 所有文件处理完成，共处理 {len(filepaths)} 个文件")
            
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
            
            # 计算 token 使用量（区分 input 和 output）
            def sum_tokens(client):
                total = sum(u["total_tokens"] for u in client.token_usage)
                prompt = sum(u.get("prompt_tokens", 0) for u in client.token_usage)
                completion = sum(u.get("completion_tokens", 0) for u in client.token_usage)
                return {
                    "total": total,
                    "input": prompt,
                    "output": completion
                }
            
            synthesizer_usage = sum_tokens(graph_gen.synthesizer_llm_client)
            trainee_usage = (
                sum_tokens(graph_gen.trainee_llm_client)
                if graphgen_config["if_trainee_model"]
                else {"total": 0, "input": 0, "output": 0}
            )
            
            total_tokens = synthesizer_usage["total"] + trainee_usage["total"]
            total_input_tokens = synthesizer_usage["input"] + trainee_usage["input"]
            total_output_tokens = synthesizer_usage["output"] + trainee_usage["output"]
            
            # 验证 token 使用量
            if total_tokens == 0:
                raise Exception("数据生成失败：未使用任何 token。请检查 API key 是否正确，以及 LLM 服务是否可用。")
            
            token_usage = {
                "synthesizer_tokens": synthesizer_usage["total"],
                "synthesizer_input_tokens": synthesizer_usage["input"],
                "synthesizer_output_tokens": synthesizer_usage["output"],
                "trainee_tokens": trainee_usage["total"],
                "trainee_input_tokens": trainee_usage["input"],
                "trainee_output_tokens": trainee_usage["output"],
                "total_tokens": total_tokens,
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens
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
            
            # 清理临时工作目录（但保留日志文件）
            # 只删除 working_dir，保留 logs 目录和日志文件
            if working_dir and os.path.exists(working_dir):
                try:
                    shutil.rmtree(working_dir)
                    logger.info(f"[TaskProcessor] 已清理临时工作目录: {working_dir}")
                except Exception as e:
                    logger.warning(f"[TaskProcessor] 清理工作目录失败: {e}")
            
            # 记录日志文件路径，确保日志被保留
            if log_file:
                logger.info(f"[TaskProcessor] 任务完成，日志文件已保存: {log_file}")
            
        except Exception as e:
            # 更新任务状态为失败
            task_manager.update_task_status(
                task_id,
                TaskStatus.FAILED,
                error_message=str(e)
            )
            # 记录错误日志
            if log_file:
                logger.error(f"[TaskProcessor] 任务失败，日志文件: {log_file}")
        
        finally:
            # 清理临时工作目录（但保留日志文件）
            # 只删除 working_dir，保留 logs 目录和日志文件
            # 注意：不要删除整个 cache_folder，因为 logs 目录在其中
            if working_dir and os.path.exists(working_dir):
                try:
                    shutil.rmtree(working_dir)
                    logger.info(f"[TaskProcessor] 已清理临时工作目录: {working_dir}")
                except Exception as e:
                    logger.warning(f"[TaskProcessor] 清理工作目录失败: {e}")
            
            # 确保日志文件被保留
            if log_file:
                logger.info(f"[TaskProcessor] 日志文件已保存: {log_file}")
    
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
        
        # 注意：多文件处理已在 process_task 方法中实现
        # 这里保留 input_file 字段以保持配置结构兼容性，但实际不会被使用
        # 因为 process_task 会循环处理每个文件
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
                    # 如果选择了部分模式，也使用 "all"（因为 KGE-Gen 目前只支持单个模式或 "all"）
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
                # 批量生成配置（问题生成阶段）
                "enable_batch_requests": getattr(config, "enable_batch_requests", True),
                "batch_size": getattr(config, "batch_size", 10),
                "max_wait_time": getattr(config, "max_wait_time", 0.5),
                "use_adaptive_batching": getattr(config, "use_adaptive_batching", False),
                "min_batch_size": getattr(config, "min_batch_size", 5),
                "max_batch_size": getattr(config, "max_batch_size", 50),
                "enable_prompt_cache": getattr(config, "enable_prompt_cache", True),
                "cache_max_size": getattr(config, "cache_max_size", 10000),
                "cache_ttl": getattr(config, "cache_ttl", None),
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

