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
    
    async def process_task(self, task_id: str, config: TaskConfig):
        """处理任务的具体逻辑"""
        cache_folder = None
        working_dir = None
        log_file = None
        synthesizer_llm_client = None
        trainee_llm_client = None
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
                api_key=config.api_key.strip() if config.api_key else None,
                request_limit=True,
                rpm=RPM(config.rpm),
                tpm=TPM(config.tpm),
                tokenizer=tokenizer_instance,
            )
            trainee_llm_client = OpenAIClient(
                model_name=config.trainee_model,
                base_url=config.trainee_url,
                api_key=(config.trainee_api_key or config.api_key).strip() if (config.trainee_api_key or config.api_key) else None,
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
            
            # Bypass async_to_sync_method wrapper by calling __wrapped__ directly
            await graph_gen.clear.__wrapped__(graph_gen)
            
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
                await graph_gen.insert.__wrapped__(graph_gen, read_config=file_read_config, split_config=graphgen_config["split"])
            
            logger.info(f"[TaskProcessor] 所有文件处理完成，共处理 {len(filepaths)} 个文件")
            
            if graphgen_config["if_trainee_model"]:
                await graph_gen.quiz_and_judge.__wrapped__(graph_gen, quiz_and_judge_config=graphgen_config["quiz_and_judge"])
            
            # 根据任务类型执行不同的生成逻辑
            if task.task_type == "evaluation":
                # 评测任务：只生成评测集
                logger.info(f"[TaskProcessor] 评测任务：开始生成评测集")
                await graph_gen.generate_evaluation.__wrapped__(
                    graph_gen,
                    partition_config=graphgen_config["partition"],
                    evaluation_config=graphgen_config.get("evaluation", {})
                )
                logger.info(f"[TaskProcessor] 评测集生成完成")
                
                # 对于评测任务，检查评测数据文件
                eval_data_dir = os.path.join(working_dir, "data", "evaluation")
                eval_files = []
                if os.path.exists(eval_data_dir):
                    eval_files = [f for f in os.listdir(eval_data_dir) if f.endswith('.json')]
                
                if not eval_files:
                    raise ValueError("评测集生成失败：未生成任何评测数据文件")
                
                # 使用第一个评测文件作为源文件
                source_file = os.path.join(eval_data_dir, eval_files[0])
                logger.info(f"[TaskProcessor] 源评测数据文件: {source_file}")
                
                # 复制到期望的文件名（使用task_id而不是unique_id）
                expected_file = os.path.join(eval_data_dir, f"{task_id}_eval.json")
                if source_file != expected_file:
                    import shutil as sh
                    sh.copy2(source_file, expected_file)
                    logger.info(f"[TaskProcessor] 已复制评测文件到: {expected_file}")
                
                # 同时复制到永久位置（cache_folder下），避免被working_dir清理删除
                permanent_eval_dir = os.path.join(cache_folder, "data", "evaluation")
                os.makedirs(permanent_eval_dir, exist_ok=True)
                permanent_eval_file = os.path.join(permanent_eval_dir, f"{task_id}_eval.json")
                sh.copy2(expected_file, permanent_eval_file)
                logger.info(f"[TaskProcessor] 已复制评测文件到永久位置: {permanent_eval_file}")
                
                # 使用永久位置的文件作为输出文件
                output_file = permanent_eval_file
                logger.info(f"[TaskProcessor] 最终评测数据文件: {output_file}")
                
                # 读取评测数据统计信息
                try:
                    with open(output_file, 'r', encoding='utf-8') as f:
                        eval_data = json.load(f)
                    
                    # 获取评测项数量
                    eval_count = len(eval_data.get('items', []))
                    logger.info(f"[TaskProcessor] 评测集包含 {eval_count} 个评测项")
                    
                    # 获取token使用统计（与SFT任务相同）
                    synthesizer_usage = graph_gen.synthesizer_llm_client.get_usage()
                    trainee_usage = graph_gen.trainee_llm_client.get_usage() if graph_gen.trainee_llm_client else {"total": 0, "input": 0, "output": 0}
                    
                    total_tokens = synthesizer_usage["total"] + trainee_usage["total"]
                    total_input_tokens = synthesizer_usage["input"] + trainee_usage["input"]
                    total_output_tokens = synthesizer_usage["output"] + trainee_usage["output"]
                    
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
                    
                    logger.info(f"[TaskProcessor] Token使用统计 - 总计: {total_tokens}, 输入: {total_input_tokens}, 输出: {total_output_tokens}")
                    
                    # 更新任务状态为完成（评测任务）
                    task_manager.update_task_status(
                        task_id,
                        TaskStatus.COMPLETED,
                        output_file=output_file,
                        token_usage=token_usage,
                        qa_count=eval_count  # 使用评测项数量
                    )
                except Exception as e:
                    logger.error(f"[TaskProcessor] 读取评测数据失败: {e}")
                    raise ValueError(f"读取评测数据失败: {e}")
                
            else:
                # SFT任务：生成训练数据
                logger.info("[TaskProcessor] SFT任务：开始生成训练数据")
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
                await graph_gen.generate.__wrapped__(
                    graph_gen,
                    partition_config=graphgen_config["partition"],
                    generate_config=graphgen_config["generate"],
                )
                logger.info(f"[TaskProcessor] 训练数据生成完成")
                
                # 检查生成的数据
                output_data = graph_gen.qa_storage.get_all()
                if not output_data:
                    raise ValueError("数据生成失败：未生成任何问答对。请检查 API key 是否正确，以及 LLM 服务是否可用。")
                
                # 保存输出文件到永久位置（cache_folder下），与评测任务保持一致
                permanent_data_dir = os.path.join(cache_folder, "data")
                os.makedirs(permanent_data_dir, exist_ok=True)
                output_file = os.path.join(permanent_data_dir, f"{task_id}_output.json")
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(output_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"[TaskProcessor] 输出文件已保存到永久位置: {output_file}")
                
                # 获取token使用统计
                synthesizer_usage = graph_gen.synthesizer_llm_client.get_usage()
                trainee_usage = graph_gen.trainee_llm_client.get_usage() if graph_gen.trainee_llm_client else {"total": 0, "input": 0, "output": 0}
                
                total_tokens = synthesizer_usage["total"] + trainee_usage["total"]
                total_input_tokens = synthesizer_usage["input"] + trainee_usage["input"]
                total_output_tokens = synthesizer_usage["output"] + trainee_usage["output"]
                
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
                
                # 更新任务状态为完成（SFT任务）
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
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"[TaskProcessor] Task failed: {e}\n{error_trace}")
            
            task_manager.update_task_status(
                task_id,
                TaskStatus.FAILED,
                error_message=str(e)
            )
            # 记录错误日志
            if log_file:
                logger.error(f"[TaskProcessor] 任务失败，日志文件: {log_file}")
        
        finally:
            # 清理资源
            try:
                if synthesizer_llm_client:
                    try:
                        await synthesizer_llm_client.aclose()
                    except Exception as e:
                        logger.debug(f"[TaskProcessor] Failed to close synthesizer client: {e}")
                
                if trainee_llm_client:
                    try:
                        await trainee_llm_client.aclose()
                    except Exception as e:
                        logger.debug(f"[TaskProcessor] Failed to close trainee client: {e}")
            except Exception as e:
                logger.debug(f"[TaskProcessor] Error during client cleanup: {e}")
            
            # 清理临时工作目录（但保留日志文件）
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
        selected_modes = set()  # 记录用户选择的模式
        
        if isinstance(mode, list):
            if len(mode) == 0:
                mode = "aggregated"  # 默认值
                selected_modes = {"aggregated"}
            elif len(mode) == 1:
                mode = mode[0]
                selected_modes = {mode}
            else:
                # 用户选择了多个模式
                selected_modes = set(mode)
                all_modes = {"atomic", "multi_hop", "aggregated", "cot"}
                
                if selected_modes == all_modes:
                    # 如果选择了所有4种模式，使用 "all"
                    mode = "all"
                else:
                    # 如果选择了部分模式（2个或3个），也使用 "all"
                    # 但通过 mode_ratios 控制只生成选中的模式
                    mode = "all"
                    logger.info(
                        "[TaskProcessor] 用户选择了部分模式: %s，将使用 mode='all' 但只生成选中的模式",
                        selected_modes
                    )
        else:
            # mode 是字符串
            if mode == "all":
                selected_modes = {"atomic", "multi_hop", "aggregated", "cot"}
            else:
                selected_modes = {mode}
        
        # 构建 mode_ratios，未选中的模式设置为 0
        all_mode_names = {"atomic", "aggregated", "multi_hop", "cot"}
        mode_ratios = {}
        
        for mode_name in all_mode_names:
            ratio_attr = f"qa_ratio_{mode_name}"
            configured_ratio = float(getattr(config, ratio_attr, 25.0))
            
            # 如果模式未被选中，强制设置为 0
            if mode_name not in selected_modes:
                mode_ratios[mode_name] = 0.0
            else:
                mode_ratios[mode_name] = configured_ratio
        
        # 记录最终的 mode_ratios
        logger.info(
            "[TaskProcessor] 选择的模式: %s，mode_ratios: %s",
            selected_modes, mode_ratios
        )

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
                "chinese_only": getattr(config, "chinese_only", False),  # 添加 chinese_only 配置
                # 批量请求配置（问题生成阶段）
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
            "evaluation": {
                "enabled": getattr(config, "evaluation_enabled", False),
                "dataset_name": getattr(config, "evaluation_dataset_name", "Domain Knowledge Evaluation Dataset"),
                "description": getattr(config, "evaluation_description", "Evaluation dataset for domain model assessment"),
                "target_eval_items": getattr(config, "evaluation_target_items", 200),
                "type_distribution": getattr(config, "evaluation_type_distribution", {
                    "knowledge_coverage": 0.3,
                    "reasoning_ability": 0.3,
                    "factual_accuracy": 0.2,
                    "comprehensive": 0.2,
                }),
                "difficulty_distribution": getattr(config, "evaluation_difficulty_distribution", {
                    "easy": 0.3,
                    "medium": 0.5,
                    "hard": 0.2,
                }),
                "output_format": getattr(config, "evaluation_output_format", "benchmark"),
                "min_quality_score": getattr(config, "evaluation_min_quality_score", 0.5),
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

