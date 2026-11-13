"""Baseline unit test verifying package integrity and metadata."""

import repopilot
import repopilot.agents
import repopilot.ast
import repopilot.mcp
import repopilot.rag
import repopilot.sandbox
import repopilot.server


def test_package_metadata() -> None:
    """Verify package version and author metadata are defined."""
    assert repopilot.__version__ == "0.1.0"
    assert repopilot.__author__ == "Anmol Vishvas"


def test_subsystem_packages_importable() -> None:
    """Verify that all core subsystems can be imported cleanly."""
    assert repopilot.ast is not None
    assert repopilot.rag is not None
    assert repopilot.mcp is not None
    assert repopilot.agents is not None
    assert repopilot.sandbox is not None
    assert repopilot.server is not None
