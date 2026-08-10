"""
Universal Tree-sitter Code Parser — Production Grade
=====================================================
Supports: Python, Java, JavaScript, TypeScript, Go, C#
Fallback: Sliding Window for all other file types

Each CodeNode carries:
  - node_type, name, code, start_line, end_line
  - language, file_path, parent_name
  - docstring, imports (file-level)
  - annotations       (decorators / Java annotations)
  - package           (package/namespace/module)
  - framework         (spring/fastapi/express/nestjs/django …)
  - extends           (parent classes)
  - implements        (interfaces)
  - calls             (called symbols within the body)
  - return_type
  - signature         (full method signature)
  - content_type      (code / architecture / config / api)
"""
from __future__ import annotations
import re
import os
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Set

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data Model
# ---------------------------------------------------------------------------

@dataclass
class CodeNode:
    """Represents a fully-parsed code element with rich metadata."""
    # Core
    node_type: str          # class | function | section | chunk | sql_statement
    name: str
    code: str
    start_line: int
    end_line: int
    language: str = ""
    file_path: str = ""

    # Hierarchy
    parent_name: Optional[str] = None

    # Semantics
    docstring: str = ""
    imports: str = ""           # file-level import block

    # Rich metadata
    annotations: List[str] = field(default_factory=list)   # @RestController, @staticmethod
    package: str = ""           # com.wellness.payment.controller
    framework: str = ""         # spring | fastapi | express | nestjs | django | unknown
    extends: List[str] = field(default_factory=list)        # parent class names
    implements: List[str] = field(default_factory=list)     # interface names
    calls: List[str] = field(default_factory=list)          # called symbols
    return_type: str = ""
    signature: str = ""

    # Collection routing
    content_type: str = "code"  # code | architecture | config | api | summary

    # Extra key-value bag (framework-specific fields)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Language / Extension Registry
# ---------------------------------------------------------------------------

EXTENSION_TO_LANGUAGE: Dict[str, str] = {
    ".py":   "python",
    ".java": "java",
    ".kt":   "kotlin",
    ".js":   "javascript",
    ".jsx":  "javascript",
    ".ts":   "typescript",
    ".tsx":  "typescript",
    ".go":   "go",
    ".cs":   "csharp",
    ".cpp":  "cpp",
    ".c":    "c",
    ".rs":   "rust",
    ".rb":   "ruby",
    ".php":  "php",
    ".sql":  "sql",
    ".md":   "markdown",
    ".txt":  "text",
    ".rst":  "text",
    ".yaml": "yaml",
    ".yml":  "yaml",
    ".json": "json",
    ".xml":  "xml",
    ".sh":   "bash",
    ".tf":   "terraform",
    ".toml": "toml",
    ".properties": "properties",
    ".gradle": "gradle",
}

ARCHITECTURE_FILENAMES: Set[str] = {
    "readme.md", "readme.txt", "architecture.md", "design.md",
    "adr.md", "contributing.md", "changelog.md", "history.md",
}

API_FILENAMES: Set[str] = {
    "openapi.yaml", "openapi.yml", "swagger.yaml", "swagger.yml",
    "swagger.json", "openapi.json",
}

CONFIG_EXTENSIONS: Set[str] = {".yaml", ".yml", ".json", ".xml", ".toml",
                                ".properties", ".env", ".gradle", ".tf"}

# ---------------------------------------------------------------------------
# Tree-sitter Grammar Cache
# ---------------------------------------------------------------------------

_TS_LANG_CACHE: Dict[str, Any] = {}


def _load_ts_lang(lang: str):
    """Lazily load and cache a tree-sitter Language object."""
    if lang in _TS_LANG_CACHE:
        return _TS_LANG_CACHE[lang]
    try:
        from tree_sitter import Language
        if lang == "python":
            import tree_sitter_python as m; _TS_LANG_CACHE[lang] = Language(m.language())
        elif lang == "java":
            import tree_sitter_java as m; _TS_LANG_CACHE[lang] = Language(m.language())
        elif lang == "javascript":
            import tree_sitter_javascript as m; _TS_LANG_CACHE[lang] = Language(m.language())
        elif lang == "typescript":
            import tree_sitter_typescript as m; _TS_LANG_CACHE[lang] = Language(m.language_typescript())
        elif lang == "go":
            import tree_sitter_go as m; _TS_LANG_CACHE[lang] = Language(m.language())
        elif lang == "csharp":
            import tree_sitter_c_sharp as m; _TS_LANG_CACHE[lang] = Language(m.language())
        else:
            _TS_LANG_CACHE[lang] = None
    except Exception as e:
        logger.debug(f"Tree-sitter grammar not available for '{lang}': {e}")
        _TS_LANG_CACHE[lang] = None
    return _TS_LANG_CACHE[lang]


# ---------------------------------------------------------------------------
# Language Detection
# ---------------------------------------------------------------------------

def detect_language(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    return EXTENSION_TO_LANGUAGE.get(ext, "text")


def detect_content_type(file_path: str, language: str) -> str:
    """Route the file to the appropriate semantic collection."""
    fn = os.path.basename(file_path).lower()
    ext = os.path.splitext(file_path)[1].lower()

    if fn in ARCHITECTURE_FILENAMES or language == "markdown":
        return "architecture"
    if fn in API_FILENAMES:
        return "api"
    if ext in CONFIG_EXTENSIONS or language in ("yaml", "json", "xml", "toml",
                                                 "terraform", "properties", "gradle"):
        return "config"
    # Heuristic: controllers/routes → api
    if any(kw in fn for kw in ("controller", "router", "route", "endpoint", "handler")):
        return "api"
    return "code"


# ---------------------------------------------------------------------------
# Package / Namespace Extraction
# ---------------------------------------------------------------------------

_PACKAGE_PATTERNS: Dict[str, List[str]] = {
    "java":       [r"^\s*package\s+([\w.]+)\s*;"],
    "kotlin":     [r"^\s*package\s+([\w.]+)"],
    "csharp":     [r"^\s*namespace\s+([\w.]+)"],
    "go":         [r"^\s*package\s+(\w+)"],
    "typescript": [r"declare\s+module\s+[\"']([\w/@-]+)[\"']"],
    "javascript": [],
    "python":     [],   # Python uses __package__ / directory structure
}

def _extract_package(source: str, language: str) -> str:
    for pat in _PACKAGE_PATTERNS.get(language, []):
        m = re.search(pat, source[:2000], re.MULTILINE)
        if m:
            return m.group(1)
    return ""


# ---------------------------------------------------------------------------
# Framework Detection
# ---------------------------------------------------------------------------

_FRAMEWORK_SIGNALS: Dict[str, List[str]] = {
    "spring":    ["@SpringBootApplication", "@RestController", "@Service", "@Repository",
                  "org.springframework", "@Autowired", "@Bean", "@Component"],
    "fastapi":   ["from fastapi", "FastAPI(", "@app.get", "@app.post", "@router."],
    "django":    ["from django", "django.db", "models.Model", "views.View"],
    "flask":     ["from flask", "Flask(__name__", "@app.route"],
    "express":   ["require('express')", "require(\"express\")", "express()", "Router()"],
    "nestjs":    ["@Controller", "@Injectable", "@Module", "from '@nestjs"],
    "gin":       ["\"github.com/gin-gonic/gin\"", "gin.Default()", "gin.New()"],
    "dotnet":    ["using Microsoft.AspNetCore", "[ApiController]", "ControllerBase"],
    "hibernate": ["@Entity", "@Table", "@Column", "javax.persistence"],
}

def _detect_framework(source: str) -> str:
    for fw, signals in _FRAMEWORK_SIGNALS.items():
        if any(sig in source for sig in signals):
            return fw
    return ""


# ---------------------------------------------------------------------------
# Import Block Extraction
# ---------------------------------------------------------------------------

_IMPORT_PREFIXES = (
    "import ", "from ", "package ", "using ", "require(",
    "#include", "extern crate", "use std", "use crate",
)

def _extract_imports(source: str) -> str:
    lines = []
    for line in source.splitlines()[:100]:
        stripped = line.strip()
        if any(stripped.startswith(p) for p in _IMPORT_PREFIXES):
            lines.append(line)
    return "\n".join(lines[:40])


# ---------------------------------------------------------------------------
# Sliding Window Chunker (Universal Fallback)
# ---------------------------------------------------------------------------

def _sliding_window(text: str, file_path: str, language: str,
                    chunk_size: int = 60, overlap: int = 15,
                    content_type: str = "code") -> List[CodeNode]:
    lines = text.splitlines()
    if not lines:
        return []
    chunks: List[CodeNode] = []
    i, idx = 0, 0
    while i < len(lines):
        end = min(i + chunk_size, len(lines))
        snippet = "\n".join(lines[i:end])
        if snippet.strip():
            chunks.append(CodeNode(
                node_type="chunk",
                name=f"chunk_{idx}",
                code=snippet,
                start_line=i + 1,
                end_line=end,
                language=language,
                file_path=file_path,
                content_type=content_type,
            ))
            idx += 1
        i += chunk_size - overlap
    return chunks


# ---------------------------------------------------------------------------
# Markdown Heading-Aware Splitter
# ---------------------------------------------------------------------------

def _parse_markdown(text: str, file_path: str) -> List[CodeNode]:
    heading_re = re.compile(r'^(#{1,6})\s+(.+)', re.MULTILINE)
    lines = text.splitlines()
    sections: List[tuple] = []
    cur_heading, cur_lines = "Document Overview", []

    for line in lines:
        m = heading_re.match(line)
        if m:
            if cur_lines:
                sections.append((cur_heading, list(cur_lines)))
            cur_heading = m.group(2).strip()
            cur_lines = [line]
        else:
            cur_lines.append(line)
    if cur_lines:
        sections.append((cur_heading, cur_lines))

    nodes: List[CodeNode] = []
    sl = 1
    for heading, sec_lines in sections:
        content = "\n".join(sec_lines)
        el = sl + len(sec_lines) - 1
        if len(sec_lines) <= 80:
            if content.strip():
                nodes.append(CodeNode(
                    node_type="section",
                    name=heading,
                    code=content,
                    start_line=sl,
                    end_line=el,
                    language="markdown",
                    file_path=file_path,
                    content_type="architecture",
                ))
        else:
            for chunk in _sliding_window(content, file_path, "markdown",
                                         chunk_size=60, overlap=10,
                                         content_type="architecture"):
                chunk.name = f"{heading} [{chunk.start_line}-{chunk.end_line}]"
                chunk.node_type = "section"
                nodes.append(chunk)
        sl = el + 1

    return nodes or _sliding_window(text, file_path, "markdown", content_type="architecture")


# ---------------------------------------------------------------------------
# SQL Statement Splitter
# ---------------------------------------------------------------------------

def _parse_sql(text: str, file_path: str) -> List[CodeNode]:
    statements = [s.strip() for s in text.split(";") if s.strip()]
    nodes: List[CodeNode] = []
    line_counter = 1
    for i, stmt in enumerate(statements):
        stmt_lines = stmt.splitlines()
        el = line_counter + len(stmt_lines)
        first_word = stmt.lstrip().split()[0].upper() if stmt.strip() else "SQL"
        nm = re.search(r'(?:TABLE|VIEW|INDEX|PROCEDURE|FUNCTION)\s+(\w+)', stmt, re.IGNORECASE)
        name = nm.group(1) if nm else f"statement_{i}"
        nodes.append(CodeNode(
            node_type="sql_statement",
            name=f"{first_word}_{name}",
            code=stmt,
            start_line=line_counter,
            end_line=el,
            language="sql",
            file_path=file_path,
            content_type="code",
        ))
        line_counter = el + 2
    return nodes or _sliding_window(text, file_path, "sql")


# ---------------------------------------------------------------------------
# Tree-sitter Node Type Maps
# ---------------------------------------------------------------------------

LANG_NODE_TYPES: Dict[str, Dict[str, List[str]]] = {
    "python": {
        "class":    ["class_definition"],
        "function": ["function_definition", "decorated_definition"],
    },
    "java": {
        "class":    ["class_declaration", "interface_declaration",
                     "enum_declaration", "annotation_type_declaration"],
        "function": ["method_declaration", "constructor_declaration"],
    },
    "javascript": {
        "class":    ["class_declaration", "class_expression"],
        "function": ["function_declaration", "arrow_function",
                     "method_definition", "generator_function_declaration"],
    },
    "typescript": {
        "class":    ["class_declaration", "interface_declaration",
                     "abstract_class_declaration", "enum_declaration"],
        "function": ["function_declaration", "arrow_function", "method_definition",
                     "abstract_method_signature"],
    },
    "go": {
        "class":    ["type_declaration"],
        "function": ["function_declaration", "method_declaration"],
    },
    "csharp": {
        "class":    ["class_declaration", "interface_declaration",
                     "struct_declaration", "enum_declaration", "record_declaration"],
        "function": ["method_declaration", "constructor_declaration",
                     "local_function_statement"],
    },
}

# ---------------------------------------------------------------------------
# Helper: extract identifier text
# ---------------------------------------------------------------------------

def _node_text(node, source_bytes: bytes) -> str:
    return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")


def _get_identifier(node, source_bytes: bytes) -> str:
    for child in node.children:
        if child.type in ("identifier", "type_identifier", "field_identifier",
                          "property_identifier", "name", "simple_identifier"):
            return _node_text(child, source_bytes)
    return "unknown"


# ---------------------------------------------------------------------------
# Annotation / Decorator extraction
# ---------------------------------------------------------------------------

def _extract_annotations_python(node, source_bytes: bytes) -> List[str]:
    """Extract Python decorator names from a decorated_definition or class/function."""
    anns: List[str] = []
    for child in node.children:
        if child.type == "decorator":
            text = _node_text(child, source_bytes).strip()
            anns.append(text.split("(")[0])  # keep just @name
    return anns


def _extract_annotations_java(node, source_bytes: bytes, lines: List[str]) -> List[str]:
    """Look at lines just above a Java node for @Annotation tokens."""
    start = max(0, node.start_point[0] - 10)
    preceding = "\n".join(lines[start:node.start_point[0]])
    return re.findall(r'@[\w.]+', preceding)


_ANNOTATION_EXTRACTORS = {
    "python":     _extract_annotations_python,
    "java":       _extract_annotations_java,
    "kotlin":     _extract_annotations_java,   # same pattern
    "csharp":     _extract_annotations_java,
    "typescript": _extract_annotations_java,
}

# ---------------------------------------------------------------------------
# Extends / Implements extraction
# ---------------------------------------------------------------------------

def _get_extends_implements(node, source_bytes: bytes) -> tuple[List[str], List[str]]:
    """Extract extends and implements type names from a class node."""
    extends: List[str] = []
    implements: List[str] = []
    for child in node.children:
        if child.type in ("superclass", "extends_clause"):
            text = _node_text(child, source_bytes)
            extends += re.findall(r'\b[A-Z]\w+', text)
        elif child.type in ("super_interfaces", "implements_clause",
                            "class_implements", "interface_body"):
            text = _node_text(child, source_bytes)
            implements += re.findall(r'\b[A-Z]\w+', text)
    return extends, implements


# ---------------------------------------------------------------------------
# Call Site extraction (body scan)
# ---------------------------------------------------------------------------

_CALL_PATTERNS = [
    re.compile(r'\b(\w+)\s*\('),                   # foo(
    re.compile(r'(\w+)\.(\w+)\s*\('),              # obj.method(
]

def _extract_calls(code: str) -> List[str]:
    """Heuristically extract called identifiers from code."""
    calls: Set[str] = set()
    for pat in _CALL_PATTERNS:
        for m in pat.finditer(code):
            name = m.group(1) if pat.groups == 1 else m.group(2)
            # Skip language keywords and common stdlib noise
            if name and len(name) > 2 and not name.startswith(
                ("if", "for", "while", "return", "print", "len",
                 "str", "int", "list", "dict", "set", "type")):
                calls.add(name)
    return sorted(calls)[:20]   # cap at 20 per node


# ---------------------------------------------------------------------------
# Return type extraction
# ---------------------------------------------------------------------------

def _get_return_type(node, source_bytes: bytes) -> str:
    for child in node.children:
        if child.type in ("type_annotation", "type", "void_type",
                          "generic_type", "array_type", "return_type"):
            return _node_text(child, source_bytes).strip().lstrip(":").strip()
    return ""


# ---------------------------------------------------------------------------
# Docstring extraction
# ---------------------------------------------------------------------------

def _get_docstring(node, source_bytes: bytes) -> str:
    for child in node.children:
        if child.type in ("block", "statement_block", "declaration_list", "class_body"):
            for gc in child.children:
                if gc.type == "expression_statement":
                    code = _node_text(gc, source_bytes)
                    if code.strip().startswith(('"""', "'''", '"', "'")):
                        return code.strip().strip("\"'").strip()[:300]
                elif gc.type in ("comment", "block_comment", "line_comment"):
                    return _node_text(gc, source_bytes)[:300]
    return ""


# ---------------------------------------------------------------------------
# Tree-sitter AST Parser (core)
# ---------------------------------------------------------------------------

def _parse_with_ts(text: str, file_path: str, language: str) -> List[CodeNode]:
    ts_lang = _load_ts_lang(language)
    if ts_lang is None:
        return []

    try:
        from tree_sitter import Parser
        parser = Parser(ts_lang)
        source_bytes = text.encode("utf-8")
        tree = parser.parse(source_bytes)
    except Exception as e:
        logger.warning(f"Tree-sitter parse failed for {file_path}: {e}")
        return []

    lines = text.splitlines()
    type_map = LANG_NODE_TYPES.get(language, {})
    class_types = set(type_map.get("class", []))
    func_types  = set(type_map.get("function", []))
    all_types   = class_types | func_types

    imports   = _extract_imports(text)
    package   = _extract_package(text, language)
    framework = _detect_framework(text)
    content_type = detect_content_type(file_path, language)
    nodes: List[CodeNode] = []

    def walk(node, parent_class: Optional[str] = None):
        if node.type in all_types:
            name       = _get_identifier(node, source_bytes)
            sl         = node.start_point[0] + 1
            el         = node.end_point[0] + 1
            snippet    = "\n".join(lines[sl - 1:el])[:4000]
            docstr     = _get_docstring(node, source_bytes)
            ret_type   = _get_return_type(node, source_bytes)
            calls      = _extract_calls(snippet)
            ext, impl  = _get_extends_implements(node, source_bytes)
            type_label = "class" if node.type in class_types else "function"

            # Annotations / decorators
            ann_fn = _ANNOTATION_EXTRACTORS.get(language)
            if ann_fn and language == "python":
                annotations = ann_fn(node, source_bytes)
            elif ann_fn:
                annotations = ann_fn(node, source_bytes, lines)
            else:
                annotations = []

            # Build method signature string
            sig_end  = min(el, sl + 4)
            sig_code = "\n".join(lines[sl - 1:sig_end])
            # Trim at first { or : or newline after paren
            sig_line = sig_code.split("{")[0].split(":\n")[0].strip()[:200]

            nodes.append(CodeNode(
                node_type    = type_label,
                name         = name,
                code         = snippet,
                start_line   = sl,
                end_line     = el,
                language     = language,
                file_path    = file_path,
                parent_name  = parent_class,
                docstring    = docstr,
                imports      = imports,
                annotations  = annotations,
                package      = package,
                framework    = framework,
                extends      = ext,
                implements   = impl,
                calls        = calls,
                return_type  = ret_type,
                signature    = sig_line,
                content_type = content_type,
            ))

            new_parent = name if type_label == "class" else parent_class
            for child in node.children:
                walk(child, parent_class=new_parent)
        else:
            for child in node.children:
                walk(child, parent_class=parent_class)

    walk(tree.root_node)
    return nodes


# ---------------------------------------------------------------------------
# Universal Entry Point
# ---------------------------------------------------------------------------

def parse_file(file_path: str, content: str) -> List[CodeNode]:
    """
    Parse any source/doc/config file into a list of richly-annotated CodeNodes.
    Strategy selection is fully automatic based on file extension.
    """
    language = detect_language(file_path)

    if not content.strip():
        return []

    # Markdown → heading-aware splitter
    if language == "markdown":
        return _parse_markdown(content, file_path)

    # SQL → statement splitter
    if language == "sql":
        return _parse_sql(content, file_path)

    # Config/Data → sliding window
    if language in ("yaml", "json", "xml", "text", "terraform", "bash",
                    "toml", "properties", "gradle"):
        ct = detect_content_type(file_path, language)
        return _sliding_window(content, file_path, language,
                               chunk_size=50, overlap=10, content_type=ct)

    # Source code → tree-sitter AST
    if language in LANG_NODE_TYPES:
        nodes = _parse_with_ts(content, file_path, language)
        if nodes:
            return nodes

    # Universal fallback → sliding window
    ct = detect_content_type(file_path, language)
    return _sliding_window(content, file_path, language,
                           chunk_size=60, overlap=15, content_type=ct)


# ---------------------------------------------------------------------------
# Chunk Content Builder
# ---------------------------------------------------------------------------

def build_chunk_content(node: CodeNode) -> str:
    """
    Build the final rich text for a CodeNode that will be embedded.
    Includes: package context + annotations + semantic header + docstring + code.
    """
    parts: List[str] = []

    # Package / namespace header
    if node.package:
        parts.append(f"Package: {node.package}")

    # Import context
    if node.imports:
        parts.append(f"[Imports]\n{node.imports}")

    # Annotations
    if node.annotations:
        parts.append("Annotations: " + "  ".join(node.annotations))

    # Semantic header
    header = f"[{node.language.upper()}] {node.node_type.capitalize()}: {node.name}"
    if node.parent_name:
        header += f"  (in {node.parent_name})"
    if node.framework:
        header += f"  | Framework: {node.framework}"
    header += f"  | File: {node.file_path} (L{node.start_line}–{node.end_line})"
    parts.append(header)

    # Extends / implements
    if node.extends:
        parts.append(f"Extends: {', '.join(node.extends)}")
    if node.implements:
        parts.append(f"Implements: {', '.join(node.implements)}")

    # Docstring
    if node.docstring:
        parts.append(f"Description: {node.docstring}")

    # Return type
    if node.return_type:
        parts.append(f"Returns: {node.return_type}")

    # Code
    parts.append(f"\n{node.code}")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class UniversalCodeParser:
    def parse(self, file_path: str, content: str) -> List[CodeNode]:
        return parse_file(file_path, content)

    def detect_language(self, file_path: str) -> str:
        return detect_language(file_path)

    def detect_content_type(self, file_path: str) -> str:
        lang = detect_language(file_path)
        return detect_content_type(file_path, lang)

    def build_chunk_content(self, node: CodeNode) -> str:
        return build_chunk_content(node)


universal_parser = UniversalCodeParser()
