from typing import Any, Dict, List

from graphgen.bases.base_reader import BaseReader

try:
    from docx import Document
except ImportError:
    raise ImportError(
        "python-docx is required for reading Word documents. "
        "Please install it using: pip install python-docx"
    )


class DOCXReader(BaseReader):
    """
    Reader for Microsoft Word (.docx) files.
    Extracts text content from Word documents while preserving paragraph structure.
    """
    
    def read(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Read text content from a .docx file.
        
        :param file_path: Path to the .docx file.
        :return: List containing a single dictionary with the document content.
        """
        try:
            doc = Document(file_path)
            # Extract text from all paragraphs
            paragraphs = []
            for para in doc.paragraphs:
                if para.text.strip():  # Only include non-empty paragraphs
                    paragraphs.append(para.text)
            
            # Join paragraphs with newlines to preserve structure
            full_text = "\n\n".join(paragraphs)
            
            # Also extract text from tables if present
            tables_text = []
            for table in doc.tables:
                table_rows = []
                for row in table.rows:
                    row_cells = []
                    for cell in row.cells:
                        if cell.text.strip():
                            row_cells.append(cell.text.strip())
                    if row_cells:
                        table_rows.append(" | ".join(row_cells))
                if table_rows:
                    tables_text.append("\n".join(table_rows))
            
            # Combine paragraphs and tables
            if tables_text:
                full_text += "\n\n--- Tables ---\n\n" + "\n\n".join(tables_text)
            
            docs = [{
                self.text_column: full_text,
                "type": "text"
            }]
            
            return self.filter(docs)
        except Exception as e:
            raise ValueError(f"Failed to read Word document {file_path}: {str(e)}")

