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
        """Try to match a left-attaching modifier at current position."""
        char = self.word_lower[self.pos]
        if char not in self.rule.modifiers_attach_left:
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

    def _try_match_consonant_digraph(self) -> bool:
        """Try to match a consonant digraph at current position."""
        for length in [2, 1]:
            if self.pos + length > len(self.word):
                continue
            substr = self.word_lower[self.pos : self.pos + length]
            if substr in self.rule.dont_split_digraphs:
                self.tokens.append(
                    Token(
                        surface=self.word[self.pos : self.pos + length],
                        token_class=TokenClass.CONSONANT,
                        start_idx=self.pos,
                        end_idx=self.pos + length,
                    )
                )
                self.pos += length
                return True
        return False

    def _try_match_vowel_digraph(self) -> bool:
        """Try to match a vowel digraph at current position."""
        # Length 3 supports trigraphs like BCMS "ije"/"ије" (long-jat reflex).
        for length in [3, 2, 1]:
            if self.pos + length > len(self.word):
                continue
            substr = self.word_lower[self.pos : self.pos + length]
            if substr in self.rule.digraph_vowels:
                self.tokens.append(
                    Token(
                        surface=self.word[self.pos : self.pos + length],
                        token_class=TokenClass.VOWEL,
                        start_idx=self.pos,
                        end_idx=self.pos + length,
                    )
                )
                self.pos += length
                return True
        return False

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
