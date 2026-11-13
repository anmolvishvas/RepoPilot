"""Domain exception hierarchy for RepoPilot."""


class RepoPilotError(Exception):
    """Base exception for all domain errors within RepoPilot."""

    def __init__(self, message: str, details: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} (Details: {self.details})"
        return self.message


class ASTParseError(RepoPilotError):
    """Raised when an AST parser fails to parse a source code file."""


class SymbolNotFoundError(RepoPilotError):
    """Raised when an AST symbol cannot be located in the symbol catalog."""


class CallGraphError(RepoPilotError):
    """Raised when an error occurs during call graph construction or traversal."""


class DiffApplicationError(RepoPilotError):
    """Raised when applying a unified diff against a target file fails."""


class SandboxExecutionError(RepoPilotError):
    """Raised when Docker sandbox runner fails to execute a command."""


class SandboxTimeoutError(SandboxExecutionError):
    """Raised when a sandbox execution exceeds its allotted timeout."""


class RAGRetrievalError(RepoPilotError):
    """Raised when vector or sparse retrieval encounters an error."""


class ConfigurationError(RepoPilotError):
    """Raised when application settings or environment variables are invalid."""
