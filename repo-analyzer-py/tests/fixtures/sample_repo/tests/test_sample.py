"""Tests for the sample module."""

import pytest
from sample import Dog, complex_function, greet
from sample.utils import add, multiply


def test_greet() -> None:
    assert greet("World") == "Hello, World!"


def test_complex_function() -> None:
    assert complex_function(1, 2, 3) >= 0


@pytest.mark.parametrize("a,b", [(1, 2), (3, 4)])
def test_add(a: int, b: int) -> None:
    assert add(a, b) == a + b


def test_multiply() -> None:
    assert multiply(3, 4) == 12


def test_dog_speak() -> None:
    dog = Dog("Rex")
    assert dog.speak() == "Woof!"
