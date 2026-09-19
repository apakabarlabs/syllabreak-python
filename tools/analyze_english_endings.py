#!/usr/bin/env python3
"""Measure English ending rules against a pinned external pronunciation corpus.

This development tool never modifies runtime rules. It reports disagreements for
human classification, ordered by an independent corpus-frequency estimate.
"""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path

from wordfreq import zipf_frequency

from syllabreak import Syllabreak

CMUDICT_COMMIT = "74790861f652b15e4ac49015a90074ad62a27690"
CMUDICT_URL = f"https://raw.githubusercontent.com/cmusphinx/cmudict/{CMUDICT_COMMIT}/cmudict.dict"
PRONUNCIATION_VARIANT = re.compile(r"\(\d+\)$")
VOWEL_PHONEME = re.compile(r"\d$")


def load_cmudict(path: Path) -> dict[str, list[tuple[str, ...]]]:
    """Return the attested pronunciations for each alphabetic CMUdict word."""
    result: dict[str, list[tuple[str, ...]]] = defaultdict(list)
    with path.open(encoding="utf-8") as source:
        for line in source:
            spelling, *phonemes = line.rstrip().split()
            spelling = PRONUNCIATION_VARIANT.sub("", spelling.lower())
            if spelling.isascii() and spelling.isalpha():
                result[spelling].append(tuple(phonemes))
    return dict(result)


def syllable_counts(pronunciations: list[tuple[str, ...]]) -> set[int]:
    return {sum(bool(VOWEL_PHONEME.search(phone)) for phone in pronunciation) for pronunciation in pronunciations}


def pronounced_final_e(pronunciations: list[tuple[str, ...]]) -> bool:
    return any(pronunciation and pronunciation[-1].rstrip("012") in {"IY", "EY"} for pronunciation in pronunciations)


def ed_contains_final_vowel(pronunciations: list[tuple[str, ...]]) -> bool:
    return any(
        len(pronunciation) >= 2
        and pronunciation[-1].rstrip("012") in {"D", "T"}
        and pronunciation[-2] in {"AH0", "IH0"}
        for pronunciation in pronunciations
    )


def predicted_count(engine: Syllabreak, word: str) -> int:
    """Return the number of syllables emitted by the current generic rules."""
    rendered = engine.syllabify(word, lang="eng")
    return rendered.count("-") + 1


def ending_class(word: str) -> str | None:
    if word.endswith("ed"):
        return "ed"
    if word.endswith("e"):
        return "e"
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Rank final-e/-ed rule disagreements against CMUdict and wordfreq.")
    parser.add_argument("cmudict", type=Path, help=f"cmudict.dict from {CMUDICT_URL}")
    parser.add_argument("--minimum-zipf", type=float, default=3.0)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--include-lexicon", action="store_true")
    args = parser.parse_args()

    gold = load_cmudict(args.cmudict)
    engine = Syllabreak(soft_hyphen="-")
    english = engine._get_rule_by_lang("eng")
    english.exceptions = {}
    if not args.include_lexicon:
        english.vowel_nucleus_rules = tuple(rule for rule in english.vowel_nucleus_rules if not rule.words)

    rows: list[tuple[float, str, str, int, set[int]]] = []
    totals: dict[str, list[int]] = {"e": [0, 0], "ed": [0, 0]}
    lexical_e: list[tuple[float, str]] = []
    lexical_ed: list[tuple[float, str]] = []
    for word, pronunciations in gold.items():
        group = ending_class(word)
        if group is None:
            continue
        expected = syllable_counts(pronunciations)
        actual = predicted_count(engine, word)
        frequency = zipf_frequency(word, "en")
        undercounts = actual < min(expected)
        if frequency >= args.minimum_zipf and undercounts:
            if group == "e" and len(word) > 1 and word[-2] not in "aeiouy" and pronounced_final_e(pronunciations):
                lexical_e.append((frequency, word))
            if (
                group == "ed"
                and len(word) > 2
                and word[-3] not in "aeiouytd"
                and ed_contains_final_vowel(pronunciations)
            ):
                lexical_ed.append((frequency, word))
        totals[group][0] += 1
        if actual not in expected:
            totals[group][1] += 1
            if frequency >= args.minimum_zipf:
                rows.append((frequency, group, word, actual, expected))

    for group, (total, failures) in totals.items():
        print(f"{group}: {failures}/{total} disagreements ({failures / total:.1%})")
    print()
    for frequency, group, word, actual, expected in sorted(rows, reverse=True)[: args.limit]:
        expected_text = ",".join(str(value) for value in sorted(expected))
        print(f"{frequency:4.2f}\t{group}\t{word}\tpredicted={actual}\tcmudict={expected_text}")
    print()
    print(f"pronounced final-e candidates: {len(lexical_e)}")
    print(" ".join(word for _, word in sorted(lexical_e, reverse=True)[: args.limit]))
    print(f"syllabic -ed candidates: {len(lexical_ed)}")
    print(" ".join(word for _, word in sorted(lexical_ed, reverse=True)[: args.limit]))


if __name__ == "__main__":
    main()
