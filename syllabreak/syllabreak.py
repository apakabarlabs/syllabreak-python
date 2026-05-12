from __future__ import annotations

import unicodedata
from pathlib import Path

import yaml

from .language_rule import LanguageRule, MetaRule
from .word_syllabifier import WordSyllabifier


class Syllabreak:
    def __init__(self, soft_hyphen: str = "\u00ad"):
        self.soft_hyphen = soft_hyphen
        self.meta_rule = self._load_rules()

    def _load_rules(self) -> MetaRule:
        rules_file = Path(__file__).parent / "data" / "rules.yaml"
        with open(rules_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        rules = [LanguageRule(rule_data) for rule_data in data["rules"]]
        return MetaRule(rules)

    def detect_language(self, text: str) -> list[str]:
        # Detect on NFC-normalised text so precomposed letters (Polish ą,
        # deu ä, polytonic Greek ἤ …) sit in their canonical form and
        # discriminate via each rule's unique_chars set. Callers handing
        # us NFD-decomposed input get the same answer as NFC.
        matching_rules = self.meta_rule.find_matches(unicodedata.normalize("NFC", text))
        return [rule.lang for rule in matching_rules]

    def supported_languages(self) -> list[str]:
        """Codes of every language the loaded rules cover, in rule-file order."""
        return [rule.lang for rule in self.meta_rule.rules]

    def _auto_detect_rule(self, text: str) -> LanguageRule | None:
        """Auto-detect the first matching language rule for the text."""
        matching_rules = self.meta_rule.find_matches(text)
        return matching_rules[0] if matching_rules else None

    def _get_rule_by_lang(self, lang: str) -> LanguageRule:
        """Get language rule by language code."""
        for rule in self.meta_rule.rules:
            if rule.lang == lang:
                return rule
        raise ValueError(f"Language '{lang}' is not supported")

    def syllabify(self, text: str, lang: str | None = None) -> str:
        """Syllabify text by inserting soft hyphens at syllable boundaries.

        Args:
            text: Text to syllabify
            lang: Optional language code (e.g., 'eng', 'srp-latn'). If not provided, auto-detects.

        Raises:
            ValueError: If specified language is not supported
        """
        if not text:
            return text

        if lang:
            rule = self._get_rule_by_lang(lang)
        else:
            rule = self._auto_detect_rule(unicodedata.normalize("NFC", text))
            if not rule:
                return text

        # Internally we work on the NFD form so that combining marks
        # (polytonic Greek, BCMS с́, etc.) are visible as separate codepoints
        # at known positions, and rule fields (also NFD on load) match
        # consistently. The final result is renormalised to NFC so callers
        # see the canonical user-visible form.
        nfd_text = unicodedata.normalize("NFD", text)

        result = []
        i = 0
        while i < len(nfd_text):
            if not nfd_text[i].isalpha():
                result.append(nfd_text[i])
                i += 1
                continue

            word_start = i
            while i < len(nfd_text) and rule.is_word_char(nfd_text[i]):
                i += 1

            word = nfd_text[word_start:i]
            result.append(WordSyllabifier(word, rule, self.soft_hyphen).syllabify())

        return unicodedata.normalize("NFC", "".join(result))
