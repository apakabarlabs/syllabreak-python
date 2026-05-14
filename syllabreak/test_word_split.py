"""Reads `data/word_split_tests.yaml` and asserts every row.

This file lives next to the implementation so every platform's port can mirror
the same table (kotlin and swift load the same yaml).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from .word_split import WordSplitter


def _load_cases() -> list[tuple[str, str, list[str]]]:
    path = Path(__file__).parent / "data" / "word_split_tests.yaml"
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return [(row["lang"], row["text"], row["expected"]) for row in data["tests"]]


@pytest.fixture(scope="module")
def splitter() -> WordSplitter:
    return WordSplitter()


@pytest.mark.parametrize(("lang", "text", "expected"), _load_cases())
def test_word_split(splitter: WordSplitter, lang: str, text: str, expected: list[str]) -> None:
    assert splitter.split(text, lang) == expected
