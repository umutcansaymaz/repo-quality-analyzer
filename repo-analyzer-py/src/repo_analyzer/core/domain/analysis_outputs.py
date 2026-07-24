"""File-system scan result model.

Produced by the :mod:`repo_analyzer.analyzers.filesystem` analyzer. Captures a
complete inventory of the repository working tree: file count, directory
count, binary/empty/duplicate/symlink/hidden files, total bytes and
extension distribution.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FileInventory(BaseModel):
    """A structured inventory of files in a repository working tree."""

    model_config = ConfigDict(extra="forbid")

    total_files: int = 0
    total_directories: int = 0
    total_bytes: int = 0
    empty_files: int = 0
    binary_files: int = 0
    generated_files: int = 0
    duplicate_files: int = 0
    symlinks: int = 0
    hidden_files: int = 0

    #: Mapping of extension (lowercase, without dot) → file count.
    extension_distribution: dict[str, int] = Field(default_factory=dict)

    #: Mapping of language name → file count (filled by the language detector).
    language_distribution: dict[str, int] = Field(default_factory=dict)

    #: Largest directories by total byte size (path → bytes), top N.
    largest_directories: list[tuple[str, int]] = Field(default_factory=list)

    #: Largest files (path → bytes), top N.
    largest_files: list[tuple[str, int]] = Field(default_factory=list)

    #: Duplicate-file groups: list of (hash, [paths]).
    duplicate_groups: list[tuple[str, list[str]]] = Field(default_factory=list)

    #: Full list of file paths relative to the repository root (lazy-filled).
    files: list[str] = Field(default_factory=list)

    #: Arbitrary scanner metadata.
    metadata: dict[str, Any] = Field(default_factory=dict)

    def add_file(self, path: Path, size: int) -> None:
        """Record a single file in the inventory."""
        rel = str(path)
        self.files.append(rel)
        self.total_files += 1
        self.total_bytes += size
        if size == 0:
            self.empty_files += 1
        ext = path.suffix.lower().lstrip(".")
        if ext:
            self.extension_distribution[ext] = self.extension_distribution.get(ext, 0) + 1

    def add_directory(self) -> None:
        """Record a directory."""
        self.total_directories += 1


class RepositoryMetadata(BaseModel):
    """Metadata about a repository (host-provided + git-derived)."""

    model_config = ConfigDict(extra="forbid")

    name: str = ""
    owner: str = ""
    description: str | None = None
    stars: int | None = None
    forks: int | None = None
    contributors: list[str] = Field(default_factory=list)
    default_branch: str | None = None
    tags: list[str] = Field(default_factory=list)
    releases: list[str] = Field(default_factory=list)
    license: str | None = None
    readme_path: str | None = None
    primary_language: str | None = None
    size_bytes: int | None = None
    last_commit_sha: str | None = None
    last_commit_date: str | None = None
    total_branches: int | None = None
    total_commits: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LanguageDistribution(BaseModel):
    """Per-language summary for a repository."""

    model_config = ConfigDict(extra="forbid")

    #: Mapping of language name → percentage (0-100).
    percentages: dict[str, float] = Field(default_factory=dict)

    #: Mapping of language name → lines of code.
    loc: dict[str, int] = Field(default_factory=dict)

    #: Mapping of language name → file count.
    file_counts: dict[str, int] = Field(default_factory=dict)

    #: Mapping of file path → detected language.
    file_languages: dict[str, str] = Field(default_factory=dict)

    @property
    def primary_language(self) -> str | None:
        """The language with the most lines of code, if any."""
        if not self.loc:
            return None
        return max(self.loc, key=lambda k: self.loc[k])

    @property
    def total_loc(self) -> int:
        """Total lines of code across all languages."""
        return sum(self.loc.values())


class SymbolCollection(BaseModel):
    """A collection of source-code symbols extracted by the AST parser."""

    model_config = ConfigDict(extra="forbid")

    functions: list[dict[str, Any]] = Field(default_factory=list)
    classes: list[dict[str, Any]] = Field(default_factory=list)
    methods: list[dict[str, Any]] = Field(default_factory=list)
    interfaces: list[dict[str, Any]] = Field(default_factory=list)
    structs: list[dict[str, Any]] = Field(default_factory=list)
    enums: list[dict[str, Any]] = Field(default_factory=list)
    constants: list[dict[str, Any]] = Field(default_factory=list)
    variables: list[dict[str, Any]] = Field(default_factory=list)
    decorators: list[dict[str, Any]] = Field(default_factory=list)
    annotations: list[dict[str, Any]] = Field(default_factory=list)
    imports: list[dict[str, Any]] = Field(default_factory=list)
    exports: list[dict[str, Any]] = Field(default_factory=list)
    inheritances: list[dict[str, Any]] = Field(default_factory=list)

    @property
    def total_symbols(self) -> int:
        """Total number of symbols across all categories."""
        return (
            len(self.functions)
            + len(self.classes)
            + len(self.methods)
            + len(self.interfaces)
            + len(self.structs)
            + len(self.enums)
            + len(self.constants)
            + len(self.variables)
        )


class ImportAnalysis(BaseModel):
    """Result of analyzing imports across the repository."""

    model_config = ConfigDict(extra="forbid")

    unused_imports: list[dict[str, Any]] = Field(default_factory=list)
    circular_imports: list[list[str]] = Field(default_factory=list)
    duplicate_imports: list[dict[str, Any]] = Field(default_factory=list)
    most_imported_modules: list[tuple[str, int]] = Field(default_factory=list)
    external_dependencies: list[str] = Field(default_factory=list)
    internal_dependencies: list[str] = Field(default_factory=list)
    import_graph: dict[str, list[str]] = Field(default_factory=dict)


class DependencyAnalysis(BaseModel):
    """Result of analyzing project dependencies."""

    model_config = ConfigDict(extra="forbid")

    dependencies: list[dict[str, Any]] = Field(default_factory=list)
    dependency_graph: dict[str, list[str]] = Field(default_factory=dict)
    unused_dependencies: list[str] = Field(default_factory=list)
    duplicate_dependencies: list[str] = Field(default_factory=list)
    ecosystems: list[str] = Field(default_factory=list)
    total_dependencies: int = 0


class FileMetrics(BaseModel):
    """Metrics for a single file."""

    model_config = ConfigDict(extra="forbid")

    path: str
    loc: int = 0
    sloc: int = 0
    comment_lines: int = 0
    blank_lines: int = 0
    comment_ratio: float = 0.0
    function_count: int = 0
    class_count: int = 0
    avg_function_length: float = 0.0
    avg_class_length: float = 0.0
    avg_nesting: float = 0.0


class MetricsReport(BaseModel):
    """Repository-wide code metrics."""

    model_config = ConfigDict(extra="forbid")

    total_loc: int = 0
    total_sloc: int = 0
    total_comment_lines: int = 0
    total_blank_lines: int = 0
    overall_comment_ratio: float = 0.0
    total_functions: int = 0
    total_classes: int = 0
    avg_function_length: float = 0.0
    avg_class_length: float = 0.0
    avg_nesting: float = 0.0
    per_file: list[FileMetrics] = Field(default_factory=list)


class ComplexityReport(BaseModel):
    """Cyclomatic / cognitive / maintainability / Halstead complexity."""

    model_config = ConfigDict(extra="forbid")

    top_complex_functions: list[dict[str, Any]] = Field(default_factory=list)
    top_complex_classes: list[dict[str, Any]] = Field(default_factory=list)
    maintainability_index: dict[str, float] = Field(default_factory=dict)
    halstead: dict[str, Any] = Field(default_factory=dict)
    average_complexity: float = 0.0


class GitAnalysis(BaseModel):
    """Git-history analysis result."""

    model_config = ConfigDict(extra="forbid")

    most_changed_files: list[tuple[str, int]] = Field(default_factory=list)
    most_active_directories: list[tuple[str, int]] = Field(default_factory=list)
    most_active_contributors: list[tuple[str, int]] = Field(default_factory=list)
    commit_distribution: dict[str, int] = Field(default_factory=dict)
    hotspots: list[tuple[str, float]] = Field(default_factory=list)
    total_commits: int = 0
    total_authors: int = 0


class DocumentationReport(BaseModel):
    """Documentation-coverage report."""

    model_config = ConfigDict(extra="forbid")

    has_installation: bool = False
    has_usage_example: bool = False
    has_api_docs: bool = False
    has_contribution_guide: bool = False
    has_license: bool = False
    has_changelog: bool = False
    has_wiki_link: bool = False
    readme_score: float = 0.0
    docstring_coverage: float = 0.0


class TestAnalysis(BaseModel):
    """Test-suite analysis result."""

    model_config = ConfigDict(extra="forbid")

    frameworks: list[str] = Field(default_factory=list)
    total_test_files: int = 0
    total_test_functions: int = 0
    estimated_coverage: float | None = None
    has_integration_tests: bool = False
    has_unit_tests: bool = False
    has_fixtures: bool = False
    has_mocks: bool = False
    test_files: list[str] = Field(default_factory=list)


class GraphReport(BaseModel):
    """Graph-engine output (NetworkX-derived summaries)."""

    model_config = ConfigDict(extra="forbid")

    dependency_graph: dict[str, Any] = Field(default_factory=dict)
    import_graph: dict[str, Any] = Field(default_factory=dict)
    directory_graph: dict[str, Any] = Field(default_factory=dict)
    module_graph: dict[str, Any] = Field(default_factory=dict)
    cycles: list[list[str]] = Field(default_factory=list)


__all__ = [
    "FileInventory",
    "RepositoryMetadata",
    "LanguageDistribution",
    "SymbolCollection",
    "ImportAnalysis",
    "DependencyAnalysis",
    "FileMetrics",
    "MetricsReport",
    "ComplexityReport",
    "GitAnalysis",
    "DocumentationReport",
    "TestAnalysis",
    "GraphReport",
]
