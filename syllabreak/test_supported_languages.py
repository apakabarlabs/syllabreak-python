from syllabreak import Syllabreak


def test_supported_languages_returns_known_codes():
    langs = Syllabreak().supported_languages()
    # Spot-check across alphabetic families so future additions don't silently
    # break the list, while leaving room for new languages.
    for code in ["eng", "rus", "srp-cyrl", "srp-latn", "bos", "hrv", "cnr-latn", "cnr-cyrl"]:
        assert code in langs, f"expected {code} in supported_languages()"


def test_supported_languages_matches_rule_order():
    s = Syllabreak()
    assert s.supported_languages() == [rule.lang for rule in s.meta_rule.rules]
