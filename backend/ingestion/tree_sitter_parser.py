import logging
import os
from typing import Any

import tree_sitter_language_pack as tslp
from tree_sitter import Parser

logger = logging.getLogger(__name__)

# Map common file extensions to Tree-Sitter language names
LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "c_sharp",
    ".rb": "ruby",
    ".php": "php",
}


class CodeParser:
    def __init__(self):
        # We instantiate parsers dynamically on demand
        self.parsers = {}

    def _get_parser(self, language: str) -> Parser:
        """Retrieves or initializes a Tree-Sitter parser for a specific language."""
        if language not in self.parsers:
            try:
                lang_obj = tslp.get_language(language)
                self.parsers[language] = Parser(lang_obj)
            except Exception as e:
                logger.error(f"Failed to load tree-sitter language '{language}': {e}")
                raise ValueError(
                    f"Language '{language}' is not supported or failed to load."
                )

        return self.parsers[language]

    def _detect_language(self, file_path: str, fallback_language: str) -> str:
        """Determines the language based on file extension, falling back to the provided argument."""
        _, ext = os.path.splitext(file_path)
        return LANGUAGE_MAP.get(ext.lower(), fallback_language)

    def parse_file(
        self, file_path: str, language: str = "python"
    ) -> list[dict[str, Any]]:
        """
        Parses a file and extracts code objects (functions, classes, methods).
        Uses a universal AST walk to identify definitions across multiple languages.
        """
        target_lang = self._detect_language(file_path, language)
        logger.info(f"Parsing {file_path} using {target_lang} AST parser.")

        objects = []
        try:
            parser = self._get_parser(target_lang)

            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                content_bytes = bytes(content, "utf8")

            tree = parser.parse(content_bytes)

            # Universal AST walker
            def walk(node):
                node_type = node.type.lower()

                # Check for common AST node names indicating a function, method, or class
                is_function = "function" in node_type or "method" in node_type
                is_class = "class" in node_type or "struct" in node_type

                # We only want declarations/definitions, not usages/calls
                is_definition = any(
                    suffix in node_type
                    for suffix in [
                        "_definition",
                        "_declaration",
                        "_spec",
                        "method_definition",
                        "arrow_function",
                    ]
                )

                if (is_function or is_class) and is_definition:
                    # Attempt to extract the name (usually the first child that is an identifier)
                    name = "unknown"
                    for child in node.children:
                        if (
                            child.type == "identifier"
                            or child.type == "property_identifier"
                            or child.type == "type_identifier"
                        ):
                            name = content_bytes[
                                child.start_byte : child.end_byte
                            ].decode("utf8")
                            break

                    obj_type = "class" if is_class else "function"

                    # Extract the raw signature (up to the first block)
                    signature = (
                        content_bytes[node.start_byte : node.end_byte]
                        .decode("utf8")
                        .split("\n")[0]
                        .strip()
                    )
                    if "{" in signature:
                        signature = signature.split("{")[0].strip()

                    objects.append(
                        {
                            "object_type": obj_type,
                            "name": name,
                            "signature": signature,
                            "start_line": node.start_point.row
                            + 1,  # Tree-sitter is 0-indexed
                            "end_line": node.end_point.row + 1,
                            "cyclomatic_complexity": self._calculate_complexity(node),
                        }
                    )

                # Continue recursively
                for child in node.children:
                    walk(child)

            walk(tree.root_node)
            return objects

        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            return []

    def _calculate_complexity(self, node) -> int:
        """
        Estimates cyclomatic complexity by counting branching nodes.
        """
        complexity = 1

        def walk(n):
            nonlocal complexity
            node_type = n.type.lower()
            if node_type in [
                "if_statement",
                "for_statement",
                "while_statement",
                "catch_clause",
                "elif_clause",
                "case_statement",
                "&&",
                "||",
            ]:
                complexity += 1
            for child in n.children:
                walk(child)

        walk(node)
        return complexity


code_parser = CodeParser()
