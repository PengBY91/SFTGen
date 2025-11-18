import codecs
import os
from typing import Optional, Tuple, Any

try:
    import gradio as gr
    GRADIO_AVAILABLE = True
except ImportError:
    GRADIO_AVAILABLE = False
    # 创建一个占位类，用于类型注解
    class gr:
        @staticmethod
        def update(*args, **kwargs):
            raise ImportError("gradio is required for preview_file function")

import pandas as pd


def preview_file(file: Optional[Any]) -> Tuple[Any, Any]:
    """
    预览文件内容
    注意：此函数需要 gradio 库。如果没有安装 gradio，将抛出 ImportError。
    """
    if not GRADIO_AVAILABLE:
        raise ImportError("preview_file requires gradio. Install gradio to use this function.")
    
    if file is None:
        return gr.update(visible=False), gr.update(visible=False)

    path = file.name
    ext = os.path.splitext(path)[1].lower()

    try:
        if ext == ".csv":
            df = pd.read_csv(path, nrows=10)
            return gr.update(visible=False), gr.update(value=df, visible=True)
        with codecs.open(path, "r", encoding="utf-8") as f:
            text = f.read(5000)
            if len(text) == 5000:
                text += "\n\n... (truncated at 5000 chars)"
        return gr.update(
            value=text, visible=True, language="json" if ext != ".txt" else None
        ), gr.update(visible=False)
    except Exception as e:  # pylint: disable=broad-except
        return gr.update(
            value=f"Preview failed: {e}", visible=True, language=None
        ), gr.update(visible=False)
