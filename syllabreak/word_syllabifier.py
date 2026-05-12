from __future__ import annotations

from .language_rule import LanguageRule
from .tokenizer import Token, TokenClass, Tokenizer


class WordSyllabifier:
    """Handles syllabification of a single word."""

    def __init__(self, word: str, rule: LanguageRule, soft_hyphen: str):
        self.original_word = word
        self.word, self.geminate_spans = rule.expand_geminate_digraphs(word)
        self.rule = rule
        self.soft_hyphen = soft_hyphen
        self.tokens = self._tokenize()
        self.nuclei = self._find_nuclei()

    def _tokenize(self) -> list[Token]:
        """Tokenize the word according to language rules."""
        tokenizer = Tokenizer(self.word, self.rule)
        return tokenizer.tokenize()

    def _find_nuclei(self) -> list[int]:
        """Find syllable nuclei in the token list."""
        nuclei = []
        for i, token in enumerate(self.tokens):
            if token.token_class == TokenClass.VOWEL:
                nuclei.append(i)

        # Check for final semivowels (e.g., Romanian final -i after consonant)
        # These don't form a separate syllable nucleus
        if nuclei and self.rule.final_semivowels:
            last_nucleus_idx = nuclei[-1]
            last_token = self.tokens[last_nucleus_idx]
            # Check if it's the last token (or only followed by non-letters)
            is_final = all(
                self.tokens[j].token_class in (TokenClass.SEPARATOR, TokenClass.OTHER)
                for j in range(last_nucleus_idx + 1, len(self.tokens))
            )
            if is_final and last_token.surface.lower() in self.rule.final_semivowels:
                # Check if preceded by consonant
                if last_nucleus_idx > 0:
                    prev_idx = last_nucleus_idx - 1
                    if self.tokens[prev_idx].token_class == TokenClass.CONSONANT:
                        # Remove this nucleus - it's a semivowel, not a syllable
                        nuclei.pop()

        # Check for syllabic consonants surrounded by other consonants
        # (e.g., Serbian "r" in "prljav" -> "pr-ljav")
        # Must have consonant on both sides AND have at least one consonant
        # between it and the nearest vowel on BOTH sides (not just one)
        if self.rule.syllabic_consonants and nuclei:
            syllabic_nuclei = []
            for i, token in enumerate(self.tokens):
                if token.token_class != TokenClass.CONSONANT:
                    continue
                if token.surface.lower() not in self.rule.syllabic_consonants:
                    continue
                # Check if surrounded by consonants (not adjacent to vowels)
                prev_is_consonant = (i == 0) or (self.tokens[i - 1].token_class == TokenClass.CONSONANT)
                next_is_consonant = (i == len(self.tokens) - 1) or (
                    self.tokens[i + 1].token_class == TokenClass.CONSONANT
                )
                if not (prev_is_consonant and next_is_consonant):
                    continue
                # Find distance to nearest vowel before (or word start)
                dist_to_prev_vowel = i + 1  # default: distance to word start
                for j in range(i - 1, -1, -1):
                    if self.tokens[j].token_class == TokenClass.VOWEL:
                        dist_to_prev_vowel = i - j
                        break
                # Find distance to nearest vowel after (or word end)
                dist_to_next_vowel = len(self.tokens) - i  # default: distance to word end
                for j in range(i + 1, len(self.tokens)):
                    if self.tokens[j].token_class == TokenClass.VOWEL:
                        dist_to_next_vowel = j - i
                        break
                # Syllabic consonant only if there's at least one consonant between
                # it and nearest vowel on BOTH sides (distance > 1)
                has_buffer_before = dist_to_prev_vowel > 1
                has_buffer_after = dist_to_next_vowel > 1
                if has_buffer_before and has_buffer_after:
                    syllabic_nuclei.append(i)
            # Merge syllabic consonant nuclei with vowel nuclei
            if syllabic_nuclei:
                nuclei = sorted(set(nuclei + syllabic_nuclei))

        if nuclei:
            return nuclei

        # Fallback: if no vowels at all, try syllabic consonants anywhere
        for i, token in enumerate(self.tokens):
            if token.token_class == TokenClass.CONSONANT and token.surface.lower() in self.rule.syllabic_consonants:
                nuclei.append(i)

        return nuclei

    def _skip_separators_forward(self, start: int) -> int:
        """Skip separator tokens forward from start position."""
        pos = start
        while pos < len(self.tokens) and self.tokens[pos].token_class == TokenClass.SEPARATOR:
            pos += 1
        return pos

    def _skip_separators_backward(self, start: int) -> int:
        """Skip separator tokens backward from start position."""
        pos = start
        while pos >= 0 and self.tokens[pos].token_class == TokenClass.SEPARATOR:
            pos -= 1
        return pos

    def _extract_consonant_cluster(self, left: int, right: int) -> tuple[list[Token], list[int]]:
        """Extract consonants between left and right indices."""
        cluster = []
        cluster_indices = []
        for i in range(left, right + 1):
            if self.tokens[i].token_class == TokenClass.CONSONANT:
                cluster.append(self.tokens[i])
                cluster_indices.append(i)
        return cluster, cluster_indices

    def _find_cluster_between_nuclei(self, nk: int, nk1: int) -> tuple[list[Token], list[int]]:
        """Find consonant cluster between two nuclei."""
        left = self._skip_separators_forward(nk + 1)
        right = self._skip_separators_backward(nk1 - 1)
        return self._extract_consonant_cluster(left, right)

    def _is_valid_onset(self, consonant1: str, consonant2: str, prev_nucleus_idx: int | None = None) -> bool:
        """Check if two consonants form a valid onset cluster."""
        onset_candidate = consonant1.lower() + consonant2.lower()

        # Check if this cluster requires a long vowel before it
        if onset_candidate in self.rule.clusters_only_after_long and prev_nucleus_idx is not None:
            # Check if previous nucleus is long (digraph or marked as long)
            if not self._is_long_nucleus(prev_nucleus_idx):
                return False

        return onset_candidate in self.rule.clusters_keep_next

    def _is_long_nucleus(self, nucleus_idx: int) -> bool:
        """Check if nucleus at given index is long (digraph vowel or followed by lengthening marker)."""
        if nucleus_idx >= len(self.tokens):
            return False

        # Get the vowel token
        vowel_token = self.tokens[nucleus_idx]

        # Check if this vowel token itself is already a digraph (tokenized as one unit)
        if vowel_token.surface.lower() in self.rule.digraph_vowels:
            return True

        # Check if current vowel + next character forms a digraph vowel
        if nucleus_idx + 1 < len(self.tokens):
            next_token = self.tokens[nucleus_idx + 1]
            # Build potential digraph from current vowel and next token
            digraph = vowel_token.surface.lower() + next_token.surface.lower()
            if digraph in self.rule.digraph_vowels:
                return True

        # Single vowel is considered short
        return False

    def _find_boundary_for_single_consonant(self, cluster_indices: list[int], nk: int, nk1: int) -> int:
        """V-CV: boundary before single consonant.

        Exception: Don't split V-r-e patterns (care, here, more) when:
        - At word end, OR
        - Before light suffixes (-s, -less, -ful, -ly, -ing, -ed)

        But split AFTER the consonant when followed by breaking suffixes (-ent, -ence, -ency, -ment):
        - parent -> par-ent, adherent -> ad-her-ent
        """
        consonant_idx = cluster_indices[0]

        # Check for protected sequences (like -are, -ere, -ore, -ure, -ire)
        if self.rule.final_sequences_keep:
            # Build the sequence from current vowel nucleus through next nucleus
            sequence = "".join(t.surface.lower() for t in self.tokens[nk : nk1 + 1])
            if sequence in self.rule.final_sequences_keep:
                # Get the rest of the word starting from next nucleus (includes the vowel)
                rest_with_vowel = "".join(t.surface.lower() for t in self.tokens[nk1:])
                rest_after_vowel = "".join(t.surface.lower() for t in self.tokens[nk1 + 1 :])

                # Check if followed by a breaking suffix (par-ent, ad-her-ent)
                # The suffix starts from the next vowel: "ent" in "par-ent"
                if self.rule.suffixes_break_vre:
                    for suffix in self.rule.suffixes_break_vre:
                        if rest_with_vowel == suffix or rest_with_vowel.startswith(suffix):
                            # Split after consonant = before next nucleus
                            return nk1

                # Check if at word end or followed by light suffix (care, care-less)
                is_at_end = nk1 == len(self.tokens) - 1
                has_light_suffix = False
                if self.rule.suffixes_keep_vre and rest_after_vowel:
                    has_light_suffix = rest_after_vowel in self.rule.suffixes_keep_vre

                if is_at_end or has_light_suffix:
                    # Don't split - return None to indicate no boundary
                    return None

        return consonant_idx

    def _find_boundary_for_two_consonants(
        self, cluster: list[Token], cluster_indices: list[int], prev_nucleus_idx: int | None = None
    ) -> int:
        """Determine boundary for two-consonant cluster."""
        if self._is_valid_onset(cluster[0].surface, cluster[1].surface, prev_nucleus_idx):
            return cluster_indices[0]
        else:
            return cluster_indices[1]

    def _find_boundary_for_long_cluster(
        self, cluster: list[Token], cluster_indices: list[int], prev_nucleus_idx: int | None = None
    ) -> int:
        """Determine boundary for cluster with 3+ consonants."""
        boundary_idx = cluster_indices[-1]

        if len(cluster) >= 2 and self._is_valid_onset(cluster[-2].surface, cluster[-1].surface, prev_nucleus_idx):
            boundary_idx = cluster_indices[-2]

        return boundary_idx

    def _find_boundary_in_cluster(
        self, cluster: list[Token], cluster_indices: list[int], nk: int, nk1: int
    ) -> int | None:
        """Determine where to place boundary in a consonant cluster or between vowels."""
        if len(cluster) == 0:
            # Check for vowel hiatus (adjacent vowels that form separate syllables)
            if not self.rule.split_hiatus:
                return None

            # Check if nuclei are adjacent (or only separated by modifiers/separators)
            are_adjacent = nk1 - nk == 1
            if not are_adjacent:
                # Check if there are only separators between vowels
                all_separators = True
                for i in range(nk + 1, nk1):
                    if self.tokens[i].token_class != TokenClass.SEPARATOR:
                        all_separators = False
                        break
                are_adjacent = all_separators

            if are_adjacent:
                # Check if these two vowels form a digraph (don't split)
                vowel_pair = self.tokens[nk].surface.lower() + self.tokens[nk1].surface.lower()
                if vowel_pair in self.rule.digraph_vowels:
                    return None
                # Hiatus: split between vowels
                return nk1
            return None
        elif len(cluster) == 1:
            return self._find_boundary_for_single_consonant(cluster_indices, nk, nk1)
        elif len(cluster) == 2:
            return self._find_boundary_for_two_consonants(cluster, cluster_indices, nk)
        else:
            return self._find_boundary_for_long_cluster(cluster, cluster_indices, nk)

    def _place_boundaries(self) -> list[int]:
        """Determine syllable boundaries between nuclei."""
        boundaries = []

        for k in range(len(self.nuclei) - 1):
            cluster, cluster_indices = self._find_cluster_between_nuclei(self.nuclei[k], self.nuclei[k + 1])
            boundary = self._find_boundary_in_cluster(cluster, cluster_indices, self.nuclei[k], self.nuclei[k + 1])
            if boundary is not None:
                boundaries.append(boundary)

        return boundaries

    def syllabify(self) -> str:
        """Perform syllabification and return the word with soft hyphens."""
        exception = self.rule.exceptions.get(self.original_word.lower())
        if exception is not None:
            return self._apply_exception(exception)

        # When the word doesn't actually split, hand back the original surface
        # so any geminate-digraph expansion isn't visible to the caller.
        if len(self.nuclei) < 2:
            return self.original_word

        boundaries = self._place_boundaries()
        if not boundaries:
            return self.original_word

        return self._render_with_geminate_spans(boundaries)

    def _render_with_geminate_spans(self, boundaries: list[int]) -> str:
        """Render the result, collapsing geminate expansions that don't split.

        For each geminate span produced by pre-expansion, we keep the expanded
        surface (sz, sz; gy, gy …) only when a boundary actually falls between
        its tokens. When no boundary falls inside, we substitute back the
        original compact text ('ssz', 'ggy', …) so the caller never sees a
        cosmetic expansion that wasn't earned by an actual line break.
        """
        boundary_set = set(boundaries)
        span_ranges = self._span_token_ranges()
        spans_with_internal = self._spans_containing_any_boundary(span_ranges, boundary_set)
        token_to_span = self._token_to_span_index(span_ranges)

        output: list[str] = []
        i = 0
        while i < len(self.tokens):
            s_idx = token_to_span.get(i)
            if s_idx is not None and s_idx not in spans_with_internal:
                first, last, compact = span_ranges[s_idx]
                if i == first and i in boundary_set:
                    output.append(self.soft_hyphen)
                output.append(compact)
                i = last + 1
            else:
                if i in boundary_set:
                    output.append(self.soft_hyphen)
                output.append(self.tokens[i].surface)
                i += 1
        return "".join(output)

    def _span_token_ranges(self) -> list[tuple[int, int, str]]:
        """For each geminate span, find the (first_token, last_token, compact)."""
        ranges: list[tuple[int, int, str]] = []
        for start, length, compact in self.geminate_spans:
            end = start + length
            first: int | None = None
            last: int | None = None
            for i, token in enumerate(self.tokens):
                if token.start_idx >= start and token.end_idx <= end:
                    if first is None:
                        first = i
                    last = i
            if first is not None and last is not None:
                ranges.append((first, last, compact))
        return ranges

    def _spans_containing_any_boundary(self, ranges: list[tuple[int, int, str]], boundary_set: set[int]) -> set[int]:
        result: set[int] = set()
        for s_idx, (first, last, _) in enumerate(ranges):
            for b in boundary_set:
                if first < b <= last:
                    result.add(s_idx)
                    break
        return result

    def _token_to_span_index(self, ranges: list[tuple[int, int, str]]) -> dict[int, int]:
        mapping: dict[int, int] = {}
        for s_idx, (first, last, _) in enumerate(ranges):
            for t_idx in range(first, last + 1):
                mapping[t_idx] = s_idx
        return mapping

    def _apply_exception(self, split_lower: str) -> str:
        """Render an exception's hyphen-marked lowercase split using the original case."""
        result = []
        src_idx = 0
        for ch in split_lower:
            if ch == "-":
                result.append(self.soft_hyphen)
            else:
                result.append(self.original_word[src_idx])
                src_idx += 1
        return "".join(result)
