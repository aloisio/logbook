from __future__ import annotations

from dataclasses import dataclass
from textwrap import dedent

import pytest

from model import (
    MarkdownParser,
)


@pytest.mark.parametrize(
    "case",
    [
        "link_normalization",
        "move_inline_links_to_link_references",
        "detect_duplicates",
        "zero_fill_link_reference_labels",
        "rearrange_existing_link_reference_definitions",
        "image_links",
        "autolink_does_not_create_link_reference_definition",
        "auto_links_are_skipped",
        "number_nested_links_depth_first",
        "do_not_linkify",
    ],
    indirect=True,
)
def test_markdown_parser_acceptance(case: Case):
    input_markdown = dedent(case.input_content).lstrip()
    normalized = MarkdownParser.normalize_markdown(input_markdown)

    if case.expected_content is not None:
        assert normalized == dedent(case.expected_content).lstrip()

    for substring in case.expected_substrings:
        assert substring in normalized

    for substring in case.unexpected_substrings:
        assert substring not in normalized


@pytest.fixture
def link_normalization() -> Case:
    return Case(
        input_content="""
            # [A](a) [B][1] [C](c) [D](c)

            paragraph

            [1]: b
        """,
        expected_substrings=[
            "# [A][1] [B][2] [C][3] [D][3]",
            "[1]: a",
            "[2]: b",
            "[3]: c",
        ],
        unexpected_substrings=[],
    )


@pytest.fixture
def move_inline_links_to_link_references() -> Case:
    return Case(
        input_content="""
            # [❮](../prev.md) [Header](../top.md "Top") [❯](../next.md)

            paragraph
        """,
        expected_content="""
            # [❮][1] [Header][2] [❯][3]

            paragraph

            [1]: ../prev.md
            [2]: ../top.md "Top"
            [3]: ../next.md
        """,
        expected_substrings=[],
        unexpected_substrings=[],
    )


@pytest.fixture
def detect_duplicates() -> Case:
    return Case(
        input_content="""
            # [❮](linked.md) [Header](../top.md "Top") [❯](linked.md)

            paragraph
        """,
        expected_content="""
            # [❮][1] [Header][2] [❯][1]

            paragraph

            [1]: linked.md
            [2]: ../top.md "Top"
        """,
        expected_substrings=[],
        unexpected_substrings=[],
    )


@pytest.fixture
def zero_fill_link_reference_labels() -> Case:
    return Case(
        input_content="""
            # [A](a) [B](b) [C](c) [D](d) [E](e) [F](f) [G](g) [H](h) [I](i) [J](j)

            paragraph
        """,
        expected_content="""
            # [A][01] [B][02] [C][03] [D][04] [E][05] [F][06] [G][07] [H][08] [I][09] [J][10]

            paragraph

            [01]: a
            [02]: b
            [03]: c
            [04]: d
            [05]: e
            [06]: f
            [07]: g
            [08]: h
            [09]: i
            [10]: j
        """,
        expected_substrings=[],
        unexpected_substrings=[],
    )


@pytest.fixture
def rearrange_existing_link_reference_definitions() -> Case:
    return Case(
        input_content="""
            # [A](a) [B][1] [C](c) [D](c)

            paragraph

            [1]: b
        """,
        expected_content="""
            # [A][1] [B][2] [C][3] [D][3]

            paragraph

            [1]: a
            [2]: b
            [3]: c
        """,
        expected_substrings=[],
        unexpected_substrings=[],
    )


@pytest.fixture
def image_links() -> Case:
    return Case(
        input_content="""
            ![Alt](image.jpg "title")
        """,
        expected_content="""
            ![Alt][1]

            [1]: image.jpg "title"
        """,
        expected_substrings=[],
        unexpected_substrings=[],
    )


@pytest.fixture
def autolink_does_not_create_link_reference_definition() -> Case:
    return Case(
        input_content="""
            ## Test

            > Test <email@example.com>
            >
            > ![test](image.jpg)
            >
        """,
        expected_content="""
            ## Test

            > Test <email@example.com>
            >
            > ![test][1]

            [1]: image.jpg
        """,
        expected_substrings=[],
        unexpected_substrings=[],
    )


@pytest.fixture
def auto_links_are_skipped() -> Case:
    return Case(
        input_content="""
            Go to <https://www.google.com>
        """,
        expected_content="""
            Go to <https://www.google.com>
        """,
        expected_substrings=[],
        unexpected_substrings=[],
    )


@pytest.fixture
def number_nested_links_depth_first() -> Case:
    return Case(
        input_content="""
            [![Alt](image.jpg "title")](external.md) [Figure 1](list_of_figures.md)
        """,
        expected_content="""
            [![Alt][1]][2] [Figure 1][3]

            [1]: image.jpg "title"
            [2]: external.md
            [3]: list_of_figures.md
        """,
        expected_substrings=[],
        unexpected_substrings=[],
    )


@pytest.fixture
def do_not_linkify() -> Case:
    return Case(
        input_content="""
            - List all available workflows (Workpace.ID = 1)
        """,
        expected_content="""
            - List all available workflows (Workpace.ID = 1)
        """,
        expected_substrings=[],
        unexpected_substrings=[],
    )


@dataclass
class Case:
    input_content: str
    expected_substrings: list[str]
    unexpected_substrings: list[str]
    expected_content: str | None = None
