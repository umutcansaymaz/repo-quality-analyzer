"""Dependency-injection / service container.

A lightweight, type-safe service container that lazily constructs and caches
shared service instances. Services are registered with a factory callable
and resolved by type (or by an explicit key). This keeps modules decoupled:
they depend on interfaces (ports) and receive concrete instances through the
container.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any, Generic, TypeVar

from repo_analyzer.infrastructure.logging import get_logger

_logger = get_logger(__name__)

T = TypeVar("T")


class ServiceContainer:
    """A simple, thread-safe service container.

    Services are registered with a factory ``Callable[[], T]``. The first
    call to :meth:`get` constructs the instance; subsequent calls return the
    cached instance (singleton semantics within the container).
    """

    def __init__(self) -> None:
        self._factories: dict[Any, Callable[[], Any]] = {}
        self._instances: dict[Any, Any] = {}
        self._lock = threading.RLock()

    # ----- registration ---------------------------------------------------------
    def register(
        self,
        key: Any,
        factory: Callable[[], Any] | Any,
        *,
        singleton: bool = True,
    ) -> None:
        """Register a service.

        Args:
            key: The lookup key (typically a class / Protocol). Use a string
                for named services.
            factory: Either a zero-arg callable that builds the instance, or
                a ready instance (registered as a singleton).
            singleton: If ``True`` (default) the first resolved instance is
                cached and reused.
        """
        with self._lock:
            if callable(factory) and not isinstance(factory, type):
                if singleton:
                    self._factories[key] = factory
                    self._instances.pop(key, None)
                else:
                    # Non-singleton: wrap so get() always calls the factory.
                    self._factories[key] = factory
                    self._instances.pop(key, None)
            else:
                # ``factory`` is an instance.
                self._instances[key] = factory
                self._factories.pop(key, None)

    def register_instance(self, key: Any, instance: Any) -> None:
        """Register a pre-built instance as a singleton."""
        with self._lock:
            self._instances[key] = instance
            self._factories.pop(key, None)

    # ----- resolution -----------------------------------------------------------
    def get(self, key: type[T] | Any) -> T:
        """Resolve a service.

        Args:
            key: The lookup key (typically a class).

        Returns:
            The service instance.

        Raises:
            KeyError: If the key is not registered.
        """
        with self._lock:
            if key in self._instances:
                return self._instances[key]  # type: ignore[no-any-return]
            if key in self._factories:
                instance = self._factories[key]()
                self._instances[key] = instance
                _logger.debug("Constructed singleton for %r", key)
                return instance  # type: ignore[no-any-return]
            raise KeyError(f"No service registered for key {key!r}")

    def try_get(self, key: type[T] | Any) -> T | None:
        """Like :meth:`get` but returns ``None`` when the key is unknown."""
        try:
            value: T = self.get(key)
        except KeyError:
            return None
        except Exception:
            return None
        return value

    def has(self, key: Any) -> bool:
        """Return ``True`` if ``key`` is registered."""
        with self._lock:
            return key in self._factories or key in self._instances

    # ----- lifecycle ------------------------------------------------------------
    def reset(self) -> None:
        """Clear all cached instances (factories are kept).

        Useful in tests to force re-construction of singletons.
        """
        with self._lock:
            self._instances.clear()

    def clear(self) -> None:
        """Remove all registrations."""
        with self._lock:
            self._factories.clear()
            self._instances.clear()

    # ----- helpers --------------------------------------------------------------
    def get_typed(self, key: type[T]) -> T:
        """Resolve a service with a static type hint.

        Equivalent to :meth:`get` but narrowed to ``T`` for type checkers.
        """
        return self.get(key)

    def __contains__(self, key: object) -> bool:
        return self.has(key)


class TypedResolver(Generic[T]):
    """A typed convenience wrapper around :class:`ServiceContainer`.

    Example::

        cache_resolver = TypedResolver[CachePort](container, CachePort)
        cache = cache_resolver()
    """

    def __init__(self, container: ServiceContainer, key: type[T]) -> None:
        self._container = container
        self._key = key

    def __call__(self) -> T:
        return self._container.get(self._key)


__all__ = ["ServiceContainer", "TypedResolver"]
