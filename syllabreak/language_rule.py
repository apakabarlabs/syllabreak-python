class MetaRule:
    """Aggregates information about all language rules and provides cross-language analysis"""

    def __init__(self, rules: list):
        self.rules = rules
        self._calculate_unique_chars()
        self._link_rules_to_meta()

    def _calculate_unique_chars(self):
        """Calculate unique characters for each language rule"""
        for rule in self.rules:
            rule.unique_chars = rule.all_chars.copy()
            for other_rule in self.rules:
                if other_rule.lang != rule.lang:
                    rule.unique_chars -= other_rule.all_chars

    def _link_rules_to_meta(self):
        """Link each rule back to this meta rule"""
        for rule in self.rules:
            rule.meta = self

    def get_all_known_chars(self) -> set[str]:
        """Get all characters from all languages"""
        all_chars = set()
        for rule in self.rules:
            all_chars |= rule.all_chars
        return all_chars

    def find_matches(self, text: str) -> list:
        """Find all matching languages for the text, sorted by score"""
        if not text:
            return []

        clean_text = "".join(c.lower() for c in text if c.isalpha())
        if not clean_text:
            return []

        matches = []

        # Calculate scores for all rules
        for rule in self.rules:
            score = rule.calculate_match_score(text)
            if score > 0:
                # Boost score if has unique characters
                if rule.unique_chars and any(c in rule.unique_chars for c in clean_text):
                    score = 1.0  # Maximum score for unique chars
                matches.append((rule, score))

        # Sort by score descending
        matches.sort(key=lambda x: x[1], reverse=True)

        return [rule for rule, score in matches]


class LanguageRule:
    """Represents syllabification rules for a specific language and script"""

    lang: str
    vowels: set[str]
    consonants: set[str]
    sonorants: set[str]
    clusters_keep_next: set[str]
    dont_split_digraphs: set[str]
    digraph_vowels: set[str]
    glides: set[str]
    syllabic_consonants: set[str]
    modifiers_attach_left: set[str]
    modifiers_attach_right: set[str]
    modifiers_separators: set[str]
    clusters_only_after_long: set[str]
    split_hiatus: bool
    final_semivowels: set[str]
    final_sequences_keep: set[str]
    suffixes_break_vre: set[str]
    suffixes_keep_vre: set[str]
    exceptions: dict[str, str]
    _all_chars: set[str]

    def __init__(self, data: dict):
        self.lang = data["lang"]
        self.vowels = set(data["vowels"])
        self.consonants = set(data["consonants"])
        self.sonorants = set(data["sonorants"])
        self.clusters_keep_next = set(data.get("clusters_keep_next", []))
        self.dont_split_digraphs = set(data.get("dont_split_digraphs", []))
        self.digraph_vowels = set(data.get("digraph_vowels", []))
        self.glides = set(data.get("glides", ""))
        self.syllabic_consonants = set(data.get("syllabic_consonants", ""))
        self.modifiers_attach_left = set(data.get("modifiers_attach_left", ""))
        self.modifiers_attach_right = set(data.get("modifiers_attach_right", ""))
        self.modifiers_separators = set(data.get("modifiers_separators", ""))
        self.clusters_only_after_long = set(data.get("clusters_only_after_long", []))
        self.split_hiatus = data.get("split_hiatus", False)
        self.final_semivowels = set(data.get("final_semivowels", ""))
        self.final_sequences_keep = set(data.get("final_sequences_keep", []))
        self.suffixes_break_vre = set(data.get("suffixes_break_vre", []))
        self.suffixes_keep_vre = set(data.get("suffixes_keep_vre", []))
        # Lowercased word -> hyphen-marked split. Used to override the algorithm
        # for individual words that escape the general rules (e.g. BCMS "dvije",
        # "prije" — graphic -ije- not from jat, see Matešić 2015 rule P11).
        self.exceptions = dict(data.get("exceptions", {}))

        self._all_chars = self.vowels | self.consonants

    @property
    def all_chars(self) -> set[str]:
        return self._all_chars

    def is_vowel(self, char: str) -> bool:
        return char in self.vowels

    def is_consonant(self, char: str) -> bool:
        return char in self.consonants

    def contains_char(self, char: str) -> bool:
        return char in self._all_chars

    def is_word_char(self, char: str) -> bool:
        """Whether a character extends a word — letter or any tokenizer-attaching mark."""
        if char.isalpha():
            return True
        if char in self.modifiers_attach_left:
            return True
        if char in self.modifiers_attach_right:
            return True
        if char in self.modifiers_separators:
            return True
        return False

    def calculate_match_score(self, text: str) -> float:
        clean_text = "".join(c.lower() for c in text if c.isalpha())
        if not clean_text:
            return 0.0

        matching = sum(1 for c in clean_text if self.contains_char(c))
        return matching / len(clean_text)
