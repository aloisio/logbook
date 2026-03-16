from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

import pytest

from format import mdformat

@pytest.mark.parametrize("case", ["check_boxes_not_rendered_as_input"], indirect=True)
def test_mdformat_acceptance(tmp_path: Path, case: Case):
    # Given a markdown file with task lists, tables, and un-normalized links
    # strikethrough is currently NOT supported by this renderer because of a KeyError: 's' bug
    # in mdformat/mdformat-gfm when using MDRenderer directly.
    # So we omit it from this acceptance test for now.
    md_file = tmp_path / "test.md"
    md_file.write_text(case.input_content, encoding="utf-8")
    
    # When we run mdformat (which calls MarkdownParser.normalize_markdown)
    mdformat(md_file)
    
    # Then task lists should NOT be converted to HTML input tags
    # and links should be normalized (labels zero-filled and moved to bottom)
    # and tables should be formatted
    normalized_content = md_file.read_text(encoding="utf-8")
    
    for substring in case.unexpected_substrings:
        assert substring not in normalized_content
    
    for substring in case.expected_substrings:
        assert substring in normalized_content


@pytest.fixture
def check_boxes_not_rendered_as_input() -> Case:
    return Case(
        input_content=dedent("""\
            # [❮](../2025/12/28/20251228.md) [2026-03-15][2] ❯
            
            - [ ] Fix Garage Door
            - [x] Done Task
            
            | a | b |
            |---|---|
            | 1 | 2 |
            
            [2]: ../../2026.md#march
        """).strip(),
        expected_substrings=[
            "- [ ] Fix Garage Door",
            "- [x] Done Task",
            "| a   | b   |",
            "| --- | --- |",
            "# [❮][1] [2026-03-15][2] ❯",
            "[1]: ../2025/12/28/20251228.md",
            "[2]: ../../2026.md#march",
        ],
        unexpected_substrings=[
            '<input class="task-list-item-checkbox"',
        ],
    )


@dataclass
class Case:
    input_content: str
    expected_substrings: list[str]
    unexpected_substrings: list[str]
    expected_content: str | None = None
