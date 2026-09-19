import unicodedata
from dataclasses import dataclass


def _nfd(value: str) -> str:
    return unicodedata.normalize("NFD", value)


def _augment_set(values) -> set[str]:
    result: set[str] = set()
    for value in values:
        result.add(value)
        result.add(_nfd(value))
    return result


def _augment_mapping(mapping) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in mapping.items():
        result[key] = value
        result[_nfd(key)] = _nfd(value)
    return result


@dataclass(frozen=True)
class VowelNucleusRule:
    suffix: str
    vowel_offset: int
    vowel_length: int
    outcome: str
    words: frozenset[str]
    preceded_by: frozenset[str]
    preceded_by_class: str | None


class MetaRule:
    def __init__(self, rules: list):
        self.rules = rules
        self._calculate_unique_chars()
        self._link_rules_to_meta()

    def _calculate_unique_chars(self):
        for rule in self.rules:
            rule.unique_chars = rule.all_chars.copy()
            for other_rule in self.rules:
                if other_rule.lang != rule.lang:
                    rule.unique_chars -= other_rule.all_chars

    def _link_rules_to_meta(self):
        for rule in self.rules:
            rule.meta = self

    def get_all_known_chars(self) -> set[str]:
        all_chars = set()
        for rule in self.rules:
            all_chars |= rule.all_chars
        return all_chars

    def find_matches(self, text: str) -> list:
        if not text:
            return []

        clean_text = "".join(c.lower() for c in text if c.isalpha())
        if not clean_text:
            return []

        matches = []

        for rule in self.rules:
            score = rule.calculate_match_score(text)
            if score > 0:
                if rule.unique_chars and any(c in rule.unique_chars for c in clean_text):
                    score = 1.0
                matches.append((rule, score))

        matches.sort(key=lambda x: x[1], reverse=True)

        return [rule for rule, score in matches]


class LanguageRule:
    lang: str
    vowels: set[str]
    consonants: set[str]
    clusters_keep_next: set[str]
    trailing_onsets: set[str]
    dont_split_digraphs: set[str]
    digraph_vowels: set[str]
    vowel_glides: set[str]
    syllabic_consonants: set[str]
    modifiers_attach_left: set[str]
    modifiers_separators: set[str]
    clusters_only_after_long: set[str]
    split_hiatus: bool
    final_semivowels: set[str]
    final_sequences_keep: set[str]
    suffixes_break_vre: set[str]
    suffixes_keep_vre: set[str]
    vowel_nucleus_rules: tuple[VowelNucleusRule, ...]
    exceptions: dict[str, str]
    geminate_digraphs: dict[str, str]
    _all_chars: set[str]

    def __init__(self, data: dict):
        self.lang = data["lang"]
        self.vowels = set(data["vowels"])
        self.consonants = set(data["consonants"])
        self.clusters_keep_next = _augment_set(data.get("clusters_keep_next", []))

        self.trailing_onsets = _augment_set(data.get("trailing_onsets", []))
        self.dont_split_digraphs = _augment_set(data.get("dont_split_digraphs", []))
        self.digraph_vowels = _augment_set(data.get("digraph_vowels", []))

        self.vowel_glides = set(data.get("vowel_glides", ""))
        self.syllabic_consonants = set(data.get("syllabic_consonants", ""))
        self.modifiers_attach_left = set(data.get("modifiers_attach_left", ""))
        self.modifiers_separators = set(data.get("modifiers_separators", ""))
        self.clusters_only_after_long = _augment_set(data.get("clusters_only_after_long", []))
        self.split_hiatus = data.get("split_hiatus", False)
        self.final_semivowels = set(data.get("final_semivowels", ""))
        self.final_sequences_keep = _augment_set(data.get("final_sequences_keep", []))
        self.suffixes_break_vre = _augment_set(data.get("suffixes_break_vre", []))
        self.suffixes_keep_vre = _augment_set(data.get("suffixes_keep_vre", []))
        self.vowel_nucleus_rules = self._load_vowel_nucleus_rules(data.get("vowel_nucleus_rules", []))

        self.exceptions = _augment_mapping(data.get("exceptions", {}))

        self.geminate_digraphs = _augment_mapping(data.get("geminate_digraphs", {}))

        self._all_chars = self.vowels | self.consonants

    def _load_vowel_nucleus_rules(self, entries: list[dict]) -> tuple[VowelNucleusRule, ...]:
        result: list[VowelNucleusRule] = []
        for entry in entries:
            suffix = _nfd(entry["suffix"])
            vowel_offset = entry["vowel_offset"]
            vowel_length = entry.get("vowel_length", 1)
            if (
                not isinstance(vowel_offset, int)
                or not isinstance(vowel_length, int)
                or vowel_length < 1
                or not 0 <= vowel_offset < len(suffix)
                or vowel_offset + vowel_length > len(suffix)
            ):
                raise ValueError(f"invalid vowel offset for nucleus rule: {suffix}")
            if not all(char in self.vowels for char in suffix[vowel_offset : vowel_offset + vowel_length]):
                raise ValueError(f"nucleus rule target is not a vowel: {suffix}")
            outcome = entry["outcome"]
            if outcome not in {"preserve", "silent"}:
                raise ValueError(f"invalid nucleus rule outcome: {outcome}")
            words = frozenset(_nfd(value).casefold() for value in entry.get("words", []))
            preceded_by = frozenset(_nfd(value) for value in entry.get("preceded_by", []))
            if any(len(value) != 1 for value in preceded_by):
                raise ValueError(f"nucleus rule predecessor must be one character: {suffix}")
            preceded_by_class = entry.get("preceded_by_class")
            if preceded_by_class not in {None, "consonant", "vowel"}:
                raise ValueError(f"invalid nucleus rule predecessor class: {preceded_by_class}")
            result.append(
                VowelNucleusRule(
                    suffix,
                    vowel_offset,
                    vowel_length,
                    outcome,
                    words,
                    preceded_by,
                    preceded_by_class,
                )
            )
        return tuple(result)

    @property
    def all_chars(self) -> set[str]:
        return self._all_chars

    def is_vowel(self, char: str) -> bool:
        return char in self.vowels

    def is_consonant(self, char: str) -> bool:
        return char in self.consonants

    def contains_char(self, char: str) -> bool:
        return char in self._all_chars

    def expand_geminate_digraphs(self, word: str) -> tuple[str, list[tuple[int, int, str]]]:
        if not self.geminate_digraphs:
            return word, []
        patterns = sorted(self.geminate_digraphs.items(), key=lambda kv: -len(kv[0]))
        word_lower = word.lower()
        result: list[str] = []
        spans: list[tuple[int, int, str]] = []
        i = 0
        expanded_pos = 0
        while i < len(word):
            matched = False
            for short, long in patterns:
                if word_lower[i : i + len(short)] == short:
                    original_compact = word[i : i + len(short)]
                    if original_compact.isupper():
                        expansion = long.upper()
                    elif original_compact[0].isupper():
                        expansion = long[0].upper() + long[1:].lower()
                    else:
                        expansion = long
                    spans.append((expanded_pos, len(expansion), original_compact))
                    result.append(expansion)
                    expanded_pos += len(expansion)
                    i += len(short)
                    matched = True
                    break
            if not matched:
                result.append(word[i])
                expanded_pos += 1
                i += 1
        return "".join(result), spans

    def is_word_char(self, char: str) -> bool:
        if char.isalpha():
            return True
        if char in self.modifiers_attach_left:
            return True
        if char in self.modifiers_separators:
            return True

        if unicodedata.category(char) == "Mn":
            return True
        return False

    def calculate_match_score(self, text: str) -> float:
        clean_text = "".join(c.lower() for c in text if c.isalpha())
        if not clean_text:
            return 0.0

        matching = sum(1 for c in clean_text if self.contains_char(c))
        return matching / len(clean_text)
