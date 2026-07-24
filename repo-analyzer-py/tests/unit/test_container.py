"""Tests for the :class:`ServiceContainer`."""

from __future__ import annotations

import pytest

from repo_analyzer.infrastructure.container import ServiceContainer, TypedResolver


class _DummyService:
    def __init__(self, value: int = 0) -> None:
        self.value = value


def test_register_and_get_singleton() -> None:
    """A registered factory should produce a singleton."""
    container = ServiceContainer()
    container.register(_DummyService, lambda: _DummyService(42))
    first = container.get(_DummyService)
    second = container.get(_DummyService)
    assert first is second
    assert first.value == 42


def test_register_instance() -> None:
    """A pre-built instance should be returned directly."""
    container = ServiceContainer()
    instance = _DummyService(99)
    container.register_instance(_DummyService, instance)
    assert container.get(_DummyService) is instance


def test_get_missing_raises_keyerror() -> None:
    """Resolving an unregistered key should raise KeyError."""
    container = ServiceContainer()
    with pytest.raises(KeyError):
        container.get(_DummyService)


def test_try_get_missing_returns_none() -> None:
    """``try_get`` should return None for unknown keys."""
    container = ServiceContainer()
    assert container.try_get(_DummyService) is None


def test_try_get_present_returns_instance() -> None:
    """``try_get`` should return the instance when present."""
    container = ServiceContainer()
    container.register(_DummyService, lambda: _DummyService(1))
    assert container.try_get(_DummyService) is not None


def test_has() -> None:
    """``has`` should report registration state."""
    container = ServiceContainer()
    assert container.has(_DummyService) is False
    container.register(_DummyService, lambda: _DummyService())
    assert container.has(_DummyService) is True


def test_contains_operator() -> None:
    """The ``in`` operator should work."""
    container = ServiceContainer()
    assert _DummyService not in container
    container.register(_DummyService, lambda: _DummyService())
    assert _DummyService in container


def test_reset_clears_instances() -> None:
    """``reset`` should clear cached instances but keep factories."""
    container = ServiceContainer()
    container.register(_DummyService, lambda: _DummyService(1))
    first = container.get(_DummyService)
    container.reset()
    second = container.get(_DummyService)
    assert first is not second


def test_clear_removes_all() -> None:
    """``clear`` should remove everything."""
    container = ServiceContainer()
    container.register(_DummyService, lambda: _DummyService())
    container.clear()
    assert container.has(_DummyService) is False


def test_register_named_key() -> None:
    """String keys should be supported."""
    container = ServiceContainer()
    container.register("my-service", lambda: _DummyService(7))
    svc = container.get("my-service")
    assert svc.value == 7


def test_typed_resolver() -> None:
    """``TypedResolver`` should resolve by key."""
    container = ServiceContainer()
    container.register(_DummyService, lambda: _DummyService(5))
    resolver = TypedResolver(container, _DummyService)
    svc = resolver()
    assert svc.value == 5


def test_register_idempotent_instance() -> None:
    """Registering an instance twice should not error."""
    container = ServiceContainer()
    inst = _DummyService()
    container.register_instance(_DummyService, inst)
    container.register_instance(_DummyService, inst)
    assert container.get(_DummyService) is inst
