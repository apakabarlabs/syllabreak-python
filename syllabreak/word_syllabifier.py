from __future__ import annotations

from .language_rule import LanguageRule
from .tokenizer import Token, TokenClass, Tokenizer


class WordSyllabifier:
    def __init__(self, word: str, rule: LanguageRule, soft_hyphen: str):
        self.original_word = word
        self.word, self.geminate_spans = rule.expand_geminate_digraphs(word)
        self.rule = rule
        self.soft_hyphen = soft_hyphen
        self.tokens = self._tokenize()
        self._reclassify_vowel_glides()
        self.nuclei = self._find_nuclei()

    def _tokenize(self) -> list[Token]:
        tokenizer = Tokenizer(self.word, self.rule)
        return tokenizer.tokenize()

    def _reclassify_vowel_glides(self) -> None:
        if not self.rule.vowel_glides:
            return
        for i, token in enumerate(self.tokens):
            if token.token_class != TokenClass.VOWEL:
                continue
            if token.surface.lower() not in self.rule.vowel_glides:
                continue
            prev = i - 1
            while prev >= 0 and self.tokens[prev].token_class == TokenClass.SEPARATOR:
                prev -= 1
            if prev >= 0 and self.tokens[prev].token_class == TokenClass.VOWEL:
                token.token_class = TokenClass.CONSONANT

    def _find_nuclei(self) -> list[int]:
        nuclei = []
        for i, token in enumerate(self.tokens):
            if token.token_class == TokenClass.VOWEL:
                nuclei.append(i)

        if nuclei and self.rule.final_semivowels:
            last_nucleus_idx = nuclei[-1]
            last_token = self.tokens[last_nucleus_idx]

            is_final = all(
                self.tokens[j].token_class in (TokenClass.SEPARATOR, TokenClass.OTHER)
                for j in range(last_nucleus_idx + 1, len(self.tokens))
            )
            if is_final and last_token.surface.lower() in self.rule.final_semivowels:
                if last_nucleus_idx > 0:
                    prev_idx = last_nucleus_idx - 1
                    if self.tokens[prev_idx].token_class == TokenClass.CONSONANT:
                        nuclei.pop()

        if self.rule.syllabic_consonants and nuclei:
            syllabic_nuclei = []
            for i, token in enumerate(self.tokens):
                if token.token_class != TokenClass.CONSONANT:
                    continue
                if token.surface.lower() not in self.rule.syllabic_consonants:
                    continue

                prev_is_consonant = (i == 0) or (self.tokens[i - 1].token_class == TokenClass.CONSONANT)
                next_is_consonant = (i == len(self.tokens) - 1) or (
                    self.tokens[i + 1].token_class == TokenClass.CONSONANT
                )
                if not (prev_is_consonant and next_is_consonant):
                    continue

                dist_to_prev_vowel: int | None = None
                for j in range(i - 1, -1, -1):
                    if self.tokens[j].token_class == TokenClass.VOWEL:
                        dist_to_prev_vowel = i - j
                        break

                dist_to_next_vowel: int | None = None
                for j in range(i + 1, len(self.tokens)):
                    if self.tokens[j].token_class == TokenClass.VOWEL:
                        dist_to_next_vowel = j - i
                        break

                has_buffer_before = dist_to_prev_vowel is None or dist_to_prev_vowel > 1
                has_buffer_after = dist_to_next_vowel is None or dist_to_next_vowel > 1
                if has_buffer_before and has_buffer_after:
                    syllabic_nuclei.append(i)

            if syllabic_nuclei:
                nuclei = sorted(set(nuclei + syllabic_nuclei))

        if nuclei:
            return nuclei

        for i, token in enumerate(self.tokens):
            if token.token_class == TokenClass.CONSONANT and token.surface.lower() in self.rule.syllabic_consonants:
                nuclei.append(i)

        return nuclei

    def _skip_separators_forward(self, start: int) -> int:
        pos = start
        while pos < len(self.tokens) and self.tokens[pos].token_class == TokenClass.SEPARATOR:
            pos += 1
        return pos

    def _skip_separators_backward(self, start: int) -> int:
        pos = start
        while pos >= 0 and self.tokens[pos].token_class == TokenClass.SEPARATOR:
            pos -= 1
        return pos

    def _extract_consonant_cluster(self, left: int, right: int) -> tuple[list[Token], list[int]]:
        cluster = []
        cluster_indices = []
        for i in range(left, right + 1):
            if self.tokens[i].token_class == TokenClass.CONSONANT:
                cluster.append(self.tokens[i])
                cluster_indices.append(i)
        return cluster, cluster_indices

    def _find_cluster_between_nuclei(self, nk: int, nk1: int) -> tuple[list[Token], list[int]]:
        left = self._skip_separators_forward(nk + 1)
        right = self._skip_separators_backward(nk1 - 1)
        return self._extract_consonant_cluster(left, right)

    def _find_separator_between(self, nk: int, nk1: int) -> int | None:
        for i in range(nk + 1, nk1):
            if self.tokens[i].token_class == TokenClass.SEPARATOR:
                return i
        return None

    def _is_valid_onset(
        self,
        consonant1: str,
        consonant2: str,
        prev_nucleus_idx: int | None = None,
        include_trailing_onsets: bool = False,
    ) -> bool:
        onset_candidate = consonant1.lower() + consonant2.lower()

        if onset_candidate in self.rule.clusters_only_after_long and prev_nucleus_idx is not None:
            if not self._is_long_nucleus(prev_nucleus_idx):
                return False

        if onset_candidate in self.rule.clusters_keep_next:
            return True
        if include_trailing_onsets and onset_candidate in self.rule.trailing_onsets:
            return True
        return False

    def _is_long_nucleus(self, nucleus_idx: int) -> bool:
        if nucleus_idx >= len(self.tokens):
            return False

        vowel_token = self.tokens[nucleus_idx]

        if vowel_token.surface.lower() in self.rule.digraph_vowels:
            return True

        if nucleus_idx + 1 < len(self.tokens):
            next_token = self.tokens[nucleus_idx + 1]

            digraph = vowel_token.surface.lower() + next_token.surface.lower()
            if digraph in self.rule.digraph_vowels:
                return True

        return False

    def _find_boundary_for_single_consonant(self, cluster_indices: list[int], nk: int, nk1: int) -> int:
        consonant_idx = cluster_indices[0]

        if self.rule.final_sequences_keep:
            sequence = "".join(t.surface.lower() for t in self.tokens[nk : nk1 + 1])
            if sequence in self.rule.final_sequences_keep:
                rest_with_vowel = "".join(t.surface.lower() for t in self.tokens[nk1:])
                rest_after_vowel = "".join(t.surface.lower() for t in self.tokens[nk1 + 1 :])

                if self.rule.suffixes_break_vre:
                    for suffix in self.rule.suffixes_break_vre:
                        if rest_with_vowel == suffix or rest_with_vowel.startswith(suffix):
                            return nk1

                is_at_end = nk1 == len(self.tokens) - 1
                has_light_suffix = False
                if self.rule.suffixes_keep_vre and rest_after_vowel:
                    has_light_suffix = rest_after_vowel in self.rule.suffixes_keep_vre

                if is_at_end or has_light_suffix:
                    return None

        return consonant_idx

    def _find_boundary_for_two_consonants(
        self, cluster: list[Token], cluster_indices: list[int], prev_nucleus_idx: int | None = None
    ) -> int:
        if self._is_valid_onset(cluster[0].surface, cluster[1].surface, prev_nucleus_idx):
            return cluster_indices[0]
        else:
            return cluster_indices[1]

    def _find_boundary_for_long_cluster(
        self, cluster: list[Token], cluster_indices: list[int], prev_nucleus_idx: int | None = None
    ) -> int:
        if len(cluster) >= 3:
            onset3 = (cluster[-3].surface + cluster[-2].surface + cluster[-1].surface).lower()
            if onset3 in self.rule.clusters_keep_next or onset3 in self.rule.trailing_onsets:
                return cluster_indices[-3]

        boundary_idx = cluster_indices[-1]
        if len(cluster) >= 2 and self._is_valid_onset(
            cluster[-2].surface, cluster[-1].surface, prev_nucleus_idx, include_trailing_onsets=True
        ):
            boundary_idx = cluster_indices[-2]

        return boundary_idx

    def _find_boundary_in_cluster(
        self, cluster: list[Token], cluster_indices: list[int], nk: int, nk1: int
    ) -> int | None:
        if len(cluster) == 0:
            if not self.rule.split_hiatus:
                return None

            are_adjacent = nk1 - nk == 1
            if not are_adjacent:
                all_separators = True
                for i in range(nk + 1, nk1):
                    if self.tokens[i].token_class != TokenClass.SEPARATOR:
                        all_separators = False
                        break
                are_adjacent = all_separators

            if are_adjacent:
                vowel_pair = self.tokens[nk].surface.lower() + self.tokens[nk1].surface.lower()
                if vowel_pair in self.rule.digraph_vowels:
                    return None

                return nk1
            return None
        elif len(cluster) == 1:
            return self._find_boundary_for_single_consonant(cluster_indices, nk, nk1)
        elif len(cluster) == 2:
            return self._find_boundary_for_two_consonants(cluster, cluster_indices, nk)
        else:
            return self._find_boundary_for_long_cluster(cluster, cluster_indices, nk)

    def _place_boundaries(self) -> list[int]:
        boundaries = []

        for k in range(len(self.nuclei) - 1):
            separator_idx = self._find_separator_between(self.nuclei[k], self.nuclei[k + 1])
            if separator_idx is not None:
                boundaries.append(separator_idx)
                continue
            cluster, cluster_indices = self._find_cluster_between_nuclei(self.nuclei[k], self.nuclei[k + 1])
            boundary = self._find_boundary_in_cluster(cluster, cluster_indices, self.nuclei[k], self.nuclei[k + 1])
            if boundary is not None:
                boundaries.append(boundary)

        return boundaries

    def syllabify(self) -> str:
        exception = self.rule.exceptions.get(self.original_word.lower())
        if exception is not None:
            return self._apply_exception(exception)

        if len(self.nuclei) < 2:
            return self.original_word

        boundaries = self._place_boundaries()
        if not boundaries:
            return self.original_word

        return self._render_with_geminate_spans(boundaries)

    def _render_with_geminate_spans(self, boundaries: list[int]) -> str:
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
        result = []
        src_idx = 0
        for ch in split_lower:
            if ch == "-":
                result.append(self.soft_hyphen)
            else:
                result.append(self.original_word[src_idx])
                src_idx += 1
        return "".join(result)
