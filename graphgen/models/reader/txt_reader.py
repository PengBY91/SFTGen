from typing import Any, Dict, List

from graphgen.bases.base_reader import BaseReader


class TXTReader(BaseReader):
    def read(self, file_path: str) -> List[Dict[str, Any]]:
        docs = []
        with open(file_path, "r", encoding="utf-8") as f:
            docs.append({
                        self.text_column: f.read(),
                        "type": "text"  # 明确标记为文本类型
                    })
        return self.filter(docs)
