from pathlib import Path

import pytest
import yaml

from syllabreak import Syllabreak


def load_test_cases():
    test_file = Path(__file__).parent / "data" / "syllabify_tests.yaml"
    with open(test_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    test_cases = []
    for section in data["tests"]:
        section_name = section["section"]
        lang = section.get("lang")
        for case in section["cases"]:
            test_cases.append((section_name, lang, case["text"], case["want"]))
    return test_cases


@pytest.mark.parametrize("section,lang,text,want", load_test_cases())
def test_syllabify(section, lang, text, want):
    syllabifier = Syllabreak("-")
    if lang:
        result = syllabifier.syllabify(text, lang=lang)
    else:
        result = syllabifier.syllabify(text)
    assert result == want, f"[{section}] Failed for '{text}': got '{result}', want '{want}'"
