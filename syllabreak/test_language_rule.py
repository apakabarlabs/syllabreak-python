from pathlib import Path

import pytest
import yaml

from syllabreak.language_rule import LanguageRule, _augment_mapping, _augment_set


def _load_cases():
    path = Path(__file__).parent / "data" / "language_rule_tests.yaml"
    return yaml.safe_load(path.read_text())["tests"]


def _load_mapping_cases():
    path = Path(__file__).parent / "data" / "language_rule_tests.yaml"
    return yaml.safe_load(path.read_text())["mapping_tests"]


def _load_geminate_cases():
    path = Path(__file__).parent / "data" / "language_rule_tests.yaml"
    return yaml.safe_load(path.read_text())["geminate_tests"]


def _load_vowel_nucleus_rule_cases():
    path = Path(__file__).parent / "data" / "language_rule_tests.yaml"
    return yaml.safe_load(path.read_text())["vowel_nucleus_rule_tests"]


@pytest.mark.parametrize("case", _load_cases(), ids=lambda case: case["name"])
def test_augment_set(case):
    assert _augment_set(case["values"]) == set(case["expected"])


@pytest.mark.parametrize("case", _load_mapping_cases(), ids=lambda case: case["name"])
def test_augment_mapping(case):
    actual = _augment_mapping(case["mapping"])
    for entry in case["expected"]:
        assert actual[entry["key"]] == entry["value"]


@pytest.mark.parametrize("case", _load_geminate_cases(), ids=lambda case: case["name"])
def test_expand_geminate_digraphs(case):
    expanded, spans = LanguageRule(case["rule"]).expand_geminate_digraphs(case["word"])
    expected_spans = [(span["start"], span["length"], span["compact"]) for span in case["spans"]]
    assert expanded == case["expanded"]
    assert spans == expected_spans


@pytest.mark.parametrize("case", _load_vowel_nucleus_rule_cases(), ids=lambda case: case["name"])
def test_vowel_nucleus_rule_validation(case):
    data = {
        "lang": "test",
        "vowels": "aeiou",
        "consonants": "bcdfghjklmnpqrstvwxyz",
        "vowel_nucleus_rules": case["entries"],
    }
    if "error" in case:
        with pytest.raises(ValueError, match=case["error"]):
            LanguageRule(data)
    else:
        rule = LanguageRule(data)
        assert [entry.suffix for entry in rule.vowel_nucleus_rules] == case["expected"]
