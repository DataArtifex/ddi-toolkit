"""Parametrized automated regression tests driven by the Harmonizer Example Bank."""

from __future__ import annotations

from pathlib import Path

import pytest

from dartfx.ddi.harmonizer import (
    CaseBankLoader,
    ExactComparator,
    HarmonizationRegistry,
    HarmonizedCategory,
    HarmonizedCode,
    HarmonizedCodeList,
    HarmonizedConcept,
    HarmonizedQuestion,
    HarmonizedVariable,
    HarmonizerTestCase,
    LevenshteinComparator,
    MatchType,
    SanitizerConfig,
    SemanticVectorComparator,
    SequenceMatcherComparator,
    TextNormalizer,
    TextSanitizer,
    WeightedAttributeComparator,
    compare_variables,
)
from dartfx.ddi.harmonizer.comparators import RuleBasedMockAgentComparator

CASES_DIR = Path(__file__).parent / "data" / "harmonizer" / "cases"
loader = CaseBankLoader(search_paths=[CASES_DIR])
ALL_CASES = loader.load_all()


def _get_comparator(name: str, threshold: float, normalizer: TextNormalizer):
    if name == "Exact":
        return ExactComparator(normalizer=normalizer)
    elif name == "Levenshtein":
        return LevenshteinComparator(normalizer=normalizer, threshold=threshold)
    elif name == "Semantic":
        return SemanticVectorComparator(threshold=threshold)
    elif name == "Agent":
        return RuleBasedMockAgentComparator()
    else:  # SequenceMatcher
        return SequenceMatcherComparator(normalizer=normalizer, threshold=threshold)


@pytest.mark.parametrize("case", ALL_CASES, ids=lambda c: c.id)
def test_harmonizer_use_case_from_bank(case: HarmonizerTestCase):
    """Executes a declarative test scenario from the Example Bank and verifies outcomes."""
    # 1. Pipeline preparation
    sanitizer = TextSanitizer(SanitizerConfig(typo_replacements=case.custom_typos))
    normalizer = TextNormalizer.from_preset(case.preset)
    normalizer.sanitizer = sanitizer
    comparator = _get_comparator(case.comparator, case.comparator_threshold, normalizer)

    # 2. Domain-specific execution
    if case.domain == "categorical":
        reg: HarmonizationRegistry[HarmonizedCategory] = HarmonizationRegistry(
            comparator=comparator,
        )
        cat_src = HarmonizedCategory(
            label=case.source_resource["label"],
            value=str(case.source_resource.get("value", "")),
            is_missing=bool(case.source_resource.get("is_missing", False)),
            urn=case.source_resource.get("urn"),
        )
        cat_cand = HarmonizedCategory(
            label=case.candidate_resource["label"],
            value=str(case.candidate_resource.get("value", "")),
            is_missing=bool(case.candidate_resource.get("is_missing", False)),
            urn=case.candidate_resource.get("urn"),
        )

        reg.register(cat_src)
        match = reg.match(cat_cand, threshold=case.comparator_threshold)

    elif case.domain == "enumerated_list":
        reg_cl: HarmonizationRegistry[HarmonizedCodeList] = HarmonizationRegistry(
            comparator=comparator,
        )
        codes_src = [
            HarmonizedCode(
                value=str(c["value"]),
                category=HarmonizedCategory(
                    label=c["label"],
                    value=str(c.get("category_value", "")),
                    is_missing=bool(c.get("is_missing", False)),
                    sentinel_type=c.get("sentinel_type"),
                    urn=c.get("category_urn") or c.get("urn"),
                ),
                is_missing_override=c.get("is_missing"),
                sentinel_type_override=c.get("sentinel_type"),
                urn=c.get("urn"),
            )
            for c in case.source_resource["codes"]
        ]
        codes_cand = [
            HarmonizedCode(
                value=str(c["value"]),
                category=HarmonizedCategory(
                    label=c["label"],
                    value=str(c.get("category_value", "")),
                    is_missing=bool(c.get("is_missing", False)),
                    sentinel_type=c.get("sentinel_type"),
                    urn=c.get("category_urn") or c.get("urn"),
                ),
                is_missing_override=c.get("is_missing"),
                sentinel_type_override=c.get("sentinel_type"),
                urn=c.get("urn"),
            )
            for c in case.candidate_resource["codes"]
        ]

        cl_src = HarmonizedCodeList(
            name=case.source_resource["name"],
            codes=codes_src,
            urn=case.source_resource.get("urn"),
        )
        cl_cand = HarmonizedCodeList(
            name=case.candidate_resource["name"],
            codes=codes_cand,
            urn=case.candidate_resource.get("urn"),
        )

        reg_cl.register(cl_src)
        match = reg_cl.match(cl_cand, threshold=case.comparator_threshold)

    elif case.domain == "question":
        q_src = HarmonizedQuestion(**case.source_resource)
        q_cand = HarmonizedQuestion(**case.candidate_resource)
        assert q_src.question_text
        assert q_cand.question_text

        # Multi-attribute comparison
        cmp = WeightedAttributeComparator(
            attribute_weights={
                "question_text": 0.65,
                "instructions": 0.15,
                "pre_question_text": 0.10,
                "intent": 0.10,
            },
            base_comparator=comparator,
            match_threshold=case.comparator_threshold,
        )
        if case.source_resource.get("urn") and case.source_resource.get("urn") == case.candidate_resource.get("urn"):
            reg_q: HarmonizationRegistry[HarmonizedQuestion] = HarmonizationRegistry(
                comparator=comparator,
            )
            reg_q.register(q_src)
            match = reg_q.match(q_cand, threshold=case.comparator_threshold)
        else:
            comp_res = cmp.compare_attributes(
                case.source_resource,
                case.candidate_resource,
            )
            match_type = comp_res.match_type
            if case.comparator == "Semantic" and comp_res.score >= case.comparator_threshold:
                match_type = MatchType.SEMANTIC_SIMILAR

            match = type(
                "QuestionMatchResult",
                (),
                {
                    "matched": comp_res.score >= case.comparator_threshold,
                    "score": comp_res.score,
                    "match_type": match_type,
                },
            )()

    elif case.domain == "conceptual":
        c_src = HarmonizedConcept(**case.source_resource)
        c_cand = HarmonizedConcept(**case.candidate_resource)
        assert c_src.preferred_label
        assert c_cand.preferred_label

        cmp_concept = WeightedAttributeComparator(
            attribute_weights={"preferred_label": 0.50, "notation": 0.20, "definition": 0.30},
            base_comparator=comparator,
            match_threshold=case.comparator_threshold,
        )
        if case.source_resource.get("urn") and case.source_resource.get("urn") == case.candidate_resource.get("urn"):
            reg_c: HarmonizationRegistry[HarmonizedConcept] = HarmonizationRegistry(
                comparator=comparator,
            )
            reg_c.register(c_src)
            match = reg_c.match(c_cand, threshold=case.comparator_threshold)
        else:
            comp_res = cmp_concept.compare_attributes(
                case.source_resource,
                case.candidate_resource,
            )
            match = type(
                "ConceptMatchResult",
                (),
                {
                    "matched": comp_res.score >= case.comparator_threshold,
                    "score": comp_res.score,
                    "match_type": comp_res.match_type,
                },
            )()
    elif case.domain == "variable":
        v_src = HarmonizedVariable.from_dict(case.source_resource)
        v_cand = HarmonizedVariable.from_dict(case.candidate_resource)
        comp_res = compare_variables(v_src, v_cand, threshold=case.comparator_threshold)
        match = type(
            "VariableMatchResult",
            (),
            {
                "matched": comp_res.score >= case.comparator_threshold,
                "score": comp_res.score,
                "match_type": comp_res.match_type,
            },
        )()
    else:
        pytest.fail(f"Unknown domain: {case.domain}")

    # 3. Assertions against expected bank criteria
    assert match.matched == case.expected_match, (
        f"Case {case.id}: expected matched={case.expected_match}, got {match.matched}"
    )
    assert match.match_type == case.expected_match_type, (
        f"Case {case.id}: expected match_type={case.expected_match_type}, got {match.match_type}"
    )
    assert case.expected_score_min <= match.score <= case.expected_score_max, (
        f"Case {case.id}: score {match.score} outside expected [{case.expected_score_min}, {case.expected_score_max}]"
    )
