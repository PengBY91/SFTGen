from .cache import cleanup_workspace, setup_workspace
from .count_tokens import count_tokens

# preview_file 仅在 Gradio Web UI 中使用，可选导入以避免 gradio 依赖
try:
    from .preview_file import preview_file
except ImportError:
    # 如果没有 gradio，提供一个占位函数
    def preview_file(file):
        """占位函数，仅在 Gradio 环境中可用"""
        raise ImportError("preview_file requires gradio. Install gradio to use this function.")
