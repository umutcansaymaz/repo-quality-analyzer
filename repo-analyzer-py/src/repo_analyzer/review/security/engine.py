"""Security review engine.

Runs three layers of security analysis:

1. **Bandit** — Python SAST (if installed).
2. **detect-secrets** — secret scanning (if installed).
3. **Custom regex rules** — hardcoded credentials, API keys, unsafe patterns.

Each finding is enriched with engineering context: why it is risky, the
real-world impact, a fix and a safe-code example.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from repo_analyzer.core.domain.repository import Repository
from repo_analyzer.core.domain.review_outputs import (
    RiskLevel,
    SecurityFindingDetail,
    SecurityReview,
)
from repo_analyzer.infrastructure.logging import get_logger

_logger = get_logger(__name__)

#: Custom regex rules for secret / unsafe-pattern detection.
#: Each rule: (id, title, category, severity, pattern, why, risk, solution, safe_example, references).
_CUSTOM_RULES: list[dict[str, Any]] = [
    {
        "id": "hardcoded_password",
        "title": "Hardcoded Password",
        "category": "hardcoded_password",
        "severity": RiskLevel.HIGH,
        "pattern": r"""(?i)(?:password|passwd|pwd)\s*[:=]\s*['"]([^'"]{4,})['"]""",
        "why": "Hardcoded passwords can be extracted from source code or compiled artifacts, granting unauthorized access.",
        "risk": "Credential theft leading to account compromise, data breaches, and privilege escalation.",
        "solution": "Load secrets from environment variables or a secret manager (Vault, AWS Secrets Manager).",
        "safe": "password = os.environ['DB_PASSWORD']",
        "refs": ["CWE-798", "OWASP A07:2021"],
    },
    {
        "id": "hardcoded_token",
        "title": "Hardcoded Token",
        "category": "hardcoded_token",
        "severity": RiskLevel.HIGH,
        "pattern": r"""(?i)(?:token|api_key|apikey|secret_key)\s*[:=]\s*['"]([A-Za-z0-9_\-]{20,})['"]""",
        "why": "Tokens embedded in source are trivially extracted from public repos or decompiled binaries.",
        "risk": "API abuse, impersonation, unauthorized access to third-party services.",
        "solution": "Store tokens in environment variables or a secrets vault; rotate immediately if committed.",
        "safe": "api_key = os.environ['API_KEY']",
        "refs": ["CWE-798", "OWASP A07:2021"],
    },
    {
        "id": "hardcoded_jwt",
        "title": "Hardcoded JWT",
        "category": "hardcoded_jwt",
        "severity": RiskLevel.CRITICAL,
        "pattern": r"""eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}""",
        "why": "JWTs contain claims and may encode user identities or permissions; a leaked JWT is a live credential.",
        "risk": "Authentication bypass, impersonation of any user encoded in the token.",
        "solution": "Issue JWTs at runtime from a secure auth service; never commit sample tokens.",
        "safe": "token = auth_service.issue_jwt(user)",
        "refs": ["CWE-798", "OWASP A01:2021"],
    },
    {
        "id": "aws_key",
        "title": "AWS Access Key ID",
        "category": "aws_key",
        "severity": RiskLevel.CRITICAL,
        "pattern": r"""AKIA[0-9A-Z]{16}""",
        "why": "AWS access key IDs are permanent credentials; the secret access key is usually nearby.",
        "risk": "Full compromise of the AWS account — data exfiltration, resource abuse, ransomware.",
        "solution": "Use IAM roles for compute; rotate the key immediately via the IAM console.",
        "safe": "session = boto3.Session(profile_name='prod')",
        "refs": ["CWE-798", "OWASP A07:2021"],
    },
    {
        "id": "openai_key",
        "title": "OpenAI API Key",
        "category": "openai_key",
        "severity": RiskLevel.HIGH,
        "pattern": r"""sk-[A-Za-z0-9]{20,}""",
        "why": "OpenAI keys are billed per usage; a leaked key leads to direct financial loss.",
        "risk": "Unauthorized API usage billed to the account owner; potential data exfiltration via completions.",
        "solution": "Rotate the key in the OpenAI dashboard; load from a secret manager at runtime.",
        "safe": "openai.api_key = os.environ['OPENAI_API_KEY']",
        "refs": ["CWE-798"],
    },
    {
        "id": "stripe_key",
        "title": "Stripe Secret Key",
        "category": "stripe_key",
        "severity": RiskLevel.CRITICAL,
        "pattern": r"""sk_live_[A-Za-z0-9]{20,}""",
        "why": "Stripe live keys can create charges, refunds, and access customer PII.",
        "risk": "Financial fraud, PCI compliance violation, theft of customer card data.",
        "solution": "Roll the key immediately in the Stripe dashboard; use restricted keys with minimal scopes.",
        "safe": "stripe.api_key = os.environ['STRIPE_SECRET_KEY']",
        "refs": ["CWE-798", "OWASP A07:2021"],
    },
    {
        "id": "github_token",
        "title": "GitHub Personal Access Token",
        "category": "github_token",
        "severity": RiskLevel.CRITICAL,
        "pattern": r"""gh[pousr]_[A-Za-z0-9]{36,}""",
        "why": "GitHub tokens grant repository, organization and sometimes admin access.",
        "risk": "Source code theft, forced pushes, secret mining across repos, org-wide compromise.",
        "solution": "Revoke the token at github.com/settings/tokens; use GitHub Apps for automation.",
        "safe": "gh = github.Github(os.environ['GITHUB_TOKEN'])",
        "refs": ["CWE-798", "OWASP A07:2021"],
    },
    {
        "id": "private_ssh_key",
        "title": "Private SSH Key",
        "category": "private_ssh_key",
        "severity": RiskLevel.CRITICAL,
        "pattern": r"""-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----""",
        "why": "Private SSH keys grant passwordless access to every server the key is authorized on.",
        "risk": "Lateral movement, server compromise, supply-chain attacks via git push.",
        "solution": "Never commit private keys; rotate the keypair and remove from history via filter-branch.",
        "safe": "# Store keys in ~/.ssh/ with 600 permissions; use ssh-agent.",
        "refs": ["CWE-798", "OWASP A07:2021"],
    },
    {
        "id": "env_leak",
        "title": "Committed .env File",
        "category": "env_leak",
        "severity": RiskLevel.HIGH,
        "pattern": r"""^(?:[A-Z_]+=.+)$""",
        "filename_pattern": r"\.env(?:\.(?:local|development|production))?$",
        "why": ".env files typically contain database URLs, API keys and secrets in plaintext.",
        "risk": "Full credential exposure; often the single most damaging leak in a repository.",
        "solution": "Add .env to .gitignore; use .env.example with dummy values; rotate all leaked secrets.",
        "safe": "# .gitignore: .env",
        "refs": ["CWE-798", "OWASP A07:2021"],
    },
    {
        "id": "unsafe_eval",
        "title": "Unsafe eval()",
        "category": "unsafe_eval",
        "severity": RiskLevel.HIGH,
        "pattern": r"""\beval\s*\(""",
        "why": "eval() executes arbitrary code; if the argument is user-controlled it is a code-injection vector.",
        "risk": "Remote code execution (RCE), server takeover, data exfiltration.",
        "solution": "Avoid eval entirely; use ast.literal_eval for literals or a proper parser.",
        "safe": "value = ast.literal_eval(user_input)  # only for literals",
        "refs": ["CWE-95", "OWASP A03:2021"],
    },
    {
        "id": "unsafe_exec",
        "title": "Unsafe exec()",
        "category": "unsafe_exec",
        "severity": RiskLevel.HIGH,
        "pattern": r"""\bexec\s*\(""",
        "why": "exec() runs arbitrary Python code; combined with user input it enables RCE.",
        "risk": "Remote code execution, sandbox escape, persistence.",
        "solution": "Replace with a safe interpreter or a DSL parser; never exec user-supplied strings.",
        "safe": "# Use a restricted sandbox or avoid dynamic code execution.",
        "refs": ["CWE-95"],
    },
    {
        "id": "pickle_load",
        "title": "Unsafe pickle.load()",
        "category": "pickle",
        "severity": RiskLevel.HIGH,
        "pattern": r"""\bpickle\.loads?\(""",
        "why": "Pickle deserialization executes arbitrary code embedded in the pickle stream.",
        "risk": "RCE by any attacker who can supply a pickle file (e.g. a cached model).",
        "solution": "Use JSON or a schema-validated format; if pickle is unavoidable, sign the payload.",
        "safe": "data = json.loads(payload)",
        "refs": ["CWE-502", "OWASP A08:2021"],
    },
    {
        "id": "yaml_unsafe_load",
        "title": "Unsafe yaml.load()",
        "category": "yaml_load",
        "severity": RiskLevel.HIGH,
        "pattern": r"""\byaml\.load\s*\((?!\s*.*Loader)""",
        "why": "yaml.load() without a SafeLoader executes arbitrary Python objects tagged in the YAML.",
        "risk": "RCE via crafted YAML files (configuration, CI configs).",
        "solution": "Always pass Loader=yaml.SafeLoader or use yaml.safe_load().",
        "safe": "data = yaml.safe_load(stream)",
        "refs": ["CWE-502", "OWASP A08:2021"],
    },
    {
        "id": "shell_true",
        "title": "subprocess with shell=True",
        "category": "shell_true",
        "severity": RiskLevel.HIGH,
        "pattern": r"""subprocess\.\w+\([^)]*shell\s*=\s*True""",
        "why": "shell=True passes the command through a shell, enabling injection via shell metacharacters.",
        "risk": "Command injection — attacker-controlled arguments become shell commands.",
        "solution": "Pass args as a list with shell=False; sanitize and validate inputs.",
        "safe": "subprocess.run(['ls', path], check=True)",
        "refs": ["CWE-78", "OWASP A03:2021"],
    },
    {
        "id": "sql_injection",
        "title": "Potential SQL Injection",
        "category": "sql_injection",
        "severity": RiskLevel.HIGH,
        "pattern": r"""(?:execute|executemany)\s*\(\s*(?:['"]|%s|f['"]).*(?:%s|\{|format)""",
        "why": "String-interpolated SQL allows attackers to append or modify the query.",
        "risk": "Data exfiltration, authentication bypass, data destruction.",
        "solution": "Use parameterized queries / an ORM; never f-string or % format SQL.",
        "safe": "cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))",
        "refs": ["CWE-89", "OWASP A03:2021"],
    },
    {
        "id": "weak_random",
        "title": "Weak Random Number Generator",
        "category": "weak_random",
        "severity": RiskLevel.MEDIUM,
        "pattern": r"""\brandom\.(?:random|randint|choice)\s*\(""",
        "why": "The random module is not cryptographically secure; outputs are predictable.",
        "risk": "Predictable tokens, session IDs, or passwords that can be brute-forced.",
        "solution": "Use secrets module for security-sensitive randomness.",
        "safe": "token = secrets.token_urlsafe(32)",
        "refs": ["CWE-338"],
    },
    {
        "id": "debug_mode",
        "title": "Debug Mode Enabled",
        "category": "debug_mode",
        "severity": RiskLevel.HIGH,
        "pattern": r"""(?i)(?:app\.run|django\.conf).*debug\s*=\s*True""",
        "why": "Debug mode exposes stack traces, environment variables and an interactive console.",
        "risk": "Information disclosure, remote code execution via the debug console.",
        "solution": "Set DEBUG=False in production; load from environment.",
        "safe": "app.run(debug=os.environ.get('FLASK_DEBUG', '0') == '1')",
        "refs": ["CWE-489", "OWASP A05:2021"],
    },
]


class SecurityReviewEngine:
    """Run the full security review and produce a :class:`SecurityReview`."""

    def __init__(self, *, skip_bandit: bool = False, skip_detect_secrets: bool = False) -> None:
        self._skip_bandit = skip_bandit
        self._skip_detect_secrets = skip_detect_secrets

    def review(self, repository: Repository, workspace: Path) -> SecurityReview:
        """Run all security checks and return a :class:`SecurityReview`."""
        findings: list[SecurityFindingDetail] = []
        findings.extend(self._run_custom_rules(repository, workspace))
        findings.extend(self._run_bandit(repository, workspace))
        findings.extend(self._run_detect_secrets(repository, workspace))
        # Deduplicate by (file, line, category).
        findings = self._deduplicate(findings)
        severity = self._overall_severity(findings)
        score = self._compute_score(findings)
        review = SecurityReview(
            findings=findings,
            overall_severity=severity,
            security_score=score,
            summary=self._build_summary(findings, score),
            owasp_top10_coverage=self._owasp_coverage(findings),
            credential_exposure_count=sum(
                1 for f in findings if "hardcoded" in f.category or "key" in f.category
            ),
            injection_risk_count=sum(
                1 for f in findings if "injection" in f.category or "eval" in f.category
            ),
            misconfiguration_count=sum(
                1 for f in findings if f.category in {"debug_mode", "shell_true", "yaml_load"}
            ),
        )
        return review

    # ----- custom regex rules --------------------------------------------------

    def _run_custom_rules(
        self, repository: Repository, workspace: Path
    ) -> list[SecurityFindingDetail]:
        """Run all custom regex rules across source files."""
        findings: list[SecurityFindingDetail] = []
        for path in self._iter_source_files(workspace):
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            rel = str(path.relative_to(workspace))
            for rule in _CUSTOM_RULES:
                # Skip .env-style rules unless the filename matches.
                filename_pat = rule.get("filename_pattern")
                if filename_pat and not re.search(filename_pat, path.name):
                    continue
                findings.extend(self._apply_rule(rule, rel, content))
        return findings

    def _apply_rule(
        self, rule: dict[str, Any], file_path: str, content: str
    ) -> list[SecurityFindingDetail]:
        """Apply a single regex rule to a file's content."""
        results: list[SecurityFindingDetail] = []
        pattern = rule["pattern"]
        try:
            compiled = re.compile(pattern)
        except re.error:
            return results
        for match in compiled.finditer(content):
            line = content[: match.start()].count("\n") + 1
            snippet = self._snippet(content, line)
            results.append(
                SecurityFindingDetail(
                    title=rule["title"],
                    category=rule["category"],
                    severity=rule["severity"],
                    risk_level=rule["severity"],
                    cvss_estimate=self._cvss(rule["severity"]),
                    file=file_path,
                    line=line,
                    code_snippet=snippet,
                    why_risky=rule["why"],
                    real_world_risk=rule["risk"],
                    solution=rule["solution"],
                    safe_code_example=rule["safe"],
                    references=rule["refs"],
                    tool="custom",
                )
            )
        return results

    @staticmethod
    def _snippet(content: str, line: int, context: int = 1) -> str:
        """Return a small code snippet around ``line``."""
        lines = content.splitlines()
        start = max(0, line - 1 - context)
        end = min(len(lines), line + context)
        return "\n".join(lines[start:end])

    # ----- bandit --------------------------------------------------------------

    def _run_bandit(self, repository: Repository, workspace: Path) -> list[SecurityFindingDetail]:
        """Run Bandit if installed and collect findings."""
        if self._skip_bandit:
            return []
        try:
            proc = subprocess.run(
                ["bandit", "-r", str(workspace), "-f", "json", "-q"],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            _logger.debug("Bandit unavailable: %s", exc)
            return []
        if proc.returncode not in (0, 1):
            return []
        try:
            data = json.loads(proc.stdout or "{}")
        except json.JSONDecodeError:
            return []
        findings: list[SecurityFindingDetail] = []
        for item in data.get("results", []):
            severity = self._bandit_severity(item.get("issue_severity", "MEDIUM"))
            findings.append(
                SecurityFindingDetail(
                    title=item.get("test_name", "Bandit finding"),
                    category=item.get("test_id", "bandit").lower(),
                    severity=severity,
                    risk_level=severity,
                    cvss_estimate=self._cvss(severity),
                    file=item.get("filename", ""),
                    line=item.get("line_number"),
                    code_snippet=item.get("issue_text", ""),
                    why_risky=item.get("issue_text", ""),
                    real_world_risk=self._bandit_risk(item.get("test_id", "")),
                    solution=self._bandit_solution(item.get("test_id", "")),
                    safe_code_example=None,
                    references=[item.get("test_id", ""), item.get("more_info", "")],
                    tool="bandit",
                    confidence=self._bandit_confidence(item.get("issue_confidence", "MEDIUM")),
                )
            )
        return findings

    @staticmethod
    def _bandit_severity(label: str) -> RiskLevel:
        return {
            "HIGH": RiskLevel.HIGH,
            "MEDIUM": RiskLevel.MEDIUM,
            "LOW": RiskLevel.LOW,
        }.get(label.upper(), RiskLevel.MEDIUM)

    @staticmethod
    def _bandit_confidence(label: str) -> float:
        return {"HIGH": 0.9, "MEDIUM": 0.6, "LOW": 0.3}.get(label.upper(), 0.5)

    @staticmethod
    def _bandit_risk(test_id: str) -> str:
        return {
            "B101": "assert statements are stripped in optimized mode, hiding security checks.",
            "B301": "Pickle deserialization can execute arbitrary code.",
            "B602": "subprocess with shell=True enables command injection.",
            "B608": "String SQL construction enables SQL injection.",
        }.get(test_id, "This pattern is a known security anti-pattern.")

    @staticmethod
    def _bandit_solution(test_id: str) -> str:
        return {
            "B101": "Remove assert for security checks; use a proper if/raise.",
            "B301": "Use a safe serialization format like JSON.",
            "B602": "Pass arguments as a list with shell=False.",
            "B608": "Use parameterized queries.",
        }.get(test_id, "Follow the Bandit recommendation in the linked docs.")

    # ----- detect-secrets ------------------------------------------------------

    def _run_detect_secrets(
        self, repository: Repository, workspace: Path
    ) -> list[SecurityFindingDetail]:
        """Run detect-secrets if installed and collect findings."""
        if self._skip_detect_secrets:
            return []
        try:
            proc = subprocess.run(
                ["detect-secrets", "scan", str(workspace)],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            _logger.debug("detect-secrets unavailable: %s", exc)
            return []
        if proc.returncode != 0:
            return []
        try:
            data = json.loads(proc.stdout or "{}")
        except json.JSONDecodeError:
            return []
        findings: list[SecurityFindingDetail] = []
        for file_path, entries in data.get("results", {}).items():
            for entry in entries:
                severity = self._secret_severity(entry.get("type", ""))
                findings.append(
                    SecurityFindingDetail(
                        title=f"Secret detected: {entry.get('type', 'unknown')}",
                        category=entry.get("type", "secret").lower(),
                        severity=severity,
                        risk_level=severity,
                        cvss_estimate=self._cvss(severity),
                        file=file_path,
                        line=entry.get("line_number"),
                        code_snippet=None,
                        why_risky="A live secret was detected in source control.",
                        real_world_risk="The secret grants access to the associated service and must be rotated.",
                        solution="Rotate the secret immediately and load it from a secret manager.",
                        safe_code_example="secret = os.environ['SECRET_NAME']",
                        references=[entry.get("type", "")],
                        tool="detect-secrets",
                    )
                )
        return findings

    @staticmethod
    def _secret_severity(secret_type: str) -> RiskLevel:
        high = {"AWS Access Key", "Stripe", "GitHub Token", "JWT Token"}
        if any(h in secret_type for h in high):
            return RiskLevel.CRITICAL
        if "Key" in secret_type or "Token" in secret_type:
            return RiskLevel.HIGH
        return RiskLevel.MEDIUM

    # ----- helpers -------------------------------------------------------------

    def _iter_source_files(self, workspace: Path):  # type: ignore[no-untyped-def]
        skip_dirs = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build"}
        for root, dirs, files in os.walk(workspace):
            dirs[:] = [d for d in dirs if d not in skip_dirs]
            for name in files:
                if name.endswith(
                    (
                        ".py",
                        ".js",
                        ".ts",
                        ".jsx",
                        ".tsx",
                        ".go",
                        ".rs",
                        ".java",
                        ".kt",
                        ".rb",
                        ".php",
                        ".env",
                        ".yaml",
                        ".yml",
                        ".json",
                    )
                ):
                    yield Path(root) / name

    @staticmethod
    def _cvss(severity: RiskLevel) -> float:
        return {
            RiskLevel.CRITICAL: 9.5,
            RiskLevel.HIGH: 7.5,
            RiskLevel.MEDIUM: 5.0,
            RiskLevel.LOW: 2.5,
            RiskLevel.INFO: 0.0,
        }[severity]

    @staticmethod
    def _overall_severity(findings: Sequence[SecurityFindingDetail]) -> RiskLevel:
        if any(f.severity == RiskLevel.CRITICAL for f in findings):
            return RiskLevel.CRITICAL
        if any(f.severity == RiskLevel.HIGH for f in findings):
            return RiskLevel.HIGH
        if any(f.severity == RiskLevel.MEDIUM for f in findings):
            return RiskLevel.MEDIUM
        if findings:
            return RiskLevel.LOW
        return RiskLevel.INFO

    @staticmethod
    def _compute_score(findings: Sequence[SecurityFindingDetail]) -> float:
        """Compute a 0-100 security score from findings."""
        penalties = {
            RiskLevel.CRITICAL: 30,
            RiskLevel.HIGH: 15,
            RiskLevel.MEDIUM: 7,
            RiskLevel.LOW: 3,
            RiskLevel.INFO: 0,
        }
        score = 100.0
        for finding in findings:
            score -= penalties.get(finding.severity, 0)
        return max(0.0, score)

    @staticmethod
    def _deduplicate(
        findings: Sequence[SecurityFindingDetail],
    ) -> list[SecurityFindingDetail]:
        """Deduplicate by (file, line, category)."""
        seen: set[tuple[str, int | None, str]] = set()
        unique: list[SecurityFindingDetail] = []
        for f in findings:
            key = (f.file, f.line, f.category)
            if key in seen:
                continue
            seen.add(key)
            unique.append(f)
        return unique

    @staticmethod
    def _owasp_coverage(findings: Sequence[SecurityFindingDetail]) -> list[str]:
        """Return OWASP Top-10 categories touched by the findings."""
        mapping = {
            "sql_injection": "A03: Injection",
            "shell_true": "A03: Injection",
            "unsafe_eval": "A03: Injection",
            "hardcoded_password": "A07: Identification & Auth Failures",
            "hardcoded_token": "A07: Identification & Auth Failures",
            "debug_mode": "A05: Security Misconfiguration",
        }
        covered: set[str] = set()
        for f in findings:
            if f.category in mapping:
                covered.add(mapping[f.category])
        return sorted(covered)

    @staticmethod
    def _build_summary(findings: Sequence[SecurityFindingDetail], score: float) -> str:
        """Build a one-paragraph engineering summary."""
        if not findings:
            return "No security findings were detected by the configured scanners."
        critical = sum(1 for f in findings if f.severity == RiskLevel.CRITICAL)
        high = sum(1 for f in findings if f.severity == RiskLevel.HIGH)
        medium = sum(1 for f in findings if f.severity == RiskLevel.MEDIUM)
        parts = [
            f"Security scan identified {len(findings)} finding(s)",
            f"({critical} critical, {high} high, {medium} medium)",
            f"with an overall security score of {score:.0f}/100.",
        ]
        if critical > 0:
            parts.append("Critical findings require immediate remediation and secret rotation.")
        elif high > 0:
            parts.append("High-severity findings should be addressed before the next release.")
        else:
            parts.append(
                "The repository has a moderate security posture with room for improvement."
            )
        return " ".join(parts)


__all__ = ["SecurityReviewEngine"]
