import logging
from logging.handlers import RotatingFileHandler

from rich.logging import RichHandler

logger = logging.getLogger("graphgen")


def set_logger(
    log_file: str,
    file_level: int = logging.DEBUG,
    console_level: int = logging.INFO,
    *,
    if_stream: bool = True,
    max_bytes: int = 50 * 1024 * 1024,  # 50 MB
    backup_count: int = 5,
    force: bool = False,
):
    """
    Set up logger with file and console handlers.
    
    Args:
        log_file: Path to log file
        file_level: Logging level for file handler
        console_level: Logging level for console handler
        if_stream: Whether to add console handler
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup log files to keep
        force: Force reconfiguration even if handlers exist
    """
    import os
    
    # 确保日志文件目录存在
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    
    # 如果已经有 handlers 且不强制重新配置，检查是否需要更新文件路径
    if logger.hasHandlers() and not force:
        # 检查当前的文件 handler 是否指向同一个文件
        file_handlers = [h for h in logger.handlers if isinstance(h, RotatingFileHandler)]
        if file_handlers:
            current_log_file = file_handlers[0].baseFilename
            if os.path.abspath(current_log_file) == os.path.abspath(log_file):
                # 同一个文件，不需要重新配置
                return
            else:
                # 不同的文件，需要重新配置
                logger.handlers.clear()
        else:
            # 没有文件 handler，需要添加
            logger.handlers.clear()
    elif force:
        logger.handlers.clear()

    logger.setLevel(
        min(file_level, console_level)
    )  # Set to the lowest level to capture all logs
    logger.propagate = False

    if logger.handlers:
        logger.handlers.clear()

    if if_stream:
        console = RichHandler(
            level=console_level, show_path=False, rich_tracebacks=True
        )
        console.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(console)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(file_level)
    file_handler.setFormatter(
        logging.Formatter(
            "[%(asctime)s] %(levelname)s [%(name)s:%(filename)s:%(lineno)d] %(message)s",
            datefmt="%y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(file_handler)


def parse_log(log_file: str):
    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return lines
