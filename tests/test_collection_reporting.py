"""Unit tests for the Multi-Dataset DDI Collection Comparison & Reporting Engine (Phase 1 & Phase 2)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from dartfx.ddi.harmonizer.llm import (
    LLMConfig,
    LLMProvider,
    NarrativeStyle,
    StoryKind,
    build_story_prompt,
    generate_all_stories,
    generate_collection_story,
)
from dartfx.ddi.harmonizer.reporting import (
    analyze_collection,
)
from dartfx.ddi.harmonizer.reporting_html import render_collection_explorer_html

WAVE_2021_XML = """<?xml version="1.0" encoding="UTF-8"?>
<codeBook xmlns="ddi:codebook:2_5" version="2.5" ID="study_elipss_2021" xml:lang="fr">
  <stdyDscr>
    <citation>
      <titlStmt>
        <titl>Enquête Annuelle ELIPSS - Vague 1 (2021)</titl>
      </titlStmt>
    </citation>
    <stdyInfo>
      <sumDscr>
        <timePrd event="start" date="2021-03-01"/>
        <timePrd event="end" date="2021-05-01"/>
      </sumDscr>
    </stdyInfo>
  </stdyDscr>
  <dataDscr>
    <!-- V1: Gender with standard 1/2 + explicit missing 99 -->
    <var ID="V1" name="SEXE" dcml="0">
      <labl>Sexe du répondant</labl>
      <qstn><qstnLit>Quel est votre sexe ?</qstnLit></qstn>
      <catgry><catValu>1</catValu><labl>Homme</labl></catgry>
      <catgry><catValu>2</catValu><labl>Femme</labl></catgry>
      <catgry missing="Y"><catValu>99</catValu><labl>Refus</labl></catgry>
      <varFormat type="numeric"/>
    </var>
    <!-- V2: Inclusive writing & recode test across waves -->
    <var ID="V2" name="STATUT_PRO" dcml="0">
      <labl>Statut professionnel</labl>
      <qstn><qstnLit>Êtes-vous actuellement salarié dans le secteur privé ?</qstnLit></qstn>
      <catgry><catValu>1</catValu><labl>Oui</labl></catgry>
      <catgry><catValu>2</catValu><labl>Non</labl></catgry>
      <catgry missing="Y"><catValu>8</catValu><labl>Ne sait pas</labl></catgry>
      <varFormat type="numeric"/>
    </var>
    <!-- V3: Numeric scale 0..10 -->
    <var ID="V3" name="ECHELLE_GAUCHE_DROITE" dcml="0">
      <labl>Position politique gauche-droite</labl>
      <qstn><qstnLit>En politique, où vous situez-vous sur une échelle de 0 à 10 ?</qstnLit></qstn>
      <valrng><range min="0" max="10"/></valrng>
      <varFormat type="numeric"/>
    </var>
    <!-- V4: False friend positional variable V10 -->
    <var ID="V4" name="V10" dcml="0">
      <labl>Diplôme de la mère</labl>
      <qstn><qstnLit>Quel est le diplôme le plus élevé obtenu par votre mère ?</qstnLit></qstn>
      <catgry><catValu>1</catValu><labl>Ma mère a le baccalauréat</labl></catgry>
      <catgry><catValu>2</catValu><labl>Sans diplôme</labl></catgry>
      <varFormat type="numeric"/>
    </var>
    <!-- V5: Battery item 1 -->
    <var ID="V5" name="CONF_PARLEMENT" dcml="0">
      <labl>Confiance Parlement</labl>
      <qstn><qstnLit>Avez-vous confiance dans les institutions suivantes [...] Le Parlement</qstnLit></qstn>
      <catgry><catValu>1</catValu><labl>Tout à fait confiance</labl></catgry>
      <catgry><catValu>2</catValu><labl>Pas du tout confiance</labl></catgry>
      <varFormat type="numeric"/>
    </var>
    <!-- V6: Battery item 2 -->
    <var ID="V6" name="CONF_JUSTICE" dcml="0">
      <labl>Confiance Justice</labl>
      <qstn><qstnLit>Avez-vous confiance dans les institutions suivantes [...] La Justice</qstnLit></qstn>
      <catgry><catValu>1</catValu><labl>Tout à fait confiance</labl></catgry>
      <catgry><catValu>2</catValu><labl>Pas du tout confiance</labl></catgry>
      <varFormat type="numeric"/>
    </var>
  </dataDscr>
</codeBook>
"""

WAVE_2022_XML = """<?xml version="1.0" encoding="UTF-8"?>
<codeBook xmlns="ddi:codebook:2_5" version="2.5" ID="study_elipss_2022" xml:lang="fr">
  <stdyDscr>
    <citation>
      <titlStmt>
        <titl>Enquête Annuelle ELIPSS - Vague 2 (2022)</titl>
      </titlStmt>
    </citation>
    <stdyInfo>
      <sumDscr>
        <timePrd event="start" date="2022-03-01"/>
        <timePrd event="end" date="2022-05-01"/>
      </sumDscr>
    </stdyInfo>
  </stdyDscr>
  <dataDscr>
    <!-- V1: Gender with same substantive 1/2 but DIFFERENT sentinel 9999 -->
    <var ID="V1" name="ea22_sexe" dcml="0">
      <labl>Sexe du répondant</labl>
      <qstn><qstnLit>Quel est votre sexe ?</qstnLit></qstn>
      <catgry><catValu>1</catValu><labl>Homme</labl></catgry>
      <catgry><catValu>2</catValu><labl>Femme</labl></catgry>
      <catgry missing="Y"><catValu>9999</catValu><labl>Non réponse</labl></catgry>
      <varFormat type="numeric"/>
    </var>
    <!-- V2: Inclusive writing in question + recoded Oui=1, Non=0 + unflagged 'Ne sait pas' -->
    <var ID="V2" name="ea22_statut" dcml="0">
      <labl>Statut professionnel</labl>
      <qstn><qstnLit>Êtes-vous actuellement salarié(e) dans le secteur privé ?</qstnLit></qstn>
      <catgry><catValu>1</catValu><labl>Oui</labl></catgry>
      <catgry><catValu>0</catValu><labl>Non</labl></catgry>
      <catgry><catValu>99</catValu><labl>Ne sait pas</labl></catgry>
      <varFormat type="numeric"/>
    </var>
    <!-- V3: Numeric scale drifted from 0..10 to 1..10 -->
    <var ID="V3" name="ea22_echelle" dcml="0">
      <labl>Position politique gauche-droite</labl>
      <qstn><qstnLit>En politique, où vous situez-vous sur une échelle de 0 à 10 ?</qstnLit></qstn>
      <valrng><range min="1" max="10"/></valrng>
      <varFormat type="numeric"/>
    </var>
    <!-- V4: Typo in category ('Mon mère') AND routing artifact AND False Friend V10 -->
    <var ID="V4" name="DIPL_MERE" dcml="0">
      <labl>Diplôme de la mère</labl>
      <qstn><qstnLit>Quel est le diplôme le plus élevé obtenu par votre mère ?</qstnLit></qstn>
      <catgry><catValu>1</catValu><labl>Mon mère a le baccalauréat</labl></catgry>
      <catgry><catValu>2</catValu><labl>Sans diplôme</labl></catgry>
      <catgry><catValu>9</catValu><labl>b2-b3-b5-b5d</labl></catgry>
      <varFormat type="numeric"/>
    </var>
    <var ID="V5" name="V10" dcml="0">
      <labl>Revenu mensuel du foyer</labl>
      <qstn><qstnLit>Quel est le revenu mensuel net de votre foyer ?</qstnLit></qstn>
      <valrng><range min="0" max="50000"/></valrng>
      <varFormat type="numeric"/>
    </var>
  </dataDscr>
</codeBook>
"""


def test_collection_comparison_phase1_and_html(tmp_path: Path) -> None:
    """Verifies Phase 1 multi-survey comparison across Categories, CodeLists, Questions, Variables, and Longitudinal."""
    f2022 = tmp_path / "fr.cdsp.ddi.elipss.2022.ddic.xml"
    f2021 = tmp_path / "fr.cdsp.ddi.elipss.2021.ddic.xml"
    f2021.write_text(WAVE_2021_XML, encoding="utf-8")
    f2022.write_text(WAVE_2022_XML, encoding="utf-8")

    cache_dir = tmp_path / "cache"
    # Pass in reverse order (2022 then 2021) to verify auto chronological wave ordering
    report = analyze_collection(
        files=[f2022, f2021],
        title="Test ELIPSS Collection Report",
        cache_dir=cache_dir,
        order_by="auto",
    )

    assert report.collection_size == 2
    assert report.ordered_survey_keys == ["2021", "2022"]

    # 1. Verify Stage 1 intra-survey deduplication & DDI 4.0 caching
    s2021 = report.surveys[0]
    assert s2021.survey_key == "2021"
    assert s2021.raw_codelist_count >= 5
    assert s2021.unique_codelist_count < s2021.raw_codelist_count  # Battery items share codelist
    assert s2021.ddi40_cache_file is not None
    assert Path(s2021.ddi40_cache_file).exists()

    # 2. Verify Category analysis: typo ('Ma mère' vs 'Mon mère'), inconsistent 'Ne sait pas' flag, and routing artifact
    cats = report.categories_section
    assert cats.typographical_variants_count >= 1
    assert any("mère a le baccalauréat" in v.canonical_label for v in cats.spelling_variations)
    assert cats.inconsistent_sentinel_flag_count >= 1
    assert any(
        sf.label == "Ne sait pas" and sf.finding_type == "INCONSISTENT_MISSING_FLAG"
        for sf in cats.sentinel_audit_findings
    )
    assert cats.routing_artifact_labels_count >= 1
    assert any(a["label"] == "b2-b3-b5-b5d" for a in cats.routing_artifact_examples)

    # 3. Verify CodeList analysis: inclusive vs exclusive of sentinels & recoded Oui/Non
    cls = report.codelists_section
    assert cls.substantive_exact_sentinel_diff_count >= 1
    assert any("Homme" in " ".join(f.substantive_codes_a) for f in cls.sentinel_divergence_findings)
    assert cls.recoded_same_categories_diff_codes_count >= 1
    assert any("Non" in " ".join(f.recode_map.keys()) for f in cls.recoded_codelist_findings)

    # 4. Verify Question analysis: inclusive writing, same question / diff rep, and batteries
    qs = report.questions_section
    assert qs.inclusive_writing_variants_count >= 1
    assert qs.same_question_different_representation_count >= 2
    assert qs.shared_stem_batteries_count >= 1

    # 5. Verify Variable Cascade: shared substantive RepVar, numeric range drift, and False Friend V10
    vs = report.variables_section
    assert vs.cross_survey_shared_represented_variables_substantive >= 1
    assert any("NUMERIC_RANGE_CHANGE" in d.drift_types for d in vs.representation_drift_findings)
    assert vs.false_friend_variable_names_count >= 1
    assert any(ff.variable_name == "V10" and ff.distinct_concepts_count == 2 for ff in vs.false_friend_variables)

    # 6. Verify Longitudinal transitions & Markdown/HTML outputs
    ls = report.longitudinal_section
    assert len(ls.wave_transitions) == 1
    assert ls.wave_transitions[0].from_survey == "2021"
    assert ls.wave_transitions[0].to_survey == "2022"

    md = report.to_markdown()
    assert "## 1. Per-Survey Deduplication" in md
    assert "## 3. CodeLists (`CodeList`) & Sentinel/Missing Values Analysis" in md
    assert "## 5. Variable Cascade (`InstanceVariable` → `RepresentedVariable`) Analysis" in md

    html_path = tmp_path / "explorer.html"
    html = render_collection_explorer_html(report, output_path=html_path)
    assert html_path.exists()
    assert "Multi-Dataset Collection Harmonization Explorer" in html


def test_phase2_llm_narrative_generation(tmp_path: Path) -> None:
    """Verifies Phase 2 story generation across template mode and mocked OpenAI/Ollama/Gemini providers."""
    f2021 = tmp_path / "fr.cdsp.ddi.elipss.2021.ddic.xml"
    f2022 = tmp_path / "fr.cdsp.ddi.elipss.2022.ddic.xml"
    f2021.write_text(WAVE_2021_XML, encoding="utf-8")
    f2022.write_text(WAVE_2022_XML, encoding="utf-8")

    report = analyze_collection([f2021, f2022], cache_dir=tmp_path / "cache")

    # 1. Deterministic template provider (technical + journalistic)
    cfg_tpl = LLMConfig(provider=LLMProvider.TEMPLATE)
    stories = generate_all_stories(report, output_dir=tmp_path, config=cfg_tpl)
    assert len(stories) == 4
    assert (tmp_path / "stories" / "story_highlights.md").exists()
    assert (tmp_path / "stories" / "all_stories.md").exists()

    cfg_jour = LLMConfig(provider=LLMProvider.TEMPLATE, style=NarrativeStyle.JOURNALISTIC)
    jour_stories = generate_all_stories(report, output_dir=tmp_path, config=cfg_jour)
    assert len(jour_stories) == 4
    assert (tmp_path / "stories_journalistic" / "story_highlights.md").exists()
    assert jour_stories[0].style_used == "journalistic"

    # 2. Prompt construction check (technical & journalistic)
    sys_p, usr_p = build_story_prompt(report, StoryKind.QUALITY_ANOMALIES)
    assert "Senior DDI Metadata Architect" in sys_p
    assert "false_friend_variables" in usr_p

    sys_j, usr_j = build_story_prompt(report, StoryKind.HIGHLIGHTS, style=NarrativeStyle.JOURNALISTIC)
    assert "data journalist" in sys_j
    assert "Great Missing-Data Divide" in usr_j

    # 3. Mocked OpenAI / Ollama response with inline <think> stripping & padded table compaction
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": (
                        "<think>internal chain of thought</think>\n"
                        "# AI Executive Story\n\nSynthesized by LLM.\n\n"
                        "| Wave            | Continuity                    |\n"
                        "| :-------------- | :---------------------------- |\n"
                        "| 2013->2014      | 90.5%                         |"
                    )
                }
            }
        ]
    }
    mock_resp.raise_for_status.return_value = None

    with patch("httpx.Client.post", return_value=mock_resp):
        cfg_openai = LLMConfig(
            provider=LLMProvider.OPENAI,
            api_key="sk-test-key",
            model="gpt-4o-mini",
            style=NarrativeStyle.JOURNALISTIC,
        )
        st_openai = generate_collection_story(report, StoryKind.HIGHLIGHTS, config=cfg_openai)
        assert st_openai.provider_used == "openai"
        assert "Synthesized by LLM" in st_openai.markdown_content
        assert "<think>" not in st_openai.markdown_content
        assert "| :--- | :--- |" in st_openai.markdown_content
        assert "     " not in st_openai.markdown_content
        assert "Style: `journalistic`" in st_openai.markdown_content

    # 4. Ollama auto-discovery fallback via /api/tags when model=None
    mock_tags_resp = MagicMock()
    mock_tags_resp.json.return_value = {"models": [{"name": "gemma4:e2b-mlx"}]}
    mock_tags_resp.raise_for_status.return_value = None
    with (
        patch("httpx.Client.get", return_value=mock_tags_resp),
        patch("httpx.Client.post", return_value=mock_resp),
    ):
        cfg_ollama = LLMConfig(provider=LLMProvider.OLLAMA, style=NarrativeStyle.JOURNALISTIC)
        st_ollama = generate_collection_story(report, StoryKind.HIGHLIGHTS, config=cfg_ollama)
        assert st_ollama.provider_used == "ollama"
        assert st_ollama.model_used == "gemma4:e2b-mlx"
