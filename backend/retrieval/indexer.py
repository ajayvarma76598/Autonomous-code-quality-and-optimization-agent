"""
Legacy ASTIndexer — now delegates to UniversalCodeParser.
Kept for backward compatibility with existing code that imports ASTIndexer.
"""
from backend.retrieval.universal_parser import universal_parser, CodeNode
from typing import List


class ASTIndexer:
    """Backward-compatible wrapper around UniversalCodeParser."""
    
    def __init__(self):
        pass

    def parse_file(self, file_path: str, code_content: str) -> List[CodeNode]:
        """Parse a file using the universal tree-sitter parser."""
        return universal_parser.parse(file_path, code_content)
