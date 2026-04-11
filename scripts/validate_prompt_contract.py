#!/usr/bin/env python3

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "SKILL.md"
README = ROOT / "README.md"
TOOL_MAP = ROOT / "references" / "tool-map.md"

SHARED_REQUIRED_SNIPPETS = [
    "When `--dry-run` is set, generate the transformed output and validation report\nwithout writing any files.",
    "When `--dry-run` and `--test` are combined, validate the generated content in\nmemory rather than from written files.",
    "Candidate MCP entries require explicit user approval before inclusion in\n`agents/openai.yaml`.",
    "`--overwrite` skips only the existing-directory overwrite prompt.",
]

SKILL_REQUIRED_PHRASES = [
    "Trust tier: `official`, `community`, or `scraped`.",
    "allowing only letters, numbers, `.`, `_`, and `-`.",
    "If `--multi-agent` is set and files were written, you may spawn one\n  independent tester agent that reads the written files cold.",
]


def tracked_paths() -> list[str]:
    output = subprocess.check_output(
        ["git", "ls-files"],
        cwd=ROOT,
        text=True,
    )
    return [line for line in output.splitlines() if line]


def load(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_no_whitespace_prefixed_paths(errors: list[str]) -> None:
    bad = [path for path in tracked_paths() if path[:1].isspace()]
    if bad:
        errors.append(
            "Tracked paths must not begin with whitespace: "
            + ", ".join(repr(path) for path in bad)
        )


def check_duplicate_step_headers(skill_text: str, errors: list[str]) -> None:
    headers = re.findall(r"^### Step[^\n]+", skill_text, flags=re.MULTILINE)
    duplicates = sorted({header for header in headers if headers.count(header) > 1})
    if duplicates:
        errors.append(
            "SKILL.md contains duplicate step headers: " + ", ".join(duplicates)
        )


def check_tool_map_frontmatter(tool_map_text: str, errors: list[str]) -> None:
    if re.search(r"^\s*invocation\s*:", tool_map_text, flags=re.MULTILINE):
        errors.append(
            "references/tool-map.md must not reintroduce frontmatter guidance for "
            "`invocation`."
        )


def check_skill_required_phrases(skill_text: str, errors: list[str]) -> None:
    missing = [phrase for phrase in SKILL_REQUIRED_PHRASES if phrase not in skill_text]
    if missing:
        errors.append(
            "SKILL.md is missing required trust/safety phrases: "
            + "; ".join(repr(item) for item in missing)
        )


def check_shared_snippets(skill_text: str, readme_text: str, errors: list[str]) -> None:
    missing = [
        snippet
        for snippet in SHARED_REQUIRED_SNIPPETS
        if snippet not in skill_text or snippet not in readme_text
    ]
    if missing:
        errors.append(
            "README.md and SKILL.md must both contain the same dry-run/test/MCP "
            "behavior snippets: "
            + "; ".join(repr(item) for item in missing)
        )


def main() -> int:
    errors: list[str] = []

    skill_text = load(SKILL)
    readme_text = load(README)
    tool_map_text = load(TOOL_MAP)

    check_no_whitespace_prefixed_paths(errors)
    check_duplicate_step_headers(skill_text, errors)
    check_tool_map_frontmatter(tool_map_text, errors)
    check_skill_required_phrases(skill_text, errors)
    check_shared_snippets(skill_text, readme_text, errors)

    if errors:
        print("Prompt contract validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Prompt contract validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
