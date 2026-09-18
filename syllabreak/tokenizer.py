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
    is_modifier: bool = False
    start_idx: int = 0
    end_idx: int = 0


class Tokenizer:
    def __init__(self, word: str, rule: LanguageRule):
        self.rule = rule
        self.word = self._recompose_category_flips(word)
        self.word_lower = self.word.lower()
        self.tokens: list[Token] = []
        self.pos = 0

    def _recompose_category_flips(self, word: str) -> str:
        result: list[str] = []
        i = 0
        while i < len(word):
            end = i + 1
            while end < len(word) and unicodedata.category(word[end]) == "Mn":
                end += 1
            if end > i + 1:
                composed = unicodedata.normalize("NFC", word[i:end])
                if len(composed) == 1 and self._classify_letter(composed.lower()) not in (
                    None,
                    self._classify_letter(word[i].lower()),
                ):
                    result.append(composed)
                    i = end
                    continue
            result.append(word[i])
            i += 1
        return "".join(result)

    def tokenize(self) -> list[Token]:
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

            for q in range(end - 1, start - 1, -1):
                if unicodedata.category(self.word_lower[q]) != "Mn":
                    chars.append(self.word_lower[q])
                    break
        return chars

    DIAERESIS = "̈"

    def _diaeresis_vetoes_at(self, end_pos: int) -> bool:
        for p in range(end_pos, len(self.word)):
            ch = self.word_lower[p]
            if unicodedata.category(ch) != "Mn":
                return False
            if ch == self.DIAERESIS:
                return True
        return False

    def _try_match_digraph(self, source: set[str], token_class: TokenClass) -> bool:
        positions = self._scan_bases()
        bases = self._bases_at_positions(positions) if positions else []
        for length in (3, 2, 1):
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
        return self._try_match_digraph(self.rule.dont_split_digraphs, TokenClass.CONSONANT)

    def _try_match_vowel_digraph(self) -> bool:
        return self._try_match_digraph(self.rule.digraph_vowels, TokenClass.VOWEL)

    def _classify_letter(self, char: str) -> TokenClass | None:
        if char in self.rule.vowels:
            return TokenClass.VOWEL
        if char in self.rule.consonants:
            return TokenClass.CONSONANT
        return None

    def _add_single_character_token(self):
        char = self.word_lower[self.pos]
        token_class = self._classify_letter(char)
        self.tokens.append(
            Token(
                surface=self.word[self.pos],
                token_class=token_class if token_class is not None else TokenClass.OTHER,
                start_idx=self.pos,
                end_idx=self.pos + 1,
            )
        )
        self.pos += 1
