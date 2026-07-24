"""Tests for ``repo_analyzer.utils.file``."""

from __future__ import annotations

from pathlib import Path

import pytest

from repo_analyzer.utils.file import (
    ensure_directory,
    file_checksum,
    read_text_file,
    safe_remove,
    write_text_file,
)


def test_ensure_directory_creates_nested(tmp_path: Path) -> None:
    """Nested directories should be created."""
    target = tmp_path / "a" / "b" / "c"
    result = ensure_directory(target)
    assert result.exists()
    assert result.is_dir()


def test_ensure_directory_idempotent(tmp_path: Path) -> None:
    """Calling twice should not raise."""
    target = tmp_path / "dir"
    ensure_directory(target)
    ensure_directory(target)
    assert target.exists()


def test_write_then_read_text_file(tmp_path: Path) -> None:
    """A round-trip write/read should preserve content."""
    path = tmp_path / "file.txt"
    write_text_file(path, "hello world")
    assert read_text_file(path) == "hello world"


def test_write_text_file_atomic(tmp_path: Path) -> None:
    """Atomic write should leave no .tmp file behind."""
    path = tmp_path / "out.txt"
    write_text_file(path, "content", atomic=True)
    assert path.read_text() == "content"
    assert not (tmp_path / "out.txt.tmp").exists()


def test_write_text_file_creates_parent_dirs(tmp_path: Path) -> None:
    """Parent directories should be created automatically."""
    path = tmp_path / "deep" / "nested" / "file.txt"
    write_text_file(path, "x")
    assert path.exists()


def test_read_text_file_missing_raises(tmp_path: Path) -> None:
    """Reading a missing file should raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        read_text_file(tmp_path / "nope.txt")


def test_safe_remove_file(tmp_path: Path) -> None:
    """Removing an existing file should return True."""
    path = tmp_path / "f.txt"
    path.write_text("x")
    assert safe_remove(path) is True
    assert not path.exists()


def test_safe_remove_missing_returns_false(tmp_path: Path) -> None:
    """Removing a missing path should return False."""
    assert safe_remove(tmp_path / "missing") is False


def test_safe_remove_directory(tmp_path: Path) -> None:
    """Removing a directory tree should work."""
    d = tmp_path / "dir"
    d.mkdir()
    (d / "f.txt").write_text("x")
    assert safe_remove(d) is True
    assert not d.exists()


def test_file_checksum_is_stable(tmp_path: Path) -> None:
    """The checksum of identical content should match."""
    p1 = tmp_path / "a.bin"
    p2 = tmp_path / "b.bin"
    p1.write_bytes(b"abc")
    p2.write_bytes(b"abc")
    assert file_checksum(p1) == file_checksum(p2)


def test_file_checksum_differs_for_different_content(tmp_path: Path) -> None:
    """Different content should produce different checksums."""
    p1 = tmp_path / "a.bin"
    p2 = tmp_path / "b.bin"
    p1.write_bytes(b"abc")
    p2.write_bytes(b"abd")
    assert file_checksum(p1) != file_checksum(p2)


def test_file_checksum_supports_algorithms(tmp_path: Path) -> None:
    """The algorithm parameter should select the hash function."""
    p = tmp_path / "f.bin"
    p.write_bytes(b"data")
    assert file_checksum(p, "md5") != file_checksum(p, "sha256")
