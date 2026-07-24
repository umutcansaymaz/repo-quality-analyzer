"""Unit tests for the Evidence Engine.

Covers:
    - Empty result (no findings)
    - Single analyzer output
    - Multiple analyzer outputs
    - Duplicate finding normalization
    - Missing / partial fields
    - Plugin analyzer (custom evidence)
    - Relationship building
    - Index correctness
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from repo_analyzer.core.domain.analysis_outputs import (
    ComplexityReport,
    DependencyAnalysis,
    DocumentationReport,
    FileInventory,
    FileMetrics,
    GitAnalysis,
    ImportAnalysis,
    MetricsReport,
    RepositoryMetadata,
    SymbolCollection,
    TestAnalysis,
)
from repo_analyzer.core.domain.analysis_result import AnalysisResult
from repo_analyzer.core.domain.architecture_finding import (
    ArchitectureFinding,
    ArchitectureSmell,
    ArchitectureSmellType,
    Cycle,
)
from repo_analyzer.core.domain.report import Location, Severity
from repo_analyzer.core.domain.repository import parse_repository_url
from repo_analyzer.core.domain.security_finding import (
    Confidence,
    SecurityCategory,
    SecurityFinding,
)
from repo_analyzer.core.evidence import (
    Evidence,
    EvidenceBuilder,
    EvidenceCollection,
    EvidenceReference,
    EvidenceType,
    ReferenceKind,
    RelationshipType,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def empty_result() -> AnalysisResult:
    """An AnalysisResult with no findings — only the repository."""
    repo = parse_repository_url("https://github.com/test/empty")
    return AnalysisResult(repository=repo)


@pytest.fixture()
def single_security_result() -> AnalysisResult:
    """An AnalysisResult with one security finding."""
    repo = parse_repository_url("https://github.com/test/repo")
    result = AnalysisResult(repository=repo)
    result.security_findings = [
        SecurityFinding(
            rule_id="bandit.B101",
            category=SecurityCategory.SAST,
            severity=Severity.HIGH,
            confidence=Confidence.HIGH,
            message="Use of assert detected",
            location=Location(file="src/app.py", line=42),
            description="assert statements are stripped in optimized mode",
            fix_suggestion="Use if/raise instead",
            cwe="CWE-617",
            cvss=5.0,
        )
    ]
    return result


@pytest.fixture()
def multi_analyzer_result() -> AnalysisResult:
    """An AnalysisResult with findings from multiple analyzers."""
    repo = parse_repository_url("https://github.com/test/multi")
    result = AnalysisResult(repository=repo)
    # Security finding.
    result.security_findings = [
        SecurityFinding(
            rule_id="custom.hardcoded_password",
            category=SecurityCategory.SECRET,
            severity=Severity.HIGH,
            confidence=Confidence.HIGH,
            message="Hardcoded password",
            location=Location(file="config.py", line=10),
        )
    ]
    # Complexity report.
    result.complexity_report = ComplexityReport(
        top_complex_functions=[
            {
                "name": "complex_func",
                "file": "src/app.py",
                "lineno": 5,
                "complexity": 15,
                "rank": "C",
            },
        ],
        average_complexity=15.0,
    )
    # Import analysis.
    result.import_analysis = ImportAnalysis(
        unused_imports=[{"name": "os", "file": "src/app.py", "module": "os"}],
        circular_imports=[["module_a", "module_b", "module_a"]],
    )
    # Dependency analysis.
    result.dependency_analysis = DependencyAnalysis(
        unused_dependencies=["unused-package"],
        total_dependencies=5,
    )
    # Metrics report.
    result.metrics_report = MetricsReport(
        total_loc=100,
        total_sloc=80,
        per_file=[
            FileMetrics(path="src/big_file.py", loc=600, sloc=550, function_count=3),
        ],
    )
    # Symbols.
    result.symbols = SymbolCollection(
        functions=[{"name": "greet", "file": "src/app.py", "line": 1}],
        classes=[{"name": "Animal", "file": "src/app.py", "line": 10}],
    )
    # File inventory.
    result.file_inventory = FileInventory(
        total_files=10,
        duplicate_groups=[("abc123", ["file_a.py", "file_b.py"])],
    )
    # Architecture finding.
    result.architecture = ArchitectureFinding(
        coupling=0.8,
        cohesion=0.3,
        cycles=[Cycle(nodes=["mod_a", "mod_b"])],
        smells=[
            ArchitectureSmell(
                type=ArchitectureSmellType.CYCLIC_DEPENDENCY,
                severity=Severity.HIGH,
                message="Circular dependency detected",
                affected_modules=["mod_a", "mod_b"],
            )
        ],
    )
    # Documentation.
    result.documentation_report = DocumentationReport(
        has_installation=False,
        docstring_coverage=0.1,
    )
    # Tests.
    result.test_analysis = TestAnalysis(total_test_files=0)
    # Git.
    result.git_analysis = GitAnalysis(
        most_changed_files=[("src/hotspot.py", 25)],
        total_commits=100,
    )
    # Repository metadata.
    result.repository_metadata = RepositoryMetadata(
        name="multi",
        owner="test",
        total_commits=100,
    )
    return result


# ---------------------------------------------------------------------------
# Tests: empty result
# ---------------------------------------------------------------------------


class TestEmptyResult:
    def test_empty_result_produces_empty_collection(self, empty_result: AnalysisResult) -> None:
        collection = EvidenceBuilder.build(empty_result)
        assert isinstance(collection, EvidenceCollection)
        assert collection.total == 0
        assert len(collection.relationships) == 0

    def test_empty_collection_has_empty_indexes(self, empty_result: AnalysisResult) -> None:
        collection = EvidenceBuilder.build(empty_result)
        assert collection.by_analyzer == {}
        assert collection.by_severity == {}
        assert collection.by_file == {}
        assert collection.by_type == {}

    def test_empty_collection_statistics(self, empty_result: AnalysisResult) -> None:
        collection = EvidenceBuilder.build(empty_result)
        assert collection.statistics["total_evidence"] == 0
        assert collection.statistics["total_relationships"] == 0


# ---------------------------------------------------------------------------
# Tests: single analyzer
# ---------------------------------------------------------------------------


class TestSingleAnalyzer:
    def test_single_security_finding(self, single_security_result: AnalysisResult) -> None:
        collection = EvidenceBuilder.build(single_security_result)
        assert collection.total >= 1
        security_evidence = collection.filter_by_type(EvidenceType.SECURITY)
        assert len(security_evidence) >= 1

    def test_evidence_has_correct_analyzer(self, single_security_result: AnalysisResult) -> None:
        collection = EvidenceBuilder.build(single_security_result)
        assert "security-engine" in collection.by_analyzer

    def test_evidence_has_severity(self, single_security_result: AnalysisResult) -> None:
        collection = EvidenceBuilder.build(single_security_result)
        ev = collection.evidence[0]
        assert ev.severity == Severity.HIGH

    def test_evidence_has_file_path(self, single_security_result: AnalysisResult) -> None:
        collection = EvidenceBuilder.build(single_security_result)
        ev = collection.filter_by_type(EvidenceType.SECURITY)[0]
        assert ev.file_path == "src/app.py"
        assert ev.line == 42

    def test_evidence_has_references(self, single_security_result: AnalysisResult) -> None:
        collection = EvidenceBuilder.build(single_security_result)
        ev = collection.filter_by_type(EvidenceType.SECURITY)[0]
        assert len(ev.references) >= 1
        file_ref = [r for r in ev.references if r.kind == ReferenceKind.FILE]
        assert len(file_ref) >= 1
        assert file_ref[0].value == "src/app.py"

    def test_evidence_has_source_id(self, single_security_result: AnalysisResult) -> None:
        collection = EvidenceBuilder.build(single_security_result)
        ev = collection.evidence[0]
        assert ev.source_id is not None

    def test_evidence_is_immutable(self, single_security_result: AnalysisResult) -> None:
        collection = EvidenceBuilder.build(single_security_result)
        ev = collection.evidence[0]
        with pytest.raises(Exception):  # noqa: B017
            ev.message = "mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Tests: multiple analyzers
# ---------------------------------------------------------------------------


class TestMultipleAnalyzers:
    def test_multiple_types_present(self, multi_analyzer_result: AnalysisResult) -> None:
        collection = EvidenceBuilder.build(multi_analyzer_result)
        types_present = {ev.finding_type for ev in collection.evidence}
        assert EvidenceType.SECURITY in types_present
        assert EvidenceType.COMPLEXITY in types_present
        assert EvidenceType.IMPORT in types_present
        assert EvidenceType.DEPENDENCY in types_present
        assert EvidenceType.METRIC in types_present
        assert EvidenceType.SYMBOL in types_present
        assert EvidenceType.ARCHITECTURE in types_present
        assert EvidenceType.DOCUMENTATION in types_present
        assert EvidenceType.TEST in types_present
        assert EvidenceType.GIT in types_present
        assert EvidenceType.REPOSITORY in types_present

    def test_by_analyzer_index(self, multi_analyzer_result: AnalysisResult) -> None:
        collection = EvidenceBuilder.build(multi_analyzer_result)
        assert "security-engine" in collection.by_analyzer
        assert "complexity-analyzer" in collection.by_analyzer
        assert "import-analyzer" in collection.by_analyzer
        assert "dependency-analyzer" in collection.by_analyzer
        assert "metrics-engine" in collection.by_analyzer
        assert "ast-analyzer" in collection.by_analyzer
        assert "graph-engine" in collection.by_analyzer
        assert "documentation-analyzer" in collection.by_analyzer
        assert "test-coverage-analyzer" in collection.by_analyzer
        assert "git-history-analyzer" in collection.by_analyzer
        assert "repository-detector" in collection.by_analyzer

    def test_by_severity_index(self, multi_analyzer_result: AnalysisResult) -> None:
        collection = EvidenceBuilder.build(multi_analyzer_result)
        assert "high" in collection.by_severity
        assert len(collection.by_severity["high"]) >= 1

    def test_by_file_index(self, multi_analyzer_result: AnalysisResult) -> None:
        collection = EvidenceBuilder.build(multi_analyzer_result)
        assert "src/app.py" in collection.by_file
        assert "config.py" in collection.by_file

    def test_statistics_correct(self, multi_analyzer_result: AnalysisResult) -> None:
        collection = EvidenceBuilder.build(multi_analyzer_result)
        stats = collection.statistics
        assert stats["total_evidence"] == collection.total
        assert stats["total_relationships"] == len(collection.relationships)
        assert stats["total_evidence"] > 0
        assert "by_analyzer_counts" in stats
        assert "by_severity_counts" in stats

    def test_filter_by_file(self, multi_analyzer_result: AnalysisResult) -> None:
        collection = EvidenceBuilder.build(multi_analyzer_result)
        app_py_evidence = collection.filter_by_file("src/app.py")
        assert len(app_py_evidence) >= 1

    def test_filter_by_type(self, multi_analyzer_result: AnalysisResult) -> None:
        collection = EvidenceBuilder.build(multi_analyzer_result)
        security = collection.filter_by_type(EvidenceType.SECURITY)
        assert len(security) >= 1


# ---------------------------------------------------------------------------
# Tests: duplicate normalization
# ---------------------------------------------------------------------------


class TestDuplicateNormalization:
    def test_duplicates_are_merged(self) -> None:
        """Two security findings in the same file+category should merge."""
        repo = parse_repository_url("https://github.com/test/dup")
        result = AnalysisResult(repository=repo)
        result.security_findings = [
            SecurityFinding(
                rule_id="r1",
                category=SecurityCategory.SAST,
                severity=Severity.LOW,
                confidence=Confidence.LOW,
                message="Finding A",
                location=Location(file="app.py", line=1),
            ),
            SecurityFinding(
                rule_id="r2",
                category=SecurityCategory.SAST,
                severity=Severity.HIGH,
                confidence=Confidence.HIGH,
                message="Finding B",
                location=Location(file="app.py", line=2),
            ),
        ]
        collection = EvidenceBuilder.build(result)
        # Both have file_path="app.py", symbol=None, finding_type=SECURITY, category="sast"
        # → dedup key is the same → should merge to 1.
        security = collection.filter_by_type(EvidenceType.SECURITY)
        assert len(security) == 1
        # The keeper should be the one with higher severity.
        assert security[0].severity == Severity.HIGH

    def test_duplicate_relationship_recorded(self) -> None:
        repo = parse_repository_url("https://github.com/test/dup")
        result = AnalysisResult(repository=repo)
        result.security_findings = [
            SecurityFinding(
                rule_id="r1",
                category=SecurityCategory.SAST,
                severity=Severity.LOW,
                message="Finding A",
                location=Location(file="app.py"),
            ),
            SecurityFinding(
                rule_id="r2",
                category=SecurityCategory.SAST,
                severity=Severity.HIGH,
                message="Finding B",
                location=Location(file="app.py"),
            ),
        ]
        collection = EvidenceBuilder.build(result)
        assert len(collection.relationships) >= 1
        dup_rels = [
            r for r in collection.relationships if r.relationship_type == RelationshipType.DUPLICATE
        ]
        assert len(dup_rels) >= 1

    def test_no_data_lost_on_dedup(self) -> None:
        """The keeper's related_evidence_ids should contain the discarded item's id."""
        repo = parse_repository_url("https://github.com/test/dup")
        result = AnalysisResult(repository=repo)
        result.security_findings = [
            SecurityFinding(
                rule_id="r1",
                category=SecurityCategory.SAST,
                severity=Severity.LOW,
                message="Finding A",
                location=Location(file="app.py"),
            ),
            SecurityFinding(
                rule_id="r2",
                category=SecurityCategory.SAST,
                severity=Severity.HIGH,
                message="Finding B",
                location=Location(file="app.py"),
            ),
        ]
        collection = EvidenceBuilder.build(result)
        keeper = collection.filter_by_type(EvidenceType.SECURITY)[0]
        assert len(keeper.related_evidence_ids) >= 1

    def test_non_duplicates_not_merged(self) -> None:
        """Findings in different files should not be merged."""
        repo = parse_repository_url("https://github.com/test/nodup")
        result = AnalysisResult(repository=repo)
        result.security_findings = [
            SecurityFinding(
                rule_id="r1",
                category=SecurityCategory.SAST,
                severity=Severity.LOW,
                message="Finding A",
                location=Location(file="app.py"),
            ),
            SecurityFinding(
                rule_id="r2",
                category=SecurityCategory.SAST,
                severity=Severity.HIGH,
                message="Finding B",
                location=Location(file="other.py"),
            ),
        ]
        collection = EvidenceBuilder.build(result)
        security = collection.filter_by_type(EvidenceType.SECURITY)
        assert len(security) == 2


# ---------------------------------------------------------------------------
# Tests: missing / partial fields
# ---------------------------------------------------------------------------


class TestPartialFields:
    def test_missing_location(self) -> None:
        """Security findings without a location should still produce evidence."""
        repo = parse_repository_url("https://github.com/test/noloc")
        result = AnalysisResult(repository=repo)
        result.security_findings = [
            SecurityFinding(
                rule_id="r1",
                category=SecurityCategory.SAST,
                severity=Severity.LOW,
                message="No location",
            )
        ]
        collection = EvidenceBuilder.build(result)
        ev = collection.filter_by_type(EvidenceType.SECURITY)[0]
        assert ev.file_path is None
        assert ev.line is None

    def test_missing_complexity_report(self, empty_result: AnalysisResult) -> None:
        collection = EvidenceBuilder.build(empty_result)
        assert len(collection.filter_by_type(EvidenceType.COMPLEXITY)) == 0

    def test_missing_symbols(self, empty_result: AnalysisResult) -> None:
        collection = EvidenceBuilder.build(empty_result)
        assert len(collection.filter_by_type(EvidenceType.SYMBOL)) == 0

    def test_missing_ai_review(self, empty_result: AnalysisResult) -> None:
        collection = EvidenceBuilder.build(empty_result)
        assert len(collection.filter_by_type(EvidenceType.CODE_QUALITY)) == 0
        assert len(collection.filter_by_type(EvidenceType.RISK)) == 0
        assert len(collection.filter_by_type(EvidenceType.TECHNICAL_DEBT)) == 0

    def test_partial_complexity_report(self) -> None:
        """Complexity report with empty top_complex_functions."""
        repo = parse_repository_url("https://github.com/test/partial")
        result = AnalysisResult(repository=repo)
        result.complexity_report = ComplexityReport(average_complexity=2.0)
        collection = EvidenceBuilder.build(result)
        assert len(collection.filter_by_type(EvidenceType.COMPLEXITY)) == 0


# ---------------------------------------------------------------------------
# Tests: plugin analyzer (custom evidence source)
# ---------------------------------------------------------------------------


class TestPluginCompatibility:
    def test_builder_reads_whatever_is_present(self) -> None:
        """The builder should work with any AnalysisResult, regardless of
        which analyzers populated it. No hardcoded analyzer names are used."""
        repo = parse_repository_url("https://github.com/test/plugin")
        result = AnalysisResult(repository=repo)
        # Only populate one field — simulating a custom plugin that only
        # fills in metrics_report.
        result.metrics_report = MetricsReport(
            per_file=[FileMetrics(path="big.py", loc=600, sloc=550)],
        )
        collection = EvidenceBuilder.build(result)
        assert collection.total >= 1
        metrics = collection.filter_by_type(EvidenceType.METRIC)
        assert len(metrics) >= 1

    def test_builder_does_not_require_specific_analyzers(
        self, empty_result: AnalysisResult
    ) -> None:
        """Building from an empty result must not raise."""
        collection = EvidenceBuilder.build(empty_result)
        assert collection.total == 0

    def test_evidence_from_custom_data(self) -> None:
        """Evidence can be created directly without any analyzer."""
        ev = Evidence(
            analyzer="custom-plugin",
            finding_type=EvidenceType.CODE_QUALITY,
            severity=Severity.MEDIUM,
            message="Custom finding",
            tags=["custom"],
        )
        assert ev.analyzer == "custom-plugin"
        assert ev.finding_type == EvidenceType.CODE_QUALITY


# ---------------------------------------------------------------------------
# Tests: relationship building
# ---------------------------------------------------------------------------


class TestRelationships:
    def test_no_relationships_when_no_duplicates(
        self, single_security_result: AnalysisResult
    ) -> None:
        collection = EvidenceBuilder.build(single_security_result)
        assert len(collection.relationships) == 0

    def test_relationships_link_correct_ids(self) -> None:
        repo = parse_repository_url("https://github.com/test/rel")
        result = AnalysisResult(repository=repo)
        result.security_findings = [
            SecurityFinding(
                rule_id="r1",
                category=SecurityCategory.SAST,
                severity=Severity.LOW,
                message="A",
                location=Location(file="app.py"),
            ),
            SecurityFinding(
                rule_id="r2",
                category=SecurityCategory.SAST,
                severity=Severity.HIGH,
                message="B",
                location=Location(file="app.py"),
            ),
        ]
        collection = EvidenceBuilder.build(result)
        for rel in collection.relationships:
            assert rel.source_id != rel.target_id
            assert rel.relationship_type == RelationshipType.DUPLICATE


# ---------------------------------------------------------------------------
# Tests: model properties
# ---------------------------------------------------------------------------


class TestModelProperties:
    def test_evidence_dedup_key(self) -> None:
        ev = Evidence(
            analyzer="test",
            finding_type=EvidenceType.SECURITY,
            severity=Severity.HIGH,
            file_path="app.py",
            symbol="func_a",
            category="sast",
            message="test",
        )
        key = ev.dedup_key()
        assert key == ("app.py", "func_a", "security", "sast")

    def test_evidence_reference_is_immutable(self) -> None:
        ref = EvidenceReference(kind=ReferenceKind.FILE, value="app.py", line=10)
        with pytest.raises(Exception):  # noqa: B017
            ref.value = "other.py"  # type: ignore[misc]

    def test_collection_total_property(self, single_security_result: AnalysisResult) -> None:
        collection = EvidenceBuilder.build(single_security_result)
        assert collection.total == len(collection.evidence)

    def test_collection_get_by_id(self, single_security_result: AnalysisResult) -> None:
        collection = EvidenceBuilder.build(single_security_result)
        ev = collection.evidence[0]
        found = collection.get_by_id(ev.id)
        assert found is not None
        assert found.id == ev.id
        assert collection.get_by_id(uuid4()) is None

    def test_collection_by_severity_counts(self, single_security_result: AnalysisResult) -> None:
        collection = EvidenceBuilder.build(single_security_result)
        counts = collection.by_severity_counts
        assert "high" in counts
        assert counts["high"] >= 1
