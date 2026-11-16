"""Safe file reading and atomic unified diff application tools for MCP."""

from __future__ import annotations

import re
from pathlib import Path

from repopilot.ast.parser import TreeSitterParser
from repopilot.core.exceptions import DiffApplicationError, RepoPilotError
from repopilot.core.result import Err, Ok, Result


def read_file_range(
    repo_root: Path | str,
    relative_path: str,
    start_line: int = 1,
    end_line: int = 100,
) -> Result[str, RepoPilotError]:
    """Safely read a specific line range from a file, preventing path traversal attacks."""
    root = Path(repo_root).resolve()
    target = (root / relative_path).resolve()

    # Directory traversal security guard
    if not target.is_relative_to(root):
        return Err(
            RepoPilotError(
                f"Security error: path '{relative_path}' traverses outside repository root."
            )
        )

    if not target.exists():
        return Err(RepoPilotError(f"File not found: {relative_path}"))

    if not target.is_file():
        return Err(RepoPilotError(f"Target is not a file: {relative_path}"))

    try:
        lines = target.read_text(encoding="utf-8").splitlines(keepends=True)
        # 1-based indexing for start_line and end_line
        s = max(1, start_line) - 1
        e = max(s, end_line)
        selected_lines = lines[s:e]
        return Ok("".join(selected_lines))
    except Exception as exc:
        return Err(RepoPilotError(f"Failed to read file {relative_path}", details=str(exc)))


def apply_unified_diff(
    repo_root: Path | str,
    target_file: str,
    patch_str: str,
    parser: TreeSitterParser | None = None,
) -> Result[str, DiffApplicationError]:
    """Validate, apply a unified diff to a target file, and verify AST syntax."""
    root = Path(repo_root).resolve()
    target = (root / target_file).resolve()

    if not target.is_relative_to(root):
        return Err(DiffApplicationError(f"Path traversal detected: {target_file}"))

    if not target.exists():
        return Err(DiffApplicationError(f"Target file does not exist: {target_file}"))

    try:
        original_content = target.read_text(encoding="utf-8")
        patched_content = _patch_text(original_content, patch_str)

        # Pre-validate AST syntax before committing changes to disk
        tree_parser = parser or TreeSitterParser()
        parse_res = tree_parser.parse_code(patched_content, file_path=target_file)
        if parse_res.is_err or tree_parser.has_syntax_errors(parse_res.unwrap()):
            return Err(
                DiffApplicationError(
                    f"Applying diff to {target_file} resulted in syntax errors. Patch rejected."
                )
            )

        # Write patched content to file
        target.write_text(patched_content, encoding="utf-8")
        return Ok(f"Successfully applied diff to {target_file}")
    except DiffApplicationError:
        raise
    except Exception as exc:
        return Err(DiffApplicationError(f"Failed applying diff to {target_file}", details=str(exc)))


def _patch_text(original_text: str, patch_str: str) -> str:
    """Apply unified diff patch hunks directly in memory."""
    orig_lines = original_text.splitlines()
    patch_lines = patch_str.splitlines()

    # If no @@ header found, treat patch_str as full replacement text
    hunk_indices = [idx for idx, line in enumerate(patch_lines) if line.startswith("@@")]
    if not hunk_indices:
        return patch_str

    new_lines: list[str] = []
    current_orig_idx = 0

    hunk_pattern = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

    line_idx = 0
    total_patch_lines = len(patch_lines)

    while line_idx < total_patch_lines:
        line = patch_lines[line_idx]
        match = hunk_pattern.match(line)
        if match:
            orig_start = int(match.group(1))
            # 1-based index in original file: copy any unmodified lines prior to this hunk
            target_idx = max(0, orig_start - 1)
            if target_idx > current_orig_idx:
                new_lines.extend(orig_lines[current_orig_idx:target_idx])
                current_orig_idx = target_idx

            line_idx += 1
            while line_idx < total_patch_lines and not patch_lines[line_idx].startswith("@@"):
                hunk_line = patch_lines[line_idx]
                if hunk_line.startswith("+"):
                    new_lines.append(hunk_line[1:])
                elif hunk_line.startswith("-"):
                    current_orig_idx += 1
                elif hunk_line.startswith(" "):
                    new_lines.append(hunk_line[1:])
                    current_orig_idx += 1
                elif not hunk_line.startswith(("---", "+++")):
                    new_lines.append(hunk_line)
                    current_orig_idx += 1
                line_idx += 1
        else:
            line_idx += 1

    # Append any remaining lines from the original text
    if current_orig_idx < len(orig_lines):
        new_lines.extend(orig_lines[current_orig_idx:])

    trailing_newline = "\n" if original_text.endswith("\n") else ""
    return "\n".join(new_lines) + trailing_newline
