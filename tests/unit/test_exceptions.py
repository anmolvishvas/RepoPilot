"""Unit tests for domain exceptions."""

from repopilot.core.exceptions import (
    ASTParseError,
    CallGraphError,
    ConfigurationError,
    DiffApplicationError,
    RAGRetrievalError,
    RepoPilotError,
    SandboxExecutionError,
    SandboxTimeoutError,
    SymbolNotFoundError,
)


def test_exception_string_formatting() -> None:
    err_simple = RepoPilotError("Something went wrong")
    assert str(err_simple) == "Something went wrong"

    err_detailed = RepoPilotError("Something went wrong", details="Failed at step 4")
    assert str(err_detailed) == "Something went wrong (Details: Failed at step 4)"


def test_subclass_exceptions_instantiation() -> None:
    exceptions = [
        ASTParseError("Syntax error"),
        SymbolNotFoundError("Symbol not found"),
        CallGraphError("Cycle detected"),
        DiffApplicationError("Patch failed"),
        SandboxExecutionError("Container failed"),
        SandboxTimeoutError("Timed out"),
        RAGRetrievalError("Vector store offline"),
        ConfigurationError("Missing key"),
    ]
    for exc in exceptions:
        assert isinstance(exc, RepoPilotError)
