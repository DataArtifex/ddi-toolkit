"""Harmonization Registry for indexing, deduplicating, and matching generic resources.

Generic container supporting:
- O(1) exact-match indexing by primary digest, unordered digest, or signature
- Multi-tier fuzzy matching with pluggable ContentComparators
- Curated crosswalk overrides
- Automatic escalation to HumanReviewQueue for borderline matches
"""

from __future__ import annotations

from collections.abc import Callable

from .comparators.base import ContentComparator
from .comparators.syntactic import SequenceMatcherComparator
from .models import HarmonizableResource, HarmonizationMatch, MatchType
from .review import CuratedCrosswalk, HumanReviewQueue


class HarmonizationRegistry[T: HarmonizableResource]:
    """Central registry and matching engine for harmonizable resources."""

    def __init__(
        self,
        comparator: ContentComparator | None = None,
        curated_crosswalk: CuratedCrosswalk | None = None,
        review_queue: HumanReviewQueue | None = None,
        signature_getter: Callable[[T], str] | None = None,
    ) -> None:
        """Initializes the HarmonizationRegistry.

        Args:
            comparator: Comparator used for fuzzy similarity matching. Defaults to SequenceMatcherComparator.
            curated_crosswalk: Optional explicit approved/blocked mappings.
            review_queue: Optional queue for enqueuing borderline matches.
            signature_getter: Optional extractor function for resource signature.
        """
        self.comparator = comparator or SequenceMatcherComparator()
        self.curated_crosswalk = curated_crosswalk or CuratedCrosswalk()
        self.review_queue = review_queue
        self.signature_getter = signature_getter

        # Primary indexing
        self._by_urn: dict[str, T] = {}
        self._by_digest: dict[str, T] = {}
        self._by_unordered_digest: dict[str, T] = {}
        self._by_substantive_code_set: dict[str, T] = {}
        self._by_substantive_code_seq: dict[str, T] = {}
        self._by_category_set: dict[str, T] = {}
        self._by_category_seq: dict[str, T] = {}
        self._by_signature: dict[str, T] = {}
        self._canonical_list: list[T] = []

    def __len__(self) -> int:
        return len(self._canonical_list)

    @property
    def canonical_resources(self) -> list[T]:
        """Returns all registered canonical resources in registration order."""
        return list(self._canonical_list)

    def _get_sig(self, resource: T) -> str:
        if self.signature_getter:
            return self.signature_getter(resource)
        if hasattr(resource, "signature"):
            return str(resource.signature)
        return resource.fingerprint.signature

    def match(
        self,
        candidate: T,
        threshold: float = 1.0,
    ) -> HarmonizationMatch[T]:
        """Queries registry for identifier, exact, permutation, substantive, or fuzzy matches against candidate."""
        cand_fp = candidate.fingerprint
        cand_sig = self._get_sig(candidate)
        cand_urn = getattr(candidate, "urn", None)
        cand_ident = getattr(candidate, "identifier", None)
        cand_ident_kind = cand_ident.kind.value if cand_ident else None
        cand_is_guid = cand_ident.is_random_guid if cand_ident else None

        # 1. Unique Identifier / URN Match Check (Nominal Resource Identity)
        if cand_urn and cand_urn in self._by_urn:
            canonical = self._by_urn[cand_urn]
            canon_fp = canonical.fingerprint
            canon_sig = self._get_sig(canonical)

            # Check whether content matches bit-for-bit or has drifted
            if cand_fp.digest == canon_fp.digest or cand_sig == canon_sig:
                return HarmonizationMatch(
                    matched=True,
                    canonical_resource=canonical,
                    candidate_resource=candidate,
                    score=1.0,
                    match_type=MatchType.IDENTIFIER_EXACT_CONTENT_EXACT,
                    identifier_matched=True,
                    content_matched=True,
                    identifier_kind=cand_ident_kind,
                    is_random_guid=cand_is_guid,
                    content_similarity_score=1.0,
                    reason=f"Identical identifier ('{cand_urn}') and exact content match",
                )
            else:
                comp_res = self.comparator.compare(cand_sig, canon_sig)
                return HarmonizationMatch(
                    matched=True,
                    canonical_resource=canonical,
                    candidate_resource=candidate,
                    score=comp_res.score,
                    match_type=MatchType.IDENTIFIER_EXACT_CONTENT_DRIFT,
                    identifier_matched=True,
                    content_matched=False,
                    identifier_kind=cand_ident_kind,
                    is_random_guid=cand_is_guid,
                    content_similarity_score=comp_res.score,
                    attribute_scores=comp_res.sub_scores,
                    reason=(
                        f"Identical identifier ('{cand_urn}') with content drift "
                        f"(content similarity: {comp_res.score:.1%})"
                    ),
                )

        # 2. Curated crosswalk override check
        if cand_fp.digest in self.curated_crosswalk.explicit_mappings:
            target_key = self.curated_crosswalk.explicit_mappings[cand_fp.digest]
            canonical = self._by_digest.get(target_key)
            if canonical is not None:
                canon_urn = getattr(canonical, "urn", None)
                id_matched = bool(cand_urn and canon_urn and cand_urn == canon_urn)
                return HarmonizationMatch(
                    matched=True,
                    canonical_resource=canonical,
                    candidate_resource=candidate,
                    score=1.0,
                    match_type=MatchType.HUMAN_CURATED,
                    identifier_matched=id_matched,
                    content_matched=True,
                    identifier_kind=cand_ident_kind,
                    is_random_guid=cand_is_guid,
                    reason="Matched via verified curated crosswalk override",
                )

        for canonical in self._canonical_list:
            canon_fp = canonical.fingerprint
            if self.curated_crosswalk.is_curated_match(cand_fp.digest, canon_fp.digest):
                canon_urn = getattr(canonical, "urn", None)
                id_matched = bool(cand_urn and canon_urn and cand_urn == canon_urn)
                return HarmonizationMatch(
                    matched=True,
                    canonical_resource=canonical,
                    candidate_resource=candidate,
                    score=1.0,
                    match_type=MatchType.HUMAN_CURATED,
                    identifier_matched=id_matched,
                    content_matched=True,
                    identifier_kind=cand_ident_kind,
                    is_random_guid=cand_is_guid,
                    reason="Matched via verified curated crosswalk override",
                )
            if self.curated_crosswalk.is_blocked(cand_fp.digest, canon_fp.digest):
                continue

        # 3. Exact primary digest match (O(1))
        if cand_fp.digest in self._by_digest:
            canonical = self._by_digest[cand_fp.digest]
            canon_urn = getattr(canonical, "urn", None)

            if cand_urn and canon_urn and cand_urn != canon_urn:
                match_type = MatchType.CONTENT_EXACT_DIFFERENT_IDENTIFIER
                reason = (
                    f"Exact content match with distinct identifiers (candidate: '{cand_urn}', canonical: '{canon_urn}')"
                )
                id_matched = False
            elif cand_urn and canon_urn and cand_urn == canon_urn:
                match_type = MatchType.IDENTIFIER_EXACT_CONTENT_EXACT
                reason = f"Identical identifier ('{cand_urn}') and exact content match"
                id_matched = True
            else:
                match_type = MatchType.EXACT_IDENTICAL
                reason = "Exact cryptographic digest match"
                id_matched = False

            return HarmonizationMatch(
                matched=True,
                canonical_resource=canonical,
                candidate_resource=candidate,
                score=1.0,
                match_type=match_type,
                identifier_matched=id_matched,
                content_matched=True,
                identifier_kind=cand_ident_kind,
                is_random_guid=cand_is_guid,
                content_similarity_score=1.0,
                reason=reason,
            )

        # 4. Exact signature string match (O(1))
        if cand_sig in self._by_signature:
            canonical = self._by_signature[cand_sig]
            canon_urn = getattr(canonical, "urn", None)

            if cand_urn and canon_urn and cand_urn != canon_urn:
                match_type = MatchType.CONTENT_EXACT_DIFFERENT_IDENTIFIER
                reason = (
                    f"Exact normalized content match with distinct identifiers "
                    f"(candidate: '{cand_urn}', canonical: '{canon_urn}')"
                )
                id_matched = False
            elif cand_urn and canon_urn and cand_urn == canon_urn:
                match_type = MatchType.IDENTIFIER_EXACT_CONTENT_EXACT
                reason = f"Identical identifier ('{cand_urn}') and exact normalized content match"
                id_matched = True
            else:
                match_type = MatchType.NORMALIZED_EXACT
                reason = "Exact normalized signature match"
                id_matched = False

            return HarmonizationMatch(
                matched=True,
                canonical_resource=canonical,
                candidate_resource=candidate,
                score=1.0,
                match_type=match_type,
                identifier_matched=id_matched,
                content_matched=True,
                identifier_kind=cand_ident_kind,
                is_random_guid=cand_is_guid,
                content_similarity_score=1.0,
                reason=reason,
            )

        # 5. Unordered / Permutation match (O(1)) for collections
        if cand_fp.unordered_digest and cand_fp.unordered_digest in self._by_unordered_digest:
            canonical = self._by_unordered_digest[cand_fp.unordered_digest]
            canon_urn = getattr(canonical, "urn", None)
            id_matched = bool(cand_urn and canon_urn and cand_urn == canon_urn)
            return HarmonizationMatch(
                matched=True,
                canonical_resource=canonical,
                candidate_resource=candidate,
                score=1.0,
                match_type=MatchType.PERMUTATION,
                identifier_matched=id_matched,
                content_matched=True,
                identifier_kind=cand_ident_kind,
                is_random_guid=cand_is_guid,
                reason="Order-independent set match (identical elements in different sequence)",
            )

        # 6. Substantive Core Match for collections (identical substantive items, differing sentinels)
        cand_subst_set = cand_fp.component_digests.get("substantive_code_set")
        if (
            cand_subst_set
            and cand_subst_set in self._by_substantive_code_set
            and getattr(candidate, "substantive_count", 1) > 0
        ):
            canonical = self._by_substantive_code_set[cand_subst_set]
            cand_subst_seq = cand_fp.component_digests.get("substantive_code_sequence")
            canon_subst_seq = canonical.fingerprint.component_digests.get("substantive_code_sequence")
            if cand_subst_seq and cand_subst_seq == canon_subst_seq:
                match_type = MatchType.SUBSTANTIVE_EXACT
                reason = "Substantive measurement domain matches 100% (sentinel missing schemes differ)"
            else:
                match_type = MatchType.SUBSTANTIVE_PERMUTATION
                reason = "Substantive measurement domain matches order-independently (sentinel missing schemes differ)"

            canon_urn = getattr(canonical, "urn", None)
            id_matched = bool(cand_urn and canon_urn and cand_urn == canon_urn)
            return HarmonizationMatch(
                matched=True,
                canonical_resource=canonical,
                candidate_resource=candidate,
                score=1.0,
                match_type=match_type,
                identifier_matched=id_matched,
                content_matched=False,
                identifier_kind=cand_ident_kind,
                is_random_guid=cand_is_guid,
                reason=reason,
            )

        # 7. Category Concept Set Match (Same categories/meanings, recoded code values)
        cand_cat_set = cand_fp.component_digests.get("category_set")
        if cand_cat_set and cand_cat_set in self._by_category_set and getattr(candidate, "member_count", 1) > 0:
            canonical = self._by_category_set[cand_cat_set]
            cand_cat_seq = cand_fp.component_digests.get("category_sequence")
            canon_cat_seq = canonical.fingerprint.component_digests.get("category_sequence")
            if cand_cat_seq and cand_cat_seq == canon_cat_seq:
                reason = "Identical category concepts (same semantic universe) with recoded/different code values"
            else:
                reason = "Identical category concepts in permuted order with recoded/different code values"

            canon_urn = getattr(canonical, "urn", None)
            id_matched = bool(cand_urn and canon_urn and cand_urn == canon_urn)
            return HarmonizationMatch(
                matched=True,
                canonical_resource=canonical,
                candidate_resource=candidate,
                score=1.0,
                match_type=MatchType.CATEGORIES_EXACT_CODES_DIFFERENT,
                identifier_matched=id_matched,
                content_matched=False,
                identifier_kind=cand_ident_kind,
                is_random_guid=cand_is_guid,
                content_similarity_score=1.0,
                reason=reason,
            )

        # 8. Comparator search across canonical items
        if self._canonical_list:
            best_match: T | None = None
            best_score = 0.0
            best_reason = ""
            best_sub_scores: dict[str, float] = {}
            best_match_type = MatchType.DISTINCT

            for canonical in self._canonical_list:
                canon_fp = canonical.fingerprint
                if self.curated_crosswalk.is_blocked(cand_fp.digest, canon_fp.digest):
                    continue

                res = self.comparator.compare(cand_sig, self._get_sig(canonical))
                if res.score > best_score:
                    best_score = res.score
                    best_match = canonical
                    best_reason = res.rationale
                    best_sub_scores = res.sub_scores
                    best_match_type = res.match_type

            # Check if best match meets threshold
            if best_match and best_score >= threshold:
                canon_urn = getattr(best_match, "urn", None)
                id_matched = bool(cand_urn and canon_urn and cand_urn == canon_urn)
                return HarmonizationMatch(
                    matched=True,
                    canonical_resource=best_match,
                    candidate_resource=candidate,
                    score=best_score,
                    match_type=best_match_type,
                    identifier_matched=id_matched,
                    content_matched=False,
                    identifier_kind=cand_ident_kind,
                    is_random_guid=cand_is_guid,
                    attribute_scores=best_sub_scores,
                    reason=best_reason,
                )

            # Check if borderline candidate should be enqueued for review
            if best_match and self.review_queue:
                self.review_queue.check_and_enqueue(
                    candidate=candidate,
                    canonical=best_match,
                    score=best_score,
                    reason=best_reason,
                )

        return HarmonizationMatch(
            matched=False,
            canonical_resource=None,
            candidate_resource=candidate,
            score=0.0,
            match_type=MatchType.DISTINCT,
            identifier_matched=False,
            content_matched=False,
            identifier_kind=cand_ident_kind,
            is_random_guid=cand_is_guid,
            reason="No matching canonical resource found",
        )

    def register(
        self,
        resource: T,
        threshold: float = 1.0,
    ) -> tuple[T, HarmonizationMatch[T]]:
        """Finds an existing matching canonical resource or registers a new one.

        Args:
            resource: The candidate resource to register or match.
            threshold: Minimum similarity threshold (1.0 for exact, <1.0 for fuzzy deduplication).

        Returns:
            Tuple of (canonical_resource, match_record).
        """
        match_record = self.match(resource, threshold=threshold)

        if match_record.matched and match_record.canonical_resource is not None:
            return match_record.canonical_resource, match_record

        # Register as a new canonical resource
        fp = resource.fingerprint
        sig = self._get_sig(resource)
        urn = getattr(resource, "urn", None)

        if urn:
            self._by_urn[urn] = resource
        self._by_digest[fp.digest] = resource
        if fp.unordered_digest:
            self._by_unordered_digest[fp.unordered_digest] = resource
        self._by_signature[sig] = resource

        subst_set = fp.component_digests.get("substantive_code_set")
        if subst_set and getattr(resource, "substantive_count", 1) > 0:
            self._by_substantive_code_set[subst_set] = resource
            subst_seq = fp.component_digests.get("substantive_code_sequence")
            if subst_seq:
                self._by_substantive_code_seq[subst_seq] = resource

        cat_set = fp.component_digests.get("category_set")
        if cat_set and getattr(resource, "member_count", 1) > 0:
            self._by_category_set[cat_set] = resource
            cat_seq = fp.component_digests.get("category_sequence")
            if cat_seq:
                self._by_category_seq[cat_seq] = resource

        self._canonical_list.append(resource)

        cand_ident = getattr(resource, "identifier", None)
        new_match = HarmonizationMatch(
            matched=True,
            canonical_resource=resource,
            candidate_resource=resource,
            score=1.0,
            match_type=MatchType.EXACT_IDENTICAL,
            identifier_matched=bool(urn),
            content_matched=True,
            identifier_kind=cand_ident.kind.value if cand_ident else None,
            is_random_guid=cand_ident.is_random_guid if cand_ident else None,
            reason="Registered as new canonical resource",
        )
        return resource, new_match

    def get_by_urn(self, urn: str) -> T | None:
        """Retrieves canonical resource by URN or unique identifier."""
        return self._by_urn.get(urn)

    def get_by_digest(self, digest: str) -> T | None:
        """Retrieves canonical resource by primary digest."""
        return self._by_digest.get(digest)

    def get_by_signature(self, signature: str) -> T | None:
        """Retrieves canonical resource by signature."""
        return self._by_signature.get(signature)

    def get_by_substantive_code_set(self, substantive_code_set_digest: str) -> T | None:
        """Retrieves canonical resource by substantive code set digest."""
        return self._by_substantive_code_set.get(substantive_code_set_digest)

    def get_by_category_set(self, category_set_digest: str) -> T | None:
        """Retrieves canonical resource by category set digest."""
        return self._by_category_set.get(category_set_digest)
