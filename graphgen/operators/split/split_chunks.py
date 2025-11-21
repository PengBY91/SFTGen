from functools import lru_cache
from typing import Union

from tqdm.asyncio import tqdm as tqdm_async

from graphgen.models import (
    ChineseRecursiveTextSplitter,
    RecursiveCharacterSplitter,
    Tokenizer,
)
from graphgen.utils import compute_content_hash, detect_main_language

_MAPPING = {
    "en": RecursiveCharacterSplitter,
    "zh": ChineseRecursiveTextSplitter,
}

SplitterT = Union[RecursiveCharacterSplitter, ChineseRecursiveTextSplitter]


@lru_cache(maxsize=None)
def _get_splitter(language: str, frozen_kwargs: frozenset) -> SplitterT:
    cls = _MAPPING[language]
    kwargs = dict(frozen_kwargs)
    return cls(**kwargs)


def split_chunks(text: str, language: str = "en", **kwargs) -> list:
    if language not in _MAPPING:
        raise ValueError(
            f"Unsupported language: {language}. "
            f"Supported languages are: {list(_MAPPING.keys())}"
        )
    splitter = _get_splitter(language, frozenset(kwargs.items()))
    return splitter.split_text(text)


def calculate_optimal_chunk_size(
    text_length: int, 
    complexity_score: float = 0.5,
    base_size: int = 1024
) -> int:
    """
    Dynamically calculate optimal chunk size based on text length and complexity.
    
    :param text_length: Length of the text
    :param complexity_score: Complexity score (0.0-1.0), higher means more complex
    :param base_size: Base chunk size
    :return: Optimal chunk size
    """
    # Adjust based on text length
    if text_length > 100000:
        base_size = 2048
    elif text_length > 50000:
        base_size = 1536
    elif text_length < 10000:
        base_size = 512
    
    # Adjust based on complexity
    if complexity_score > 0.8:
        base_size = int(base_size * 0.8)  # Complex text uses smaller chunks
    elif complexity_score < 0.3:
        base_size = int(base_size * 1.2)  # Simple text can use larger chunks
    
    return max(256, min(base_size, 4096))  # Clamp between 256 and 4096


def estimate_complexity(text: str) -> float:
    """
    Estimate text complexity based on simple heuristics.
    
    :param text: Input text
    :return: Complexity score (0.0-1.0)
    """
    if not text:
        return 0.5
    
    # Simple heuristics: sentence length, punctuation density, special characters
    sentences = text.split('.')
    avg_sentence_length = sum(len(s) for s in sentences) / max(len(sentences), 1)
    
    # Normalize to 0-1 range
    complexity = min(1.0, avg_sentence_length / 200.0)
    
    # Adjust based on special characters (formulas, code, etc.)
    special_chars = sum(1 for c in text if c in '()[]{}<>$%^&*+=|\\/~`')
    if len(text) > 0:
        special_char_ratio = special_chars / len(text)
        complexity = max(complexity, special_char_ratio * 2)
    
    return min(1.0, complexity)


async def chunk_documents(
    new_docs: dict,
    chunk_size: int = 1024,
    chunk_overlap: int = 100,
    tokenizer_instance: Tokenizer = None,
    progress_bar=None,
    dynamic_chunk_size: bool = False,
) -> dict:
    inserting_chunks = {}
    cur_index = 1
    doc_number = len(new_docs)
    async for doc_key, doc in tqdm_async(
        new_docs.items(), desc="[1/4]Chunking documents", unit="doc"
    ):
        doc_type = doc.get("type")
        if doc_type == "text":
            doc_language = detect_main_language(doc["content"])
            
            # Dynamic chunk size adjustment if enabled
            actual_chunk_size = chunk_size
            if dynamic_chunk_size:
                complexity = estimate_complexity(doc["content"])
                actual_chunk_size = calculate_optimal_chunk_size(
                    len(doc["content"]),
                    complexity,
                    chunk_size
                )
                if actual_chunk_size != chunk_size:
                    logger.debug(
                        "Adjusted chunk_size from %d to %d for doc %s (complexity: %.2f)",
                        chunk_size, actual_chunk_size, doc_key, complexity
                    )
            
            text_chunks = split_chunks(
                doc["content"],
                language=doc_language,
                chunk_size=actual_chunk_size,
                chunk_overlap=chunk_overlap,
            )

            chunks = {
                compute_content_hash(txt, prefix="chunk-"): {
                    "content": txt,
                    "type": "text",
                    "full_doc_id": doc_key,
                    "length": len(tokenizer_instance.encode(txt))
                    if tokenizer_instance
                    else len(txt),
                    "language": doc_language,
                }
                for txt in text_chunks
            }
        else:
            chunks = {doc_key.replace("doc-", f"{doc_type}-"): {**doc}}

        inserting_chunks.update(chunks)

        if progress_bar is not None:
            progress_bar(cur_index / doc_number, f"Chunking {doc_key}")
            cur_index += 1

    return inserting_chunks
