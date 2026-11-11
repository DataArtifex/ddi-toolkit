# ruff: noqa: E501
"""Interactive HTML Collection Explorer for Multi-Dataset DDI Comparison & Harmonization Reports.

Generates a standalone, zero-dependency, responsive HTML5 application with:
- Overview & Per-Survey Intra-Survey Deduplication dashboard
- Interactive Longitudinal Continuity Heatmap & Wave-over-Wave Transition Explorer
- Questions Explorer (Spelling/Inclusive/Typo variants, Same Question / Different Representation, Batteries)
- CodeLists & Sentinel Inspector (Inclusive vs. Exclusive of Sentinels, Recodes, Permutations, Scale Evolution)
- Categories & Missingness Curation Audit (Inconsistent missing flags, Undocumented sentinels, Routing artifacts)
- Variable Cascade & False Friends Browser (Shared RepresentedVariables across waves, Representation Drift, Name Collisions)
"""

from __future__ import annotations

import json
from pathlib import Path

from .reporting import CollectionComparisonReport

COLLECTION_EXPLORER_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>__REPORT_TITLE__</title>
  <style>
    :root {
      --bg-base: #0b0f19;
      --bg-surface: #111827;
      --bg-card: #1f2937;
      --bg-hover: #283548;
      --border: #374151;
      --text-main: #f9fafb;
      --text-muted: #9ca3af;
      --primary: #6366f1;
      --primary-soft: rgba(99, 102, 241, 0.16);
      --success: #10b981;
      --success-soft: rgba(16, 185, 129, 0.16);
      --warning: #f59e0b;
      --warning-soft: rgba(245, 158, 11, 0.16);
      --danger: #ef4444;
      --danger-soft: rgba(239, 68, 68, 0.16);
      --info: #3b82f6;
      --info-soft: rgba(59, 130, 246, 0.16);
      --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif;
      --font-mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
    }
    body.light {
      --bg-base: #f8fafc;
      --bg-surface: #ffffff;
      --bg-card: #f1f5f9;
      --bg-hover: #e2e8f0;
      --border: #cbd5e1;
      --text-main: #0f172a;
      --text-muted: #64748b;
      --primary: #4f46e5;
      --primary-soft: rgba(79, 70, 229, 0.12);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: var(--font-sans);
      background: var(--bg-base);
      color: var(--text-main);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }
    header {
      background: var(--bg-surface);
      border-bottom: 1px solid var(--border);
      padding: 14px 24px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      position: sticky;
      top: 0;
      z-index: 50;
    }
    .brand { display: flex; align-items: center; gap: 12px; }
    .brand-badge {
      background: linear-gradient(135deg, #6366f1, #8b5cf6);
      color: #fff;
      font-weight: 700;
      font-size: 0.72rem;
      padding: 4px 9px;
      border-radius: 6px;
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }
    .brand h1 { font-size: 1.05rem; font-weight: 700; }
    .brand-sub { font-size: 0.78rem; color: var(--text-muted); }
    .nav-tabs {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
      background: var(--bg-Surface);
      padding: 8px 24px;
      border-bottom: 1px solid var(--border);
    }
    .tab-btn {
      background: transparent;
      color: var(--text-muted);
      border: 1px solid transparent;
      padding: 7px 14px;
      border-radius: 7px;
      font-size: 0.84rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.15s;
    }
    .tab-btn:hover { color: var(--text-main); background: var(--bg-card); }
    .tab-btn.active {
      background: var(--primary-soft);
      color: var(--primary);
      border-color: var(--primary);
    }
    .btn-action {
      background: var(--bg-card);
      color: var(--text-main);
      border: 1px solid var(--border);
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 0.8rem;
      cursor: pointer;
      font-weight: 600;
    }
    .btn-action:hover { background: var(--bg-hover); }
    main { flex: 1; padding: 24px; max-width: 1650px; width: 100%; margin: 0 auto; }
    .tab-panel { display: none; }
    .tab-panel.active { display: block; }
    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 14px;
      margin-bottom: 22px;
    }
    .kpi-card {
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 16px;
    }
    .kpi-label { font-size: 0.76rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.04em; font-weight: 600; }
    .kpi-val { font-size: 1.65rem; font-weight: 800; margin: 6px 0 4px; font-family: var(--font-mono); }
    .kpi-sub { font-size: 0.78rem; color: var(--text-muted); }
    .section-card {
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 18px 20px;
      margin-bottom: 22px;
    }
    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-bottom: 14px;
      flex-wrap: wrap;
    }
    .section-title { font-size: 1rem; font-weight: 700; }
    .controls { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
    input[type="search"], select {
      background: var(--bg-card);
      color: var(--text-main);
      border: 1px solid var(--border);
      padding: 7px 11px;
      border-radius: 6px;
      font-size: 0.83rem;
      min-width: 220px;
    }
    .table-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 0.83rem; }
    th, td {
      padding: 9px 11px;
      border-bottom: 1px solid var(--border);
      text-align: left;
      vertical-align: top;
    }
    th {
      background: var(--bg-card);
      color: var(--text-muted);
      font-weight: 600;
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      position: sticky;
      top: 0;
    }
    tr:hover td { background: var(--bg-hover); }
    .badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 0.72rem;
      font-weight: 600;
      font-family: var(--font-mono);
    }
    .badge-primary { background: var(--primary-soft); color: var(--primary); }
    .badge-success { background: var(--success-soft); color: var(--success); }
    .badge-warning { background: var(--warning-soft); color: var(--warning); }
    .badge-danger { background: var(--danger-soft); color: var(--danger); }
    .badge-info { background: var(--info-soft); color: var(--info); }
    .mono { font-family: var(--font-mono); font-size: 0.79rem; }
    .cell-exact { background: rgba(16, 185, 129, 0.18); color: #34d399; font-weight: 600; text-align: center; font-family: var(--font-mono); font-size: 0.74rem; }
    .cell-sent { background: rgba(245, 158, 11, 0.18); color: #fbbf24; font-weight: 600; text-align: center; font-family: var(--font-mono); font-size: 0.74rem; }
    .cell-drift { background: rgba(239, 68, 68, 0.18); color: #f87171; font-weight: 600; text-align: center; font-family: var(--font-mono); font-size: 0.74rem; }
    .cell-empty { color: var(--text-muted); text-align: center; opacity: 0.4; }
    .bar-bg { background: var(--bg-card); height: 6px; border-radius: 3px; overflow: hidden; margin-top: 4px; width: 100px; }
    .bar-fill { background: var(--primary); height: 100%; }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <span class="brand-badge">DDI-Toolkit</span>
      <div>
        <h1 id="hdr-title">Multi-Dataset Collection Harmonization Explorer</h1>
        <div class="brand-sub" id="hdr-meta"></div>
      </div>
    </div>
    <div class="controls">
      <button class="btn-action" onclick="toggleTheme()">Toggle Theme</button>
      <button class="btn-action" onclick="downloadJson()">Export JSON</button>
    </div>
  </header>

  <nav class="nav-tabs">
    <button class="tab-btn active" onclick="switchTab('overview', this)">1. Overview &amp; Upgrade</button>
    <button class="tab-btn" onclick="switchTab('longitudinal', this)">2. Longitudinal Continuity</button>
    <button class="tab-btn" onclick="switchTab('questions', this)">3. Questions Explorer</button>
    <button class="tab-btn" onclick="switchTab('codelists', this)">4. CodeLists &amp; Sentinels</button>
    <button class="tab-btn" onclick="switchTab('categories', this)">5. Categories &amp; Missingness Audit</button>
    <button class="tab-btn" onclick="switchTab('variables', this)">6. Variable Cascade &amp; False Friends</button>
  </nav>

  <main>
    <!-- TAB 1: OVERVIEW -->
    <section id="tab-overview" class="tab-panel active">
      <div class="kpi-grid" id="overview-kpis"></div>
      <div class="section-card">
        <div class="section-header">
          <div class="section-title">Stage 1 — Per-Survey Intra-Survey Deduplication &amp; DDI-L 4.0 Upgrade Summary</div>
        </div>
        <div class="table-wrap">
          <table id="tbl-surveys">
            <thead>
              <tr>
                <th>Wave / Key</th>
                <th>Study ID &amp; Title</th>
                <th>DDI Standard</th>
                <th>Variables (Raw → RepVar)</th>
                <th>Questions (Raw → Unique)</th>
                <th>CodeLists (Raw → Unique)</th>
                <th>Categories (Raw → Unique)</th>
                <th>Explicit Sentinels</th>
                <th>Undocumented Sentinels</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- TAB 2: LONGITUDINAL -->
    <section id="tab-longitudinal" class="tab-panel">
      <div class="kpi-grid" id="longitudinal-kpis"></div>
      <div class="section-card">
        <div class="section-header">
          <div class="section-title">Wave-over-Wave Continuity &amp; Transition Metrics (W<sub>t-1</sub> → W<sub>t</sub>)</div>
        </div>
        <div class="table-wrap">
          <table id="tbl-transitions">
            <thead>
              <tr>
                <th>Transition</th>
                <th>Concepts (W<sub>t-1</sub> → W<sub>t</sub>)</th>
                <th>Retained Exact</th>
                <th>Retained Substantive (Sentinel Diff)</th>
                <th>Retained w/ Drift</th>
                <th>Returning from Earlier Wave</th>
                <th>Newly Introduced</th>
                <th>Dropped</th>
                <th>Continuity Rate</th>
              </tr>
            </thead>
            <tbody></tbody>
          </table>
        </div>
      </div>

      <div class="section-card">
        <div class="section-header">
          <div class="section-title">Longitudinal Continuity Matrix across Waves (✅ Exact Rep | 🟡 Sentinel Diff | 🟠 Rep Drift)</div>
          <div class="controls">
            <input type="search" id="q-matrix" placeholder="Search question or variable..." oninput="renderMatrix()">
            <select id="f-matrix-tier" onchange="renderMatrix()">
              <option value="ALL">All Persistence Tiers</option>
              <option value="CORE_PERMANENT">Core Permanent (≥80% waves)</option>
              <option value="ROTATING_MODULE">Rotating Module (3+ waves)</option>
              <option value="PAIR_WAVE">Pair Wave (2 waves)</option>
            </select>
            <select id="f-matrix-drift" onchange="renderMatrix()">
              <option value="ALL">All Drift Statuses</option>
              <option value="DRIFT">Has Representation Drift</option>
              <option value="STABLE">Stable Representation</option>
            </select>
          </div>
        </div>
        <div class="table-wrap">
          <table id="tbl-matrix">
            <thead></thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- TAB 3: QUESTIONS -->
    <section id="tab-questions" class="tab-panel">
      <div class="kpi-grid" id="questions-kpis"></div>
      <div class="section-card">
        <div class="section-header">
          <div class="section-title">Questions Comparison &amp; Harmonization Explorer</div>
          <div class="controls">
            <input type="search" id="q-questions" placeholder="Filter question text or wave..." oninput="renderQuestions()">
            <select id="f-questions-mode" onchange="renderQuestions()">
              <option value="SPELLING">1. Spelling, Inclusive Writing &amp; Typo Variations</option>
              <option value="DIFF_REP">2. Same Question, Different Variable Representation</option>
              <option value="NEAR">3. Near-Match Harmonization Candidates</option>
              <option value="BATTERIES">4. Shared-Stem Multi-Item Batteries ([...])</option>
            </select>
          </div>
        </div>
        <div class="table-wrap">
          <table id="tbl-questions">
            <thead></thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- TAB 4: CODELISTS & SENTINELS -->
    <section id="tab-codelists" class="tab-panel">
      <div class="kpi-grid" id="codelists-kpis"></div>
      <div class="section-card">
        <div class="section-header">
          <div class="section-title">CodeLists &amp; Sentinel Value Comparison Inspector</div>
          <div class="controls">
            <input type="search" id="q-codelists" placeholder="Search categories, codes, or variables..." oninput="renderCodeLists()">
            <select id="f-codelists-mode" onchange="renderCodeLists()">
              <option value="SENTINEL_DIFF">1. Substantive-Exact / Sentinel-Different (Inclusive vs. Exclusive)</option>
              <option value="RECODED">2. Same Categories, Different Codes (Recodes)</option>
              <option value="LABEL_VAR">3. Same Codes, Category Label Variants (Inclusive/Typo)</option>
              <option value="SCALE_EVO">4. Scale Evolution (Partial Substantive Overlap)</option>
              <option value="TOP_REUSED">5. Top Reused Canonical CodeLists</option>
            </select>
          </div>
        </div>
        <div class="table-wrap">
          <table id="tbl-codelists">
            <thead></thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- TAB 5: CATEGORIES & MISSINGNESS -->
    <section id="tab-categories" class="tab-panel">
      <div class="kpi-grid" id="categories-kpis"></div>
      <div class="section-card">
        <div class="section-header">
          <div class="section-title">Categories Harmonization &amp; Sentinel Missingness Curation Audit</div>
          <div class="controls">
            <input type="search" id="q-categories" placeholder="Search category label..." oninput="renderCategories()">
            <select id="f-categories-mode" onchange="renderCategories()">
              <option value="SPELLING">1. Spelling, Inclusive Writing &amp; Typographical Variants</option>
              <option value="SENTINEL_AUDIT">2. Sentinel / Missingness Flag Consistency Audit</option>
              <option value="NEAR">3. Near-Match Category Candidates</option>
              <option value="ARTIFACTS">4. Routing Filter Artifacts in Category Labels</option>
            </select>
          </div>
        </div>
        <div class="table-wrap">
          <table id="tbl-categories">
            <thead></thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- TAB 6: VARIABLE CASCADE & FALSE FRIENDS -->
    <section id="tab-variables" class="tab-panel">
      <div class="kpi-grid" id="variables-kpis"></div>
      <div class="section-card">
        <div class="section-header">
          <div class="section-title">Variable Cascade (InstanceVariable → RepresentedVariable) &amp; False Friends</div>
          <div class="controls">
            <input type="search" id="q-variables" placeholder="Search variable name, question, or domain..." oninput="renderVariables()">
            <select id="f-variables-mode" onchange="renderVariables()">
              <option value="SHARED_RV">1. InstanceVariables Sharing the Same RepresentedVariable</option>
              <option value="DRIFT">2. Concept / Question Lineages with Representation Drift</option>
              <option value="FALSE_FRIENDS">3. "False Friend" Variable Names (Same Name, Different Concept)</option>
            </select>
          </div>
        </div>
        <div class="table-wrap">
          <table id="tbl-variables">
            <thead></thead>
            <tbody></tbody>
          </table>
        </div>
      </div>
    </section>
  </main>

  <script>
    const REPORT = __REPORT_JSON_PAYLOAD__;

    function esc(s) {
      if (s === null || s === undefined) return '';
      return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function switchTab(tabId, btn) {
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.getElementById('tab-' + tabId).classList.add('active');
      btn.classList.add('active');
    }

    function toggleTheme() {
      document.body.classList.toggle('light');
    }

    function downloadJson() {
      const blob = new Blob([JSON.stringify(REPORT, null, 2)], {type: 'application/json'});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'collection_report.json';
      a.click();
    }

    function kpiHtml(label, val, sub) {
      return `<div class="kpi-card"><div class="kpi-label">${esc(label)}</div><div class="kpi-val">${esc(val)}</div><div class="kpi-sub">${esc(sub)}</div></div>`;
    }

    function initApp() {
      document.getElementById('hdr-title').textContent = REPORT.title;
      document.getElementById('hdr-meta').textContent = `${REPORT.collection_size} Datasets (${REPORT.ordered_survey_keys.join(', ')}) • Generated ${REPORT.generated_at.slice(0, 19).replace('T', ' ')}`;

      // Overview KPIs
      const totVars = REPORT.surveys.reduce((a, s) => a + s.raw_variable_count, 0);
      const qs = REPORT.questions_section;
      const cls = REPORT.codelists_section;
      const vs = REPORT.variables_section;
      document.getElementById('overview-kpis').innerHTML = [
        kpiHtml('Surveys Analyzed', REPORT.collection_size, REPORT.ordered_survey_keys.join(' → ')),
        kpiHtml('InstanceVariables', totVars, `${vs.unique_substantive_represented_variables_global} Substantive RepVars`),
        kpiHtml('Unique Questions', qs.unique_exact_questions_global, `${qs.cross_survey_reused_questions_count} reused across 2+ waves`),
        kpiHtml('Unique CodeLists (Full → Subst)', `${cls.unique_full_codelists_global} → ${cls.unique_substantive_codelists_global}`, `+${cls.additional_merges_when_excluding_sentinels} merges w/o sentinels`),
        kpiHtml('Core Permanent Concepts', REPORT.longitudinal_section.core_permanent_lineages_count, 'Present in ≥80% of waves')
      ].join('');

      // Survey table
      const sBody = document.querySelector('#tbl-surveys tbody');
      sBody.innerHTML = REPORT.surveys.map(s => `
        <tr>
          <td><span class="badge badge-primary">${esc(s.survey_key)}</span></td>
          <td><strong>${esc(s.study_id)}</strong><br><span style="color:var(--text-muted);font-size:0.76rem">${esc(s.title)}</span></td>
          <td><span class="badge badge-info">${esc(s.ddi_flavor)}</span></td>
          <td class="mono">${s.raw_variable_count} → ${s.unique_represented_variable_count} (-${s.variable_reduction_pct}%)
            <div class="bar-bg"><div class="bar-fill" style="width:${Math.min(100, s.variable_reduction_pct)}%"></div></div>
          </td>
          <td class="mono">${s.raw_question_count} → ${s.unique_question_count} (-${s.question_reduction_pct}%)
            <div class="bar-bg"><div class="bar-fill" style="width:${Math.min(100, s.question_reduction_pct)}%"></div></div>
          </td>
          <td class="mono">${s.raw_codelist_count} → ${s.unique_codelist_count} (-${s.codelist_reduction_pct}%)
            <div class="bar-bg"><div class="bar-fill" style="width:${Math.min(100, s.codelist_reduction_pct)}%"></div></div>
          </td>
          <td class="mono">${s.raw_category_count} → ${s.unique_category_count} (-${s.category_reduction_pct}%)
            <div class="bar-bg"><div class="bar-fill" style="width:${Math.min(100, s.category_reduction_pct)}%"></div></div>
          </td>
          <td class="mono">${s.explicit_sentinel_category_count} cats (${s.codelists_with_explicit_sentinels} CLs)</td>
          <td class="mono">${s.inferred_undocumented_sentinel_category_count > 0 ? `<span class="badge badge-warning">${s.inferred_undocumented_sentinel_category_count} unflagged</span>` : '0'}</td>
        </tr>
      `).join('');

      // Longitudinal KPIs & Transitions
      const ls = REPORT.longitudinal_section;
      document.getElementById('longitudinal-kpis').innerHTML = [
        kpiHtml('Total Concept Lineages', ls.total_concept_lineages, 'Across all waves'),
        kpiHtml('Core Permanent (≥80% waves)', ls.core_permanent_lineages_count, 'Longitudinal backbone'),
        kpiHtml('Rotating Modules (3+ waves)', ls.rotating_module_lineages_count, 'Intermittent topical batteries'),
        kpiHtml('Two-Wave Modules', ls.pair_wave_lineages_count, 'Appeared in 2 waves'),
        kpiHtml('Single-Wave Modules', ls.single_wave_topical_lineages_count, 'Wave-specific modules')
      ].join('');

      document.querySelector('#tbl-transitions tbody').innerHTML = ls.wave_transitions.map(t => `
        <tr>
          <td><strong>${esc(t.from_survey)} → ${esc(t.to_survey)}</strong></td>
          <td class="mono">${t.from_total_concepts} → ${t.to_total_concepts}</td>
          <td class="mono"><span class="badge badge-success">${t.retained_exact_representation}</span></td>
          <td class="mono"><span class="badge badge-warning">${t.retained_substantive_representation}</span></td>
          <td class="mono"><span class="badge badge-danger">${t.retained_with_representation_or_text_drift}</span></td>
          <td class="mono">${t.returning_from_earlier_wave}</td>
          <td class="mono">${t.newly_introduced}</td>
          <td class="mono">${t.dropped_from_previous}</td>
          <td class="mono"><strong>${t.continuity_rate_pct}%</strong></td>
        </tr>
      `).join('');

      // Questions KPIs
      document.getElementById('questions-kpis').innerHTML = [
        kpiHtml('Global Unique Questions', qs.unique_exact_questions_global, `${qs.cross_survey_reused_questions_count} reused in 2+ waves`),
        kpiHtml('Spelling & Inclusive Variants', qs.spelling_and_phrasing_variations_count, `${qs.inclusive_writing_variants_count} inclusive, ${qs.typographical_variants_count} typos`),
        kpiHtml('Same Question / Diff Rep', qs.same_question_different_representation_count, 'Scale, code, or range changed'),
        kpiHtml('Near-Match Candidates', qs.near_match_candidates_count, 'High syntactic similarity'),
        kpiHtml('Shared-Stem Batteries', qs.shared_stem_batteries_count, 'Multi-item question grids')
      ].join('');

      // CodeLists KPIs
      document.getElementById('codelists-kpis').innerHTML = [
        kpiHtml('Unique Full CodeLists', cls.unique_full_codelists_global, 'Inclusive of sentinels'),
        kpiHtml('Unique Substantive CodeLists', cls.unique_substantive_codelists_global, `+${cls.additional_merges_when_excluding_sentinels} merges excluding sentinels`),
        kpiHtml('Substantive Exact / Sentinel Diff', cls.substantive_exact_sentinel_diff_count, 'Same scale, different missing codes'),
        kpiHtml('Recoded (Same Cats / Diff Codes)', cls.recoded_same_categories_diff_codes_count, 'Requires code remapping'),
        kpiHtml('Scale Evolution & Label Variants', cls.scale_evolution_near_matches_count + cls.label_variant_same_codes_count, `${cls.label_variant_same_codes_count} label variants, ${cls.scale_evolution_near_matches_count} scale shifts`)
      ].join('');

      // Categories KPIs
      const cats = REPORT.categories_section;
      document.getElementById('categories-kpis').innerHTML = [
        kpiHtml('Global Unique Category Labels', cats.unique_exact_labels_global, `${cats.cross_survey_reused_labels_count} reused in 2+ waves`),
        kpiHtml('Spelling / Inclusive / Typo', cats.spelling_and_phrasing_variations_count, `${cats.inclusive_writing_variants_count} inclusive, ${cats.typographical_variants_count} typos`),
        kpiHtml('Inconsistent Missing Flags', cats.inconsistent_sentinel_flag_count, 'Flagged in some waves, unflagged in others'),
        kpiHtml('Undocumented Sentinels', cats.undocumented_sentinel_labels_count, 'Missing="Y" omitted on NSP/Refus'),
        kpiHtml('Routing Filter Artifacts', cats.routing_artifact_labels_count, 'Filter strings in category labels')
      ].join('');

      // Variables KPIs
      document.getElementById('variables-kpis').innerHTML = [
        kpiHtml('Total InstanceVariables', vs.total_instance_variables_across_surveys, 'Across all waves'),
        kpiHtml('Shared Substantive RepVars', vs.cross_survey_shared_represented_variables_substantive, `${vs.cross_survey_shared_represented_variables_strict} strict exact`),
        kpiHtml('Lineages w/ Rep Drift', vs.concept_clusters_with_representation_drift, 'Scale, range, or type changed'),
        kpiHtml('False Friend Variable Names', vs.false_friend_variable_names_count, 'Same variable name, different concept'),
        kpiHtml('Numeric Vars w/ [Min, Max]', vs.numeric_variables_with_range_count, 'Explicit numeric bounds')
      ].join('');

      renderMatrix();
      renderQuestions();
      renderCodeLists();
      renderCategories();
      renderVariables();
    }

    function renderMatrix() {
      const ls = REPORT.longitudinal_section;
      const q = (document.getElementById('q-matrix').value || '').toLowerCase();
      const tier = document.getElementById('f-matrix-tier').value;
      const drift = document.getElementById('f-matrix-drift').value;

      const thead = document.querySelector('#tbl-matrix thead');
      thead.innerHTML = `<tr><th>ID</th><th>Question / Concept Lineage</th><th>Tier</th><th>Waves</th>${ls.ordered_surveys.map(s => `<th>${esc(s)}</th>`).join('')}</tr>`;

      const rows = ls.continuity_matrix.filter(r => {
        if (tier !== 'ALL' && r.persistence_tier !== tier) return false;
        if (drift === 'DRIFT' && !r.has_representation_drift) return false;
        if (drift === 'STABLE' && r.has_representation_drift) return false;
        if (q && !r.label_or_question.toLowerCase().includes(q) && !JSON.stringify(r.wave_status).toLowerCase().includes(q)) return false;
        return true;
      });

      document.querySelector('#tbl-matrix tbody').innerHTML = rows.map(r => {
        const cells = ls.ordered_surveys.map(sk => {
          const st = r.wave_status[sk] || '';
          if (st.startsWith('EXACT')) return `<td class="cell-exact" title="Exact Representation">${esc(st.slice(7, -1))}</td>`;
          if (st.startsWith('SENTINEL_DIFF')) return `<td class="cell-sent" title="Same substantive domain, sentinel differs">${esc(st.slice(15, -1))}</td>`;
          if (st.startsWith('DRIFT')) return `<td class="cell-drift" title="Representation drifted">${esc(st.slice(7, -1))}</td>`;
          return `<td class="cell-empty">—</td>`;
        }).join('');
        return `<tr>
          <td class="mono">${esc(r.lineage_id)}</td>
          <td>${esc(r.label_or_question)}</td>
          <td><span class="badge badge-info">${esc(r.persistence_tier)}</span></td>
          <td class="mono">${r.waves_present_count}/${ls.ordered_surveys.length}</td>
          ${cells}
        </tr>`;
      }).join('');
    }

    function renderQuestions() {
      const qs = REPORT.questions_section;
      const q = (document.getElementById('q-questions').value || '').toLowerCase();
      const mode = document.getElementById('f-questions-mode').value;
      const thead = document.querySelector('#tbl-questions thead');
      const tbody = document.querySelector('#tbl-questions tbody');

      if (mode === 'SPELLING' || mode === 'NEAR') {
        const list = mode === 'SPELLING' ? qs.spelling_variations : qs.near_match_candidates;
        thead.innerHTML = `<tr><th>Variation Type</th><th>Score</th><th>Question A (Waves &amp; Variables)</th><th>Question B (Waves &amp; Variables)</th><th>Explanation</th></tr>`;
        tbody.innerHTML = list.filter(x => !q || x.question_a.toLowerCase().includes(q) || x.question_b.toLowerCase().includes(q)).map(x => `
          <tr>
            <td><span class="badge badge-primary">${esc(x.finding_kind)}</span></td>
            <td class="mono">${x.similarity_score.toFixed(3)}</td>
            <td><strong>${esc(x.question_a)}</strong><br><span class="mono" style="color:var(--text-muted)">Waves: ${esc(x.surveys_a.join(', '))} | Vars: ${esc(x.variables_a.join(', '))}</span></td>
            <td><strong>${esc(x.question_b)}</strong><br><span class="mono" style="color:var(--text-muted)">Waves: ${esc(x.surveys_b.join(', '))} | Vars: ${esc(x.variables_b.join(', '))}</span></td>
            <td>${esc(x.divergence_details)}</td>
          </tr>
        `).join('');
      } else if (mode === 'DIFF_REP') {
        thead.innerHTML = `<tr><th>Question Text</th><th>Representation A (Waves &amp; Vars)</th><th>Representation B (Waves &amp; Vars)</th><th>Why Representation Differs</th></tr>`;
        tbody.innerHTML = qs.same_question_different_representations.filter(x => !q || x.question_a.toLowerCase().includes(q) || (x.representation_a || '').toLowerCase().includes(q)).map(x => `
          <tr>
            <td><strong>${esc(x.question_a)}</strong></td>
            <td><span class="badge badge-info">${esc(x.representation_a)}</span><br><span class="mono" style="color:var(--text-muted)">Waves: ${esc(x.surveys_a.join(', '))} (${esc(x.variables_a.join(', '))})</span></td>
            <td><span class="badge badge-warning">${esc(x.representation_b)}</span><br><span class="mono" style="color:var(--text-muted)">Waves: ${esc(x.surveys_b.join(', '))} (${esc(x.variables_b.join(', '))})</span></td>
            <td>${esc(x.divergence_details)}</td>
          </tr>
        `).join('');
      } else {
        thead.innerHTML = `<tr><th>Shared Battery Stem</th><th>Waves Present</th><th>Unique Sub-Items</th><th>Sample Sub-Items</th><th>Sample Variables</th></tr>`;
        tbody.innerHTML = qs.shared_stem_batteries.filter(x => !q || x.stem_text.toLowerCase().includes(q)).map(x => `
          <tr>
            <td><strong>${esc(x.stem_text)}</strong></td>
            <td><span class="badge badge-primary">${esc(x.surveys_present.join(', '))}</span></td>
            <td class="mono">${x.total_sub_items_unique}</td>
            <td>${x.sample_sub_items.map(s => `• ${esc(s)}`).join('<br>')}</td>
            <td class="mono">${esc(x.sample_variables.join(', '))}</td>
          </tr>
        `).join('');
      }
    }

    function renderCodeLists() {
      const cls = REPORT.codelists_section;
      const q = (document.getElementById('q-codelists').value || '').toLowerCase();
      const mode = document.getElementById('f-codelists-mode').value;
      const thead = document.querySelector('#tbl-codelists thead');
      const tbody = document.querySelector('#tbl-codelists tbody');

      if (mode === 'SENTINEL_DIFF') {
        thead.innerHTML = `<tr><th>Shared Substantive Scale</th><th>Variant A Sentinels (Waves &amp; Vars)</th><th>Variant B Sentinels (Waves &amp; Vars)</th><th>Explanation</th></tr>`;
        tbody.innerHTML = cls.sentinel_divergence_findings.filter(f => !q || JSON.stringify(f).toLowerCase().includes(q)).map(f => `
          <tr>
            <td>${f.substantive_codes_a.slice(0, 6).map(c => `<span class="mono">${esc(c)}</span>`).join('<br>')}</td>
            <td><span class="badge badge-warning">${esc(f.sentinel_codes_a.join('; ') || 'None')}</span><br><span class="mono" style="color:var(--text-muted)">Waves: ${esc(f.surveys_a.join(', '))} (${esc(f.variables_a.slice(0,4).join(', '))})</span></td>
            <td><span class="badge badge-info">${esc(f.sentinel_codes_b.join('; ') || 'None')}</span><br><span class="mono" style="color:var(--text-muted)">Waves: ${esc(f.surveys_b.join(', '))} (${esc(f.variables_b.slice(0,4).join(', '))})</span></td>
            <td>${esc(f.explanation)}</td>
          </tr>
        `).join('');
      } else if (mode === 'RECODED') {
        thead.innerHTML = `<tr><th>CodeList A (Waves &amp; Vars)</th><th>CodeList B (Waves &amp; Vars)</th><th>Recode Mapping (A → B)</th><th>Explanation</th></tr>`;
        tbody.innerHTML = cls.recoded_codelist_findings.filter(f => !q || JSON.stringify(f).toLowerCase().includes(q)).map(f => `
          <tr>
            <td>${esc(f.codelist_a_Summary)}<br><span class="mono" style="color:var(--text-muted)">Waves: ${esc(f.surveys_a.join(', '))} (${esc(f.variables_a.slice(0,4).join(', '))})</span></td>
            <td>${esc(f.codelist_b_Summary)}<br><span class="mono" style="color:var(--text-muted)">Waves: ${esc(f.surveys_b.join(', '))} (${esc(f.variables_b.slice(0,4).join(', '))})</span></td>
            <td class="mono">${Object.entries(f.recode_map).map(([k, v]) => `${esc(k)} → <strong>${esc(v)}</strong>`).join('<br>')}</td>
            <td>${esc(f.explanation)}</td>
          </tr>
        `).join('');
      } else if (mode === 'LABEL_VAR' || mode === 'SCALE_EVO') {
        const list = mode === 'LABEL_VAR' ? cls.label_variant_findings : cls.scale_evolution_findings;
        thead.innerHTML = `<tr><th>Score</th><th>CodeList A (Waves &amp; Vars)</th><th>CodeList B (Waves &amp; Vars)</th><th>Details</th></tr>`;
        tbody.innerHTML = list.filter(f => !q || JSON.stringify(f).toLowerCase().includes(q)).map(f => `
          <tr>
            <td class="mono">${f.similarity_score.toFixed(3)}</td>
            <td>${esc(f.codelist_a_Summary)}<br><span class="mono" style="color:var(--text-muted)">Waves: ${esc(f.surveys_a.join(', '))}</span></td>
            <td>${esc(f.codelist_b_Summary)}<br><span class="mono" style="color:var(--text-muted)">Waves: ${esc(f.surveys_b.join(', '))}</span></td>
            <td>${esc(f.explanation)}</td>
          </tr>
        `).join('');
      } else {
        thead.innerHTML = `<tr><th>Digest</th><th>CodeList Summary</th><th>Substantive / Sentinel</th><th>Waves Reused</th><th>Total Variables</th></tr>`;
        tbody.innerHTML = cls.top_reused_codelists.filter(c => !q || c.summary.toLowerCase().includes(q)).map(c => `
          <tr>
            <td class="mono">${esc(c.digest)}</td>
            <td>${esc(c.summary)}</td>
            <td class="mono">${c.substantive_count} subst / ${c.sentinel_count} sentinel</td>
            <td><span class="badge badge-success">${c.surveys_count} waves</span> (${esc(c.surveys.join(', '))})</td>
            <td class="mono">${c.total_variables_using}</td>
          </tr>
        `).join('');
      }
    }

    function renderCategories() {
      const cats = REPORT.categories_section;
      const q = (document.getElementById('q-categories').value || '').toLowerCase();
      const mode = document.getElementById('f-categories-mode').value;
      const thead = document.querySelector('#tbl-categories thead');
      const tbody = document.querySelector('#tbl-categories tbody');

      if (mode === 'SPELLING' || mode === 'NEAR') {
        const list = mode === 'SPELLING' ? cats.spelling_variations : cats.near_match_candidates;
        thead.innerHTML = `<tr><th>Variation Type</th><th>Score</th><th>Canonical Label (Waves)</th><th>Variant Label (Waves)</th><th>Explanation</th></tr>`;
        tbody.innerHTML = list.filter(x => !q || x.canonical_label.toLowerCase().includes(q) || x.variant_label.toLowerCase().includes(q)).map(x => `
          <tr>
            <td><span class="badge badge-primary">${esc(x.match_type)}</span></td>
            <td class="mono">${x.similarity_score.toFixed(3)}</td>
            <td><strong>${esc(x.canonical_label)}</strong><br><span class="mono" style="color:var(--text-muted)">Waves: ${esc(x.canonical_surveys.join(', '))}</span></td>
            <td><strong>${esc(x.variant_label)}</strong><br><span class="mono" style="color:var(--text-muted)">Waves: ${esc(x.variant_surveys.join(', '))}</span></td>
            <td>${esc(x.explanation)}</td>
          </tr>
        `).join('');
      } else if (mode === 'SENTINEL_AUDIT') {
        thead.innerHTML = `<tr><th>Category Label</th><th>Finding Type</th><th>Flagged missing="Y" In</th><th>Unflagged In</th><th>Codes Seen</th><th>Recommendation</th></tr>`;
        tbody.innerHTML = cats.sentinel_audit_findings.filter(x => !q || x.label.toLowerCase().includes(q)).map(x => `
          <tr>
            <td><strong>${esc(x.label)}</strong></td>
            <td><span class="badge ${x.finding_type === 'EXPLICIT_SENTINEL' ? 'badge-success' : 'badge-warning'}">${esc(x.finding_type)}</span></td>
            <td class="mono">${esc(x.surveys_explicit_missing.join(', ') || 'None')}</td>
            <td class="mono">${esc(x.surveys_unflagged.join(', ') || 'None')}</td>
            <td class="mono">${esc(x.code_values_seen.join(', '))}</td>
            <td>${esc(x.recommendation)}</td>
          </tr>
        `).join('');
      } else {
        thead.innerHTML = `<tr><th>Corrupted Routing Filter Label</th><th>Surveys Affected</th><th>Total Usages</th></tr>`;
        tbody.innerHTML = cats.routing_artifact_examples.filter(x => !q || x.label.toLowerCase().includes(q)).map(x => `
          <tr>
            <td class="mono"><span class="badge badge-danger">${esc(x.label)}</span></td>
            <td class="mono">${esc(x.surveys.join(', '))}</td>
            <td class="mono">${x.total_usages}</td>
          </tr>
        `).join('');
      }
    }

    function renderVariables() {
      const vs = REPORT.variables_section;
      const q = (document.getElementById('q-variables').value || '').toLowerCase();
      const mode = document.getElementById('f-variables-mode').value;
      const thead = document.querySelector('#tbl-variables thead');
      const tbody = document.querySelector('#tbl-variables tbody');

      if (mode === 'SHARED_RV') {
        thead.innerHTML = `<tr><th>RepVar ID</th><th>Question / Concept Anchor</th><th>Representation &amp; Value Domain</th><th>Waves &amp; InstanceVariable Lineage</th><th>Match Status</th></tr>`;
        tbody.innerHTML = vs.top_shared_represented_variables.filter(r => !q || JSON.stringify(r).toLowerCase().includes(q)).map(r => `
          <tr>
            <td class="mono"><strong>${esc(r.represented_variable_id)}</strong></td>
            <td>${esc(r.anchor_label_or_question)}</td>
            <td><span class="badge badge-info">${esc(r.representation_type)} (${esc(r.canonical_data_type)})</span><br><span style="font-size:0.78rem;color:var(--text-muted)">${esc(r.domain_summary)}</span></td>
            <td class="mono">${Object.entries(r.instances_by_survey).map(([sk, vl]) => `<strong>${esc(sk)}</strong>: ${esc(vl.join(','))}`).join(' → ')}</td>
            <td>${r.strict_match ? '<span class="badge badge-success">Strict Exact</span>' : `<span class="badge badge-warning" title="${esc(r.sentinel_variation_note)}">Substantive Exact (Sentinel Diff)</span>`}</td>
          </tr>
        `).join('');
      } else if (mode === 'DRIFT') {
        thead.innerHTML = `<tr><th>Question / Concept</th><th>Drift Classifications</th><th>Waves Involved</th><th>Representation Variants Across Waves</th></tr>`;
        tbody.innerHTML = vs.representation_drift_findings.filter(d => !q || JSON.stringify(d).toLowerCase().includes(q)).map(d => `
          <tr>
            <td><strong>${esc(d.concept_or_question)}</strong></td>
            <td>${d.drift_types.map(t => `<span class="badge badge-warning">${esc(t)}</span>`).join(' ')}</td>
            <td class="mono">${esc(d.surveys_involved.join(', '))}</td>
            <td>${d.variants.map(v => `• <strong>${esc(v.representation)}</strong> <span class="mono" style="color:var(--text-muted)">[Waves: ${esc(v.surveys.join(', '))} | Vars: ${esc(v.variables.join(', '))}]</span>`).join('<br>')}</td>
          </tr>
        `).join('');
      } else {
        thead.innerHTML = `<tr><th>Physical Variable Name</th><th>Distinct Concepts</th><th>Waves Involved</th><th>Wave-by-Wave Meaning Collision</th></tr>`;
        tbody.innerHTML = vs.false_friend_variables.filter(f => !q || JSON.stringify(f).toLowerCase().includes(q)).map(f => `
          <tr>
            <td class="mono"><span class="badge badge-danger">${esc(f.variable_name)}</span></td>
            <td class="mono">${f.distinct_concepts_count}</td>
            <td class="mono">${esc(f.surveys_involved.join(', '))}</td>
            <td>${f.usages.map(u => `<strong>${esc(u.survey)}</strong>: ${esc(u.label)} <span style="color:var(--text-muted)">(${esc(u.question)})</span>`).join('<br>')}</td>
          </tr>
        `).join('');
      }
    }

    initApp();
  </script>
</body>
</html>
"""


def render_collection_explorer_html(
    report: CollectionComparisonReport,
    output_path: str | Path | None = None,
) -> str:
    """Renders the standalone interactive HTML Collection Explorer."""
    payload_json = json.dumps(report.model_dump(mode="json"), ensure_ascii=False)
    html = COLLECTION_EXPLORER_TEMPLATE.replace("__REPORT_TITLE__", report.title).replace(
        "__REPORT_JSON_PAYLOAD__", payload_json
    )
    if output_path is not None:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")
    return html
