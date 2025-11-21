# 首先导入logger，确保其他模块可以使用
from .log import logger, parse_log, set_logger

from .calculate_confidence import yes_no_loss_entropy
from .detect_lang import detect_if_chinese, detect_main_language
from .device import pick_device
from .format import (
    handle_single_entity_extraction,
    handle_single_relationship_extraction,
    load_json,
    pack_history_conversations,
    split_string_by_multi_markers,
    write_json,
)
from .hash import compute_args_hash, compute_content_hash, compute_mm_hash
from .loop import create_event_loop
from .batch_request_manager import BatchRequestManager, batch_generate_answers
from .prompt_cache import PromptCache
from .adaptive_batch_manager import AdaptiveBatchRequestManager
from .run_concurrent import run_concurrent
from .temperature_scheduler import TemperatureScheduler
from .wrap import async_to_sync_method

# 可选依赖，如果导入失败不影响其他功能
try:
    from .help_nltk import NLTKHelper
except ImportError:
    # 如果jieba等依赖未安装，NLTKHelper不可用但不影响其他功能
    NLTKHelper = None
