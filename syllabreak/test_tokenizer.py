import pytest

from syllabreak.language_rule import LanguageRule
from syllabreak.tokenizer import TokenClass, Tokenizer


@pytest.fixture
def create_test_rule():
    """Fixture to create a test LanguageRule with defaults that can be overridden."""

    def _create(lang="test", **overrides):
        default_data = {
            "lang": lang,
            "vowels": "aeiou",
            "consonants": "bcdfghjklmnpqrstvwxyz",
            "clusters_keep_next": [],
            "dont_split_digraphs": [],
            "digraph_vowels": [],
            "glides": "",
            "syllabic_consonants": "",
            "modifiers_attach_left": "",
            "modifiers_separators": "",
        }
        default_data.update(overrides)
        return LanguageRule(default_data)

    return _create


def test_consonant_digraph_nj(create_test_rule):
    """Test that 'nj' is recognized as a single consonant digraph."""
    rule = create_test_rule(vowels="aeio", consonants="njgv", dont_split_digraphs=["nj"])

    tokenizer = Tokenizer("njegov", rule)
    tokens = tokenizer.tokenize()

    surfaces = [t.surface for t in tokens]
    assert surfaces == ["nj", "e", "g", "o", "v"]
    assert tokens[0].token_class == TokenClass.CONSONANT
    assert tokens[0].start_idx == 0
    assert tokens[0].end_idx == 2


def test_consonant_digraph_precedence(create_test_rule):
    """Test that consonant digraphs have precedence over single chars."""
    rule = create_test_rule(vowels="aeiou", consonants="chlst", dont_split_digraphs=["ch", "sh", "th"])

    tokenizer = Tokenizer("cheat", rule)
    tokens = tokenizer.tokenize()

    surfaces = [t.surface for t in tokens]
    assert surfaces == ["ch", "e", "a", "t"]
    assert tokens[0].token_class == TokenClass.CONSONANT


def test_vowel_digraph(create_test_rule):
    """Test vowel digraph recognition."""
    rule = create_test_rule(vowels="aeiou", consonants="bcdfg", digraph_vowels=["ea", "ee"])

    tokenizer = Tokenizer("beat", rule)
    tokens = tokenizer.tokenize()

    surfaces = [t.surface for t in tokens]
    assert surfaces == ["b", "ea", "t"]
    assert tokens[1].token_class == TokenClass.VOWEL


def test_left_attaching_modifier(create_test_rule):
    """Test that left-attaching modifiers attach to previous token."""
    rule = create_test_rule(vowels="aoуие", consonants="кмпьтр", modifiers_attach_left="ь")

    tokenizer = Tokenizer("компь", rule)
    tokens = tokenizer.tokenize()

    surfaces = [t.surface for t in tokens]
    assert surfaces == ["к", "о", "м", "пь"]
    assert tokens[3].is_modifier is True


def test_separator(create_test_rule):
    """Test separator tokens."""
    rule = create_test_rule(vowels="aeiou", consonants="bcdfg", modifiers_separators="-")

    tokenizer = Tokenizer("ab-cd", rule)
    tokens = tokenizer.tokenize()

    surfaces = [t.surface for t in tokens]
    classes = [t.token_class for t in tokens]
    assert surfaces == ["a", "b", "-", "c", "d"]
    assert classes == [
        TokenClass.VOWEL,
        TokenClass.CONSONANT,
        TokenClass.SEPARATOR,
        TokenClass.CONSONANT,
        TokenClass.CONSONANT,
    ]


def test_vowel_classification(create_test_rule):
    """Test single vowel classification."""
    rule = create_test_rule()

    tokenizer = Tokenizer("aei", rule)
    tokens = tokenizer.tokenize()

    assert all(t.token_class == TokenClass.VOWEL for t in tokens)


def test_consonant_classification(create_test_rule):
    """Test single consonant classification."""
    rule = create_test_rule()

    tokenizer = Tokenizer("bcd", rule)
    tokens = tokenizer.tokenize()

    assert all(t.token_class == TokenClass.CONSONANT for t in tokens)


def test_glide_classification(create_test_rule):
    """Test that glides are marked correctly."""
    rule = create_test_rule(consonants="bcdjwy", glides="jwy")

    tokenizer = Tokenizer("jay", rule)
    tokens = tokenizer.tokenize()

    assert tokens[0].token_class == TokenClass.CONSONANT
    assert tokens[0].is_glide
    assert tokens[2].token_class == TokenClass.CONSONANT
    assert tokens[2].is_glide


def test_unknown_char_classification(create_test_rule):
    """Test that unknown characters get 'other' class."""
    rule = create_test_rule(vowels="aeiou", consonants="bcdfg")

    tokenizer = Tokenizer("a#b", rule)
    tokens = tokenizer.tokenize()

    assert tokens[0].token_class == TokenClass.VOWEL
    assert tokens[1].token_class == TokenClass.OTHER
    assert tokens[2].token_class == TokenClass.CONSONANT


def test_empty_string(create_test_rule):
    """Test tokenizing empty string."""
    rule = create_test_rule()
    tokenizer = Tokenizer("", rule)
    tokens = tokenizer.tokenize()
    assert tokens == []


def test_case_preservation(create_test_rule):
    """Test that original case is preserved in surface."""
    rule = create_test_rule()
    tokenizer = Tokenizer("HeLLo", rule)
    tokens = tokenizer.tokenize()

    surfaces = [t.surface for t in tokens]
    assert surfaces == ["H", "e", "L", "L", "o"]
