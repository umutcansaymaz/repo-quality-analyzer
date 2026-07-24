"""Pure utility functions used across the application.

These helpers have no dependencies on the rest of the codebase and are safe
to use from any layer (core, adapters, infrastructure).
"""

from __future__ import annotations

from repo_analyzer.utils.file import (
    ensure_directory,
    file_checksum,
    read_text_file,
    safe_remove,
    write_text_file,
)
from repo_analyzer.utils.hash import deterministic_hash, hash_dict, hash_string
from repo_analyzer.utils.path import (
    expand_user_path,
    normalize_path,
    repo_cache_dir,
    temp_directory,
)
from repo_analyzer.utils.size import bytes_to_human, human_to_bytes
from repo_analyzer.utils.time import format_duration, utc_now_iso
from repo_analyzer.utils.validation import (
    is_valid_git_url,
    is_valid_semver,
    is_valid_url,
)

__all__ = [
    # path
    "expand_user_path",
    "normalize_path",
    "repo_cache_dir",
    "temp_directory",
    # file
    "ensure_directory",
    "file_checksum",
    "read_text_file",
    "safe_remove",
    "write_text_file",
    # hash
    "deterministic_hash",
    "hash_dict",
    "hash_string",
    # size
    "bytes_to_human",
    "human_to_bytes",
    # time
    "format_duration",
    "utc_now_iso",
    # validation
    "is_valid_git_url",
    "is_valid_semver",
    "is_valid_url",
]
