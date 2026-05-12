import unicodedata


def _nfd(value: str) -> str:
    return unicodedata.normalize("NFD", value)


def _augment_set(values) -> set[str]:
    """Build a set with both the NFC entries from the rule and their NFD
    decompositions. Multi-character fields (digraph_vowels, clusters,
    suffix groups, ...) need this because tokenisation runs on NFD input
    and entries with precomposed letters like deu's "üh" would otherwise
    fail to match."""
    result: set[str] = set()
    for value in values:
        result.add(value)
        result.add(_nfd(value))
    return result


def _augment_mapping(mapping) -> dict[str, str]:
    """Augment a mapping with NFD-form keys (mapped to NFD-form values),
    so that exception/geminate lookups succeed whether the caller has
    handed us NFC or NFD input."""
    result: dict[str, str] = {}
    for key, value in mapping.items():
        result[key] = value
        result[_nfd(key)] = _nfd(value)
    return result


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
        """Find all matching languages for the text, sorted by score."""
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
    geminate_digraphs: dict[str, str]
    _all_chars: set[str]

    def __init__(self, data: dict):
        # Rule fields stay as the NFC entries from rules.yaml. The engine
        # normalises text to NFD only inside syllabify(), and the tokenizer
        # tolerates combining marks by:
        #   - auto-attaching any Mn codepoint to the preceding token, and
        #   - skipping Mn marks while matching multi-char digraphs so
        #     forms like ἀι (NFD: α + U+0313 + ι) still match the base
        #     "αι" digraph entry.
        # Detection runs on NFC-normalised input — Polish ą/ż, deu ä,
        # polytonic Greek ἀ/ἤ all sit precomposed and discriminate via
        # each rule's unique_chars.
        self.lang = data["lang"]
        self.vowels = set(data["vowels"])
        self.consonants = set(data["consonants"])
        self.sonorants = set(data["sonorants"])
        self.clusters_keep_next = _augment_set(data.get("clusters_keep_next", []))
        self.dont_split_digraphs = _augment_set(data.get("dont_split_digraphs", []))
        self.digraph_vowels = _augment_set(data.get("digraph_vowels", []))
        self.glides = set(data.get("glides", ""))
        self.syllabic_consonants = set(data.get("syllabic_consonants", ""))
        self.modifiers_attach_left = set(data.get("modifiers_attach_left", ""))
        self.modifiers_attach_right = set(data.get("modifiers_attach_right", ""))
        self.modifiers_separators = set(data.get("modifiers_separators", ""))
        self.clusters_only_after_long = _augment_set(data.get("clusters_only_after_long", []))
        self.split_hiatus = data.get("split_hiatus", False)
        self.final_semivowels = set(data.get("final_semivowels", ""))
        self.final_sequences_keep = _augment_set(data.get("final_sequences_keep", []))
        self.suffixes_break_vre = _augment_set(data.get("suffixes_break_vre", []))
        self.suffixes_keep_vre = _augment_set(data.get("suffixes_keep_vre", []))
        # Lowercased word -> hyphen-marked split. Used to override the algorithm
        # for individual words that escape the general rules (e.g. BCMS "dvije",
        # "prije" — graphic -ije- not from jat, see Matešić 2015 rule P11).
        self.exceptions = _augment_mapping(data.get("exceptions", {}))
        # Compact-form digraph geminates -> expanded form, applied before
        # tokenisation. Hungarian writes long double digraphs in a simplified
        # form (ssz=sz+sz, ggy=gy+gy, ...) but at a line break both halves
        # are restored in full (asz-szony, meny-nyi). Expanding here makes
        # the boundary algorithm produce the correct surface automatically.
        self.geminate_digraphs = _augment_mapping(data.get("geminate_digraphs", {}))

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

    def expand_geminate_digraphs(self, word: str) -> tuple[str, list[tuple[int, int, str]]]:
        """Expand compact-form digraph geminates (Hungarian ssz, ggy, ...).

        Returns (expanded_word, spans). Each span is (start_in_expanded,
        length_in_expanded, original_compact_text); the spans let the caller
        decide whether to render the expanded form (when a boundary falls
        inside the span — AkH 12 §226 line-break behaviour) or restore the
        compact form (when the geminate is not actually split).

        Case is preserved per match: an ALL-UPPER compact stretch expands to
        all-upper, a single-cap-prefix to title-case, otherwise lowercase.
        """
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
        """Whether a character extends a word — letter or any attaching mark."""
        if char.isalpha():
            return True
        if char in self.modifiers_attach_left:
            return True
        if char in self.modifiers_attach_right:
            return True
        if char in self.modifiers_separators:
            return True
        # Unicode nonspacing marks (Mn) always belong to the preceding letter,
        # so they extend whatever word they sit on.
        if unicodedata.category(char) == "Mn":
            return True
        return False

    def calculate_match_score(self, text: str) -> float:
        clean_text = "".join(c.lower() for c in text if c.isalpha())
        if not clean_text:
            return 0.0

        matching = sum(1 for c in clean_text if self.contains_char(c))
        return matching / len(clean_text)
