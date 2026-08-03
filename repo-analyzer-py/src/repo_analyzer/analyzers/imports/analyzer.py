"""Import analyzer.

Analyzes imports across the repository to find:

- Unused imports (files that import a module never referenced in the body).
- Circular imports (A imports B imports A).
- Duplicate imports (same module imported multiple times in one file).
- Most-imported modules.
- External vs internal dependencies.
- The import graph (module → imported modules).
"""

from __future__ import annotations

import ast
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from repo_analyzer.analyzers.base import BaseAnalyzer
from repo_analyzer.core.domain.analysis_outputs import ImportAnalysis
from repo_analyzer.core.domain.repository import Repository


class ImportAnalyzer(BaseAnalyzer):
    """Analyze imports (Python-focused with best-effort JS/TS)."""

    _analyzer_name = "import"
    _analyzer_version = "0.1.0"
    _analyzer_phase = 1

    def run(self, repository: Repository, workspace: Path) -> dict[str, Any]:
        """Run import analysis and return an :class:`ImportAnalysis`."""
        import_graph: dict[str, list[str]] = defaultdict(list)
        all_imports: list[dict[str, Any]] = []
        module_import_counts: dict[str, int] = defaultdict(int)
        duplicate_imports: list[dict[str, Any]] = []
        unused_imports: list[dict[str, Any]] = []

        for path in self._iter_python_files(workspace):
            rel = str(path.relative_to(workspace))
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            file_imports, file_dups, file_unused = self._analyze_python_imports(content, rel)
            for imp in file_imports:
                module = imp["module"]
                import_graph[rel].append(module)
                all_imports.append(imp)
                module_import_counts[module] += 1
            for dup in file_dups:
                duplicate_imports.append(dup)
            for unused in file_unused:
                unused_imports.append(unused)

        # JS/TS imports (best-effort regex).
        for path in self._iter_jsts_files(workspace):
            rel = str(path.relative_to(workspace))
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            for mod in self._extract_jsts_imports(content):
                import_graph[rel].append(mod)
                module_import_counts[mod] += 1

        circular = self._detect_cycles(dict(import_graph))
        most_imported = sorted(module_import_counts.items(), key=lambda kv: kv[1], reverse=True)[
            :30
        ]
        external, internal = self._classify_dependencies(module_import_counts.keys(), workspace)

        analysis = ImportAnalysis(
            unused_imports=unused_imports,
            circular_imports=circular,
            duplicate_imports=duplicate_imports,
            most_imported_modules=most_imported,
            external_dependencies=sorted(external),
            internal_dependencies=sorted(internal),
            import_graph=dict(import_graph),
        )
        return {"import_analysis": analysis.model_dump(mode="json")}

    # ----- helpers -------------------------------------------------------------

    def _iter_python_files(self, workspace: Path):  # type: ignore[no-untyped-def]
        for root, _dirs, files in os.walk(workspace):
            if ".git" in root:
                continue
            for name in files:
                if name.endswith(".py"):
                    yield Path(root) / name

    def _iter_jsts_files(self, workspace: Path):  # type: ignore[no-untyped-def]
        for root, _dirs, files in os.walk(workspace):
            if ".git" in root:
                continue
            for name in files:
                if name.endswith((".js", ".jsx", ".ts", ".tsx")):
                    yield Path(root) / name

    def _analyze_python_imports(
        self, content: str, file_path: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
        """Analyze Python imports via the :mod:`ast` module."""
        imports: list[dict[str, Any]] = []
        duplicates: list[dict[str, Any]] = []
        unused: list[dict[str, Any]] = []
        try:
            tree = ast.parse(content, filename=file_path)
        except SyntaxError:
            return imports, duplicates, unused
        seen: dict[str, int] = {}
        imported_names: dict[str, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name
                    imports.append(
                        {"file": file_path, "module": module, "line": node.lineno, "kind": "import"}
                    )
                    if module in seen:
                        duplicates.append(
                            {"file": file_path, "module": module, "line": node.lineno}
                        )
                    seen[module] = node.lineno
                    if alias.asname:
                        imported_names[alias.asname] = module
                    else:
                        imported_names[module.split(".")[0]] = module
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module:
                    imports.append(
                        {"file": file_path, "module": module, "line": node.lineno, "kind": "from"}
                    )
                    if module in seen:
                        duplicates.append(
                            {"file": file_path, "module": module, "line": node.lineno}
                        )
                    seen[module] = node.lineno
                for alias in node.names:
                    name = alias.asname or alias.name
                    imported_names[name] = module or alias.name
        # Unused detection: check if each imported name appears elsewhere.
        for name, module in imported_names.items():
            pattern = re.compile(r"\b" + re.escape(name) + r"\b")
            # Search in content minus the import lines themselves.
            body = self._strip_imports(content)
            if not pattern.search(body):
                unused.append({"file": file_path, "name": name, "module": module})
        return imports, duplicates, unused

    @staticmethod
    def _strip_imports(content: str) -> str:
        """Remove import lines from content for unused-import detection."""
        lines = []
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                continue
            lines.append(line)
        return "\n".join(lines)

    @staticmethod
    def _extract_jsts_imports(content: str) -> list[str]:
        """Best-effort extraction of JS/TS import specifiers."""
        modules: list[str] = []
        for match in re.finditer(r"""import\s+(?:[^'"]+\s+from\s+)?['"]([^'"]+)['"]""", content):
            modules.append(match.group(1))
        for match in re.finditer(r"""require\(\s*['"]([^'"]+)['"]\s*\)""", content):
            modules.append(match.group(1))
        return modules

    def _detect_cycles(self, graph: dict[str, list[str]]) -> list[list[str]]:
        """Detect cycles in the import graph via DFS."""
        cycles: list[list[str]] = []
        visited: set[str] = set()
        stack: set[str] = set()

        def dfs(node: str, path: list[str]) -> None:
            if node in stack:
                idx = path.index(node) if node in path else 0
                cycle = path[idx:] + [node]
                cycles.append(cycle)
                return
            if node in visited:
                return
            stack.add(node)
            path.append(node)
            for neighbor in graph.get(node, []):
                # Map module name back to a file path if possible.
                target = self._resolve_module(node, neighbor)
                if target:
                    dfs(target, path)
            path.pop()
            stack.discard(node)
            visited.add(node)

        for node in graph:
            if node not in visited:
                dfs(node, [])
        return cycles[:50]  # cap

    @staticmethod
    def _resolve_module(current_file: str, module: str) -> str | None:
        """Resolve a Python module name to a file path in the graph."""
        if module.startswith("."):
            # Relative import: best-effort resolution.
            return None
        candidate = module.replace(".", "/") + ".py"
        return candidate

    def _classify_dependencies(self, modules: Any, workspace: Path) -> tuple[set[str], set[str]]:
        """Classify modules as external or internal."""
        external: set[str] = set()
        internal: set[str] = set()
        local_modules = self._local_modules(workspace)
        for mod in modules:
            top = mod.split(".")[0]
            if top in local_modules or mod.startswith("."):
                internal.add(mod)
            else:
                external.add(mod)
        return external, internal

    @staticmethod
    def _local_modules(workspace: Path) -> set[str]:
        """Return the set of top-level module names in the workspace."""
        local: set[str] = set()
        for entry in workspace.iterdir():
            if entry.is_dir() and (entry / "__init__.py").exists():
                local.add(entry.name)
            elif entry.is_file() and entry.suffix == ".py":
                local.add(entry.stem)
        return local


__all__ = ["ImportAnalyzer"]
