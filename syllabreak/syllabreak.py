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
        matching_rules = self.meta_rule.find_matches(text)
        return [rule.lang for rule in matching_rules]

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
            rule = self._auto_detect_rule(text)
            if not rule:
                return text

        # Process each word
        result = []
        i = 0

        while i < len(text):
            # Find word boundaries
            if not text[i].isalpha():
                result.append(text[i])
                i += 1
                continue

            # Found start of word — word continues across letters and any
            # tokenizer-attaching marks declared by the rule (e.g. combining
            # acute U+0301 used by Montenegrin Cyrillic с́, з́).
            word_start = i
            while i < len(text) and rule.is_word_char(text[i]):
                i += 1

            word = text[word_start:i]
            result.append(WordSyllabifier(word, rule, self.soft_hyphen).syllabify())

        return "".join(result)
