"""AST parser analyzer using tree-sitter.

Parses source files into ASTs via the ``tree-sitter-language-pack`` and
extracts symbols: functions, classes, methods, interfaces, structs, enums,
constants, variables, decorators, annotations, imports, exports and
inheritance relationships.

Languages without a tree-sitter grammar fall back to a lightweight
regex-based extractor.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from repo_analyzer.analyzers.ast.tree_sitter_loader import TreeSitterLoader
from repo_analyzer.analyzers.base import BaseAnalyzer
from repo_analyzer.core.domain.analysis_outputs import SymbolCollection
from repo_analyzer.core.domain.repository import Repository


class ASTAnalyzer(BaseAnalyzer):
    """Parse source files and collect symbols via tree-sitter."""

    _analyzer_name = "ast"
    _analyzer_version = "0.1.0"
    _analyzer_phase = 1

    def __init__(self, *, max_file_size_bytes: int = 1 * 1024 * 1024) -> None:
        super().__init__()
        self._max_file_size = max_file_size_bytes
        self._loader = TreeSitterLoader()

    def run(self, repository: Repository, workspace: Path) -> dict[str, Any]:
        """Parse all parseable source files and collect symbols."""
        symbols = SymbolCollection()
        for path in self._iter_source_files(workspace):
            language = self._loader.language_for_file(path)
            if language is None:
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if len(content) > self._max_file_size:
                continue
            self._extract_symbols(path, language, content, symbols, workspace)
        return {"symbols": symbols.model_dump(mode="json")}

    # ----- helpers -------------------------------------------------------------

    def _iter_source_files(self, workspace: Path):  # type: ignore[no-untyped-def]
        """Yield source files, skipping ``.git`` and vendored dirs."""
        import os

        skip_dirs = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}
        for root, dirs, files in os.walk(workspace):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for name in files:
                p = Path(root) / name
                if self._loader.language_for_file(p) is not None:
                    yield p

    def _extract_symbols(
        self,
        path: Path,
        language: str,
        content: str,
        symbols: SymbolCollection,
        workspace: Path,
    ) -> None:
        """Extract symbols from a single file."""
        rel = str(path.relative_to(workspace))
        tree = self._loader.parse(language, content)
        if tree is None:
            # Fallback to regex extraction.
            self._regex_extract(language, rel, content, symbols)
            return
        try:
            root = tree.root_node
        except Exception:  # pragma: no cover - defensive
            return
        self._walk_node(root, language, rel, content, symbols)

    def _walk_node(
        self,
        node: Any,
        language: str,
        file_path: str,
        content: str,
        symbols: SymbolCollection,
    ) -> None:
        """Recursively walk the AST and collect symbols by node type."""
        node_type = node.type
        name = self._node_name(node, content)
        # Python.
        if language == "python":
            if node_type == "function_definition":
                symbols.functions.append(self._sym(file_path, name, node, content, kind="function"))
            elif node_type == "class_definition":
                symbols.classes.append(self._sym(file_path, name, node, content, kind="class"))
                # Detect inheritance.
                superclasses = self._python_superclasses(node, content)
                for sc in superclasses:
                    symbols.inheritances.append({"file": file_path, "class": name, "parent": sc})
            elif node_type == "import_statement" or node_type == "import_from_statement":
                symbols.imports.append(
                    {"file": file_path, "text": self._text(node, content).strip()}
                )
            elif node_type == "decorator":
                symbols.decorators.append(
                    {"file": file_path, "text": self._text(node, content).strip()}
                )
        # JavaScript / TypeScript.
        elif language in {"javascript", "typescript"}:
            if node_type in {"function_declaration", "arrow_function", "function_expression"}:
                symbols.functions.append(self._sym(file_path, name, node, content, kind="function"))
            elif node_type in {"class_declaration", "class"}:
                symbols.classes.append(self._sym(file_path, name, node, content, kind="class"))
            elif node_type in {"import_statement", "import_clause"}:
                symbols.imports.append(
                    {"file": file_path, "text": self._text(node, content).strip()}
                )
            elif node_type == "export_statement":
                symbols.exports.append(
                    {"file": file_path, "text": self._text(node, content).strip()}
                )
            elif node_type == "decorator":
                symbols.decorators.append(
                    {"file": file_path, "text": self._text(node, content).strip()}
                )
        # Go.
        elif language == "go":
            if node_type in {"function_declaration", "method_declaration"}:
                symbols.functions.append(self._sym(file_path, name, node, content, kind="function"))
            elif node_type == "type_declaration":
                symbols.structs.append(self._sym(file_path, name, node, content, kind="struct"))
            elif node_type == "import_declaration":
                symbols.imports.append(
                    {"file": file_path, "text": self._text(node, content).strip()}
                )
        # Java / Kotlin.
        elif language in {"java", "kotlin"}:
            if node_type in {"method_declaration", "function_declaration"}:
                symbols.methods.append(self._sym(file_path, name, node, content, kind="method"))
            elif node_type in {"class_declaration", "class"}:
                symbols.classes.append(self._sym(file_path, name, node, content, kind="class"))
            elif node_type == "interface_declaration":
                symbols.interfaces.append(
                    self._sym(file_path, name, node, content, kind="interface")
                )
            elif node_type == "enum_declaration":
                symbols.enums.append(self._sym(file_path, name, node, content, kind="enum"))
            elif node_type == "import_declaration":
                symbols.imports.append(
                    {"file": file_path, "text": self._text(node, content).strip()}
                )
            elif node_type in {"annotation", "annotation_declaration"}:
                symbols.annotations.append(
                    {"file": file_path, "text": self._text(node, content).strip()}
                )
        # Rust.
        elif language == "rust":
            if node_type == "function_item":
                symbols.functions.append(self._sym(file_path, name, node, content, kind="function"))
            elif node_type == "struct_item":
                symbols.structs.append(self._sym(file_path, name, node, content, kind="struct"))
            elif node_type == "enum_item":
                symbols.enums.append(self._sym(file_path, name, node, content, kind="enum"))
            elif node_type == "trait_item":
                symbols.interfaces.append(self._sym(file_path, name, node, content, kind="trait"))
            elif node_type == "use_declaration":
                symbols.imports.append(
                    {"file": file_path, "text": self._text(node, content).strip()}
                )
        # C / C++.
        elif language in {"c", "cpp"}:
            if node_type in {"function_definition", "function_declaration"}:
                symbols.functions.append(self._sym(file_path, name, node, content, kind="function"))
            elif node_type in {"class_specifier", "struct_specifier"}:
                symbols.classes.append(self._sym(file_path, name, node, content, kind="class"))
            elif node_type == "enum_specifier":
                symbols.enums.append(self._sym(file_path, name, node, content, kind="enum"))
        # C#.
        elif language == "csharp":
            if node_type == "method_declaration":
                symbols.methods.append(self._sym(file_path, name, node, content, kind="method"))
            elif node_type == "class_declaration":
                symbols.classes.append(self._sym(file_path, name, node, content, kind="class"))
            elif node_type == "interface_declaration":
                symbols.interfaces.append(
                    self._sym(file_path, name, node, content, kind="interface")
                )
            elif node_type == "enum_declaration":
                symbols.enums.append(self._sym(file_path, name, node, content, kind="enum"))
            elif node_type == "using_directive":
                symbols.imports.append(
                    {"file": file_path, "text": self._text(node, content).strip()}
                )
        # Recurse into children.
        for child in node.children:
            self._walk_node(child, language, file_path, content, symbols)

    def _regex_extract(
        self, language: str, file_path: str, content: str, symbols: SymbolCollection
    ) -> None:
        """Regex-based fallback for languages without a tree-sitter grammar."""
        import re

        if language == "ruby":
            for match in re.finditer(r"^\s*def\s+([A-Za-z0-9_?!]+)", content, re.MULTILINE):
                symbols.functions.append(
                    {"file": file_path, "name": match.group(1), "kind": "function"}
                )
            for match in re.finditer(r"^\s*class\s+([A-Za-z0-9_]+)", content, re.MULTILINE):
                symbols.classes.append({"file": file_path, "name": match.group(1), "kind": "class"})
        elif language == "php":
            for match in re.finditer(r"function\s+([A-Za-z0-9_]+)\s*\(", content):
                symbols.functions.append(
                    {"file": file_path, "name": match.group(1), "kind": "function"}
                )
            for match in re.finditer(r"class\s+([A-Za-z0-9_]+)", content):
                symbols.classes.append({"file": file_path, "name": match.group(1), "kind": "class"})

    @staticmethod
    def _node_name(node: Any, content: str) -> str:
        """Extract a human-readable name for a node (best-effort)."""
        for child in node.children:
            if child.type in {"identifier", "name", "property_identifier", "type_identifier"}:
                return ASTAnalyzer._text(child, content)
        return "<anonymous>"

    @staticmethod
    def _text(node: Any, content: str) -> str:
        """Return the source text covered by ``node``."""
        try:
            start = node.start_byte
            end = node.end_byte
            return content[start:end]
        except Exception:  # pragma: no cover - defensive
            return ""

    def _sym(
        self, file_path: str, name: str, node: Any, content: str, *, kind: str
    ) -> dict[str, Any]:
        """Build a symbol dict with location info."""
        return {
            "file": file_path,
            "name": name,
            "kind": kind,
            "line": self._start_line(node),
            "end_line": self._end_line(node),
            "length_lines": self._end_line(node) - self._start_line(node) + 1,
        }

    @staticmethod
    def _start_line(node: Any) -> int:
        try:
            return int(node.start_point[0]) + 1
        except Exception:  # pragma: no cover - defensive
            return 0

    @staticmethod
    def _end_line(node: Any) -> int:
        try:
            return int(node.end_point[0]) + 1
        except Exception:  # pragma: no cover - defensive
            return 0

    @staticmethod
    def _python_superclasses(node: Any, content: str) -> Sequence[str]:
        """Extract superclass names from a Python ``class`` node."""
        try:
            for child in node.children:
                if child.type == "argument_list":
                    text = ASTAnalyzer._text(child, content).strip("()")
                    return [arg.strip() for arg in text.split(",") if arg.strip()]
                if child.type == "superclasses":
                    text = ASTAnalyzer._text(child, content).strip("()")
                    return [arg.strip() for arg in text.split(",") if arg.strip()]
        except Exception:  # pragma: no cover - defensive
            pass
        return []


__all__ = ["ASTAnalyzer"]
