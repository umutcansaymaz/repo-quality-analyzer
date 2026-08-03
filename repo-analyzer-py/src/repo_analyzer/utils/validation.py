"""Input validation utilities."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

# Blocked private/reserved IP ranges for SSRF protection.
_PRIVATE_NETS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def _is_private_host(host: str) -> bool:
    """Return ``True`` if *host* is an IP literal in a private/reserved range."""
    try:
        ip = ipaddress.ip_address(host)
        return any(ip in net for net in _PRIVATE_NETS)
    except ValueError:
        return False  # hostname, not IP


_GIT_SSH_PATTERN = re.compile(
    r"^(?:git@[A-Za-z0-9._-]+[:/][A-Za-z0-9._~/-]+(?:\.git)?|"
    r"ssh://(?:[A-Za-z0-9._-]+@)?[A-Za-z0-9._-]+(?::[0-9]+)?/[A-Za-z0-9._~/-]+(?:\.git)?)$"
)
_GIT_HTTPS_PATTERN = re.compile(
    r"^https://[A-Za-z0-9._-]+(?:[:0-9]+)?/[A-Za-z0-9._~/-]+(?:\.git)?$",
    re.IGNORECASE,
)
_GIT_PATTERN = re.compile(
    r"^(?:git@[A-Za-z0-9._-]+[:/][A-Za-z0-9._~/-]+(?:\.git)?|"
    r"ssh://(?:[A-Za-z0-9._-]+@)?[A-Za-z0-9._-]+(?::[0-9]+)?/[A-Za-z0-9._~/-]+(?:\.git)?|"
    r"https?://[A-Za-z0-9._-]+(?:[:0-9]+)?/[A-Za-z0-9._~/-]+(?:\.git)?)$",
    re.IGNORECASE,
)
_SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)


def is_valid_url(url: str) -> bool:
    """Return ``True`` if ``url`` is a syntactically valid HTTP(S) URL.

    Args:
        url: The string to test.

    Returns:
        ``True`` for valid ``http://`` or ``https://`` URLs.
    """
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url.strip())
    except (ValueError, TypeError):
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def is_valid_git_url(url: str) -> bool:
    """Return ``True`` if ``url`` looks like a valid Git URL.

    Accepts HTTPS, SSH (``git@host:...`` and ``ssh://``) forms, optionally
    ending in ``.git``. Rejects URLs pointing to private/reserved IP ranges
    and path-traversal (``..``) segments.

    Args:
        url: The string to test.

    Returns:
        ``True`` if the URL matches a recognized Git URL form.
    """
    if not url or not isinstance(url, str):
        return False
    candidate = url.strip()
    if ".." in candidate:
        return False
    if _GIT_PATTERN.match(candidate):
        # Extract hostname for private-IP check.
        try:
            parsed = urlparse(candidate if "://" in candidate else f"ssh://{candidate}")
            if parsed.hostname and _is_private_host(parsed.hostname):
                return False
        except Exception:
            pass
        return True
    # Also accept plain https URLs without .git suffix that look like repo URLs
    return (
        _GIT_HTTPS_PATTERN.match(candidate) is not None
        or _GIT_SSH_PATTERN.match(candidate) is not None
    )


def is_valid_semver(version: str) -> bool:
    """Return ``True`` if ``version`` is a valid semantic-version string.

    Follows the SemVer 2.0.0 specification, including optional pre-release and
    build metadata segments.

    Args:
        version: The version string to test.

    Returns:
        ``True`` if the string is valid SemVer.
    """
    if not version or not isinstance(version, str):
        return False
    return _SEMVER_PATTERN.match(version.strip()) is not None


__all__ = ["is_valid_git_url", "is_valid_semver", "is_valid_url"]
