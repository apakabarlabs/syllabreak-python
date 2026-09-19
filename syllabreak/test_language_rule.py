from pathlib import Path

import pytest
import yaml

from syllabreak.language_rule import _augment_set


def _load_cases():
    path = Path(__file__).parent / "data" / "language_rule_tests.yaml"
    return yaml.safe_load(path.read_text())["tests"]


@pytest.mark.parametrize("case", _load_cases(), ids=lambda case: case["name"])
def test_augment_set(case):
    assert _augment_set(case["values"]) == set(case["expected"])
