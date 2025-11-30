"""
LLM 响应修复工具

提供统一的 LLM 响应格式修复和清理功能，确保响应可以被正确解析
"""

import re
import json
from typing import Optional, Dict, Any
from graphgen.utils import logger


def clean_markdown_code_blocks(text: str) -> str:
    """
    清理 Markdown 代码块标记
    
    很多 LLM 会在输出中包含 ```json 或 ``` 等标记
    """
    if not text:
        return text
    
    # 移除开头的代码块标记（支持更多语言标识）
    text = re.sub(r'^```(?:json|python|text|markdown|xml|yaml|txt)?\s*\n?', '', text, flags=re.MULTILINE)
    # 移除结尾的代码块标记
    text = re.sub(r'\n?```\s*$', '', text, flags=re.MULTILINE)
    
    # 移除中间可能出现的独立代码块标记
    text = re.sub(r'\n```\n', '\n', text)
    
    return text


def clean_common_llm_artifacts(text: str) -> str:
    """
    清理常见的 LLM 输出伪影
    
    - 移除前导/尾随的元描述
    - 清理多余的空行
    - 统一换行符
    """
    if not text:
        return text
    
    # 常见的 LLM 前导语模式（更全面）
    preamble_patterns = [
        r'^(?:好的|好|OK|Sure|Certainly|Here is|Here are|Here\'s|以下是)[，,。.:：!！]\s*',
        r'^(?:根据|Based on).*?(?:文本|内容|text|content)[，,]?\s*',
        r'^(?:让我|I will|Let me).*?[：:]\s*',
        r'^(?:下面|Below|Following)(?:是|are).*?[：:]\s*',
        r'^(?:这是|This is).*?[：:]\s*',
        # 清理可能的编号前缀
        r'^\d+\.\s*(?:好的|OK|Here is).*?[：:]\s*',
    ]
    
    for pattern in preamble_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)
    
    # 统一换行符
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # 清理多余的空行（保留最多一个空行）
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # 清理首尾空白
    text = text.strip()
    
    return text


def repair_json_like_text(text: str) -> str:
    """
    尝试修复类似 JSON 的文本
    
    主要用于处理 LLM 输出的结构化数据
    """
    # 修复常见的 JSON 错误
    # 1. 单引号转双引号（但要小心字符串内容）
    # 这个比较复杂，暂时跳过
    
    # 2. 修复缺失的逗号（在对象/数组元素之间）
    # 例如: {"a": 1}\n{"b": 2} -> {"a": 1},{"b": 2}
    text = re.sub(r'}\s*\n\s*{', '},\n{', text)
    text = re.sub(r']\s*\n\s*\[', '],\n[', text)
    
    # 3. 移除尾随逗号
    text = re.sub(r',\s*([}\]])', r'\1', text)
    
    return text


def repair_text_markers(text: str, expected_markers: list[str]) -> str:
    """
    修复文本标记问题
    
    对于合并提取等场景，LLM 可能不按照预期的标记格式输出
    尝试智能修复或添加标记
    
    :param text: LLM 响应文本
    :param expected_markers: 期望的标记列表，如 ["[文本1]", "[文本2]", ...]
    :return: 修复后的文本
    """
    if not text or not expected_markers:
        return text
    
    # 1. 标准化标记格式（中英文括号、空格等）
    # 将 [文本 1] 或 [ 文本1 ] 统一为 [文本1]
    text = re.sub(r'\[\s*文本\s*(\d+)\s*\]', r'[文本\1]', text)
    text = re.sub(r'\[\s*Text\s*(\d+)\s*\]', r'[Text \1]', text)
    
    # 2. 将全角括号转换为半角
    text = text.replace('【', '[').replace('】', ']')
    text = text.replace('（', '(').replace('）', ')')
    
    # 3. 修复可能的标记变体
    # 文本1: -> [文本1]
    text = re.sub(r'(?:^|\n)文本\s*(\d+)\s*[：:]\s*', r'\n[文本\1]\n', text)
    text = re.sub(r'(?:^|\n)Text\s*(\d+)\s*[：:]\s*', r'\n[Text \1]\n', text)
    
    # 4. 检查是否缺少标记
    found_markers = []
    for marker in expected_markers:
        if marker in text or marker.replace('[文本', '[Text ') in text:
            found_markers.append(marker)
    
    logger.debug(
        "Text markers check: expected %d, found %d markers",
        len(expected_markers), len(found_markers)
    )
    
    # 5. 如果缺少大部分标记，尝试智能插入
    if len(found_markers) < len(expected_markers) * 0.5:
        logger.warning(
            "Missing more than 50%% of expected markers (%d/%d), "
            "will fallback to duplicate extraction",
            len(found_markers), len(expected_markers)
        )
        # 尝试基于内容分段（简单启发式）
        # 如果响应中有明显的分隔符，尝试智能分段
        if '\n\n' in text or '---' in text or '###' in text:
            logger.debug("Attempting heuristic text segmentation")
            # 暂时返回原文，让 fallback 逻辑处理
            # 未来可以实现更复杂的分段逻辑
    
    return text


def extract_structured_content(text: str, start_marker: str, end_marker: str) -> Optional[str]:
    """
    从文本中提取指定标记之间的内容
    
    :param text: 源文本
    :param start_marker: 开始标记（支持正则）
    :param end_marker: 结束标记（支持正则）
    :return: 提取的内容，如果找不到则返回 None
    """
    pattern = f"{start_marker}(.*?){end_marker}"
    match = re.search(pattern, text, flags=re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def repair_kg_extraction_format(text: str) -> str:
    """
    修复知识图谱抽取格式
    
    确保输出符合预期的实体和关系格式:
    ("entity"<|>type<|>description)
    ("src"<|>"relation"<|>"tgt"<|>description)
    """
    if not text:
        return text
    
    # 1. 标准化分隔符
    # 如果 LLM 使用了其他分隔符，尝试替换
    # 常见错误: 使用 | 而不是 <|>
    # 但要避免替换引号内的 |
    text = re.sub(r'(?<!")(\|)(?!")', '<|>', text)
    
    # 2. 修复全角标点
    text = text.replace('，', ',').replace('。', '.')
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(''', "'").replace(''', "'")
    
    # 3. 修复括号问题
    # 确保每个记录都有完整的括号
    # 移除多余的空格
    text = re.sub(r'\(\s+', '(', text)
    text = re.sub(r'\s+\)', ')', text)
    
    # 4. 清理多余的分隔符
    text = re.sub(r'<\|>{2,}', '<|>', text)
    
    return text


def repair_qa_pair_format(text: str) -> str:
    """
    修复问答对格式
    
    确保输出包含清晰的问题和答案标记
    """
    if not text:
        return text
    
    # 1. 标准化问答标记
    # 将各种变体统一为标准格式
    
    # 问题标记变体（更全面的匹配）
    # 支持: Question:, 问题：, Q:, 问：等
    text = re.sub(r'^(?:问题|Question|Q)[：:]\s*', '问题：', text, flags=re.MULTILINE)
    text = re.sub(r'^(?:问)[：:]\s*', '问题：', text, flags=re.MULTILINE)
    # 处理可能的编号
    text = re.sub(r'^\d+\.\s*(?:问题|Question|Q)[：:]\s*', '问题：', text, flags=re.MULTILINE)
    
    # 答案标记变体
    text = re.sub(r'^(?:答案|Answer|A)[：:]\s*', '答案：', text, flags=re.MULTILINE)
    text = re.sub(r'^(?:答)[：:]\s*', '答案：', text, flags=re.MULTILINE)
    text = re.sub(r'^\d+\.\s*(?:答案|Answer|A)[：:]\s*', '答案：', text, flags=re.MULTILINE)
    
    # 2. 如果同时存在中英文标记，统一为中文
    if '问题：' in text and 'Question:' in text:
        text = text.replace('Question:', '问题：')
        text = text.replace('Answer:', '答案：')
    
    # 3. 移除多余的标点和空格
    text = re.sub(r'[：:]{2,}', '：', text)
    
    # 4. 标准化冒号（全角转半角后再转回中文冒号）
    # 确保一致性
    text = re.sub(r'问题\s*:\s*', '问题：', text)
    text = re.sub(r'答案\s*:\s*', '答案：', text)
    
    return text


def try_parse_json(text: str) -> Optional[Dict[Any, Any]]:
    """
    尝试解析 JSON，如果失败则尝试修复后再解析
    
    :param text: JSON 文本
    :return: 解析后的字典，如果失败返回 None
    """
    # 首次尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # 清理和修复
    cleaned = clean_markdown_code_blocks(text)
    cleaned = clean_common_llm_artifacts(cleaned)
    cleaned = repair_json_like_text(cleaned)
    
    # 再次尝试解析
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse JSON even after repair: %s", str(e))
        logger.debug("Problematic JSON text: %s", cleaned[:500])
        return None


def repair_llm_response(
    response: str,
    expected_format: str = "general",
    **kwargs
) -> str:
    """
    统一的 LLM 响应修复入口
    
    :param response: LLM 原始响应
    :param expected_format: 期望的格式类型
        - "general": 通用清理
        - "kg_extraction": 知识图谱抽取
        - "qa_pair": 问答对
        - "text_markers": 带文本标记的合并响应
    :param kwargs: 格式特定的参数
    :return: 修复后的响应
    """
    # 1. 空值检查
    if not response:
        logger.warning("Empty or None response received for repair")
        return response if response is not None else ""
    
    if not response.strip():
        logger.warning("Response contains only whitespace")
        return response
    
    # 2. 异常捕获：确保修复过程不会崩溃
    try:
        # 通用清理（所有格式都需要）
        repaired = clean_markdown_code_blocks(response)
        repaired = clean_common_llm_artifacts(repaired)
        
        # 格式特定的修复
        if expected_format == "kg_extraction":
            repaired = repair_kg_extraction_format(repaired)
        elif expected_format == "qa_pair":
            repaired = repair_qa_pair_format(repaired)
        elif expected_format == "text_markers":
            expected_markers = kwargs.get("expected_markers", [])
            if expected_markers:
                repaired = repair_text_markers(repaired, expected_markers)
            else:
                logger.warning("text_markers format specified but no expected_markers provided")
        
        # 3. 最终验证：确保返回的内容不为空
        if not repaired or not repaired.strip():
            logger.warning(
                "Repair resulted in empty output, returning original response. "
                "Original length: %d, format: %s",
                len(response), expected_format
            )
            return response
        
        return repaired
        
    except Exception as e:
        logger.error(
            "Error during response repair (format: %s): %s. Returning original response.",
            expected_format, str(e)
        )
        # 发生任何错误时，返回原始响应而不是崩溃
        return response

