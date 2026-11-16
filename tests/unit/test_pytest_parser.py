"""Unit tests for Pytest console and JUnit XML parsing."""

from repopilot.sandbox.pytest_parser import PytestErrorParser


def test_parse_stdout_single_failure() -> None:
    stdout = """
============================= test session starts =============================
collected 2 items

tests/test_calculator.py .F                                              [100%]

================================== FAILURES ===================================
_________________________________ test_divide _________________________________

    def test_divide():
>       assert divide(10, 0) == 0
E       ZeroDivisionError: division by zero

tests/test_calculator.py:14: ZeroDivisionError
=========================== short test summary info ===========================
FAILED tests/test_calculator.py::test_divide - ZeroDivisionError: division by zero
========================= 1 failed, 1 passed in 0.45s =========================
"""
    result = PytestErrorParser.parse_stdout(stdout=stdout, exit_code=1)

    assert result.exit_code == 1
    assert result.total_tests == 2
    assert result.passed_tests == 1
    assert result.failed_tests == 1
    assert result.execution_time_seconds == 0.45
    assert not result.is_success
    assert len(result.failures) == 1

    failure = result.failures[0]
    assert failure.test_name == "test_divide"
    assert failure.file_path == "tests/test_calculator.py"
    assert failure.line_number == 14
    assert "ZeroDivisionError: division by zero" in failure.assertion_message
    assert "assert divide(10, 0) == 0" in failure.stack_trace


def test_parse_stdout_all_passed() -> None:
    stdout = """
============================= test session starts =============================
collected 5 items

tests/test_math.py .....                                                 [100%]

============================== 5 passed in 0.12s ==============================
"""
    result = PytestErrorParser.parse_stdout(stdout=stdout, exit_code=0)

    assert result.exit_code == 0
    assert result.total_tests == 5
    assert result.passed_tests == 5
    assert result.failed_tests == 0
    assert result.execution_time_seconds == 0.12
    assert result.is_success
    assert len(result.failures) == 0


def test_parse_stdout_multiple_failures() -> None:
    stdout = """
FAILED tests/test_a.py::test_one - AssertionError: 1 != 2
tests/test_a.py:5: AssertionError
FAILED tests/test_b.py::test_two - KeyError: 'missing'
tests/test_b.py:22: KeyError
========================= 2 failed, 3 passed in 1.10s =========================
"""
    result = PytestErrorParser.parse_stdout(stdout=stdout, exit_code=1)

    assert result.failed_tests == 2
    assert result.passed_tests == 3
    assert result.total_tests == 5
    assert len(result.failures) == 2

    assert result.failures[0].test_name == "test_one"
    assert result.failures[0].line_number == 5
    assert result.failures[1].test_name == "test_two"
    assert result.failures[1].line_number == 22


def test_parse_junit_xml_valid() -> None:
    xml_content = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" tests="3" failures="1" errors="0" time="0.85">
    <testcase classname="tests.test_service" name="test_create" file="tests/test_service.py" line="10" time="0.2">
    </testcase>
    <testcase classname="tests.test_service" name="test_delete" file="tests/test_service.py" line="25" time="0.5">
      <failure message="AssertionError: assert False">Traceback: assert False</failure>
    </testcase>
  </testsuite>
</testsuites>
"""
    result = PytestErrorParser.parse_junit_xml(xml_content=xml_content, exit_code=1)

    assert result.exit_code == 1
    assert result.total_tests == 3
    assert result.failed_tests == 1
    assert result.passed_tests == 2
    assert len(result.failures) == 1
    assert result.failures[0].test_name == "test_delete"
    assert result.failures[0].line_number == 25
    assert result.failures[0].assertion_message == "AssertionError: assert False"
    assert "Traceback: assert False" in result.failures[0].stack_trace


def test_parse_junit_xml_malformed_fallback() -> None:
    malformed = "not valid xml -- 1 failed, 2 passed in 0.3s"
    result = PytestErrorParser.parse_junit_xml(xml_content=malformed, exit_code=1)

    assert result.failed_tests == 1
    assert result.passed_tests == 2
    assert result.total_tests == 3
