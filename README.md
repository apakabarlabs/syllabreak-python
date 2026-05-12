[![Tests](https://github.com/apakabarfm/syllabreak/actions/workflows/tests.yml/badge.svg)](https://github.com/apakabarfm/syllabreak/actions/workflows/tests.yml)

# syllabreak

Multilingual library for accurate and deterministic hyphenation and syllable counting without relying on dictionaries.

## Supported Languages

- 🇬🇧 English (`eng`)
- 🇷🇺 Russian (`rus`)
- 🇷🇸 Serbian Cyrillic (`srp-cyrl`)
- 🇷🇸 Serbian Latin (`srp-latn`)
- 🇧🇦 Bosnian (`bos`)
- 🇭🇷 Croatian (`hrv`)
- 🇲🇪 Montenegrin Latin (`cnr-latn`)
- 🇲🇪 Montenegrin Cyrillic (`cnr-cyrl`)
- 🇹🇷 Turkish (`tur`)
- 🇰🇿 Kazakh (`kaz`)
- 🇰🇬 Kyrgyz (`kir`)
- 🇬🇷 Modern Greek (`ell`)
- 🏛️ Ancient Greek (`grc`)
- 🇬🇪 Georgian (`kat`)
- 🇭🇺 Hungarian (`hun`)
- 🇩🇪 German (`deu`)
- 🇫🇷 French (`fra`)
- 🇷🇴 Romanian (`ron`)
- 🇪🇸 Spanish (`spa`)
- 🇵🇹 Portuguese (`por`)
- 🇵🇱 Polish (`pol`)
- 🇱🇻 Latvian (`lav`)
- 🇦🇲 Armenian (`hye`)
- 🇫🇮 Finnish (`fin`)
- 🇳🇱 Dutch (`nld`)
- 🇸🇪 Swedish (`swe`)
- 🇰🇪 Swahili (`swh`)
- 🏛️ Latin (`lat`)

## Why syllabification isn't trivial

A few language-specific quirks the algorithm has to encode. Each one would otherwise produce visibly wrong splits.

- **BCMS (bos, hrv, cnr)** — long-jat reflex `ije` is **one** syllable: `mli-je-ko` is wrong, `mlije-ko` is correct. Two graphic-but-not-jat exceptions are `dvije` and `prije` (Matešić 2015, rule P11). `srp-latn` does not encode `ije` because Serbian dictionaries cover both ekavian and ijekavian; pass `lang="hrv"` (or `bos`/`cnr-latn`) for ijekavian text.
- **Montenegrin** adds `ś`/`ź` (Latin) and `с́`/`з́` (Cyrillic, decomposed `с` + U+0301 only — no precomposed Unicode points exist).
- **French** — `eau` is a trigraph vowel: `châ-teau`.
- **Romanian** — final `-i` after a consonant is palatalization, not a separate syllable: `stu-denți`, not `stu-den-ți`. Adjacent vowels split into hiatus: `pri-e-teni`.
- **German** — `st` between vowels splits after a short nucleus but stays together after a long one (`stra-ße` vs `kin-der`-class cases).
- **Latin** — hiatus is mandatory: `po-e-ta`, `phi-lo-so-phi-a`.
- **Polish** — digraphs `sz`, `cz`, `rz`, `dz`, `ch` stay together inside a syllable.
- **Hungarian** — only one consonant moves to the next syllable, so even valid onset clusters split (`ab-lak`, not `a-blak`). Geminate digraphs are written compactly (`ssz`, `ggy`, `nny`, `lly`, `tty`, `ccs`, `zzs`, `ddz`, `ddzs`) and restored in full at the break per AkH 12 §226: `asszony` → `asz-szony`, `mennyi` → `meny-nyi`, `poggyász` → `pogy-gyász`.
- **Turkic Cyrillic (kaz, kir)** — strict V-CV/VC-CV: only one consonant moves to the next syllable, three-consonant clusters split 2|1. Kyrgyz long vowels (`аа`, `ээ`, `оо`, `ии`, `уу`, `өө`, `үү`) form a single nucleus: `буу-дай`, not `бу-удай`. Loanwords with foreign onset clusters fall through to the native algorithm (`Қазақстан` → `Қа-зақс-тан`, `галстук` → `галс-тук`) — fixing them would require lexical knowledge. Auto-detect caveat: a sample using only Cyrillic letters shared with Russian will detect as `rus` (it sits first in the rules); a sample with ң/ө/ү will detect as `kaz` (Kyrgyz's extras are a subset of Kazakh's). Pass `lang="kir"` explicitly for Kyrgyz.
- **Modern Greek** — V-CV; consonant clusters keep together with the following nucleus only if they form a valid Greek word-initial onset, up to length 3 (`βι-βλί-ο` with βλ, `ά-στρο` with στρ, `άν-θρω-πος` with θρ). Identical doubled consonants always split (`ελ-λη-νι-κά`, `θά-λασ-σα`). Vowel digraphs αι/ει/οι/υι/αυ/ευ/ηυ/ου (with all accent positions, e.g. `άι` in `τσάι`) are a single nucleus; consonant digraphs μπ/ντ/γκ/γγ/τζ/τσ are a single consonant (school orthographic convention). Adjacent vowels not forming a digraph split as hiatus (`λα-ός`, `α-έ-ρας`, `βι-βλί-ο`). **Synizesis** (modern phonetic merging of η/ι/υ with a following vowel after a consonant, e.g. `ά-γνοια` 2 syllables) is **not** applied — the algorithm follows the orthographic 3-syllable split `ά-γνοι-α`.
- **Ancient Greek** — same V-CV / onset principles as Modern Greek. Polytonic accents (smooth/rough breathing, acute/grave/circumflex, iota subscript) ride along their base letter automatically: the engine NFD-normalises input on entry, attaches every Unicode combining mark (Mn category) to the preceding token, and renormalises back to NFC on the way out. Differs from `ell` in two ways: μπ/ντ/γκ/γγ/τζ/τσ are NOT consonant digraphs (they were two phonemes in Classical Greek), and the vowel/consonant list enumerates the full Greek Extended block so that polytonic-marked words detect as `grc` rather than `ell`. Plain Greek without polytonic markings is ambiguous; the detector returns `ell` first as the more common modern surface.
- **Latvian** — V-CV/VC-CV with muta-cum-liquida kept (`la-brīt`). Diphthongs `ai`, `au`, `ei`, `ie`, `iu`, `oi`, `ui`, `eu`, `ou` form a single nucleus (`lie-li`, `pal-dies`, `draugs`). Note: macron vowels (`ā`, `ē`, `ī`, `ū`) are shared with Latin, so a Latvian word without a cedilla letter (`ļ`, `ķ`, `ģ`, `ņ`) cannot be reliably auto-detected — the detector keeps `lat` first.
- **Armenian** — strict V-CV/VC-CV (Oxford notes on Armenian syllabification: "Word-internally, -CC- is perceived as a natural syllable boundary"). Three-consonant clusters split CC|C by the same default long-cluster rule used for Turkic/Hungarian-style strict VC-CV languages. No `clusters_keep_next` — native phonotactics disallow CCV- onsets. ու is a single vowel digraph (`ու-սա-նող`); the ligature `և` (yev, U+0587) counts as one vowel-bearing letter (`ա-րև`). The pronounced schwa that surfaces between written consonants (`դպրոց` → [də.pə.rɔts]) is **not** orthographic and the algorithm does not insert it — words with one written vowel stay as one syllable. Glide `յ` is a consonant and never an onset privilege: `սենյակ` → `սեն-յակ`, `գիտություն` → `գի-տութ-յուն`.
- **Finnish** — strict V-CV/VC-CV per VISK §11–14 and Karlsson (1999). Long vowels (`aa ee ii oo uu yy ää öö`) and diphthongs are a single nucleus: i-diphthongs (`ai ei oi ui yi äi öi`) and u-diphthongs (`au eu iu ou ey äy iy öy`) in any position, opening diphthongs (`ie uo yö`) formally only in a root-initial syllable but treated as one nucleus everywhere (non-initial occurrences in derived forms would need lexical knowledge to disambiguate). Three or more consecutive vowels always contain a syllable boundary (`yliopisto` → `y-li-o-pis-to`). Auto-detect caveat: Finnish has no unique characters (alphabet is a subset of German's), so words without context will route to the first-matching rule (typically `eng`, or `deu` for words with `ä`/`ö`) — pass `lang="fin"` explicitly.
- **Dutch** — strict V-CV for one consonant, VC-CV for two consonants (`kas-teel`, `mees-ter`, `pis-tool`). Muta-cum-liquida (`br bl dr fr fl gr gl kr kl pr pl tr vr wr`) stays together as the onset of the next syllable (`pa-troon`, `a-tri-um`). In 3+ consonant clusters, s-onsets and the diminutive `tj` also keep with the next syllable (`ven-ster`, `ham-ster`, `in-dus-trie`, `pad-den-stoel`) — encoded via a new `trailing_onsets` field that only applies in this position so `pis-tool` (plain 2-cons "st") still splits. `ch` is a single phoneme; vowel digraphs (`aa ee oo uu ie oe eu ei ij au ou ui`) and triphthongs (`aai ooi oei eeu ieu`) are single nuclei. Hiatus marked by diaeresis (`idee-ën`, `pa-ti-ënt`). Known limitation: morpheme-boundary cases like `ab-rupt` (Latin prefix) come out as `a-brupt` because the orthographic algorithm has no morphology. Auto-detect caveat: no unique characters relative to German — pass `lang="nld"` explicitly.
- **Swedish** — `enkonsonantsprincipen` per Svenska Akademiens Ordlista: one consonant moves to the next syllable, V-CV / VC-CV (`sko-la`, `kvin-na`, `vac-ker`, `män-nis-ka`, `Hel-sing-fors`). No native vowel digraphs (vowel length is signalled by the consonant count that follows, not by doubling the vowel). The morphology-based `ordledsprincipen` for compounds (`glas-ögon`) needs lexical knowledge — the algorithm produces the orthographic `gla-sö-gon` instead. `ck` is the geminate of `k`; we produce `vac-ker` (SAOL also accepts `vack-er`). The `/ŋ/`-`ng` and `/ɧ/`-`sk/sj/skj/stj/sch` exceptions are phonetically conditioned and not encoded — we keep strict VC-CV throughout (`fis-ka` for the hard-vowel case is correct, but `vingar` comes out `vin-gar` rather than the phonological `ving-ar`, and `maskin` comes out `mas-kin` rather than `ma-skin`). Auto-detect: words containing `å` route cleanly to Swedish; words with only `ä`/`ö` collide with German/Dutch/Finnish — pass `lang="swe"` explicitly.
- **Swahili (Kiswahili)** — Bantu CV syllables, mostly open. Two systematic deviations are encoded: (a) prenasalized consonant sequences `mb nd nj ng mv nz` are a single consonant onset (`mbu-zi`, `ja-mbo`, `nde-ge`, `nyu-mba`); (b) word-initial `m` or `n` before a non-prenasalised consonant forms its own syllable (`m-to-to`, `n-chi`, `m-pi-shi`, `m-ze-e`) — handled by `syllabic_consonants: "mn"` plus a small engine relaxation that treats a word boundary as the buffer being satisfied for a syllabic consonant. `mw`/`my` are kept as a single onset token so the syllabic-m check does not fire on glide clusters (`mwa-na`, not `m-wa-na`); other `Cw`/`Cy` onsets stay together via `clusters_keep_next` (`Ki-swa-hi-li`, `bwa-na`, `kwa-he-ri`). Single-phoneme digraphs `ch sh th dh gh kh ny` are recognised. Out of scope: `ng'` with apostrophe for word-initial /ŋ/ would need treating the apostrophe as an internal modifier and recognising a 3-char digraph — rare; document and skip. Auto-detect: Swahili is plain ASCII with no unique characters; pass `lang="swh"` explicitly.
- **BCMS** — syllabic `r` between consonants is a syllable nucleus: `prst` and `krv` are one syllable, `smrt-no` splits around it.
- **Georgian** — no digraphs, sequences of consonants split unless they appear on a small whitelist of valid onsets.

For BCMS specifically, character-based auto-detect cannot tell `bos`/`hrv`/`srp-latn`/`cnr-latn` apart for text without script-unique letters — the detector returns `srp-latn` first to preserve prior behaviour. Pass `lang=` explicitly to get ijekavian handling.

## Unicode normalization

The engine accepts text in either NFC or NFD form and round-trips back to canonical NFC:

- `syllabify(text, lang)` normalises input to **NFD** internally, so combining marks (Unicode category `Mn` — accents, breathings, ogonek, iota subscript, cedilla, etc.) sit as their own codepoints. The tokenizer attaches each Mn codepoint to the preceding token automatically; while matching digraphs it can also skip over marks placed between two base letters (Greek `ἀι` = α + U+0313 + ι still matches the `αι` entry). A diaeresis (U+0308) on the closing base of a candidate digraph vetoes the match — that's the standard convention for `αϊ`, `Μαΐου`, `naïf` and similar hiatus markers. The returned string is renormalised to **NFC** before being handed back.
- `detect_language(text)` normalises input to NFC and scores it against each rule's character set. Precomposed letters discriminate well (Polish `ą`, German `ä`, polytonic Greek `ἤ`) via each rule's `unique_chars`.
- In rule files, character sets (`vowels`, `consonants`, …) hold the base letters as they appear in `rules.yaml`. Multi-character entries (`digraph_vowels`, `dont_split_digraphs`, `clusters_keep_next`, …) are stored as the union of their NFC form and their NFD decomposition, so entries with precomposed letters (deu `üh`) still match against the NFD-tokenised input. Combining marks themselves never need listing — the Mn auto-attach takes care of them.

## Out of Scope

Some writing systems do not fit syllabreak's alphabetic-rules paradigm and will not be added. They need fundamentally different algorithms:

- **Chinese (`cmn`)** — logographic; one character is already one syllable by construction. Nothing to split.
- **Japanese (`jpn`)** — kana is mora-syllabic by design; kanji cannot be syllabified without a dictionary. Belongs in a separate library.
- **Korean (`kor`)** — Hangul syllable blocks are syllables visually. Splitting is Unicode block normalization, not a vowel/consonant rule engine.
- **Arabic (`ara`)** — abjad: short vowels are optional diacritics. Syllabification is undecidable without vocalization.
- **Bengali (`ben`), Hindi (`hin`), Sanskrit (`san`)** — Brahmic abugidas. The unit is the akṣara (consonant + inherent/explicit vowel + conjuncts), which requires Unicode grapheme-cluster logic rather than a flat character table.

## Usage

### Auto-detect language

When no language is specified, the library automatically detects the most likely language:

```python
>>> from syllabreak import Syllabreak
>>> s = Syllabreak("-")
>>> s.syllabify("hello")
'hel-lo'
>>> s.syllabify("здраво")  # Serbian Cyrillic
'здра-во'
>>> s.syllabify("привет")  # Russian
'при-вет'
```

### Specify language explicitly

You can specify the language code for more predictable results:

```python
>>> s = Syllabreak("-")
>>> s.syllabify("problem", lang="eng")  # Force English rules
'pro-blem'
>>> s.syllabify("problem", lang="srp-latn")  # Force Serbian Latin rules
'prob-lem'
>>> s.syllabify("mlijeko", lang="hrv")  # Croatian ije is one syllable
'mlije-ko'
```

This is useful when:
- The text could match multiple languages
- You want consistent rules for a specific language
- Processing text in a known language

## Supported Languages (programmatic)

```python
>>> from syllabreak import Syllabreak
>>> s = Syllabreak()
>>> "hrv" in s.supported_languages()
True
```

## Language Detection

The library returns all matching languages sorted by confidence:

```python
>>> from syllabreak import Syllabreak
>>> s = Syllabreak()
>>> s.detect_language("hello")
['eng', 'srp-latn', 'tur']  # Matches English, Serbian Latin and Turkish
>>> s.detect_language("čovek")
['srp-latn', 'eng', 'tur']  # Serbian Latin has highest confidence due to č
```

## Lines of Code

<picture>
  <source media="(prefers-color-scheme: dark)" srcset=".github/loc-history-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset=".github/loc-history-light.svg">
  <img alt="Lines of Code graph" src=".github/loc-history-light.svg">
</picture>
