from typing import Any, Dict, List

from graphgen.bases.base_reader import BaseReader


class MarkdownReader(BaseReader):
    """
    Reader for Markdown (.md, .markdown) files.
    Reads Markdown content as text while preserving the original formatting.
    """
    
    def read(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Read content from a Markdown file.
        
        :param file_path: Path to the Markdown file.
        :return: List containing a single dictionary with the document content.
        """
        docs = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                docs.append({
                    self.text_column: content,
                    "type": "text"  # Markdown content is treated as text
                })
        except UnicodeDecodeError:
            # Try with different encoding if UTF-8 fails
            with open(file_path, "r", encoding="latin-1") as f:
                content = f.read()
                docs.append({
                    self.text_column: content,
                    "type": "text"
                })
        return self.filter(docs)

