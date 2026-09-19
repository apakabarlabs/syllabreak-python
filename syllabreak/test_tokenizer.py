import unicodedata
from pathlib import Path

import pytest
import yaml

from syllabreak.language_rule import LanguageRule
from syllabreak.tokenizer import Tokenizer


def _load_cases():
    path = Path(__file__).parent / "data" / "tokenizer_tests.yaml"
    return yaml.safe_load(path.read_text())["tests"]


@pytest.mark.parametrize("case", _load_cases(), ids=lambda case: case["name"])
def test_tokenizer(case):
    text = case["text"]
    if case.get("normalization") == "nfd":
        text = unicodedata.normalize("NFD", text)

    actual = Tokenizer(text, LanguageRule(case["rule"])).tokenize()
    expected = case["tokens"]

    assert len(actual) == len(expected)
    for token, want in zip(actual, expected, strict=True):
        assert token.surface == want["surface"]
        assert (
            token.token_class.value
            == {
                "vowel": "vowel",
                "consonant": "cons",
                "separator": "sep",
                "other": "other",
            }[want["class"]]
        )
        assert token.is_modifier is want.get("modifier", False)
        assert token.start_idx == want["start"]
        assert token.end_idx == want["end"]
