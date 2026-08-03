"""Tests for the domain models."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from repo_analyzer.core.domain.ai_review import AIReview, Priority, Recommendation
from repo_analyzer.core.domain.analysis_result import AnalysisResult, AnalysisStatus
from repo_analyzer.core.domain.architecture_finding import (
    ArchitectureFinding,
    ArchitectureSmell,
    ArchitectureSmellType,
    Cycle,
)
from repo_analyzer.core.domain.cache_entry import CacheEntry, CacheEntryType, CacheKey
from repo_analyzer.core.domain.config import ConfigSnapshot
from repo_analyzer.core.domain.dependency import Dependency, License, Version
from repo_analyzer.core.domain.health_score import Grade, HealthScore, ScoreWeights
from repo_analyzer.core.domain.issue import Issue, IssueType
from repo_analyzer.core.domain.metric import Metric
from repo_analyzer.core.domain.report import Finding, Location, Report, Severity
from repo_analyzer.core.domain.repository import (
    AccessMode,
    Credential,
    Repository,
    parse_repository_url,
)
from repo_analyzer.core.domain.security_finding import (
    Confidence,
    SecurityCategory,
    SecurityFinding,
)


class TestRepository:
    """Tests for the Repository model and URL parsing."""

    def test_parse_https_url(self) -> None:
        repo = parse_repository_url("https://github.com/owner/repo")
        assert repo.host == "github.com"
        assert repo.owner == "owner"
        assert repo.name == "repo"
        assert repo.access == AccessMode.PUBLIC

    def test_parse_ssh_url(self) -> None:
        repo = parse_repository_url("git@github.com:owner/repo.git")
        assert repo.host == "github.com"
        assert repo.owner == "owner"
        assert repo.name == "repo"

    def test_parse_url_strips_dot_git(self) -> None:
        repo = parse_repository_url("https://github.com/o/r.git")
        assert repo.name == "r"

    def test_parse_empty_url_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_repository_url("")

    def test_parse_invalid_url_raises(self) -> None:
        with pytest.raises(ValueError):
            parse_repository_url("not-a-url")

    def test_repository_to_ref(self) -> None:
        repo = parse_repository_url("https://github.com/o/r")
        ref = repo.to_ref()
        assert ref.url == repo.url
        assert ref.owner == repo.owner

    def test_private_requires_credential(self) -> None:
        with pytest.raises(ValueError):
            Repository(
                url="https://github.com/o/r",
                host="github.com",
                owner="o",
                name="r",
                access=AccessMode.PRIVATE,
            )

    def test_credential_repr_hides_value(self) -> None:
        cred = Credential(source="env", identifier="GRA_TOKEN")
        assert "GRA_TOKEN" in repr(cred)


class TestFindingAndReport:
    """Tests for Finding / Report models."""

    def test_finding_requires_message(self) -> None:
        with pytest.raises(ValueError):
            Finding(rule_id="r", severity=Severity.HIGH, message="")

    def test_severity_from_score(self) -> None:
        assert Severity.from_score(95) == Severity.CRITICAL
        assert Severity.from_score(75) == Severity.HIGH
        assert Severity.from_score(50) == Severity.MEDIUM
        assert Severity.from_score(20) == Severity.LOW
        assert Severity.from_score(5) == Severity.INFO

    def test_location_str(self) -> None:
        loc = Location(file="src/a.py", line=10, column=5)
        assert str(loc) == "src/a.py:10:5"

    def test_report_findings_by_severity(self) -> None:
        f1 = Finding(rule_id="r1", severity=Severity.HIGH, message="m1")
        f2 = Finding(rule_id="r2", severity=Severity.LOW, message="m2")
        report = Report(repository_url="https://x", findings=[f1, f2])
        grouped = report.findings_by_severity
        assert len(grouped[Severity.HIGH]) == 1
        assert len(grouped[Severity.LOW]) == 1


class TestIssue:
    def test_issue_to_finding(self) -> None:
        issue = Issue(
            type=IssueType.COMPLEXITY,
            severity=Severity.MEDIUM,
            message="too complex",
        )
        finding = issue.to_finding()
        assert finding.severity == Severity.MEDIUM
        assert finding.category == "complexity"

    def test_issue_to_finding_custom_rule_id(self) -> None:
        issue = Issue(type=IssueType.DEAD_CODE, severity=Severity.LOW, message="m")
        finding = issue.to_finding(rule_id="custom.rule")
        assert finding.rule_id == "custom.rule"


class TestMetric:
    def test_passes_threshold_no_threshold(self) -> None:
        m = Metric(name="x", value=5.0)
        assert m.passes_threshold is True

    def test_passes_threshold_lower_is_better(self) -> None:
        m = Metric(name="complexity", value=5.0, threshold=10.0, metadata={"lower_is_better": True})
        assert m.passes_threshold is True
        m2 = Metric(
            name="complexity", value=15.0, threshold=10.0, metadata={"lower_is_better": True}
        )
        assert m2.passes_threshold is False

    def test_passes_threshold_higher_is_better(self) -> None:
        m = Metric(name="coverage", value=80.0, threshold=70.0, metadata={"lower_is_better": False})
        assert m.passes_threshold is True


class TestSecurityFinding:
    def test_to_finding(self) -> None:
        sf = SecurityFinding(
            rule_id="bandit.B101",
            severity=Severity.HIGH,
            confidence=Confidence.HIGH,
            message="assert detected",
            category=SecurityCategory.SAST,
        )
        finding = sf.to_finding()
        assert finding.severity == Severity.HIGH
        assert finding.category == "sast"

    def test_confidence_to_float(self) -> None:
        assert Confidence.HIGH.to_float() == 0.9
        assert Confidence.MEDIUM.to_float() == 0.6
        assert Confidence.LOW.to_float() == 0.3


class TestArchitectureFinding:
    def test_cycle_str(self) -> None:
        cycle = Cycle(nodes=["a", "b", "c"])
        assert str(cycle) == "a -> b -> c -> a"

    def test_has_issues_true_with_cycles(self) -> None:
        finding = ArchitectureFinding(cycles=[Cycle(nodes=["a", "b"])])
        assert finding.has_issues is True

    def test_has_issues_true_with_smells(self) -> None:
        smell = ArchitectureSmell(type=ArchitectureSmellType.GOD_CLASS, message="m")
        finding = ArchitectureFinding(smells=[smell])
        assert finding.has_issues is True

    def test_has_issues_false_when_empty(self) -> None:
        finding = ArchitectureFinding()
        assert finding.has_issues is False


class TestDependency:
    def test_version_parse_full(self) -> None:
        v = Version.parse("1.2.3-alpha+build")
        assert v.major == 1
        assert v.minor == 2
        assert v.patch == 3
        assert v.prerelease == "alpha"
        assert v.build == "build"

    def test_version_parse_simple(self) -> None:
        v = Version.parse("2.0.0")
        assert v.major == 2

    def test_version_parse_invalid_returns_raw(self) -> None:
        v = Version.parse("not-a-version")
        assert v.major == 0

    def test_version_str(self) -> None:
        v = Version.parse("1.2.3")
        assert str(v) == "1.2.3"

    def test_license_str(self) -> None:
        lic = License(spdx_id="MIT")
        assert str(lic) == "MIT"

    def test_dependency_is_vulnerable(self) -> None:
        dep = Dependency(
            name="x",
            version=Version.parse("1.0.0"),
            ecosystem="pypi",
            vulnerabilities=[{"id": "CVE-1"}],
        )
        assert dep.is_vulnerable is True

    def test_dependency_not_vulnerable(self) -> None:
        dep = Dependency(name="x", version=Version.parse("1.0.0"), ecosystem="pypi")
        assert dep.is_vulnerable is False


class TestHealthScore:
    def test_recompute_overall(self) -> None:
        score = HealthScore(
            security_score=80,
            quality_score=90,
            architecture_score=70,
            test_score=60,
        )
        score.recompute_overall()
        # Ağırlıklar JS puanlama motoruyla senkronize (0.15/0.25/0.20/0.15),
        # normalizasyon sonrası toplam 0.75 üzerinden oransal ağırlıklar.
        w = ScoreWeights()
        expected = 80 * w.security + 90 * w.quality + 70 * w.architecture + 60 * w.test
        assert abs(score.overall - expected) < 0.01
        assert abs((w.security + w.quality + w.architecture + w.test) - 1.0) < 0.001

    def test_grade_from_score(self) -> None:
        assert Grade.from_score(95) == Grade.A
        assert Grade.from_score(85) == Grade.B
        assert Grade.from_score(75) == Grade.C
        assert Grade.from_score(65) == Grade.D
        assert Grade.from_score(55) == Grade.E
        assert Grade.from_score(30) == Grade.F

    def test_score_weights_normalize(self) -> None:
        w = ScoreWeights(security=0.5, quality=0.5, architecture=0.5, test=0.5)
        total = w.security + w.quality + w.architecture + w.test
        assert abs(total - 1.0) < 0.001

    def test_grade_property(self) -> None:
        score = HealthScore(overall=92)
        assert score.grade == Grade.A


class TestAIReview:
    def test_recommendation_validates_effort(self) -> None:
        with pytest.raises(ValueError):
            Recommendation(title="t", description="d", effort="bogus")

    def test_recommendation_default_priority(self) -> None:
        rec = Recommendation(title="t", description="d")
        assert rec.priority == Priority.MEDIUM

    def test_ai_review_strips_summary(self) -> None:
        review = AIReview(summary="  trimmed  ")
        assert review.summary == "trimmed"


class TestAnalysisResult:
    def test_mark_running(self) -> None:
        repo = parse_repository_url("https://github.com/o/r")
        result = AnalysisResult(repository=repo)
        result.mark_running()
        assert result.status == AnalysisStatus.RUNNING

    def test_mark_completed_sets_finished_at(self) -> None:
        repo = parse_repository_url("https://github.com/o/r")
        result = AnalysisResult(repository=repo)
        result.mark_completed()
        assert result.status == AnalysisStatus.COMPLETED
        assert result.finished_at is not None

    def test_mark_failed_records_error(self) -> None:
        repo = parse_repository_url("https://github.com/o/r")
        result = AnalysisResult(repository=repo)
        result.mark_failed({"code": "X"})
        assert result.status == AnalysisStatus.FAILED
        assert len(result.errors) == 1

    def test_total_findings(self) -> None:
        repo = parse_repository_url("https://github.com/o/r")
        result = AnalysisResult(repository=repo)
        result.security_findings.append(
            SecurityFinding(rule_id="r", severity=Severity.LOW, message="m")
        )
        result.issues.append(Issue(type=IssueType.STYLE, severity=Severity.LOW, message="m"))
        assert result.total_findings == 2

    def test_add_error_does_not_change_status(self) -> None:
        repo = parse_repository_url("https://github.com/o/r")
        result = AnalysisResult(repository=repo)
        original_status = result.status
        result.add_error({"x": 1})
        assert result.status == original_status
        assert len(result.errors) == 1


class TestCacheEntry:
    def test_cache_key_to_hash_is_stable(self) -> None:
        k1 = CacheKey(repository_url="https://github.com/o/r")
        k2 = CacheKey(repository_url="https://github.com/o/r")
        assert k1.to_hash() == k2.to_hash()

    def test_cache_key_differs_for_different_urls(self) -> None:
        k1 = CacheKey(repository_url="https://github.com/o/r")
        k2 = CacheKey(repository_url="https://github.com/o/s")
        assert k1.to_hash() != k2.to_hash()

    def test_cache_entry_is_expired(self) -> None:
        entry = CacheEntry(
            key="abc",
            repository_url="https://github.com/o/r",
            expires_at=datetime.now(tz=UTC) - timedelta(days=1),
        )
        assert entry.is_expired is True

    def test_cache_entry_not_expired(self) -> None:
        entry = CacheEntry(
            key="abc",
            repository_url="https://github.com/o/r",
            expires_at=datetime.now(tz=UTC) + timedelta(days=1),
        )
        assert entry.is_expired is False

    def test_cache_entry_touch_updates_access(self) -> None:
        entry = CacheEntry(key="abc", repository_url="https://github.com/o/r")
        original_count = entry.access_count
        entry.touch()
        assert entry.access_count == original_count + 1

    def test_cache_entry_type_enum(self) -> None:
        assert CacheEntryType.CLONE.value == "clone"
        assert CacheEntryType.ANALYSIS.value == "analysis"
        assert CacheEntryType.AI_REVIEW.value == "ai_review"


class TestConfigSnapshot:
    def test_from_config(self) -> None:
        from repo_analyzer.infrastructure.config import load_config

        config = load_config(overrides={"cache": {"dir": "/tmp/x"}})
        snapshot = ConfigSnapshot.from_config(config)
        assert snapshot.log_level == config.log_level
        assert snapshot.cache_dir == config.cache.dir
