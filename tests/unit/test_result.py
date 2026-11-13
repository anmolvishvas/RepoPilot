"""Unit tests for the Result monad."""

import pytest

from repopilot.core.result import Err, Ok, Result, err, ok


def test_ok_creation_and_properties() -> None:
    res: Result[int, str] = ok(42)
    assert res.is_ok is True
    assert res.is_err is False
    assert res.unwrap() == 42
    assert res.unwrap_or(0) == 42


def test_ok_unwrap_err_raises() -> None:
    res = ok("success")
    with pytest.raises(ValueError, match="Called unwrap_err on an Ok variant"):
        res.unwrap_err()


def test_err_creation_and_properties() -> None:
    res: Result[int, str] = err("network failure")
    assert res.is_ok is False
    assert res.is_err is True
    assert res.unwrap_err() == "network failure"
    assert res.unwrap_or(100) == 100


def test_err_unwrap_raises() -> None:
    res = err("invalid input")
    with pytest.raises(ValueError, match="Called unwrap on an Err variant"):
        res.unwrap()


def test_map_transformations() -> None:
    success = ok(10)
    doubled = success.map(lambda x: x * 2)
    assert doubled.unwrap() == 20

    failure = err("timeout")
    untouched = failure.map(lambda x: x)
    assert untouched.unwrap_err() == "timeout"


def test_map_err_transformations() -> None:
    failure = err("not found")
    mapped_err = failure.map_err(lambda msg: f"Error: {msg}")
    assert mapped_err.unwrap_err() == "Error: not found"

    success = ok(50)
    untouched = success.map_err(lambda msg: f"Error: {msg}")
    assert untouched.unwrap() == 50


def test_flat_map_chaining() -> None:
    def divide(a: int, b: int) -> Result[float, str]:
        if b == 0:
            return err("division by zero")
        return ok(a / b)

    res1 = ok(10).flat_map(lambda x: divide(x, 2))
    assert res1.unwrap() == 5.0

    res2 = ok(10).flat_map(lambda x: divide(x, 0))
    assert res2.unwrap_err() == "division by zero"

    res3 = err("prior error").flat_map(lambda x: divide(10, 2))
    assert res3.unwrap_err() == "prior error"


def test_pattern_matching_support() -> None:
    def evaluate(res: Result[int, str]) -> str:
        match res:
            case Ok(val):
                return f"Value: {val}"
            case Err(error):
                return f"Error: {error}"

    assert evaluate(ok(123)) == "Value: 123"
    assert evaluate(err("fail")) == "Error: fail"
