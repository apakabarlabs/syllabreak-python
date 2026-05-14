"""Per-language sentence → words splitter.

Single source of truth for both backend (flowbot) and clients
(apakabarlib-swift / -kotlin via the sibling syllabreak ports).

The unit returned is a *word* — the same thing the learner sees on screen and
assigns a lemma to. NOT a BPE/subword token from any LLM tokenizer.

Two modes, configured in `data/word_split_rules.yaml`:

* **default** — for space-separated scripts. A word is one or more Unicode
  letters/marks/digits, optionally joined by an apostrophe (straight or curly)
  or a hyphen. Combining marks (Hebrew points, Arabic harakat, Devanagari
  matras) attach to the preceding letter.

* **cjk** — for languages where the script has no word-boundary spaces
  (`cmn`, `jpn`, `kor`). Each Han / Hiragana / Katakana / Hangul character is
  its own word; Latin/digit runs stay together so "iPhoneを使う" yields
  ["iPhone", "を", "使", "う"].
"""

from __future__ import annotations

from pathlib import Path

import regex
import yaml

_DEFAULT_WORD_RE = regex.compile(
    r"[\p{L}\p{M}\p{Nd}]+(?:[''’\-][\p{L}\p{M}\p{Nd}]+)*",
)

# CJK character ranges: Han Unified + Extension A + Compat, Hiragana, Katakana,
# Hangul Syllables. Matched as a literal class; Latin/digit runs are caught
# first so mixed scripts (iPhoneを使う) tokenise sensibly.
_CJK_CHAR_RANGE = (
    "㐀-䶿"  # CJK Unified Ideographs Extension A
    "一-鿿"  # CJK Unified Ideographs
    "豈-﫿"  # CJK Compatibility Ideographs
    "぀-ゟ"  # Hiragana
    "゠-ヿ"  # Katakana
    "가-힯"  # Hangul Syllables
)

_CJK_WORD_RE = regex.compile(
    r"[A-Za-z0-9]+(?:[''’\-][A-Za-z0-9]+)*"
    r"|"
    rf"[{_CJK_CHAR_RANGE}]",
)


def _load_rules() -> dict[str, str]:
    rules_file = Path(__file__).parent / "data" / "word_split_rules.yaml"
    with open(rules_file, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return {entry["lang"]: entry["mode"] for entry in data["rules"]}


class WordSplitter:
    """Splits text into words per language. Rules loaded from yaml on init."""

    def __init__(self) -> None:
        self._modes = _load_rules()

    def split(self, text: str, lang: str) -> list[str]:
        return [text[s:e] for s, e in self.find_ranges(text, lang)]

    def find_ranges(self, text: str, lang: str) -> list[tuple[int, int]]:
        """Like `split` but returns (start, end) character offsets — needed
        by clients that highlight or annotate specific word positions in the
        original text (e.g. iOS lexeme spans), where re-searching the surface
        form would be ambiguous on repeats ("the cat sat on the mat")."""
        regex_obj = _CJK_WORD_RE if self._modes.get(lang) == "cjk" else _DEFAULT_WORD_RE
        return [m.span() for m in regex_obj.finditer(text)]
