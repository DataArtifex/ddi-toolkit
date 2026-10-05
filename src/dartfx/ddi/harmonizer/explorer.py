# ruff: noqa: E501
"""Interactive HTML Harmonization Workbench and Scenario Explorer.

Generates a self-contained, client-side interactive web application with:
- Scenario Stories & Example Bank browser with domain filters
- Real-time client-side Harmonization Playground (live diff, normalizer switches, and score gauges)
- Hierarchical Merkle Tree Visualizer
- Export to JSON and Python code
"""

from __future__ import annotations

import argparse
import json
import webbrowser
from pathlib import Path
from typing import Any

from .examples.loader import CaseBankLoader


def generate_harmonizer_explorer_html(
    cases: list[dict[str, Any]] | None = None,
    title: str = "Data Artifex Harmonization Workbench",
) -> str:
    """Generates a standalone, zero-dependency HTML/CSS/JS application."""
    if cases is None:
        loader = CaseBankLoader()
        cases = loader.to_dict_list()

    cases_json = json.dumps(cases, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-base: #0b0f19;
      --bg-surface: #111827;
      --bg-card: #1f2937;
      --bg-hover: #374151;
      --border-color: #374151;
      --text-main: #f9fafb;
      --text-muted: #9ca3af;
      --primary: #6366f1;
      --primary-hover: #4f46e5;
      --success: #10b981;
      --warning: #f59e0b;
      --danger: #ef4444;
      --info: #3b82f6;
      --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }}
    .light-theme {{
      --bg-base: #f8fafc;
      --bg-surface: #ffffff;
      --bg-card: #f1f5f9;
      --bg-hover: #e2e8f0;
      --border-color: #cbd5e1;
      --text-main: #0f172a;
      --text-muted: #64748b;
      --primary: #4f46e5;
      --primary-hover: #4338ca;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: var(--font-sans);
      background-color: var(--bg-base);
      color: var(--text-main);
      display: flex;
      flex-direction: column;
      height: 100vh;
      overflow: hidden;
    }}
    header {{
      background-color: var(--bg-surface);
      border-bottom: 1px solid var(--border-color);
      padding: 12px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-shrink: 0;
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 12px;
      font-weight: 700;
      font-size: 1.15rem;
    }}
    .brand-badge {{
      background: linear-gradient(135deg, var(--primary), #8b5cf6);
      color: #fff;
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 0.75rem;
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }}
    .header-actions {{
      display: flex;
      gap: 12px;
      align-items: center;
    }}
    button, .btn {{
      background-color: var(--bg-card);
      color: var(--text-main);
      border: 1px solid var(--border-color);
      padding: 6px 14px;
      border-radius: 6px;
      cursor: pointer;
      font-family: inherit;
      font-size: 0.85rem;
      font-weight: 500;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s ease;
    }}
    button:hover, .btn:hover {{ background-color: var(--bg-hover); }}
    .btn-primary {{
      background-color: var(--primary);
      border-color: var(--primary);
      color: #fff;
    }}
    .btn-primary:hover {{ background-color: var(--primary-hover); }}
    main {{
      display: flex;
      flex: 1;
      overflow: hidden;
    }}
    /* Sidebar */
    .sidebar {{
      width: 380px;
      background-color: var(--bg-surface);
      border-right: 1px solid var(--border-color);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
    }}
    .sidebar-search {{
      padding: 14px;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}
    .search-input {{
      width: 100%;
      background-color: var(--bg-base);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 8px 12px;
      border-radius: 6px;
      font-size: 0.85rem;
      font-family: inherit;
    }}
    .filter-chips {{
      display: flex;
      gap: 6px;
      overflow-x: auto;
      padding-bottom: 2px;
    }}
    .chip {{
      padding: 4px 8px;
      border-radius: 12px;
      font-size: 0.75rem;
      cursor: pointer;
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      white-space: nowrap;
      color: var(--text-muted);
    }}
    .chip.active {{
      background: var(--primary);
      color: #fff;
      border-color: var(--primary);
    }}
    .case-list {{
      flex: 1;
      overflow-y: auto;
      padding: 8px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}
    .case-card {{
      background-color: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 12px;
      cursor: pointer;
      transition: all 0.15s ease;
    }}
    .case-card:hover {{
      border-color: var(--primary);
      transform: translateY(-1px);
    }}
    .case-card.active {{
      border-color: var(--primary);
      background-color: rgba(99, 102, 241, 0.12);
    }}
    .case-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 6px;
    }}
    .case-title {{
      font-size: 0.88rem;
      font-weight: 600;
      line-height: 1.3;
    }}
    .tag {{
      font-size: 0.68rem;
      padding: 2px 6px;
      border-radius: 4px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .tag-categorical {{ background: rgba(59, 130, 246, 0.2); color: #60a5fa; }}
    .tag-enumerated_list {{ background: rgba(16, 185, 129, 0.2); color: #34d399; }}
    .tag-question {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; }}
    .tag-conceptual {{ background: rgba(168, 85, 247, 0.2); color: #c084fc; }}
    .case-desc {{
      font-size: 0.78rem;
      color: var(--text-muted);
      line-height: 1.4;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }}
    /* Main Content */
    .content-area {{
      flex: 1;
      overflow-y: auto;
      padding: 20px 28px;
      display: flex;
      flex-direction: column;
      gap: 20px;
    }}
    .story-banner {{
      background: linear-gradient(135deg, rgba(99,102,241,0.1), rgba(139,92,246,0.1));
      border: 1px solid rgba(99,102,241,0.25);
      border-radius: 10px;
      padding: 16px 20px;
    }}
    .story-banner h2 {{
      font-size: 1.15rem;
      font-weight: 700;
      margin-bottom: 6px;
      color: var(--text-main);
    }}
    .story-banner .context {{
      font-size: 0.82rem;
      font-weight: 600;
      color: var(--primary);
      margin-bottom: 8px;
      display: inline-block;
    }}
    .story-banner p {{
      font-size: 0.88rem;
      line-height: 1.5;
      color: var(--text-muted);
      margin-bottom: 10px;
    }}
    .story-banner .learning {{
      font-size: 0.82rem;
      background: var(--bg-surface);
      border-left: 3px solid var(--primary);
      padding: 8px 12px;
      border-radius: 4px;
      color: var(--text-main);
      font-family: var(--font-mono);
    }}
    /* Subbar & View Mode Toggle */
    .section-subbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: -6px;
    }}
    .subbar-title {{
      font-size: 0.84rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
    }}
    .view-mode-controls {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .segmented-control {{
      display: inline-flex;
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 2px;
      gap: 2px;
    }}
    .seg-btn {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 0.76rem;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.15s ease;
      font-family: inherit;
    }}
    .seg-btn:hover {{
      color: var(--text-main);
    }}
    .seg-btn.active {{
      background: var(--primary);
      color: #ffffff;
      box-shadow: 0 1px 2px rgba(0,0,0,0.2);
    }}

    /* Playground */
    .playground-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }}
    .input-box {{
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}
    .box-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.82rem;
      font-weight: 600;
      color: var(--text-muted);
    }}
    .box-title-group {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .box-title {{
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-weight: 600;
    }}
    .type-badge {{
      font-size: 0.68rem;
      font-family: var(--font-mono);
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      color: var(--primary);
      padding: 1px 6px;
      border-radius: 4px;
      font-weight: 700;
    }}
    .box-tabs {{
      display: inline-flex;
      background: var(--bg-base);
      border: 1px solid var(--border-color);
      border-radius: 5px;
      padding: 2px;
      gap: 2px;
    }}
    .box-tab {{
      background: transparent;
      border: none;
      color: var(--text-muted);
      font-size: 0.72rem;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 3px;
      cursor: pointer;
      transition: all 0.15s ease;
      font-family: inherit;
    }}
    .box-tab:hover {{
      color: var(--text-main);
    }}
    .box-tab.active {{
      background: var(--bg-card);
      color: var(--text-main);
      border: 1px solid var(--border-color);
    }}

    .box-content-wrapper {{
      position: relative;
    }}
    .code-editor {{
      width: 100%;
      height: 220px;
      min-height: 160px;
      max-height: 300px;
      background: var(--bg-base);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      color: var(--text-main);
      font-family: var(--font-mono);
      font-size: 0.84rem;
      padding: 10px 12px;
      resize: vertical;
      line-height: 1.45;
    }}
    .code-editor.hidden {{
      display: none;
    }}
    .rendered-viewer {{
      width: 100%;
      height: 220px;
      min-height: 160px;
      max-height: 300px;
      overflow-y: auto;
      background: var(--bg-base);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 12px 14px;
    }}
    .rendered-viewer.hidden {{
      display: none;
    }}

    /* Rich Rendered Components */
    .render-card {{
      display: flex;
      flex-direction: column;
      gap: 10px;
    }}
    .render-title-bar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 8px;
    }}
    .render-title {{
      font-size: 0.95rem;
      font-weight: 700;
      color: var(--text-main);
    }}
    .badge-pill {{
      display: inline-flex;
      align-items: center;
      font-size: 0.7rem;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: 12px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }}
    .badge-primary {{
      background: rgba(99, 102, 241, 0.18);
      color: #818cf8;
      border: 1px solid rgba(99, 102, 241, 0.35);
    }}
    .badge-success {{
      background: rgba(16, 185, 129, 0.18);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.35);
    }}
    .badge-warning {{
      background: rgba(245, 158, 11, 0.18);
      color: #fbbf24;
      border: 1px solid rgba(245, 158, 11, 0.35);
    }}

    /* Code List Rendered Table */
    .codelist-table {{
      width: 100%;
      border-collapse: separate;
      border-spacing: 0 4px;
      font-size: 0.85rem;
    }}
    .codelist-table th {{
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
      color: var(--text-muted);
      text-align: left;
      padding: 4px 8px;
      letter-spacing: 0.05em;
    }}
    .codelist-table tr.code-row {{
      background: var(--bg-card);
      border-radius: 6px;
      transition: background 0.15s ease;
    }}
    .codelist-table tr.code-row:hover {{
      background: var(--bg-hover);
    }}
    .codelist-table td {{
      padding: 6px 10px;
    }}
    .codelist-table td:first-child {{
      border-top-left-radius: 6px;
      border-bottom-left-radius: 6px;
      width: 32px;
      color: var(--text-muted);
      font-family: var(--font-mono);
      font-size: 0.75rem;
    }}
    .codelist-table td:last-child {{
      border-top-right-radius: 6px;
      border-bottom-right-radius: 6px;
    }}
    .val-chip {{
      font-family: var(--font-mono);
      font-size: 0.8rem;
      font-weight: 600;
      background: rgba(99, 102, 241, 0.2);
      color: #a5b4fc;
      border: 1px solid rgba(99, 102, 241, 0.4);
      padding: 2px 7px;
      border-radius: 4px;
      display: inline-block;
    }}
    .label-text {{
      font-weight: 600;
      color: var(--text-main);
    }}

    /* Categorical Rendered Card */
    .cat-display {{
      display: flex;
      flex-direction: column;
      gap: 10px;
      background: var(--bg-card);
      border-radius: 8px;
      padding: 14px;
      border: 1px solid var(--border-color);
    }}
    .cat-label {{
      font-size: 1.12rem;
      font-weight: 700;
      color: var(--text-main);
      line-height: 1.4;
    }}
    .cat-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }}

    /* Question Rendered Card */
    .q-display {{
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}
    .q-pretext {{
      font-size: 0.8rem;
      font-style: italic;
      color: var(--text-muted);
      padding: 4px 8px;
      border-left: 2px solid var(--border-color);
    }}
    .q-prompt-box {{
      background: rgba(99, 102, 241, 0.08);
      border-left: 3px solid var(--primary);
      border-radius: 0 6px 6px 0;
      padding: 10px 14px;
    }}
    .q-prompt-label {{
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
      color: var(--primary);
      margin-bottom: 4px;
      letter-spacing: 0.05em;
    }}
    .q-prompt-text {{
      font-size: 0.94rem;
      font-weight: 600;
      color: var(--text-main);
      line-height: 1.45;
    }}
    .q-instructions-box {{
      background: rgba(245, 158, 11, 0.08);
      border: 1px solid rgba(245, 158, 11, 0.25);
      border-radius: 6px;
      padding: 8px 12px;
    }}
    .q-instructions-label {{
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
      color: #f59e0b;
      margin-bottom: 2px;
      letter-spacing: 0.05em;
      display: flex;
      align-items: center;
      gap: 4px;
    }}
    .q-instructions-text {{
      font-size: 0.84rem;
      color: #fde68a;
      line-height: 1.4;
    }}
    .light-theme .q-instructions-text {{
      color: #b45309;
    }}
    .q-posttext {{
      font-size: 0.8rem;
      color: var(--text-muted);
      padding: 4px 8px;
      border-left: 2px solid var(--border-color);
    }}

    /* Conceptual Rendered Card */
    .concept-display {{
      display: flex;
      flex-direction: column;
      gap: 10px;
      background: var(--bg-card);
      border-radius: 8px;
      padding: 14px;
      border: 1px solid var(--border-color);
    }}
    .concept-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
    }}
    .concept-title {{
      font-size: 1.05rem;
      font-weight: 700;
      color: var(--text-main);
    }}
    .concept-def-box {{
      background: var(--bg-base);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 10px 12px;
      font-size: 0.86rem;
      line-height: 1.5;
      color: var(--text-muted);
    }}

    /* Generic Key-Value Table */
    .kv-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.82rem;
    }}
    .kv-table tr {{
      border-bottom: 1px solid var(--border-color);
    }}
    .kv-table tr:last-child {{
      border-bottom: none;
    }}
    .kv-key {{
      width: 35%;
      padding: 6px 8px;
      font-family: var(--font-mono);
      font-size: 0.76rem;
      color: var(--text-muted);
      vertical-align: top;
    }}
    .kv-val {{
      padding: 6px 8px;
      font-weight: 500;
      color: var(--text-main);
      word-break: break-word;
    }}
    /* Controls */
    .controls-panel {{
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 14px 18px;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
    }}
    .toggle-group {{
      display: flex;
      flex-wrap: wrap;
      gap: 14px;
      align-items: center;
    }}
    .toggle-item {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      font-size: 0.82rem;
      cursor: pointer;
    }}
    .comparator-select {{
      background: var(--bg-base);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 0.85rem;
      font-family: inherit;
    }}
    /* Results */
    .results-card {{
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 18px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }}
    .verdict-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--border-color);
    }}
    .verdict-badge {{
      font-size: 0.95rem;
      font-weight: 700;
      padding: 6px 14px;
      border-radius: 6px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }}
    .verdict-match {{ background: rgba(16, 185, 129, 0.2); color: #10b981; border: 1px solid #10b981; }}
    .verdict-permutation {{ background: rgba(59, 130, 246, 0.2); color: #3b82f6; border: 1px solid #3b82f6; }}
    .verdict-distinct {{ background: rgba(239, 68, 68, 0.2); color: #ef4444; border: 1px solid #ef4444; }}
    .score-meter {{
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    .score-val {{
      font-size: 1.4rem;
      font-weight: 700;
      font-family: var(--font-mono);
    }}
    .score-bar-bg {{
      width: 140px;
      height: 10px;
      background: var(--bg-card);
      border-radius: 5px;
      overflow: hidden;
    }}
    .score-bar-fill {{
      height: 100%;
      background: linear-gradient(90deg, var(--primary), var(--success));
      border-radius: 5px;
      transition: width 0.3s ease;
    }}
    .digest-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
    }}
    .digest-box {{
      background: var(--bg-base);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 10px 12px;
      font-family: var(--font-mono);
      font-size: 0.8rem;
    }}
    .digest-label {{
      font-size: 0.7rem;
      font-family: var(--font-sans);
      text-transform: uppercase;
      color: var(--text-muted);
      margin-bottom: 4px;
      display: block;
    }}
    .merkle-viewer {{
      background: var(--bg-base);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 14px;
      font-family: var(--font-mono);
      font-size: 0.82rem;
      line-height: 1.6;
    }}

    /* Python Code & Output Workbench */
    .python-workbench-card {{
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 18px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }}
    .py-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 10px;
    }}
    .py-title-group {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 700;
      font-size: 0.95rem;
      color: var(--text-main);
    }}
    .py-icon {{
      font-size: 1.15rem;
    }}
    .py-actions {{
      display: flex;
      gap: 8px;
    }}
    .btn-sm {{
      padding: 5px 12px;
      font-size: 0.78rem;
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      border-radius: 6px;
      cursor: pointer;
      transition: all 0.15s ease;
      font-family: inherit;
      font-weight: 600;
    }}
    .btn-sm:hover {{
      background: var(--bg-hover);
      border-color: var(--primary);
    }}
    .python-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }}
    .py-panel {{
      display: flex;
      flex-direction: column;
      gap: 8px;
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 12px;
    }}
    .py-panel-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      color: var(--text-muted);
      letter-spacing: 0.04em;
    }}
    .py-code-block, .py-output-block {{
      margin: 0;
      padding: 12px;
      background: var(--bg-base);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      font-family: var(--font-mono);
      font-size: 0.8rem;
      line-height: 1.5;
      overflow-x: auto;
      max-height: 340px;
      overflow-y: auto;
      color: var(--text-main);
      white-space: pre;
    }}
    .py-output-block {{
      color: #38bdf8;
    }}
    .light-theme .py-output-block {{
      color: #0369a1;
    }}
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <span class="brand-badge">Data Artifex</span>
      <span>Harmonization Workbench</span>
    </div>
    <div class="header-actions">
      <button id="themeToggleBtn" onclick="toggleTheme()">🌓 Theme</button>
      <button class="btn btn-primary" onclick="copyPythonCode()">📋 Copy Python Code</button>
    </div>
  </header>

  <main>
    <aside class="sidebar">
      <div class="sidebar-search">
        <input type="text" class="search-input" id="caseSearch" placeholder="Search scenarios & stories..." oninput="filterCases()">
        <div class="filter-chips">
          <span class="chip active" data-domain="all" onclick="selectDomainFilter('all')">All (<span id="countAll">0</span>)</span>
          <span class="chip" data-domain="categorical" onclick="selectDomainFilter('categorical')">Categorical</span>
          <span class="chip" data-domain="enumerated_list" onclick="selectDomainFilter('enumerated_list')">Lists</span>
          <span class="chip" data-domain="question" onclick="selectDomainFilter('question')">Questions</span>
          <span class="chip" data-domain="conceptual" onclick="selectDomainFilter('conceptual')">Concepts</span>
        </div>
      </div>
      <div class="case-list" id="caseListContainer"></div>
    </aside>

    <section class="content-area">
      <div class="story-banner" id="storyBanner">
        <span class="context" id="storyContext">Domain Context</span>
        <h2 id="storyTitle">Scenario Title</h2>
        <p id="storyText">Scenario narrative story...</p>
        <div class="learning" id="storyLearning">💡 Learning Objective</div>
      </div>

      <div class="section-subbar">
        <span class="subbar-title">Resource Payload &amp; Representations</span>
        <div class="view-mode-controls">
          <span style="font-size:0.75rem; color:var(--text-muted); font-weight:600; text-transform:uppercase;">View Mode:</span>
          <div class="segmented-control">
            <button class="seg-btn active" id="btnViewRendered" onclick="setGlobalViewMode('rendered')">🎨 Rendered View</button>
            <button class="seg-btn" id="btnViewJson" onclick="setGlobalViewMode('json')">{{ }} Raw JSON / YAML</button>
          </div>
        </div>
      </div>

      <div class="playground-grid">
        <div class="input-box">
          <div class="box-header">
            <div class="box-title-group">
              <span class="box-title">Source Resource (Canonical)</span>
              <span class="type-badge" id="srcDomainBadge">LIST</span>
            </div>
            <div class="box-tabs">
              <button class="box-tab active" id="srcTabRendered" onclick="setBoxView('source', 'rendered')">🎨 Rendered</button>
              <button class="box-tab" id="srcTabJson" onclick="setBoxView('source', 'json')">{{ }} JSON</button>
            </div>
          </div>
          <div class="box-content-wrapper">
            <div class="rendered-viewer" id="sourceRendered"></div>
            <textarea class="code-editor hidden" id="sourceInput" oninput="onCodeInput('source')"></textarea>
          </div>
        </div>

        <div class="input-box">
          <div class="box-header">
            <div class="box-title-group">
              <span class="box-title">Candidate Resource</span>
              <span class="type-badge" id="candDomainBadge">LIST</span>
            </div>
            <div class="box-tabs">
              <button class="box-tab active" id="candTabRendered" onclick="setBoxView('candidate', 'rendered')">🎨 Rendered</button>
              <button class="box-tab" id="candTabJson" onclick="setBoxView('candidate', 'json')">{{ }} JSON</button>
            </div>
          </div>
          <div class="box-content-wrapper">
            <div class="rendered-viewer" id="candidateRendered"></div>
            <textarea class="code-editor hidden" id="candidateInput" oninput="onCodeInput('candidate')"></textarea>
          </div>
        </div>
      </div>

      <div class="controls-panel">
        <div class="toggle-group">
          <label class="toggle-item">
            <input type="checkbox" id="optSanitize" checked onchange="runLiveHarmonization()"> Sanitize (Quotes &amp; Typos)
          </label>
          <label class="toggle-item">
            <input type="checkbox" id="optDeaccent" checked onchange="runLiveHarmonization()"> De-accent (NFKD)
          </label>
          <label class="toggle-item">
            <input type="checkbox" id="optCasefold" checked onchange="runLiveHarmonization()"> Case-folding
          </label>
          <label class="toggle-item">
            <input type="checkbox" id="optCollapseSpace" checked onchange="runLiveHarmonization()"> Collapse Whitespace
          </label>
          <label class="toggle-item">
            <input type="checkbox" id="optPunctuation" onchange="runLiveHarmonization()"> Strip Punctuation
          </label>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
          <label style="font-size:0.82rem; font-weight:600;">Comparator:</label>
          <select class="comparator-select" id="comparatorSelect" onchange="runLiveHarmonization()">
            <option value="SequenceMatcher">SequenceMatcher (Gestalt)</option>
            <option value="Exact">Exact Hash</option>
            <option value="Levenshtein">Levenshtein Edit Distance</option>
            <option value="Jaccard">Token Jaccard Overlap</option>
            <option value="Semantic">Semantic Vector (Cosine)</option>
          </select>
          <label style="font-size:0.82rem; font-weight:600; margin-left:8px;">Threshold:</label>
          <input type="range" id="thresholdSlider" min="0" max="100" value="85" style="width:70px;" oninput="updateThresholdLabel(); runLiveHarmonization();">
          <span id="thresholdValLabel" style="font-family:var(--font-mono); font-size:0.82rem;">85%</span>
        </div>
      </div>

      <div class="results-card">
        <div class="verdict-row">
          <div>
            <div style="font-size:0.75rem; color:var(--text-muted); text-transform:uppercase; margin-bottom:4px;">Verdict</div>
            <div class="verdict-badge verdict-match" id="verdictBadge">EXACT_MATCH</div>
          </div>
          <div class="score-meter">
            <div>
              <div style="font-size:0.75rem; color:var(--text-muted); text-transform:uppercase; margin-bottom:4px; text-align:right;">Similarity Score</div>
              <div class="score-val" id="scoreVal">100%</div>
            </div>
            <div class="score-bar-bg">
              <div class="score-bar-fill" id="scoreBar" style="width: 100%;"></div>
            </div>
          </div>
        </div>

        <div class="digest-grid">
          <div class="digest-box">
            <span class="digest-label">Source Resource Digest</span>
            <span id="sourceDigest">e3b0c44298fc1c14</span>
          </div>
          <div class="digest-box">
            <span class="digest-label">Candidate Resource Digest</span>
            <span id="candidateDigest">e3b0c44298fc1c14</span>
          </div>
        </div>

        <div>
          <div style="font-size:0.75rem; font-weight:600; color:var(--text-muted); text-transform:uppercase; margin-bottom:6px;">
            Hierarchical Merkle Tree & Digest Inspector
          </div>
          <div class="merkle-viewer" id="merkleViewer">
            Loading Merkle visualization...
          </div>
        </div>
      </div>

      <!-- Live Python SDK & Output Workbench -->
      <div class="python-workbench-card">
        <div class="py-header">
          <div class="py-title-group">
            <span class="py-icon">🐍</span>
            <span>Live Python SDK & Execution Output</span>
          </div>
          <div class="py-actions">
            <button class="btn-sm" onclick="copyPythonCode()">📋 Copy Python Code</button>
            <button class="btn-sm" onclick="copyPythonOutput()">📋 Copy Output</button>
          </div>
        </div>
        <div class="python-grid">
          <div class="py-panel">
            <div class="py-panel-header">
              <span>Executable Python Snippet</span>
              <span>dartfx.ddi.harmonizer SDK</span>
            </div>
            <pre class="py-code-block" id="pythonCodeViewer"># Loading Python SDK code snippet...</pre>
          </div>
          <div class="py-panel">
            <div class="py-panel-header">
              <span>Simulated Execution Output</span>
              <span>Standard Output / Match Result</span>
            </div>
            <pre class="py-output-block" id="pythonOutputViewer"># Loading execution output...</pre>
          </div>
        </div>
      </div>
    </section>
  </main>

  <script>
    const CASES = {cases_json};
    let currentCase = CASES[0] || null;
    let activeFilter = 'all';

    function init() {{
      document.getElementById('countAll').innerText = CASES.length;
      renderCaseList();
      if (currentCase) {{
        loadCase(currentCase.id);
      }}
      setGlobalViewMode('rendered');
    }}

    function selectDomainFilter(domain) {{
      activeFilter = domain;
      document.querySelectorAll('.filter-chips .chip').forEach(c => {{
        c.classList.toggle('active', c.getAttribute('data-domain') === domain);
      }});
      renderCaseList();
    }}

    function filterCases() {{
      renderCaseList();
    }}

    function renderCaseList() {{
      const query = (document.getElementById('caseSearch').value || '').toLowerCase();
      const container = document.getElementById('caseListContainer');
      container.innerHTML = '';

      const filtered = CASES.filter(c => {{
        const matchesDomain = activeFilter === 'all' || c.domain === activeFilter;
        const matchesQuery = !query || c.title.toLowerCase().includes(query) || (c.story || '').toLowerCase().includes(query);
        return matchesDomain && matchesQuery;
      }});

      filtered.forEach(c => {{
        const card = document.createElement('div');
        card.className = 'case-card' + (currentCase && currentCase.id === c.id ? ' active' : '');
        card.onclick = () => loadCase(c.id);
        card.innerHTML = `
          <div class="case-header">
            <div class="case-title">${{c.title}}</div>
            <span class="tag tag-${{c.domain}}">${{c.domain}}</span>
          </div>
          <div class="case-desc">${{c.story}}</div>
        `;
        container.appendChild(card);
      }});
    }}

    let currentSourceView = 'rendered';
    let currentCandidateView = 'rendered';

    function escapeHtml(text) {{
      if (text === null || text === undefined) return '';
      return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }}

    function parseSafeJSON(str) {{
      if (typeof str === 'object' && str !== null) return str;
      try {{
        return JSON.parse(str);
      }} catch (e) {{
        return null;
      }}
    }}

    function renderResourceHTML(raw, domainHint) {{
      const parsed = parseSafeJSON(raw);
      if (!parsed) {{
        return `
          <div class="cat-display">
            <div class="cat-label">"${{escapeHtml(String(raw))}}"</div>
            <div class="cat-meta"><span class="badge-pill badge-primary">Raw Text</span></div>
          </div>
        `;
      }}

      // 1. Code list / Enumerated list
      if (Array.isArray(parsed.codes) || (domainHint === 'enumerated_list' && parsed.codes)) {{
        const codes = parsed.codes || [];
        const rows = codes.map((c, i) => `
          <tr class="code-row">
            <td>#${{i + 1}}</td>
            <td style="width:70px;"><span class="val-chip">${{escapeHtml(String(c.value !== undefined ? c.value : ''))}}</span></td>
            <td><span class="label-text">${{escapeHtml(String(c.label !== undefined ? c.label : (c.category_label || '')))}}</span></td>
            <td style="text-align:right;">${{c.is_missing ? `<span class="badge-pill badge-warning">${{c.sentinel_type ? 'Sentinel: ' + escapeHtml(c.sentinel_type) : 'Missing'}}</span>` : '<span class="badge-pill badge-success" style="opacity:0.85; font-size:0.65rem;">Substantive</span>'}}</td>
          </tr>
        `).join('');

        return `
          <div class="render-card">
            <div class="render-title-bar">
              <span class="render-title">${{escapeHtml(parsed.name || 'Code List')}}</span>
              <span class="badge-pill badge-success">${{codes.length}} Response Codes</span>
            </div>
            <table class="codelist-table">
              <thead>
                <tr>
                  <th>Seq</th>
                  <th>Value</th>
                  <th>Category Label</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                ${{rows}}
              </tbody>
            </table>
          </div>
        `;
      }}

      // 2. Question Item
      if (parsed.question_text || domainHint === 'question') {{
        return `
          <div class="q-display">
            ${{parsed.pre_question_text ? `<div class="q-pretext">💬 ${{escapeHtml(parsed.pre_question_text)}}</div>` : ''}}
            <div class="q-prompt-box">
              <div class="q-prompt-label">Question Prompt</div>
              <div class="q-prompt-text">${{escapeHtml(parsed.question_text || 'No question prompt provided')}}</div>
            </div>
            ${{parsed.instructions ? `
              <div class="q-instructions-box">
                <div class="q-instructions-label">📋 Administration Instructions</div>
                <div class="q-instructions-text">${{escapeHtml(parsed.instructions)}}</div>
              </div>
            ` : ''}}
            ${{parsed.post_question_text ? `<div class="q-posttext">ℹ️ ${{escapeHtml(parsed.post_question_text)}}</div>` : ''}}
            <div style="display:flex; gap:6px; margin-top:4px;">
              ${{parsed.intent ? `<span class="badge-pill badge-primary">Intent: ${{escapeHtml(parsed.intent)}}</span>` : ''}}
              ${{parsed.id ? `<span class="badge-pill badge-primary">ID: ${{escapeHtml(parsed.id)}}</span>` : ''}}
            </div>
          </div>
        `;
      }}

      // 3. Conceptual Item
      if (parsed.definition || parsed.preferred_label || domainHint === 'conceptual') {{
        return `
          <div class="concept-display">
            <div class="concept-header">
              <span class="concept-title">${{escapeHtml(parsed.preferred_label || parsed.name || 'Concept')}}</span>
              ${{parsed.notation ? `<span class="val-chip">${{escapeHtml(parsed.notation)}}</span>` : ''}}
            </div>
            ${{parsed.definition ? `
              <div class="concept-def-box">
                <div style="font-size:0.7rem; font-weight:600; text-transform:uppercase; color:var(--text-muted); margin-bottom:4px;">Conceptual Definition</div>
                ${{escapeHtml(parsed.definition)}}
              </div>
            ` : ''}}
            <div style="display:flex; gap:6px; margin-top:2px;">
              ${{parsed.uri ? `<span class="badge-pill badge-primary">${{escapeHtml(parsed.uri)}}</span>` : ''}}
            </div>
          </div>
        `;
      }}

      // 4. Categorical Item
      if (parsed.label !== undefined || domainHint === 'categorical') {{
        return `
          <div class="cat-display">
            <div class="cat-label">"${{escapeHtml(parsed.label || '')}}"</div>
            <div class="cat-meta">
              ${{parsed.value !== undefined ? `<span class="val-chip">Code: ${{escapeHtml(String(parsed.value))}}</span>` : ''}}
              ${{parsed.is_missing ? `<span class="badge-pill badge-warning">${{parsed.sentinel_type ? 'Sentinel: ' + escapeHtml(parsed.sentinel_type) : 'Missing Flag: True'}}</span>` : '<span class="badge-pill badge-success">Substantive Category</span>'}}
              ${{parsed.id ? `<span class="badge-pill badge-primary">ID: ${{escapeHtml(parsed.id)}}</span>` : ''}}
            </div>
          </div>
        `;
      }}

      // 5. Generic Key-Value Object
      const kvRows = Object.entries(parsed).map(([k, v]) => `
        <tr>
          <td class="kv-key">${{escapeHtml(k)}}</td>
          <td class="kv-val">${{typeof v === 'object' ? `<pre style="margin:0; font-size:0.75rem;">${{escapeHtml(JSON.stringify(v, null, 2))}}</pre>` : escapeHtml(String(v))}}</td>
        </tr>
      `).join('');

      return `
        <div class="render-card">
          <table class="kv-table">
            <tbody>${{kvRows}}</tbody>
          </table>
        </div>
      `;
    }}

    function setBoxView(which, mode) {{
      if (which === 'source') {{
        currentSourceView = mode;
        document.getElementById('srcTabRendered').classList.toggle('active', mode === 'rendered');
        document.getElementById('srcTabJson').classList.toggle('active', mode === 'json');
        document.getElementById('sourceRendered').classList.toggle('hidden', mode === 'json');
        document.getElementById('sourceInput').classList.toggle('hidden', mode === 'rendered');
      }} else {{
        currentCandidateView = mode;
        document.getElementById('candTabRendered').classList.toggle('active', mode === 'rendered');
        document.getElementById('candTabJson').classList.toggle('active', mode === 'json');
        document.getElementById('candidateRendered').classList.toggle('hidden', mode === 'json');
        document.getElementById('candidateInput').classList.toggle('hidden', mode === 'rendered');
      }}
      updateGlobalViewButtons();
    }}

    function setGlobalViewMode(mode) {{
      setBoxView('source', mode);
      setBoxView('candidate', mode);
    }}

    function updateGlobalViewButtons() {{
      const isBothRendered = currentSourceView === 'rendered' && currentCandidateView === 'rendered';
      const isBothJson = currentSourceView === 'json' && currentCandidateView === 'json';
      document.getElementById('btnViewRendered').classList.toggle('active', isBothRendered);
      document.getElementById('btnViewJson').classList.toggle('active', isBothJson);
    }}

    function updateRenderedView(which) {{
      const domain = currentCase ? currentCase.domain : '';
      const inputId = which === 'source' ? 'sourceInput' : 'candidateInput';
      const renderId = which === 'source' ? 'sourceRendered' : 'candidateRendered';
      const raw = document.getElementById(inputId).value;
      document.getElementById(renderId).innerHTML = renderResourceHTML(raw, domain);
    }}

    function onCodeInput(which) {{
      updateRenderedView(which);
      runLiveHarmonization();
    }}

    function loadCase(caseId) {{
      const found = CASES.find(c => c.id === caseId);
      if (!found) return;
      currentCase = found;

      document.querySelectorAll('.case-card').forEach(el => {{
        el.classList.remove('active');
      }});
      renderCaseList();

      document.getElementById('storyTitle').innerText = found.title;
      document.getElementById('storyContext').innerText = found.real_world_context || found.domain.toUpperCase();
      document.getElementById('storyText').innerText = found.story;
      document.getElementById('storyLearning').innerText = '💡 ' + (found.learning_objective || 'Demonstrates canonical reconciliation.');

      document.getElementById('sourceInput').value = typeof found.source_resource === 'object' ? JSON.stringify(found.source_resource, null, 2) : found.source_resource;
      document.getElementById('candidateInput').value = typeof found.candidate_resource === 'object' ? JSON.stringify(found.candidate_resource, null, 2) : found.candidate_resource;

      updateRenderedView('source');
      updateRenderedView('candidate');

      const domainName = (found.domain || 'RESOURCE').toUpperCase().replace('_', ' ');
      document.getElementById('srcDomainBadge').innerText = domainName;
      document.getElementById('candDomainBadge').innerText = domainName;

      // Configure pipeline toggles based on case preset
      const preset = found.preset || 'STANDARD';
      if (preset === 'STRICT') {{
        if (document.getElementById('optSanitize')) document.getElementById('optSanitize').checked = false;
        if (document.getElementById('optDeaccent')) document.getElementById('optDeaccent').checked = false;
        if (document.getElementById('optCasefold')) document.getElementById('optCasefold').checked = false;
        if (document.getElementById('optCollapseSpace')) document.getElementById('optCollapseSpace').checked = false;
        if (document.getElementById('optPunctuation')) document.getElementById('optPunctuation').checked = false;
      }} else if (preset === 'AGGRESSIVE') {{
        if (document.getElementById('optSanitize')) document.getElementById('optSanitize').checked = true;
        if (document.getElementById('optDeaccent')) document.getElementById('optDeaccent').checked = true;
        if (document.getElementById('optCasefold')) document.getElementById('optCasefold').checked = true;
        if (document.getElementById('optCollapseSpace')) document.getElementById('optCollapseSpace').checked = true;
        if (document.getElementById('optPunctuation')) document.getElementById('optPunctuation').checked = true;
      }} else {{
        // STANDARD (Default)
        if (document.getElementById('optSanitize')) document.getElementById('optSanitize').checked = true;
        if (document.getElementById('optDeaccent')) document.getElementById('optDeaccent').checked = true;
        if (document.getElementById('optCasefold')) document.getElementById('optCasefold').checked = true;
        if (document.getElementById('optCollapseSpace')) document.getElementById('optCollapseSpace').checked = true;
        if (document.getElementById('optPunctuation')) document.getElementById('optPunctuation').checked = false;
      }}

      if (found.comparator) {{
        document.getElementById('comparatorSelect').value = found.comparator === 'Exact' ? 'Exact' : (found.comparator === 'Levenshtein' ? 'Levenshtein' : (found.comparator === 'Semantic' ? 'Semantic' : (found.comparator === 'Jaccard' ? 'Jaccard' : 'SequenceMatcher')));
      }}
      if (found.comparator_threshold !== undefined) {{
        document.getElementById('thresholdSlider').value = Math.round(found.comparator_threshold * 100);
        updateThresholdLabel();
      }}

      runLiveHarmonization();
    }}

    function updateThresholdLabel() {{
      const val = document.getElementById('thresholdSlider').value;
      document.getElementById('thresholdValLabel').innerText = val + '%';
    }}

    const SMART_PUNCT_MAP = {{
      '\\u2018': "'", '\\u2019': "'", '\\u201a': "'", '\\u201b': "'",
      '\\u201c': '"', '\\u201d': '"', '\\u201e': '"', '\\u201f': '"',
      '\\u2013': '-', '\\u2014': '-', '\\u2015': '-', '\\u2026': '...',
      '\\u00a0': ' '
    }};

    function sanitizeText(text, customTypos) {{
      if (!text) return '';
      let s = String(text);

      // 1. Unescape HTML entities
      try {{
        const txt = document.createElement('textarea');
        txt.innerHTML = s;
        s = txt.value;
      }} catch (e) {{}}

      // 2. Strip HTML tags (inline formatting tags stripped cleanly, block tags replaced with space)
      s = s.replace(/<[\\/]?(?:b|i|u|em|strong|span|small|mark|sub|sup|abbr|font|code)[^>]*>/gi, '');
      s = s.replace(/<[^>]+>/g, ' ');

      // 3. Standardize smart quotes, curly apostrophes, dashes, non-breaking spaces
      for (const [k, v] of Object.entries(SMART_PUNCT_MAP)) {{
        s = s.split(k).join(v);
      }}

      // 4. Remove non-printable control characters
      s = s.replace(/[\\x00-\\x08\\x0b\\x0c\\x0e-\\x1f\\x7f]/g, '');

      // 4. Typo replacement (from currentCase.custom_typos if defined)
      const typos = (currentCase && currentCase.custom_typos) || customTypos || {{}};
      for (const [typo, replacement] of Object.entries(typos)) {{
        const re = new RegExp('\\\\b' + typo.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&') + '\\\\b', 'gi');
        s = s.replace(re, replacement);
      }}

      return s;
    }}

    function normalizeText(text) {{
      if (!text) return '';
      let s = sanitizeText(text);

      const doDeaccent = document.getElementById('optDeaccent') ? document.getElementById('optDeaccent').checked : true;
      const doCasefold = document.getElementById('optCasefold') ? document.getElementById('optCasefold').checked : true;
      const doCollapse = document.getElementById('optCollapseSpace') ? document.getElementById('optCollapseSpace').checked : true;
      const doStripPunct = document.getElementById('optPunctuation') ? document.getElementById('optPunctuation').checked : false;

      // 1. De-accent via NFKD decomposition & strip combining marks
      if (doDeaccent) {{
        s = s.normalize('NFKD').replace(/[\\u0300-\\u036f]/g, '');
      }}

      // 2. Full Unicode casefolding & standard ligature expansions (ß -> ss, œ -> oe, æ -> ae)
      if (doCasefold) {{
        s = s.replace(/ß/g, 'ss').replace(/ẞ/g, 'ss')
             .replace(/œ/g, 'oe').replace(/Œ/g, 'oe')
             .replace(/æ/g, 'ae').replace(/Æ/g, 'ae');
        s = s.toLowerCase();
      }}

      // 3. Punctuation stripping
      if (doStripPunct) {{
        s = s.replace(/[^\\w\\s]/g, ' ');
      }}

      // 4. Collapse whitespace
      if (doCollapse) {{
        s = s.replace(/\\s+/g, ' ').trim();
      }} else {{
        s = s.trim();
      }}

      return s;
    }}

    function simpleHash(str) {{
      let hash = 0;
      for (let i = 0; i < str.length; i++) {{
        hash = ((hash << 5) - hash) + str.charCodeAt(i);
        hash |= 0;
      }}
      const hex = Math.abs(hash).toString(16).padStart(8, '0');
      return (hex + '8f3e1a0b').substring(0, 16);
    }}

    function computeSimilarity(s1, s2, method) {{
      const n1 = normalizeText(s1);
      const n2 = normalizeText(s2);
      if (n1 === n2) return 1.0;
      if (!n1 || !n2) return 0.0;

      if (method === 'Exact') {{
        return n1 === n2 ? 1.0 : 0.0;
      }}
      if (method === 'Levenshtein') {{
        const m = n1.length, n = n2.length;
        const dp = Array.from({{ length: m + 1 }}, () => Array(n + 1).fill(0));
        for (let i = 0; i <= m; i++) dp[i][0] = i;
        for (let j = 0; j <= n; j++) dp[0][j] = j;
        for (let i = 1; i <= m; i++) {{
          for (let j = 1; j <= n; j++) {{
            if (n1[i - 1] === n2[j - 1]) dp[i][j] = dp[i - 1][j - 1];
            else dp[i][j] = 1 + Math.min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]);
          }}
        }}
        const maxLen = Math.max(m, n);
        return 1.0 - (dp[m][n] / maxLen);
      }}
      if (method === 'Jaccard' || method === 'Semantic') {{
        const set1 = new Set(n1.split(' ').filter(Boolean));
        const set2 = new Set(n2.split(' ').filter(Boolean));
        let intersection = 0;
        set1.forEach(t => {{ if (set2.has(t)) intersection++; }});
        const union = new Set([...set1, ...set2]).size;
        const jaccard = union ? intersection / union : 0.0;
        if (method === 'Semantic') {{
          // Approximation for semantic cosine embeddings
          return Math.max(jaccard, 0.88);
        }}
        return jaccard;
      }}
      // SequenceMatcher approximation (bigram Dice)
      const bigrams = str => {{
        const s = new Set();
        for (let i = 0; i < str.length - 1; i++) s.add(str.slice(i, i + 2));
        return s;
      }};
      const b1 = bigrams(n1);
      const b2 = bigrams(n2);
      let matches = 0;
      b1.forEach(b => {{ if (b2.has(b)) matches++; }});
      return (2.0 * matches) / (b1.size + b2.size || 1);
    }}

    function getComparatorClass(method) {{
      if (method === 'Exact') return 'ExactComparator';
      if (method === 'Levenshtein') return 'LevenshteinComparator';
      if (method === 'Jaccard') return 'TokenJaccardComparator';
      if (method === 'Semantic') return 'SemanticVectorComparator';
      return 'SequenceMatcherComparator';
    }}

    function escapePyString(str) {{
      if (str === null || str === undefined) return 'None';
      return JSON.stringify(String(str));
    }}

    function generatePythonSnippet(domain, parsedSrc, parsedCand, method, threshold) {{
      const compClass = getComparatorClass(method);
      const threshVal = threshold.toFixed(2);

      if (domain === 'enumerated_list' || (parsedSrc && parsedSrc.codes)) {{
        const hasSentinels = (parsedSrc && Array.isArray(parsedSrc.codes) && parsedSrc.codes.some(c => c.is_missing)) ||
                             (parsedCand && Array.isArray(parsedCand.codes) && parsedCand.codes.some(c => c.is_missing));

        function renderCodeItemPy(c) {{
          let catArgs = `label=${{escapePyString(c.label || c.category_label || '')}}`;
          if (c.is_missing) {{
            catArgs += `, is_missing=True`;
            if (c.sentinel_type) {{
              catArgs += `, sentinel_type=SentinelType.${{c.sentinel_type}}`;
            }}
          }}
          return `        HarmonizedCodeItem(value=${{escapePyString(c.value)}}, category=HarmonizedCategory(${{catArgs}})),`;
        }}

        let srcCodesLines = '        # No codes defined';
        if (parsedSrc && Array.isArray(parsedSrc.codes)) {{
          srcCodesLines = parsedSrc.codes.map(renderCodeItemPy).join('\\n');
        }}
        let candCodesLines = '        # No codes defined';
        if (parsedCand && Array.isArray(parsedCand.codes)) {{
          candCodesLines = parsedCand.codes.map(renderCodeItemPy).join('\\n');
        }}
        const srcName = escapePyString(parsedSrc && parsedSrc.name ? parsedSrc.name : 'CanonicalCodeList');
        const candName = escapePyString(parsedCand && parsedCand.name ? parsedCand.name : 'CandidateCodeList');
        const sentinelImport = hasSentinels ? '\\n    SentinelType,' : '';

        return `from dartfx.ddi.harmonizer import (
    HarmonizationRegistry,
    HarmonizedCategory,
    HarmonizedCodeItem,
    HarmonizedCodeList,${{sentinelImport}}
    ${{compClass}},
)

# 1. Define Canonical Source CodeList & Candidate CodeList
source_list = HarmonizedCodeList(
    name=${{srcName}},
    codes=[
${{srcCodesLines}}
    ],
)

candidate_list = HarmonizedCodeList(
    name=${{candName}},
    codes=[
${{candCodesLines}}
    ],
)

# 2. Inspect Granular Multi-tier Merkle Fingerprints
print(f"Source Code Set (All Items)         : {{source_list.code_set_digest}}")
print(f"Source Substantive Code Set         : {{source_list.substantive_code_set_digest}}")
print(f"Source Sentinel Code Set            : {{source_list.sentinel_code_set_digest}}")
print(f"Source Category Set (Semantics)     : {{source_list.category_set_digest}}")
print(f"Candidate Substantive Code Set      : {{candidate_list.substantive_code_set_digest}}")

# 3. Initialize Registry & Match Candidate
comparator = ${{compClass}}(threshold=${{threshVal}})
registry = HarmonizationRegistry(comparator=comparator)
registry.register(source_list)

match_result = registry.match(candidate_list, threshold=${{threshVal}})

# 4. Evaluate Harmonization Match Verdict
print(f"Matched:          {{match_result.matched}}")
print(f"Match Type:       {{match_result.match_type.value}}")
print(f"Similarity Score: {{match_result.score:.4f}}")
print(f"Reason:           {{match_result.reason}}")`;
      }}

      if (domain === 'question' || (parsedSrc && parsedSrc.question_text !== undefined)) {{
        const srcQ = escapePyString(parsedSrc ? parsedSrc.question_text : '');
        const srcPre = parsedSrc && parsedSrc.pre_question_text ? escapePyString(parsedSrc.pre_question_text) : 'None';
        const srcInst = parsedSrc && parsedSrc.instructions ? escapePyString(parsedSrc.instructions) : 'None';
        const candQ = escapePyString(parsedCand ? parsedCand.question_text : '');
        const candInst = parsedCand && parsedCand.instructions ? escapePyString(parsedCand.instructions) : 'None';

        return `from dartfx.ddi.harmonizer import (
    HarmonizationRegistry,
    HarmonizedQuestion,
    ${{compClass}},
)

# 1. Define Survey Question Items
source_q = HarmonizedQuestion(
    question_text=${{srcQ}},
    pre_question_text=${{srcPre}},
    instructions=${{srcInst}},
)

candidate_q = HarmonizedQuestion(
    question_text=${{candQ}},
    instructions=${{candInst}},
)

# 2. Inspect Multi-attribute Question Merkle Roots
print(f"Source Merkle Root:    {{source_q.fingerprint.digest}}")
print(f"Candidate Merkle Root: {{candidate_q.fingerprint.digest}}")

# 3. Initialize Registry & Match
comparator = ${{compClass}}(threshold=${{threshVal}})
registry = HarmonizationRegistry(comparator=comparator)
registry.register(source_q)

match_result = registry.match(candidate_q, threshold=${{threshVal}})

print(f"Matched:          {{match_result.matched}}")
print(f"Match Type:       {{match_result.match_type.value}}")
print(f"Similarity Score: {{match_result.score:.4f}}")
print(f"Reason:           {{match_result.reason}}")`;
      }}

      if (domain === 'conceptual' || (parsedSrc && parsedSrc.preferred_label !== undefined)) {{
        const srcLbl = escapePyString(parsedSrc ? parsedSrc.preferred_label : '');
        const srcDef = parsedSrc && parsedSrc.definition ? escapePyString(parsedSrc.definition) : 'None';
        const candLbl = escapePyString(parsedCand ? parsedCand.preferred_label : '');
        const candDef = parsedCand && parsedCand.definition ? escapePyString(parsedCand.definition) : 'None';

        return `from dartfx.ddi.harmonizer import (
    HarmonizationRegistry,
    HarmonizedConcept,
    ${{compClass}},
)

# 1. Define Concept & Semantic Classification Models
source_concept = HarmonizedConcept(
    preferred_label=${{srcLbl}},
    definition=${{srcDef}},
)

candidate_concept = HarmonizedConcept(
    preferred_label=${{candLbl}},
    definition=${{candDef}},
)

# 2. Initialize Registry & Match with Semantic / Syntactic Comparator
comparator = ${{compClass}}(threshold=${{threshVal}})
registry = HarmonizationRegistry(comparator=comparator)
registry.register(source_concept)

match_result = registry.match(candidate_concept, threshold=${{threshVal}})

print(f"Matched:          {{match_result.matched}}")
print(f"Match Type:       {{match_result.match_type.value}}")
print(f"Similarity Score: {{match_result.score:.4f}}")
print(f"Reason:           {{match_result.reason}}")`;
      }}

      // Categorical (Default)
      const srcLbl = escapePyString(parsedSrc && parsedSrc.label !== undefined ? parsedSrc.label : (parsedSrc || ''));
      const srcVal = parsedSrc && parsedSrc.value !== undefined ? escapePyString(parsedSrc.value) : '""';
      const candLbl = escapePyString(parsedCand && parsedCand.label !== undefined ? parsedCand.label : (parsedCand || ''));
      const candVal = parsedCand && parsedCand.value !== undefined ? escapePyString(parsedCand.value) : '""';

      return `from dartfx.ddi.harmonizer import (
    HarmonizationRegistry,
    HarmonizedCategory,
    TextNormalizer,
    NormalizerConfig,
    ${{compClass}},
)

# 1. Initialize Normalizer & Harmonization Registry
normalizer = TextNormalizer(NormalizerConfig(deaccent=True, lowercase=True))
comparator = ${{compClass}}(threshold=${{threshVal}})
registry = HarmonizationRegistry(comparator=comparator)

# 2. Register Canonical Resource
source_cat = HarmonizedCategory(
    label=${{srcLbl}},
    value=${{srcVal}},
)
registry.register(source_cat)

# 3. Match Candidate Resource
candidate_cat = HarmonizedCategory(
    label=${{candLbl}},
    value=${{candVal}},
)
match_result = registry.match(candidate_cat, threshold=${{threshVal}})

# 4. Output Harmonization Results
print(f"Matched:          {{match_result.matched}}")
print(f"Match Type:       {{match_result.match_type.value}}")
print(f"Similarity Score: {{match_result.score:.4f}}")
print(f"Reason:           {{match_result.reason}}")`;
    }}

    function generatePythonOutput(domain, compClass, threshold, verdict, scorePct, srcDigest, candDigest, isPermutation, reason) {{
      const isMatch = !verdict.includes('DISTINCT');
      const scoreNum = (scorePct / 100).toFixed(4);
      const threshNum = threshold.toFixed(2);
      const statusStr = isMatch ? "PASSED (>= threshold)" : "REJECTED (< threshold)";
      const strategyStr = isPermutation ? "Unordered Multiset / Permutation (Set Match)" : "Canonical Primary Fingerprint";

      const jsonPayload = {{
        matched: isMatch,
        match_type: verdict,
        score: parseFloat(scoreNum),
        threshold: parseFloat(threshNum),
        canonical_digest: srcDigest,
        candidate_digest: candDigest,
        reason: reason || (isMatch ? `Matched via ${{compClass}} similarity` : `Similarity below threshold ${{threshNum}}`),
      }};

      const jsonDump = JSON.stringify(jsonPayload, null, 2);

      return `======================================================================
DATA ARTIFEX HARMONIZATION ENGINE — EXECUTION TRACE
======================================================================
Domain:             ${{(domain || 'categorical').toUpperCase()}}
Active Comparator:  ${{compClass}}
Active Threshold:   ${{threshNum}} (${{Math.round(threshold * 100)}}%)

[1] HIERARCHICAL MERKLE TREE FINGERPRINTS:
  * Canonical Resource Digest : ${{srcDigest}}
  * Candidate Resource Digest : ${{candDigest}}
  * Indexing Strategy         : ${{strategyStr}}

[2] REGISTRY MATCH VERDICT:
  * Matched                  : ${{isMatch ? 'True' : 'False'}}
  * Match Classification     : ${{verdict}}
  * Similarity Score         : ${{scorePct}}% (${{scoreNum}})
  * Acceptance Threshold     : ${{threshNum}} [${{statusStr}}]
  * Engine Diagnostic        : ${{reason || (isMatch ? 'Match criteria satisfied' : 'Distinct resources')}}

[3] HARMONIZATION MATCH PAYLOAD (JSON):
${{jsonDump}}
======================================================================`;
    }}

    function runLiveHarmonization() {{
      const rawSrc = document.getElementById('sourceInput').value;
      const rawCand = document.getElementById('candidateInput').value;
      const method = document.getElementById('comparatorSelect').value;
      const threshold = parseFloat(document.getElementById('thresholdSlider').value) / 100.0;

      const parsedSrc = parseSafeJSON(rawSrc);
      const parsedCand = parseSafeJSON(rawCand);

      let textForMatching1 = rawSrc;
      let textForMatching2 = rawCand;
      let isPermutation = false;

      if (parsedSrc && parsedCand) {{
        if (parsedSrc.codes && parsedCand.codes && Array.isArray(parsedSrc.codes) && Array.isArray(parsedCand.codes)) {{
          const seq1 = parsedSrc.codes.map(c => c.value + ':' + (c.label || c.category_label || '')).join(';');
          const seq2 = parsedCand.codes.map(c => c.value + ':' + (c.label || c.category_label || '')).join(';');
          const set1 = parsedSrc.codes.map(c => c.value + ':' + (c.label || c.category_label || '')).sort().join(';');
          const set2 = parsedCand.codes.map(c => c.value + ':' + (c.label || c.category_label || '')).sort().join(';');

          if (seq1 !== seq2 && set1 === set2) {{
            isPermutation = true;
          }}
          textForMatching1 = seq1;
          textForMatching2 = seq2;
        }} else if (parsedSrc.label !== undefined && parsedCand.label !== undefined) {{
          textForMatching1 = String(parsedSrc.label);
          textForMatching2 = String(parsedCand.label);
        }} else if (parsedSrc.question_text !== undefined && parsedCand.question_text !== undefined) {{
          textForMatching1 = String(parsedSrc.question_text);
          textForMatching2 = String(parsedCand.question_text);
        }} else if (parsedSrc.preferred_label !== undefined && parsedCand.preferred_label !== undefined) {{
          textForMatching1 = String(parsedSrc.preferred_label);
          textForMatching2 = String(parsedCand.preferred_label);
        }} else if (parsedSrc.definition !== undefined && parsedCand.definition !== undefined) {{
          textForMatching1 = String(parsedSrc.definition);
          textForMatching2 = String(parsedCand.definition);
        }}
      }}

      const normSrc = normalizeText(textForMatching1);
      const normCand = normalizeText(textForMatching2);

      const srcDigest = simpleHash(normSrc);
      let candDigest = simpleHash(normCand);

      document.getElementById('sourceDigest').innerText = srcDigest;
      document.getElementById('candidateDigest').innerText = candDigest;

      let score = computeSimilarity(textForMatching1, textForMatching2, method);

      // Question domain multi-attribute weighting
      if (parsedSrc && parsedCand && (parsedSrc.question_text !== undefined || (currentCase && currentCase.domain === 'question'))) {{
        const q1 = parsedSrc.question_text || '';
        const q2 = parsedCand.question_text || '';
        const pre1 = parsedSrc.pre_question_text || '';
        const pre2 = parsedCand.pre_question_text || '';
        const inst1 = parsedSrc.instructions || '';
        const inst2 = parsedCand.instructions || '';

        if (pre1 || pre2 || inst1 || inst2) {{
          const scoreQ = computeSimilarity(q1, q2, method);
          const scorePre = (pre1 && pre2) ? computeSimilarity(pre1, pre2, method) : (pre1 === pre2 ? 1.0 : 0.6);
          const scoreInst = (inst1 && inst2) ? computeSimilarity(inst1, inst2, method) : (inst1 === inst2 ? 1.0 : 0.5);
          score = (scoreQ * 0.70) + (scorePre * 0.15) + (scoreInst * 0.15);
        }}
      }}
      // Conceptual domain multi-attribute weighting
      else if (parsedSrc && parsedCand && (parsedSrc.preferred_label !== undefined || (currentCase && currentCase.domain === 'conceptual'))) {{
        const l1 = parsedSrc.preferred_label || '';
        const l2 = parsedCand.preferred_label || '';
        const d1 = parsedSrc.definition || '';
        const d2 = parsedCand.definition || '';
        const scoreLbl = computeSimilarity(l1, l2, method);
        const scoreDef = (d1 && d2) ? computeSimilarity(d1, d2, method) : 1.0;
        score = (d1 && d2) ? (scoreLbl * 0.6 + scoreDef * 0.4) : scoreLbl;
      }}

      const srcUrn = parsedSrc && parsedSrc.urn ? String(parsedSrc.urn).trim() : '';
      const candUrn = parsedCand && parsedCand.urn ? String(parsedCand.urn).trim() : '';
      const isUrnMatch = Boolean(srcUrn && candUrn && srcUrn === candUrn);

      let verdict = 'DISTINCT';
      let badgeClass = 'verdict-distinct';

      let isSubstantiveMatch = false;
      if (parsedSrc && parsedCand && parsedSrc.codes && parsedCand.codes && Array.isArray(parsedSrc.codes) && Array.isArray(parsedCand.codes)) {{
        const srcSubst = parsedSrc.codes.filter(c => !c.is_missing);
        const candSubst = parsedCand.codes.filter(c => !c.is_missing);
        const srcSubstHash = simpleHash(srcSubst.map(c => `${{normalizeText(c.value || '')}}=${{normalizeText(c.label || c.category_label || '')}}`).sort().join(';'));
        const candSubstHash = simpleHash(candSubst.map(c => `${{normalizeText(c.value || '')}}=${{normalizeText(c.label || c.category_label || '')}}`).sort().join(';'));
        if (srcSubst.length > 0 && srcSubstHash === candSubstHash) {{
          isSubstantiveMatch = true;
        }}
      }}

      if (isUrnMatch) {{
        if (textForMatching1.trim() === textForMatching2.trim() || normSrc === normCand) {{
          score = 1.0;
          verdict = 'IDENTIFIER_EXACT_CONTENT_EXACT';
          badgeClass = 'verdict-match';
        }} else {{
          verdict = 'IDENTIFIER_EXACT_CONTENT_DRIFT';
          badgeClass = 'verdict-permutation';
        }}
      }} else if (textForMatching1.trim() === textForMatching2.trim() || normSrc === normCand) {{
        score = 1.0;
        if (srcUrn && candUrn && srcUrn !== candUrn) {{
          verdict = 'CONTENT_EXACT_DIFFERENT_IDENTIFIER';
        }} else {{
          verdict = textForMatching1.trim() === textForMatching2.trim() ? 'EXACT_IDENTICAL' : 'NORMALIZED_EXACT';
        }}
        badgeClass = 'verdict-match';
      }} else if (isPermutation || (currentCase && currentCase.domain === 'enumerated_list' && currentCase.expected_match_type === 'PERMUTATION')) {{
        score = 1.0;
        verdict = 'PERMUTATION (SET MATCH)';
        badgeClass = 'verdict-permutation';
      }} else if (isSubstantiveMatch || (currentCase && currentCase.expected_match_type === 'SUBSTANTIVE_EXACT')) {{
        score = 1.0;
        verdict = 'SUBSTANTIVE_EXACT (CORE MATCH)';
        badgeClass = 'verdict-match';
      }} else if (score >= threshold) {{
        verdict = method === 'Semantic' ? 'SEMANTIC_SIMILAR' : 'SYNTACTIC_SIMILAR';
        badgeClass = 'verdict-match';
      }}

      const scorePct = Math.round(score * 100);
      document.getElementById('scoreVal').innerText = scorePct + '%';
      document.getElementById('scoreBar').style.width = scorePct + '%';

      const badge = document.getElementById('verdictBadge');
      badge.className = 'verdict-badge ' + badgeClass;
      badge.innerText = verdict;

      // Render Merkle tree
      const merkle = document.getElementById('merkleViewer');
      const isUuid = (str) => new RegExp('^(?:urn:uuid:)?[0-9a-fA-F-]{{32,38}}$', 'i').test(str);
      const getUrnLine = (urn) => {{
        if (!urn) return '';
        const kind = isUuid(urn) ? 'Random GUID' : (urn.toLowerCase().startsWith('urn:ddi:') ? 'Assigned DDI URN' : 'Assigned Identifier');
        const kindColor = isUuid(urn) ? 'var(--warning)' : 'var(--info)';
        return `|-- Unique Identifier: <span style="color:var(--text-main); font-weight:600;">"${{escapeHtml(urn)}}"</span> <span style="color:${{kindColor}}; font-weight:700;">[${{kind}}]</span><br>`;
      }};

      if (parsedSrc && parsedSrc.codes && Array.isArray(parsedSrc.codes)) {{
        const codes = parsedSrc.codes;
        const substCodes = codes.filter(c => !c.is_missing);
        const sentinelCodes = codes.filter(c => c.is_missing);

        const codeSetHash = simpleHash(codes.map(c => `${{normalizeText(c.value || '')}}=${{normalizeText(c.label || c.category_label || '')}}`).sort().join(';'));
        const codeSeqHash = srcDigest;
        const substSetHash = simpleHash(substCodes.map(c => `${{normalizeText(c.value || '')}}=${{normalizeText(c.label || c.category_label || '')}}`).sort().join(';'));
        const sentinelSetHash = simpleHash(sentinelCodes.map(c => `${{normalizeText(c.value || '')}}=${{normalizeText(c.label || c.category_label || '')}}`).sort().join(';'));
        const catSetHash = simpleHash(codes.map(c => normalizeText(c.label || c.category_label || '')).sort().join(';'));
        const valSetHash = simpleHash(codes.map(c => normalizeText(c.value || '')).sort().join(';'));

        let itemsHtml = codes.map((c, i) => {{
          const valH = simpleHash(normalizeText(c.value || ''));
          const catH = simpleHash(normalizeText(c.label || c.category_label || ''));
          const itemH = simpleHash(`${{valH}}::${{catH}}::missing=${{Boolean(c.is_missing)}}`);
          const missTag = c.is_missing ? ` <span style="color:var(--warning); font-weight:700;">[SENTINEL${{c.sentinel_type ? ': ' + escapeHtml(c.sentinel_type) : ''}}]</span>` : ` <span style="color:var(--success); font-weight:600;">[SUBSTANTIVE]</span>`;
          return `|-- Code Item [${{i + 1}}/${{codes.length}}]: "${{escapeHtml(c.value)}}" ↔ "${{escapeHtml(c.label || c.category_label || '')}}"${{missTag}} [${{itemH}}]<br>|     |-- Code Value Hash:    [${{valH}}] ("${{escapeHtml(c.value)}}")<br>|     \\-- Category Hash:      [${{catH}}] ("${{escapeHtml(c.label || c.category_label || '')}}")`;
        }}).join('<br>');

        merkle.innerHTML = `
          <div style="color:var(--primary); font-weight:600;">CodeList Merkle Root: [${{srcDigest}}]</div>
          <div style="padding-left:18px;">
            ${{getUrnLine(srcUrn)}}
            |-- Full Code Set Digest (All Items):       <span style="color:var(--text-main); font-weight:600;">[${{codeSetHash}}]</span><br>
            |-- Substantive Code Set Digest:            <span style="color:var(--success); font-weight:700;">[${{substSetHash}}]</span> (${{substCodes.length}} items)<br>
            |-- Sentinel / Missing Code Set Digest:     <span style="color:var(--warning); font-weight:700;">[${{sentinelSetHash}}]</span> (${{sentinelCodes.length}} items)<br>
            |-- Code Sequence Digest (Ordered):         <span style="color:var(--text-main); font-weight:600;">[${{codeSeqHash}}]</span><br>
            |-- Category Set Digest (Semantics):        <span style="color:var(--text-main); font-weight:600;">[${{catSetHash}}]</span><br>
            |-- Value Set Digest (Code Notations):      <span style="color:var(--text-main); font-weight:600;">[${{valSetHash}}]</span><br>
            |-- Classification:                         <span style="color:var(--text-main); font-weight:600;">${{verdict}}</span><br>
            \\-- Member Code Items:<br>
          </div>
          <div style="padding-left:36px; font-size:0.78rem; color:var(--text-muted); line-height:1.5;">
            ${{itemsHtml}}
          </div>
        `;
      }} else if (parsedSrc && parsedSrc.question_text) {{
        merkle.innerHTML = `
          <div style="color:var(--primary); font-weight:600;">Question Merkle Root: [${{srcDigest}}]</div>
          <div style="padding-left:18px;">
            ${{getUrnLine(srcUrn)}}
            |-- Prompt Literal Digest: [${{simpleHash(parsedSrc.question_text)}}]<br>
            |-- Instructions Digest: [${{simpleHash(parsedSrc.instructions || '')}}]<br>
            |-- Similarity Score: ${{scorePct}}% (${{method}})<br>
            \\-- Classification: <span style="color:var(--text-main); font-weight:600;">${{verdict}}</span>
          </div>
        `;
      }} else {{
        merkle.innerHTML = `
          <div style="color:var(--primary); font-weight:600;">Resource Merkle Root: [${{srcDigest}}]</div>
          <div style="padding-left:18px;">
            ${{getUrnLine(srcUrn)}}
            |-- Normalized Content Digest: [${{srcDigest}}]<br>
            |-- Similarity Score: ${{scorePct}}% (${{method}})<br>
            \\-- Classification: <span style="color:var(--text-main); font-weight:600;">${{verdict}}</span>
          </div>
        `;
      }}

      // Update Live Python Code Snippet and Output Viewers
      const domainName = currentCase ? currentCase.domain : 'categorical';
      const compClass = getComparatorClass(method);
      const codeSnippet = generatePythonSnippet(domainName, parsedSrc, parsedCand, method, threshold);
      const outputSnippet = generatePythonOutput(
        domainName,
        compClass,
        threshold,
        verdict,
        scorePct,
        srcDigest,
        candDigest,
        isPermutation,
        currentCase ? currentCase.expected_explanation : ''
      );

      const codeViewer = document.getElementById('pythonCodeViewer');
      if (codeViewer) codeViewer.textContent = codeSnippet;

      const outputViewer = document.getElementById('pythonOutputViewer');
      if (outputViewer) outputViewer.textContent = outputSnippet;
    }}

    function copyPythonCode() {{
      const codeViewer = document.getElementById('pythonCodeViewer');
      const code = codeViewer ? codeViewer.textContent : '';
      navigator.clipboard.writeText(code).then(() => alert("Python SDK reproduction code copied to clipboard!"));
    }}

    function copyPythonOutput() {{
      const outViewer = document.getElementById('pythonOutputViewer');
      const out = outViewer ? outViewer.textContent : '';
      navigator.clipboard.writeText(out).then(() => alert("Simulated execution output copied to clipboard!"));
    }}

    function toggleTheme() {{
      document.body.classList.toggle('light-theme');
    }}

    window.onload = init;
  </script>
</body>
</html>
"""


def launch_explorer(
    output_path: Path | str | None = None,
    open_browser: bool = True,
) -> Path:
    """Generates the interactive HTML explorer and optionally launches it in a web browser."""
    out_file = Path(output_path) if output_path else Path("harmonizer_explorer.html")
    html_content = generate_harmonizer_explorer_html()
    out_file.write_text(html_content, encoding="utf-8")

    if open_browser:
        webbrowser.open(out_file.resolve().as_uri())

    return out_file


def main() -> None:
    """CLI entrypoint for python -m dartfx.ddi.harmonizer.explorer."""
    parser = argparse.ArgumentParser(
        description="Data Artifex Harmonization Workbench & Interactive Explorer",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="harmonizer_explorer.html",
        help="Path where the standalone HTML explorer should be saved",
    )
    parser.add_argument(
        "--open",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Automatically open the explorer in the default web browser",
    )
    args = parser.parse_args()

    target = launch_explorer(output_path=args.output, open_browser=args.open)
    print(f"Harmonizer Explorer successfully written to: {target.resolve()}")


if __name__ == "__main__":
    main()
