"""Comprehensive unit tests for generic, domain-agnostic resource harmonization framework."""

from __future__ import annotations

from dartfx.ddi.harmonizer import (
    AgentDecision,
    Category,
    Code,
    CodeList,
    Concept,
    CuratedCrosswalk,
    DataType,
    ExactComparator,
    HarmonizationRegistry,
    HumanReviewQueue,
    IdentifierKind,
    LevenshteinComparator,
    MatchType,
    NormalizationPreset,
    Question,
    QuestionComparator,
    ResourceFingerprinter,
    RuleBasedMockAgentComparator,
    SanitizerConfig,
    SemanticVectorComparator,
    SentinelType,
    SequenceMatcherComparator,
    TextNormalizer,
    TextSanitizer,
    TokenJaccardComparator,
    ValueDomain,
    Variable,
    WeightedAttributeComparator,
    compare_codelists,
    compare_questions,
    compare_resources,
    compare_variables,
    parse_identifier,
)

# =============================================================================
# 1. Text Sanitizer Tests
# =============================================================================


def test_sanitizer_html_and_entities():
    sanitizer = TextSanitizer()
    raw = "<p>Hello <b>World</b> &amp; &quot;Friends&quot;!</p>"
    clean = sanitizer.sanitize(raw)
    assert clean == 'Hello World & "Friends"!'


def test_sanitizer_smart_punctuation():
    sanitizer = TextSanitizer()
    raw = "“Smart quotes” and ‘single’ with em—dash and en–dash"
    clean = sanitizer.sanitize(raw)
    assert clean == "\"Smart quotes\" and 'single' with em-dash and en-dash"


def test_sanitizer_control_characters():
    sanitizer = TextSanitizer()
    raw = "Text with \x00null and \x07bell chars"
    clean = sanitizer.sanitize(raw)
    assert clean == "Text with null and bell chars"


def test_sanitizer_typo_replacement():
    config = SanitizerConfig(typo_replacements={"fequency": "frequency", "teh": "the"})
    sanitizer = TextSanitizer(config)
    raw = "Check teh fequency of this variable"
    clean = sanitizer.sanitize(raw)
    assert clean == "Check the frequency of this variable"


# =============================================================================
# 2. Text Normalizer Tests
# =============================================================================


def test_normalizer_deaccenting():
    normalizer = TextNormalizer()
    # French, Spanish, German accents
    raw = "Élève à l'école, café crème, señor, Über"
    norm = normalizer.normalize(raw)
    assert norm == "eleve a l'ecole, cafe creme, senor, uber"


def test_normalizer_casefolding():
    normalizer = TextNormalizer()
    # German Eszett ß -> ss under casefold
    assert normalizer.normalize("GROß") == "gross"
    assert normalizer.normalize("Straße") == "strasse"


def test_normalizer_whitespace_collapsing():
    normalizer = TextNormalizer()
    raw = "   Multiple   spaces \t and \n newlines   "
    assert normalizer.normalize(raw) == "multiple spaces and newlines"


def test_normalizer_presets():
    strict = TextNormalizer.from_preset(NormalizationPreset.STRICT)
    aggressive = TextNormalizer.from_preset(NormalizationPreset.AGGRESSIVE)

    raw = "  Héllo,   World!  "
    # STRICT keeps accents and casing
    assert strict.normalize(raw) == "Héllo,   World!"
    # AGGRESSIVE removes punctuation, accents, and casefolds
    assert aggressive.normalize(raw) == "hello world"


def test_normalizer_token_and_signature():
    normalizer = TextNormalizer()
    sig = normalizer.create_signature("  Survey Question 101  ", digest_length=16)
    assert sig.normalized_text == "survey question 101"
    assert sig.tokens == ["survey", "question", "101"]
    assert len(sig.digest) == 16


# =============================================================================
# 3. Fingerprinter Tests (Atomic & Merkle Trees)
# =============================================================================


def test_fingerprinter_atomic():
    fingerprinter = ResourceFingerprinter(default_digest_length=16)
    fp1 = fingerprinter.fingerprint_atomic("Female")
    fp2 = fingerprinter.fingerprint_atomic("  FEMALE  ")
    assert fp1.digest == fp2.digest
    assert len(fp1.digest) == 16


def test_fingerprinter_ordered_sequence():
    fingerprinter = ResourceFingerprinter()
    digests_a = ["a1b2", "c3d4", "e5f6"]
    digests_b = ["e5f6", "c3d4", "a1b2"]

    hash_ordered_a = fingerprinter.fingerprint_ordered_sequence(digests_a)
    hash_ordered_b = fingerprinter.fingerprint_ordered_sequence(digests_b)
    # Different order must yield different ordered hash
    assert hash_ordered_a != hash_ordered_b


def test_fingerprinter_unordered_set():
    fingerprinter = ResourceFingerprinter()
    digests_a = ["a1b2", "c3d4", "e5f6"]
    digests_b = ["e5f6", "c3d4", "a1b2"]

    hash_set_a = fingerprinter.fingerprint_unordered_set(digests_a)
    hash_set_b = fingerprinter.fingerprint_unordered_set(digests_b)
    # Different order of same set MUST yield identical unordered hash
    assert hash_set_a == hash_set_b


def test_fingerprinter_compound():
    fingerprinter = ResourceFingerprinter()
    comp_a = {"title": "income", "desc": "monthly total"}
    comp_b = {"desc": "monthly total", "title": "income"}

    fp_a = fingerprinter.fingerprint_compound(comp_a)
    fp_b = fingerprinter.fingerprint_compound(comp_b)
    # Component order in dict shouldn't change compound digest
    assert fp_a.digest == fp_b.digest


# =============================================================================
# 4. Content Comparators Tests
# =============================================================================


def test_exact_comparator():
    cmp = ExactComparator()
    assert cmp.compare("Yes", "Yes").match_type == MatchType.EXACT_IDENTICAL
    assert cmp.compare("Yes", " yes ").match_type == MatchType.NORMALIZED_EXACT
    assert cmp.compare("Yes", "No").match_type == MatchType.DISTINCT


def test_sequence_matcher_comparator():
    cmp = SequenceMatcherComparator(threshold=0.80)
    res = cmp.compare("Employment Status", "Employmnt Sttus")
    assert res.score > 0.85
    assert res.match_type == MatchType.SYNTACTIC_SIMILAR


def test_levenshtein_comparator():
    cmp = LevenshteinComparator(threshold=0.80)
    res = cmp.compare("Household head", "Household heed")
    assert res.score >= 0.90
    assert res.sub_scores["edit_distance"] == 1.0


def test_token_jaccard_comparator():
    cmp = TokenJaccardComparator(threshold=0.70)
    # Word re-ordering: Jaccard is 1.0
    res = cmp.compare("Age of respondent", "Respondent age")
    assert res.score >= 0.66
    assert res.sub_scores["shared_tokens"] == 2.0


def test_semantic_vector_comparator():
    cmp = SemanticVectorComparator(threshold=0.75)
    res = cmp.compare(
        "Total household monthly income",
        "Monthly household total income",
    )
    assert res.score >= 0.85
    assert res.match_type == MatchType.SEMANTIC_SIMILAR


def test_mock_agent_comparator():
    agent = RuleBasedMockAgentComparator()
    res = agent.evaluate("Did you consult a doctor?", "Did you consult a medical doctor?")
    assert res.decision in (AgentDecision.MATCH, AgentDecision.BORDERLINE)
    assert res.confidence >= 0.75
    assert "doctor" in res.reasoning.lower()


def test_weighted_attribute_comparator():
    cmp = WeightedAttributeComparator(
        attribute_weights={"text": 0.70, "instructions": 0.30},
        match_threshold=0.85,
    )
    s = {"text": "Do you own a car?", "instructions": "Mark one."}
    t = {"text": "Do you own a car?", "instructions": "Select one."}
    res = cmp.compare_attributes(s, t)
    assert res.score >= 0.85
    assert res.sub_scores["text"] == 1.0

    # 1. Attributes unpopulated (empty string or None) in both resources are ignored
    s_sparse = {"text": "Total monthly household income before taxes", "instructions": "", "pre": None}
    t_sparse = {"text": "Total monthly household income before taxes", "instructions": None, "pre": ""}
    res_sparse = cmp.compare_attributes(s_sparse, t_sparse)
    assert res_sparse.score == 1.0
    assert "instructions" not in res_sparse.sub_scores
    assert "pre" not in res_sparse.sub_scores

    # 2. Attribute present in one but missing in other represents discrepancy and is penalized
    s_mixed = {"text": "Do you own a car?", "instructions": "Mark one."}
    t_mixed = {"text": "Do you own a car?", "instructions": ""}
    res_mixed = cmp.compare_attributes(s_mixed, t_mixed)
    assert res_mixed.sub_scores["text"] == 1.0
    assert res_mixed.sub_scores["instructions"] == 0.0
    assert res_mixed.score == 0.70


# =============================================================================
# 5. Domain Models Tests
# =============================================================================


def test_category_and_code():
    cat1 = Category(label="Strongly Agree", value="1", is_missing=False)
    assert cat1.signature == "val=1|label=Strongly Agree|missing=False"
    assert len(cat1.category_hash) == 16

    code1 = Code(value="1", category=cat1)
    assert code1.code == "1"
    assert code1.value_label == "1: Strongly Agree"
    assert code1.signature == "1=Strongly Agree"
    assert len(code1.code_digest) == 16
    assert len(code1.category_digest) == 16
    assert len(code1.item_digest) == 16
    assert len(code1.fingerprint.digest) == 16


def test_codelist():
    c1 = Code(value="1", category=Category(label="Yes", value="1"))
    c2 = Code(value="2", category=Category(label="No", value="2"))

    cl1 = CodeList(name="CL_YESNO", codes=[c1, c2])
    cl2 = CodeList(name="CL_NOYES", codes=[c2, c1])

    assert cl1.member_count == 2
    assert cl1.signature == "1=Yes;2=No"
    # Ordered sequence digests must differ because codes are inverted
    assert cl1.code_sequence_digest != cl2.code_sequence_digest
    assert cl1.category_sequence_digest != cl2.category_sequence_digest
    assert cl1.value_sequence_digest != cl2.value_sequence_digest

    # Unordered set digests must match because both lists contain the identical items, categories, and values
    assert cl1.code_set_digest == cl2.code_set_digest
    assert cl1.category_set_digest == cl2.category_set_digest
    assert cl1.value_set_digest == cl2.value_set_digest

    assert "code_set" in cl1.fingerprint.component_digests
    assert "category_set" in cl1.fingerprint.component_digests
    assert "value_set" in cl1.fingerprint.component_digests


def test_question():
    q = Question(
        pre_question_text="Thinking about the last 12 months:",
        question_text="Did you visit a physician?",
        post_question_text="Thank you.",
        instructions="Show card 4.",
        intent="Measure access to healthcare",
    )
    fp = q.fingerprint
    assert len(fp.digest) == 16
    assert "pre" in fp.component_digests
    assert "literal" in fp.component_digests
    assert "post" in fp.component_digests
    assert "instructions" in fp.component_digests
    assert "intent" in fp.component_digests


def test_concept():
    concept = Concept(
        preferred_label="Gross Domestic Product",
        definition="Monetary measure of market value of goods produced",
        notation="GDP",
    )
    assert len(concept.concept_hash) == 16
    assert "label" in concept.fingerprint.component_digests
    assert "notation" in concept.fingerprint.component_digests


# =============================================================================
# 6. Harmonization Registry Tests
# =============================================================================


def test_registry_category_deduplication():
    reg: HarmonizationRegistry[Category] = HarmonizationRegistry()

    cat1 = Category(label="Female", value="2", is_missing=False)
    cat2 = Category(label="Female", value="2", is_missing=False)
    cat3 = Category(label="Male", value="1", is_missing=False)

    canon1, match1 = reg.register(cat1)
    assert match1.matched
    assert len(reg) == 1

    canon2, match2 = reg.register(cat2)
    assert canon2 is canon1
    assert match2.matched
    assert match2.score == 1.0
    assert len(reg) == 1  # Deduplicated!

    canon3, match3 = reg.register(cat3)
    assert canon3 is cat3
    assert len(reg) == 2


def test_registry_codelist_permutation():
    reg: HarmonizationRegistry[CodeList] = HarmonizationRegistry()

    c_yes = Code(value="1", category=Category(label="Yes", value="1"))
    c_no = Code(value="2", category=Category(label="No", value="2"))

    cl_ordered = CodeList(name="CL_1", codes=[c_yes, c_no])
    cl_permuted = CodeList(name="CL_2", codes=[c_no, c_yes])

    reg.register(cl_ordered)
    assert len(reg) == 1

    # Permuted match should be detected via unordered_digest
    match = reg.match(cl_permuted)
    assert match.matched
    assert match.match_type == MatchType.PERMUTATION
    assert match.canonical_resource is cl_ordered


def test_registry_curated_crosswalk():
    crosswalk = CuratedCrosswalk(
        explicit_mappings={"cand_hash_99": "canon_hash_1"},
    )
    reg: HarmonizationRegistry[Category] = HarmonizationRegistry(curated_crosswalk=crosswalk)

    cat_canon = Category(label="Unknown", value="99")
    reg._by_digest["canon_hash_1"] = cat_canon
    reg._canonical_list.append(cat_canon)

    cat_cand = Category(label="Don't Know", value="88")
    reg.curated_crosswalk.explicit_mappings[cat_cand.fingerprint.digest] = "canon_hash_1"
    match = reg.match(cat_cand)
    assert match.matched is True
    assert match.canonical_resource is cat_canon


def test_registry_review_queue():
    queue = HumanReviewQueue(borderline_range=(0.70, 0.90))
    reg: HarmonizationRegistry[Category] = HarmonizationRegistry(
        comparator=SequenceMatcherComparator(),
        review_queue=queue,
    )

    cat1 = Category(label="Strongly Agree", value="1")
    reg.register(cat1)

    # Slightly similar candidate below threshold 0.95
    cat_cand = Category(label="Somewhat Agree", value="1")
    match = reg.match(cat_cand, threshold=0.95)
    assert not match.matched
    # Should have been added to the review queue
    assert queue.pending_count == 1
    assert queue.items[0].candidate == cat_cand


def test_sentinel_types_and_flags():
    cat_subst = Category(label="Employed full-time", value="1", is_missing=False)
    assert cat_subst.is_substantive is True
    assert cat_subst.sentinel_type is None

    cat_sentinel = Category(
        label="Refused / No Answer",
        value="99",
        is_missing=True,
        sentinel_type=SentinelType.REFUSED,
        flags={"obs_status": "M", "source": "census"},
    )
    assert cat_sentinel.is_substantive is False
    assert cat_sentinel.is_missing is True
    assert cat_sentinel.sentinel_type == SentinelType.REFUSED
    assert cat_sentinel.flags["obs_status"] == "M"

    code_item = Code(
        value="99",
        category=cat_sentinel,
        flags={"user_missing": True},
    )
    assert code_item.is_missing is True
    assert code_item.sentinel_type == SentinelType.REFUSED
    assert code_item.flags["user_missing"] is True

    # Test TOP_CODED and BOTTOM_CODED semi-missing / threshold sentinels
    cat_top = Category(label="90 years or older", value="90", is_missing=True, sentinel_type=SentinelType.TOP_CODED)
    cat_bottom = Category(label="Under 18 years", value="0", is_missing=True, sentinel_type=SentinelType.BOTTOM_CODED)
    assert cat_top.sentinel_type == SentinelType.TOP_CODED
    assert cat_bottom.sentinel_type == SentinelType.BOTTOM_CODED


def test_codelist_substantive_partitioning_and_matching():
    # Survey A: Substantive 1=Male, 2=Female | Missing: 98=DK, 99=Refused
    c_m_a = Code(value="1", category=Category(label="Male", value="1"))
    c_f_a = Code(value="2", category=Category(label="Female", value="2"))
    c_dk_a = Code(
        value="98",
        category=Category(label="Don't Know", value="98", is_missing=True, sentinel_type=SentinelType.DONT_KNOW),
    )
    c_ref_a = Code(
        value="99",
        category=Category(label="Refused", value="99", is_missing=True, sentinel_type=SentinelType.REFUSED),
    )
    cl_a = CodeList(name="CL_GENDER_A", codes=[c_m_a, c_f_a, c_dk_a, c_ref_a])

    assert cl_a.substantive_count == 2
    assert cl_a.sentinel_count == 2
    assert len(cl_a.substantive_items) == 2
    assert len(cl_a.sentinel_items) == 2

    # Survey B: Substantive 1=Male, 2=Female | Missing: 8=DK, 9=Refused (different missing notation scheme)
    c_m_b = Code(value="1", category=Category(label="Male", value="1"))
    c_f_b = Code(value="2", category=Category(label="Female", value="2"))
    c_dk_b = Code(
        value="8",
        category=Category(label="Don't Know", value="8", is_missing=True, sentinel_type=SentinelType.DONT_KNOW),
    )
    c_ref_b = Code(
        value="9",
        category=Category(label="Refused", value="9", is_missing=True, sentinel_type=SentinelType.REFUSED),
    )
    cl_b = CodeList(name="CL_GENDER_B", codes=[c_m_b, c_f_b, c_dk_b, c_ref_b])

    # Substantive code sets and category sets must match 100%
    assert cl_a.substantive_code_set_digest == cl_b.substantive_code_set_digest
    assert cl_a.substantive_category_set_digest == cl_b.substantive_category_set_digest
    # Full code sets must differ because 98/99 != 8/9
    assert cl_a.code_set_digest != cl_b.code_set_digest

    reg: HarmonizationRegistry[CodeList] = HarmonizationRegistry()
    reg.register(cl_a)

    match = reg.match(cl_b)
    assert match.matched is True
    assert match.match_type == MatchType.SUBSTANTIVE_EXACT
    assert match.canonical_resource is cl_a


# =============================================================================
# 11. URN / PID / Identifier Classification & Matching Tests
# =============================================================================


def test_identifier_parsing_and_classification():
    # 1. Semantic DDI URN
    ddi_id = parse_identifier("urn:ddi:us.mpc:CL_SEX:1.0.0")
    assert ddi_id is not None
    assert ddi_id.kind == IdentifierKind.SEMANTIC_URN
    assert ddi_id.is_random_guid is False
    assert ddi_id.is_assigned is True
    assert ddi_id.agency == "us.mpc"
    assert ddi_id.resource_id == "CL_SEX"
    assert ddi_id.version == "1.0.0"

    # 2. Semantic SDMX URN
    sdmx_id = parse_identifier("urn:sdmx:org.sdmx.infomodel.codelist.Codelist=ESTAT:CL_SEX(1.0)")
    assert sdmx_id is not None
    assert sdmx_id.kind == IdentifierKind.SEMANTIC_URN
    assert sdmx_id.agency == "ESTAT"
    assert sdmx_id.resource_id == "CL_SEX"
    assert sdmx_id.version == "1.0"

    # 3. DOI Persistent Identifier
    doi_id = parse_identifier("doi:10.1234/data.5678")
    assert doi_id is not None
    assert doi_id.kind == IdentifierKind.DOI
    assert doi_id.is_random_guid is False
    assert doi_id.is_assigned is True
    assert doi_id.resource_id == "10.1234/data.5678"

    # 4. Web URI / URL
    uri_id = parse_identifier("https://id.loc.gov/authorities/subjects/sh85000001")
    assert uri_id is not None
    assert uri_id.kind == IdentifierKind.URI_URL
    assert uri_id.is_assigned is True
    assert uri_id.is_random_guid is False

    # 5. Random / Synthetic GUIDs & UUIDs
    uuid_raw = parse_identifier("9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d")
    assert uuid_raw is not None
    assert uuid_raw.kind == IdentifierKind.RANDOM_GUID
    assert uuid_raw.is_random_guid is True
    assert uuid_raw.is_assigned is False

    uuid_urn = parse_identifier("urn:uuid:6ba7b810-9dad-11d1-80b4-00c04fd430c8")
    assert uuid_urn is not None
    assert uuid_urn.kind == IdentifierKind.RANDOM_GUID
    assert uuid_urn.is_random_guid is True
    assert uuid_urn.is_assigned is False

    uuid_hex = parse_identifier("e026194b6d4b4a189f7f453a9e7161b3")
    assert uuid_hex is not None
    assert uuid_hex.kind == IdentifierKind.RANDOM_GUID
    assert uuid_hex.is_random_guid is True

    # 6. Local Mnemonic Key
    local_id = parse_identifier("CL_SEX_2020")
    assert local_id is not None
    assert local_id.kind == IdentifierKind.LOCAL_KEY
    assert local_id.is_assigned is True
    assert local_id.is_random_guid is False

    # 7. None or empty string
    assert parse_identifier(None) is None
    assert parse_identifier("") is None
    assert parse_identifier("   ") is None


def test_registry_urn_match_exact_content():
    """Identical URN + 100% identical content -> IDENTIFIER_EXACT_CONTENT_EXACT."""
    urn = "urn:ddi:us.census:CL_SEX:1.0"
    codes = [
        Code(value="1", category=Category(label="Male", value="1")),
        Code(value="2", category=Category(label="Female", value="2")),
    ]
    canonical = CodeList(name="CL_SEX_CANON", urn=urn, codes=codes)
    candidate = CodeList(name="CL_SEX_CAND", urn=urn, codes=codes)

    reg: HarmonizationRegistry[CodeList] = HarmonizationRegistry()
    reg.register(canonical)

    match = reg.match(candidate)
    assert match.matched is True
    assert match.match_type == MatchType.IDENTIFIER_EXACT_CONTENT_EXACT
    assert match.identifier_matched is True
    assert match.content_matched is True
    assert match.score == 1.0
    assert match.canonical_resource is canonical
    assert match.identifier_kind == IdentifierKind.SEMANTIC_URN
    assert match.is_random_guid is False


def test_registry_urn_match_content_drift():
    """Identical URN + modified/translated content -> IDENTIFIER_EXACT_CONTENT_DRIFT."""
    urn = "urn:ddi:us.census:Q101:1.0"
    canonical = Question(
        question_text="What is your current employment status?",
        instructions="Read all response options out loud to respondent.",
        urn=urn,
    )
    # Same URN in candidate, but instructions modified for self-administered web mode
    candidate = Question(
        question_text="What is your current employment status?",
        instructions="Please select one option that best describes your situation.",
        urn=urn,
    )

    reg: HarmonizationRegistry[Question] = HarmonizationRegistry()
    reg.register(canonical)

    match = reg.match(candidate)
    assert match.matched is True
    assert match.match_type == MatchType.IDENTIFIER_EXACT_CONTENT_DRIFT
    assert match.identifier_matched is True
    assert match.content_matched is False
    assert match.canonical_resource is canonical
    assert match.score < 1.0  # Content similarity reflects the modification
    assert match.score > 0.0
    assert match.content_similarity_score == match.score
    assert "content drift" in match.reason.lower()


def test_registry_content_exact_different_identifiers():
    """Different URNs + 100% identical content -> CONTENT_EXACT_DIFFERENT_IDENTIFIER."""
    codes = [
        Code(value="1", category=Category(label="Male", value="1")),
        Code(value="2", category=Category(label="Female", value="2")),
    ]
    canonical = CodeList(
        name="CL_SEX_US",
        urn="urn:ddi:us.mpc:CL_SEX:2020",
        codes=codes,
    )
    candidate = CodeList(
        name="CL_SEX_UK",
        urn="urn:ddi:uk.data:CL_GENDER:2021",
        codes=codes,
    )

    reg: HarmonizationRegistry[CodeList] = HarmonizationRegistry()
    reg.register(canonical)

    match = reg.match(candidate)
    assert match.matched is True
    assert match.match_type == MatchType.CONTENT_EXACT_DIFFERENT_IDENTIFIER
    assert match.identifier_matched is False
    assert match.content_matched is True
    assert match.score == 1.0
    assert match.canonical_resource is canonical


def test_resource_guid_vs_assigned_urn_properties():
    # Resource with random GUID
    guid_str = "f47ac10b-58cc-4372-a567-0e02b2c3d479"
    cat_guid = Category(label="Sample Category", value="1", urn=guid_str)
    assert cat_guid.is_random_guid is True
    assert cat_guid.is_assigned_identifier is False
    assert cat_guid.identifier is not None
    assert cat_guid.identifier.kind == IdentifierKind.RANDOM_GUID

    # Resource with assigned DDI URN
    urn_str = "urn:ddi:org.example:CAT_1:1.0"
    cat_urn = Category(label="Sample Category", value="1", urn=urn_str)
    assert cat_urn.is_random_guid is False
    assert cat_urn.is_assigned_identifier is True
    assert cat_urn.identifier is not None
    assert cat_urn.identifier.kind == IdentifierKind.SEMANTIC_URN


def test_country_codelist_alpha2_vs_numeric3_harmonization():
    """Verifies that ISO 2-letter alpha and 3-digit numeric country lists share 100% category digests."""
    countries = [
        ("CA", "124", "Canada"),
        ("DE", "276", "Germany"),
        ("FR", "250", "France"),
        ("GB", "826", "United Kingdom"),
        ("JP", "392", "Japan"),
        ("MX", "484", "Mexico"),
        ("US", "840", "United States"),
    ]

    codes_alpha = [Code(value=alpha, category=Category(label=name)) for alpha, _, name in countries]
    codes_numeric = [Code(value=num, category=Category(label=name)) for _, num, name in countries]

    cl_alpha = CodeList(name="CL_COUNTRY_G7_ALPHA2", codes=codes_alpha)
    cl_numeric = CodeList(name="CL_COUNTRY_G7_NUMERIC3", codes=codes_numeric)

    # 1. Semantic category set and sequence digests match 100%
    assert cl_alpha.category_set_digest == cl_numeric.category_set_digest
    assert cl_alpha.category_sequence_digest == cl_numeric.category_sequence_digest
    assert cl_alpha.substantive_category_set_digest == cl_numeric.substantive_category_set_digest

    # 2. Literal code value digests and item bindings diverge
    assert cl_alpha.value_set_digest != cl_numeric.value_set_digest
    assert cl_alpha.code_set_digest != cl_numeric.code_set_digest
    assert cl_alpha.fingerprint.digest != cl_numeric.fingerprint.digest

    # 3. Registry exact category concept match (O(1) category set indexing)
    reg: HarmonizationRegistry[CodeList] = HarmonizationRegistry(comparator=SequenceMatcherComparator(threshold=0.75))
    reg.register(cl_alpha)
    match = reg.match(cl_numeric, threshold=0.75)

    assert match.matched is True
    assert match.match_type == MatchType.CATEGORIES_EXACT_CODES_DIFFERENT
    assert match.score == 1.0
    assert match.content_matched is False
    assert match.canonical_resource is cl_alpha
    assert reg.get_by_category_set(cl_numeric.category_set_digest) is cl_alpha


# =============================================================================
# 11. Pairwise Resource Comparison Tests (Direct Two-Resource Comparison)
# =============================================================================


def test_compare_questions_exact():
    """Verifies that identical questions return EXACT_IDENTICAL (1.0)."""
    q1 = Question(
        question_text="What is your current employment status?",
        instructions="Show Card 4.",
    )
    q2 = Question(
        question_text="What is your current employment status?",
        instructions="Show Card 4.",
    )
    res = compare_questions(q1, q2)
    assert res.score == 1.0
    assert res.match_type == MatchType.EXACT_IDENTICAL


def test_compare_questions_partial_instruction_drift():
    """Verifies pairwise comparison when prompt matches but instructions vary across survey waves."""
    q_wave1 = Question(
        question_text="Did you consult a medical doctor or specialist?",
        instructions="Show Card C to respondent.",
        pre_question_text="During the last 12 months:",
    )
    q_wave2 = Question(
        question_text="Did you consult a medical doctor or specialist?",
        instructions="Select one option on the screen.",
        pre_question_text="During the last 12 months:",
    )
    res = compare_questions(q_wave1, q_wave2, threshold=0.80)
    assert res.score >= 0.80
    assert res.match_type == MatchType.SYNTACTIC_SIMILAR
    assert "question_text" in res.sub_scores
    assert res.sub_scores["question_text"] == 1.0
    assert res.sub_scores["instructions"] < 1.0


def test_question_comparator_class():
    """Verifies QuestionComparator instance configuration and attribute weights."""
    comp = QuestionComparator(match_threshold=0.90)
    q1 = Question(question_text="Are you employed?", instructions="Show Card 1")
    q2 = Question(question_text="Are you employed?", instructions="Show Card 2")
    res = comp.compare(q1, q2)
    assert res.score > 0.70
    assert "question_text" in res.sub_scores


def test_compare_codelists_pairwise():
    """Verifies pairwise comparison of code lists across permutation and substantive partitioning."""
    c_m = Code(value="1", category=Category(label="Male", value="1"))
    c_f = Code(value="2", category=Category(label="Female", value="2"))
    c_dk1 = Code(
        value="98",
        category=Category(label="Don't Know", is_missing=True, sentinel_type=SentinelType.DONT_KNOW),
    )
    c_dk2 = Code(
        value="8",
        category=Category(label="Don't Know", is_missing=True, sentinel_type=SentinelType.DONT_KNOW),
    )

    cl_ordered = CodeList(name="CL1", codes=[c_m, c_f])
    cl_permuted = CodeList(name="CL2", codes=[c_f, c_m])
    cl_subst1 = CodeList(name="CL3", codes=[c_m, c_f, c_dk1])
    cl_subst2 = CodeList(name="CL4", codes=[c_m, c_f, c_dk2])

    # Exact
    res_exact = compare_codelists(cl_ordered, cl_ordered)
    assert res_exact.score == 1.0
    assert res_exact.match_type == MatchType.EXACT_IDENTICAL

    # Permutation
    res_perm = compare_codelists(cl_ordered, cl_permuted)
    assert res_perm.score == 1.0
    assert res_perm.match_type == MatchType.PERMUTATION

    # Substantive
    res_subst = compare_codelists(cl_subst1, cl_subst2)
    assert res_subst.score == 1.0
    assert res_subst.match_type == MatchType.SUBSTANTIVE_EXACT


def test_compare_resources_polymorphic():
    """Verifies polymorphic compare_resources across questions, code lists, concepts, and strings."""
    # Questions
    q1 = Question(question_text="Total household income")
    q2 = Question(question_text="Total household income")
    assert compare_resources(q1, q2).score == 1.0

    # Concepts
    c1 = Concept(preferred_label="GDP", notation="B1GQ")
    c2 = Concept(preferred_label="GDP", notation="B1GQ")
    assert compare_resources(c1, c2).score == 1.0

    # Raw strings
    assert compare_resources("Active Employment", "active employment").score == 1.0

    # Raw strings
    assert compare_resources("Active Employment", "active employment").score == 1.0


def test_clean_domain_models_and_operations():
    """Verifies that clean plain domain models function seamlessly across operations."""
    # 1. Clean Natural Ingestion of Raw Input Items
    cat_src = Category(label="Très satisfait / Straße", is_missing=False)
    cat_cand = Category(label="Tres satisfait / Strasse", is_missing=False)
    assert cat_src.label == "Très satisfait / Straße"
    assert cat_src.is_substantive is True
    assert compare_resources(cat_src, cat_cand).score == 1.0

    # 2. Clean Code & CodeList Composition
    code_1 = Code(value="1", category=cat_src)
    code_2 = Code(value="2", category=Category(label="Insatisfait", is_missing=False))
    cl = CodeList(name="CL_SATISFACTION", codes=[code_1, code_2])
    assert cl.member_count == 2
    assert cl.substantive_count == 2

    # 4. Clean Question Comparison
    q1 = Question(question_text="Are you currently employed?", instructions="Show card 1")
    q2 = Question(question_text="Are you currently employed?", instructions="Select on screen")
    q_res = compare_questions(q1, q2)
    assert q_res.score > 0.80

    # 5. Clean Variable & ValueDomain Composition & Comparison
    var1 = Variable(
        name="Q1_SAT",
        label="Satisfaction with services",
        data_type=DataType.from_ddi_cv("Integer"),
        value_domain=ValueDomain(kind="enumerated", codelist=cl),
    )
    var2 = Variable(
        name="Q1_SAT",
        label="Satisfaction with services",
        data_type=DataType.from_ddi_cv("Integer"),
        value_domain=ValueDomain(kind="enumerated", codelist=cl),
    )
    var_res = compare_variables(var1, var2)
    assert var_res.score == 1.0

    var_case_diff = Variable(
        name="q1_sat",
        label="Satisfaction with services",
        data_type=DataType.from_ddi_cv("Integer"),
        value_domain=ValueDomain(kind="enumerated", codelist=cl),
    )
    diff_res = compare_variables(var1, var_case_diff)
    assert diff_res.score >= 0.95
