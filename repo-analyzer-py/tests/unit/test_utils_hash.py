"""Tests for ``repo_analyzer.utils.hash``."""

from __future__ import annotations

from repo_analyzer.utils.hash import deterministic_hash, hash_dict, hash_string


def test_hash_string_is_stable() -> None:
    """The same string should always hash to the same value."""
    assert hash_string("abc") == hash_string("abc")


def test_hash_string_differs_for_different_input() -> None:
    """Different inputs should hash differently."""
    assert hash_string("abc") != hash_string("abd")


def test_hash_string_truncation() -> None:
    """The length parameter should truncate the digest."""
    full = hash_string("abc")
    short = hash_string("abc", length=8)
    assert len(short) == 8
    assert full.startswith(short)


def test_hash_string_length_zero_returns_full() -> None:
    """A length of 0 should return the full digest."""
    assert len(hash_string("abc", length=0)) == 64


def test_deterministic_hash_stable_across_calls() -> None:
    """The hash should be stable across calls (unlike builtin hash)."""
    h1 = deterministic_hash("a", 1, ["x"])
    h2 = deterministic_hash("a", 1, ["x"])
    assert h1 == h2


def test_deterministic_hash_differs_for_different_parts() -> None:
    """Different parts should produce different hashes."""
    assert deterministic_hash("a") != deterministic_hash("b")


def test_hash_dict_stable() -> None:
    """The same dict should hash to the same value regardless of key order."""
    h1 = hash_dict({"a": 1, "b": 2})
    h2 = hash_dict({"b": 2, "a": 1})
    assert h1 == h2


def test_hash_dict_differs_for_different_values() -> None:
    """Different values should produce different hashes."""
    assert hash_dict({"a": 1}) != hash_dict({"a": 2})


def test_hash_dict_handles_nested() -> None:
    """Nested dicts should be hashed deterministically."""
    h1 = hash_dict({"outer": {"inner": 1}})
    h2 = hash_dict({"outer": {"inner": 1}})
    assert h1 == h2
