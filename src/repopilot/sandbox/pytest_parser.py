"""Parser for extracting structured failure data from Pytest and JUnit XML outputs."""

from __future__ import annotations

import re

try:
    import defusedxml.ElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET  # nosec B405

from repopilot.agents.state import FailedAssertion, SandboxTestResult


class PytestErrorParser:
    """Parses Pytest stdout/stderr and JUnit XML reports into structured domain models."""

    @classmethod
    def parse_stdout(
        cls, stdout: str, stderr: str = "", exit_code: int = 0, duration: float = 0.0
    ) -> SandboxTestResult:
        """Parse raw Pytest console output into a SandboxTestResult."""
        failures: list[FailedAssertion] = []
        total_tests = 0
        passed_tests = 0
        failed_tests = 0

        # Regex for summary line: e.g. "== 2 failed, 15 passed in 1.23s =="
        summary_match = re.search(
            r"=+ (?:(\d+) failed)?[,\s]*(?:(\d+) passed)?[^=]* in ([\d\.]+)s =+",
            stdout,
        )
        if summary_match:
            failed_str = summary_match.group(1)
            passed_str = summary_match.group(2)
            time_str = summary_match.group(3)

            failed_tests = int(failed_str) if failed_str else 0
            passed_tests = int(passed_str) if passed_str else 0
            total_tests = failed_tests + passed_tests
            if time_str:
                duration = float(time_str)
        else:
            # Fallback check for single passed/failed summary
            passed_match = re.search(r"(\d+) passed", stdout)
            failed_match = re.search(r"(\d+) failed", stdout)
            if passed_match:
                passed_tests = int(passed_match.group(1))
            if failed_match:
                failed_tests = int(failed_match.group(1))
            total_tests = passed_tests + failed_tests

        # Extract individual failure blocks: e.g., "FAILED tests/test_foo.py::test_bar - AssertionError: ..."
        failure_lines = re.findall(r"FAILED\s+([^\s:]+)::([^\s\-]+)(?:\s+-\s+(.*))?", stdout)
        for file_path, test_name, message in failure_lines:
            # Extract line number from traceback if present
            line_match = re.search(rf"{re.escape(file_path)}:(\d+):", stdout)
            line_num = int(line_match.group(1)) if line_match else None

            failures.append(
                FailedAssertion(
                    test_name=test_name.strip(),
                    file_path=file_path.strip(),
                    line_number=line_num,
                    assertion_message=message.strip() if message else "Test assertion failed",
                    stack_trace=cls._extract_traceback(stdout, test_name),
                )
            )

        return SandboxTestResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            failures=failures,
            execution_time_seconds=duration,
        )

    @classmethod
    def parse_junit_xml(cls, xml_content: str, exit_code: int = 0) -> SandboxTestResult:
        """Parse JUnit XML report content into a SandboxTestResult."""
        try:
            root = ET.fromstring(xml_content)  # nosec B314
        except Exception:
            return cls.parse_stdout(xml_content, exit_code=exit_code)

        total_tests = int(root.attrib.get("tests", 0))
        failures_count = int(root.attrib.get("failures", 0)) + int(root.attrib.get("errors", 0))
        duration = float(root.attrib.get("time", 0.0))

        if total_tests == 0:
            for suite in root.iter("testsuite"):
                total_tests += int(suite.attrib.get("tests", 0))
                failures_count += int(suite.attrib.get("failures", 0)) + int(
                    suite.attrib.get("errors", 0)
                )
                duration += float(suite.attrib.get("time", 0.0))

        testcases = list(root.iter("testcase"))
        if total_tests == 0 and testcases:
            total_tests = len(testcases)

        passed_tests = max(0, total_tests - failures_count)

        failures: list[FailedAssertion] = []
        for testcase in root.iter("testcase"):
            failure_node = testcase.find("failure")
            if failure_node is None:
                failure_node = testcase.find("error")

            if failure_node is not None:
                test_name = testcase.attrib.get("name", "unknown_test")
                file_path = testcase.attrib.get(
                    "file", testcase.attrib.get("classname", "unknown_file")
                )
                message = failure_node.attrib.get("message", "")
                stack_trace = failure_node.text or ""

                line_num: int | None = None
                line_attr = testcase.attrib.get("line")
                if line_attr and line_attr.isdigit():
                    line_num = int(line_attr)

                failures.append(
                    FailedAssertion(
                        test_name=test_name,
                        file_path=file_path,
                        line_number=line_num,
                        assertion_message=message,
                        stack_trace=stack_trace.strip(),
                    )
                )

        return SandboxTestResult(
            exit_code=exit_code,
            stdout="",
            stderr="",
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failures_count,
            failures=failures,
            execution_time_seconds=duration,
        )

    @staticmethod
    def _extract_traceback(stdout: str, test_name: str) -> str:
        """Locate and extract traceback hunk for a specific test name."""
        pattern = rf"_{{3,}}\s+{re.escape(test_name)}\s+_{{3,}}(.*?)(?=\n_{{3,}}|\n=+|$)"
        match = re.search(pattern, stdout, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""
