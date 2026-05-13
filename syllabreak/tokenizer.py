import unicodedata
from dataclasses import dataclass
from enum import Enum

from .language_rule import LanguageRule


class TokenClass(Enum):
    VOWEL = "vowel"
    CONSONANT = "cons"
    SEPARATOR = "sep"
    OTHER = "other"


@dataclass
class Token:
    surface: str
    token_class: TokenClass
    is_glide: bool = False
    is_modifier: bool = False
    start_idx: int = 0
    end_idx: int = 0


class Tokenizer:
    """Tokenizes words according to language rules."""

    def __init__(self, word: str, rule: LanguageRule):
        self.word = word
        self.word_lower = word.lower()
        self.rule = rule
        self.tokens: list[Token] = []
        self.pos = 0

    def tokenize(self) -> list[Token]:
        """Main tokenization method."""
        while self.pos < len(self.word):
            if self._try_match_left_modifier():
                continue
            if self._try_match_separator():
                continue
            if self._try_match_consonant_digraph():
                continue
            if self._try_match_vowel_digraph():
                continue
            self._add_single_character_token()
        return self.tokens

    def _try_match_left_modifier(self) -> bool:
        """Try to match a left-attaching modifier at current position.

        In addition to the rule's explicit modifiers_attach_left set, any
        Unicode nonspacing mark (category Mn) attaches to the preceding token.
        Together with NFD normalisation on input this lets polytonic Greek
        (and any other diacritic-rich script) work without enumerating every
        precomposed codepoint in the rule.
        """
        char = self.word_lower[self.pos]
        is_modifier = char in self.rule.modifiers_attach_left or unicodedata.category(char) == "Mn"
        if not is_modifier:
            return False

        if self.tokens:
            self.tokens[-1].surface += self.word[self.pos]
            self.tokens[-1].end_idx = self.pos + 1
            self.tokens[-1].is_modifier = True
        else:
            self.tokens.append(
                Token(
                    surface=self.word[self.pos],
                    token_class=TokenClass.OTHER,
                    is_modifier=True,
                    start_idx=self.pos,
                    end_idx=self.pos + 1,
                )
            )
        self.pos += 1
        return True

    def _try_match_separator(self) -> bool:
        """Try to match a separator at current position."""
        char = self.word_lower[self.pos]
        if char not in self.rule.modifiers_separators:
            return False

        self.tokens.append(
            Token(
                surface=self.word[self.pos],
                token_class=TokenClass.SEPARATOR,
                start_idx=self.pos,
                end_idx=self.pos + 1,
            )
        )
        self.pos += 1
        return True

    def _scan_bases(self) -> list[int]:
        """Collect up to three upcoming base-letter end positions, skipping
        Unicode nonspacing marks (Mn) between them. Returned positions are
        slice-friendly (one past the matched base), so word[self.pos:
        positions[k-1]] is the surface for a k-base match including its
        intervening marks."""
        positions: list[int] = []
        p = self.pos
        while p < len(self.word) and len(positions) < 3:
            if unicodedata.category(self.word_lower[p]) == "Mn":
                p += 1
                continue
            positions.append(p + 1)
            p += 1
        return positions

    def _bases_at_positions(self, positions: list[int]) -> list[str]:
        chars = []
        for idx, end in enumerate(positions):
            start = self.pos if idx == 0 else positions[idx - 1]
            # The base letter is the last non-Mn char in word_lower[start:end].
            for q in range(end - 1, start - 1, -1):
                if unicodedata.category(self.word_lower[q]) != "Mn":
                    chars.append(self.word_lower[q])
                    break
        return chars

    DIAERESIS = "̈"

    def _diaeresis_vetoes_at(self, end_pos: int) -> bool:
        """Return True if a combining diaeresis (U+0308) attaches to the
        codepoint that would close a digraph match. In Greek (αϊ, εϊ, οϊ,
        Μαΐου, …) diaeresis explicitly signals "this vowel stands apart"
        — hiatus — and must break diphthong recognition; the same
        convention shows up elsewhere when ï/ü break their host digraph
        (`naïf`-style)."""
        for p in range(end_pos, len(self.word)):
            ch = self.word_lower[p]
            if unicodedata.category(ch) != "Mn":
                return False
            if ch == self.DIAERESIS:
                return True
        return False

    def _try_match_digraph(self, source: set[str], token_class: TokenClass) -> bool:
        """Shared logic for consonant and vowel digraphs.

        For each candidate length (3, 2, 1) we try the Mn-skipping match
        first, then the direct substring match. The Mn-skipping path
        composes the next N base letters while skipping any Unicode
        combining marks between them, so it can cover more codepoints
        than a direct length-N substring. This matters for triphthongs
        written with a diacritic on the middle base (Vietnamese yêu =
        y + ê + u → Mn-skip-3 matches the "yeu" base entry over 4
        codepoints, even though direct length-3 would match the shorter
        "yê"/"ye◌̂" entry first).

        The direct path is kept as a fallback within each length so
        digraphs whose marks sit on a vowel that participates in the
        digraph itself (deu "üh", a long-vowel lengthener u + ◌̈ + h)
        still match against their NFD-augmented entry.

        A diaeresis attached to the codepoint that closes the candidate
        match vetoes the digraph: αϊ / Μαΐου / naïf etc. are hiatus,
        not a digraph.
        """
        positions = self._scan_bases()
        bases = self._bases_at_positions(positions) if positions else []
        for length in (3, 2, 1):
            # Mn-skip match — composes base letters skipping marks.
            if len(bases) >= length:
                candidate = "".join(bases[:length])
                if candidate in source:
                    end = positions[length - 1]
                    if not self._diaeresis_vetoes_at(end):
                        self.tokens.append(
                            Token(
                                surface=self.word[self.pos : end],
                                token_class=token_class,
                                start_idx=self.pos,
                                end_idx=end,
                            )
                        )
                        self.pos = end
                        return True
            # Direct substring match — catches entries listed with the
            # mark inside (NFD-augmented "ye◌̂" matching the precomposed
            # YAML entry "yê").
            end = self.pos + length
            if end > len(self.word):
                continue
            substr = self.word_lower[self.pos : end]
            if substr in source and not self._diaeresis_vetoes_at(end):
                self.tokens.append(
                    Token(
                        surface=self.word[self.pos : end],
                        token_class=token_class,
                        start_idx=self.pos,
                        end_idx=end,
                    )
                )
                self.pos = end
                return True
        return False

    def _try_match_consonant_digraph(self) -> bool:
        # Length 3 supports trigraphs like Hungarian "dzs" and German "sch".
        return self._try_match_digraph(self.rule.dont_split_digraphs, TokenClass.CONSONANT)

    def _try_match_vowel_digraph(self) -> bool:
        # Length 3 supports trigraphs like BCMS "ije"/"ије" (long-jat reflex).
        return self._try_match_digraph(self.rule.digraph_vowels, TokenClass.VOWEL)

    def _add_single_character_token(self):
        """Add a single character token at current position."""
        char = self.word_lower[self.pos]
        if char in self.rule.vowels:
            self.tokens.append(
                Token(
                    surface=self.word[self.pos],
                    token_class=TokenClass.VOWEL,
                    start_idx=self.pos,
                    end_idx=self.pos + 1,
                )
            )
        elif char in self.rule.consonants or char in self.rule.glides or char in self.rule.sonorants:
            is_glide = char in self.rule.glides
            self.tokens.append(
                Token(
                    surface=self.word[self.pos],
                    token_class=TokenClass.CONSONANT,
                    is_glide=is_glide,
                    start_idx=self.pos,
                    end_idx=self.pos + 1,
                )
            )
        else:
            self.tokens.append(
                Token(
                    surface=self.word[self.pos],
                    token_class=TokenClass.OTHER,
                    start_idx=self.pos,
                    end_idx=self.pos + 1,
                )
            )
        self.pos += 1
