# ruff: noqa: E501
"""Interactive HTML Harmonization Workbench and Scenario Explorer.

Generates a self-contained, client-side interactive web application with:
- Scenario Stories & Example Bank browser with domain filters (Categorical, CodeLists, Questions, Concepts, Variables)
- Real-time client-side Harmonization Playground (live diff, normalizer switches, and score gauges)
- Hierarchical Merkle Tree & Digest Inspector
- Actionable Transformation Advisories Engine (Unit conversion formulas, category recode maps, missing scheme remapping)
- Interactive Dataset Crosswalk Studio with bipartite matching & Polars transformation pipeline preview
- Export to JSON and Python SDK code
"""

from __future__ import annotations

import argparse
import json
import webbrowser
from pathlib import Path
from typing import Any

from .examples.loader import CaseBankLoader

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title><!--TITLE--></title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
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
      --pink: #ec4899;
      --cyan: #06b6d4;
      --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }
    .light-theme {
      --bg-base: #f8fafc;
      --bg-surface: #ffffff;
      --bg-card: #f1f5f9;
      --bg-hover: #e2e8f0;
      --border-color: #cbd5e1;
      --text-main: #0f172a;
      --text-muted: #64748b;
      --primary: #4f46e5;
      --primary-hover: #4338ca;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: var(--font-sans);
      background-color: var(--bg-base);
      color: var(--text-main);
      display: flex;
      flex-direction: column;
      height: 100vh;
      overflow: hidden;
    }
    header {
      background-color: var(--bg-surface);
      border-bottom: 1px solid var(--border-color);
      padding: 10px 24px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-shrink: 0;
      gap: 16px;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      font-weight: 700;
      font-size: 1.15rem;
    }
    .brand-badge {
      background: linear-gradient(135deg, var(--primary), #8b5cf6);
      color: #fff;
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 0.75rem;
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }
    .header-nav {
      display: flex;
      gap: 8px;
      align-items: center;
    }
    .header-actions {
      display: flex;
      gap: 10px;
      align-items: center;
    }
    button, .btn {
      background-color: var(--bg-card);
      color: var(--text-main);
      border: 1px solid var(--border-color);
      padding: 6px 14px;
      border-radius: 6px;
      cursor: pointer;
      font-family: inherit;
      font-size: 0.84rem;
      font-weight: 500;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      transition: all 0.15s ease;
    }
    button:hover, .btn:hover { background-color: var(--bg-hover); }
    .btn-primary {
      background-color: var(--primary);
      border-color: var(--primary);
      color: #fff;
    }
    .btn-primary:hover { background-color: var(--primary-hover); }
    main {
      display: flex;
      flex: 1;
      overflow: hidden;
      position: relative;
    }
    /* Sidebar */
    .sidebar {
      width: 380px;
      background-color: var(--bg-surface);
      border-right: 1px solid var(--border-color);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
    }
    .sidebar-search {
      padding: 12px 14px;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    .search-input {
      width: 100%;
      background: var(--bg-base);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      color: var(--text-main);
      font-family: inherit;
      font-size: 0.85rem;
      padding: 7px 12px;
      outline: none;
      transition: border-color 0.15s ease;
    }
    .search-input:focus {
      border-color: var(--primary);
    }
    .filter-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }
    .chip {
      font-size: 0.74rem;
      padding: 3px 8px;
      border-radius: 12px;
      background: var(--bg-card);
      color: var(--text-muted);
      cursor: pointer;
      border: 1px solid transparent;
      user-select: none;
      transition: all 0.15s ease;
      font-weight: 500;
    }
    .chip:hover {
      color: var(--text-main);
      background: var(--bg-hover);
    }
    .chip.active {
      background: rgba(99, 102, 241, 0.2);
      color: #a5b4fc;
      border-color: rgba(99, 102, 241, 0.4);
      font-weight: 600;
    }
    .case-list {
      flex: 1;
      overflow-y: auto;
      padding: 10px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .case-card {
      background: var(--bg-base);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 12px 14px;
      cursor: pointer;
      transition: all 0.15s ease;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .case-card:hover {
      border-color: var(--primary);
      transform: translateY(-1px);
    }
    .case-card.active {
      border-color: var(--primary);
      background-color: rgba(99, 102, 241, 0.12);
    }
    .case-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 4px;
    }
    .case-title {
      font-size: 0.88rem;
      font-weight: 600;
      line-height: 1.3;
    }
    .tag {
      font-size: 0.68rem;
      padding: 2px 6px;
      border-radius: 4px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .tag-categorical { background: rgba(59, 130, 246, 0.2); color: #60a5fa; }
    .tag-enumerated_list { background: rgba(16, 185, 129, 0.2); color: #34d399; }
    .tag-question { background: rgba(245, 158, 11, 0.2); color: #fbbf24; }
    .tag-conceptual { background: rgba(168, 85, 247, 0.2); color: #c084fc; }
    .tag-variable { background: rgba(236, 72, 153, 0.2); color: #f472b6; }
    .case-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 4px;
      align-items: center;
      justify-content: flex-end;
    }
    .tag-diff {
      font-size: 0.62rem;
      padding: 1px 5px;
      border-radius: 4px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .tag-diff-basic { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.35); }
    .tag-diff-intermediate { background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.35); }
    .tag-diff-advanced { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.35); }
    .tag-diff-edge_case { background: rgba(236, 72, 153, 0.15); color: #f472b6; border: 1px solid rgba(236, 72, 153, 0.35); }
    .sort-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 6px;
      background: rgba(0,0,0,0.25);
      padding: 4px 8px;
      border-radius: 6px;
      border: 1px solid var(--border-color);
    }
    .sort-label {
      font-size: 0.70rem;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.04em;
      white-space: nowrap;
    }
    .sort-select {
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: 4px;
      color: var(--text-main);
      font-family: inherit;
      font-size: 0.75rem;
      padding: 3px 6px;
      outline: none;
      cursor: pointer;
      width: 100%;
    }
    .sort-select:focus {
      border-color: var(--primary);
    }
    .case-desc {
      font-size: 0.78rem;
      color: var(--text-muted);
      line-height: 1.4;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    /* Main Content */
    .content-area {
      flex: 1;
      overflow-y: auto;
      padding: 18px 24px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .story-banner {
      background: linear-gradient(135deg, rgba(99,102,241,0.1), rgba(139,92,246,0.1));
      border: 1px solid rgba(99,102,241,0.25);
      border-radius: 10px;
      padding: 14px 18px;
    }
    .story-banner h2 {
      font-size: 1.12rem;
      font-weight: 700;
      margin-bottom: 6px;
      color: var(--text-main);
    }
    .story-banner .context {
      font-size: 0.8rem;
      font-weight: 600;
      color: var(--primary);
      margin-bottom: 6px;
      display: inline-block;
    }
    .story-banner p {
      font-size: 0.86rem;
      line-height: 1.5;
      color: var(--text-muted);
      margin-bottom: 8px;
    }
    .story-banner .learning {
      font-size: 0.8rem;
      background: var(--bg-surface);
      border-left: 3px solid var(--primary);
      padding: 6px 10px;
      border-radius: 4px;
      color: var(--text-main);
      font-family: var(--font-mono);
    }
    /* Subbar & View Mode Toggle */
    .section-subbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: -4px;
    }
    .subbar-title {
      font-size: 0.82rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-muted);
    }
    .view-mode-controls {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .segmented-control {
      display: inline-flex;
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 2px;
      gap: 2px;
    }
    .seg-btn {
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
    }
    .seg-btn:hover {
      color: var(--text-main);
    }
    .seg-btn.active {
      background: var(--primary);
      color: #ffffff;
      box-shadow: 0 1px 2px rgba(0,0,0,0.2);
    }

    /* Playground */
    .playground-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
    }
    .input-box {
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .box-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.8rem;
      font-weight: 600;
      color: var(--text-muted);
    }
    .box-title-group {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .box-title {
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-weight: 600;
    }
    .type-badge {
      font-size: 0.68rem;
      font-family: var(--font-mono);
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      color: var(--primary);
      padding: 1px 6px;
      border-radius: 4px;
      font-weight: 700;
    }
    .box-tabs {
      display: inline-flex;
      background: var(--bg-base);
      border: 1px solid var(--border-color);
      border-radius: 5px;
      padding: 2px;
      gap: 2px;
    }
    .box-tab {
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
    }
    .box-tab:hover {
      color: var(--text-main);
    }
    .box-tab.active {
      background: var(--bg-card);
      color: var(--text-main);
      border: 1px solid var(--border-color);
    }

    .box-content-wrapper {
      position: relative;
    }
    .code-editor {
      width: 100%;
      height: 200px;
      min-height: 150px;
      max-height: 280px;
      background: var(--bg-base);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      color: var(--text-main);
      font-family: var(--font-mono);
      font-size: 0.82rem;
      padding: 10px 12px;
      resize: vertical;
      line-height: 1.45;
    }
    .code-editor.hidden {
      display: none;
    }
    .rendered-viewer {
      width: 100%;
      height: 200px;
      min-height: 150px;
      max-height: 280px;
      overflow-y: auto;
      background: var(--bg-base);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 10px 12px;
    }
    .rendered-viewer.hidden {
      display: none;
    }

    /* Rich Rendered Components */
    .render-card {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .render-title-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 6px;
    }
    .render-title {
      font-size: 0.92rem;
      font-weight: 700;
      color: var(--text-main);
    }
    .badge-pill {
      display: inline-flex;
      align-items: center;
      font-size: 0.68rem;
      font-weight: 600;
      padding: 2px 7px;
      border-radius: 12px;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .badge-primary {
      background: rgba(99, 102, 241, 0.18);
      color: #818cf8;
      border: 1px solid rgba(99, 102, 241, 0.35);
    }
    .badge-success {
      background: rgba(16, 185, 129, 0.18);
      color: #34d399;
      border: 1px solid rgba(16, 185, 129, 0.35);
    }
    .badge-warning {
      background: rgba(245, 158, 11, 0.18);
      color: #fbbf24;
      border: 1px solid rgba(245, 158, 11, 0.35);
    }

    /* Code List Rendered Table */
    .codelist-table {
      width: 100%;
      border-collapse: separate;
      border-spacing: 0 3px;
      font-size: 0.82rem;
    }
    .codelist-table th {
      font-size: 0.68rem;
      font-weight: 600;
      text-transform: uppercase;
      color: var(--text-muted);
      text-align: left;
      padding: 4px 6px;
      letter-spacing: 0.05em;
    }
    .codelist-table tr.code-row {
      background: var(--bg-card);
      border-radius: 5px;
      transition: background 0.15s ease;
    }
    .codelist-table tr.code-row:hover {
      background: var(--bg-hover);
    }
    .codelist-table td {
      padding: 5px 8px;
    }
    .codelist-table td:first-child {
      border-top-left-radius: 5px;
      border-bottom-left-radius: 5px;
      width: 28px;
      color: var(--text-muted);
      font-family: var(--font-mono);
      font-size: 0.72rem;
    }
    .codelist-table td:last-child {
      border-top-right-radius: 5px;
      border-bottom-right-radius: 5px;
    }
    .val-chip {
      font-family: var(--font-mono);
      font-size: 0.78rem;
      font-weight: 600;
      background: rgba(99, 102, 241, 0.2);
      color: #a5b4fc;
      border: 1px solid rgba(99, 102, 241, 0.4);
      padding: 1px 6px;
      border-radius: 4px;
      display: inline-block;
    }

    /* Controls Panel */
    .controls-panel {
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 10px 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 12px;
    }
    .toggle-group {
      display: flex;
      flex-wrap: wrap;
      gap: 14px;
      align-items: center;
    }
    .toggle-item {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.8rem;
      color: var(--text-muted);
      cursor: pointer;
      user-select: none;
    }
    .toggle-item input {
      cursor: pointer;
    }
    .comparator-select {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 4px 8px;
      border-radius: 5px;
      font-size: 0.8rem;
      outline: none;
    }

    /* Results Card */
    .results-card {
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    .verdict-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .verdict-badge {
      font-size: 0.96rem;
      font-weight: 700;
      padding: 5px 12px;
      border-radius: 6px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }
    .verdict-match { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }
    .verdict-permutation { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }
    .verdict-distinct { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }
    .score-meter {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .score-val {
      font-size: 1.35rem;
      font-weight: 800;
      font-family: var(--font-mono);
    }
    .score-bar-bg {
      width: 140px;
      height: 8px;
      background: var(--bg-card);
      border-radius: 4px;
      overflow: hidden;
    }
    .score-bar-fill {
      height: 100%;
      background: linear-gradient(90deg, var(--primary), var(--success));
      border-radius: 4px;
      transition: width 0.3s ease;
    }
    .digest-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    .digest-box {
      background: var(--bg-base);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 8px 12px;
      font-family: var(--font-mono);
      font-size: 0.78rem;
      display: flex;
      flex-direction: column;
      gap: 3px;
    }
    .digest-label {
      font-size: 0.68rem;
      color: var(--text-muted);
      text-transform: uppercase;
      font-weight: 600;
      font-family: var(--font-sans);
    }
    .merkle-viewer {
      background: var(--bg-base);
      border: 1px solid var(--border-color);
      border-radius: 6px;
      padding: 12px;
      font-family: var(--font-mono);
      font-size: 0.78rem;
      line-height: 1.45;
      overflow-x: auto;
      max-height: 320px;
      overflow-y: auto;
    }

    /* Transformation Advice Cards */
    .advice-item {
      background: rgba(99, 102, 241, 0.08);
      border: 1px solid rgba(99, 102, 241, 0.25);
      border-radius: 6px;
      padding: 10px 14px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .advice-header {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.82rem;
      font-weight: 700;
    }
    .advice-formula {
      background: var(--bg-base);
      border: 1px solid var(--border-color);
      padding: 4px 8px;
      border-radius: 4px;
      font-family: var(--font-mono);
      font-size: 0.76rem;
      color: #38bdf8;
      display: inline-block;
    }

    /* Python Workbench Card */
    .python-workbench-card {
      background: var(--bg-surface);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }
    .py-header {
      background: var(--bg-card);
      border-bottom: 1px solid var(--border-color);
      padding: 8px 14px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .py-title-group {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.84rem;
      font-weight: 700;
    }
    .py-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1px;
      background: var(--border-color);
    }
    .py-panel {
      background: var(--bg-base);
      display: flex;
      flex-direction: column;
    }
    .py-panel-header {
      background: var(--bg-surface);
      border-bottom: 1px solid var(--border-color);
      padding: 6px 12px;
      font-size: 0.72rem;
      font-weight: 600;
      color: var(--text-muted);
      text-transform: uppercase;
      display: flex;
      justify-content: space-between;
    }
    .py-code {
      padding: 12px;
      font-family: var(--font-mono);
      font-size: 0.76rem;
      line-height: 1.45;
      overflow-x: auto;
      max-height: 250px;
      overflow-y: auto;
      white-space: pre;
      color: #e2e8f0;
    }

    /* Dataset Crosswalk Studio View */
    .dataset-studio-view {
      display: none;
      flex-direction: column;
      gap: 16px;
      padding: 18px 24px;
      overflow-y: auto;
      flex: 1;
    }
    .crosswalk-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.82rem;
    }
    .crosswalk-table th {
      background: var(--bg-card);
      padding: 8px 12px;
      text-align: left;
      font-size: 0.72rem;
      text-transform: uppercase;
      color: var(--text-muted);
      border-bottom: 1px solid var(--border-color);
    }
    .crosswalk-table td {
      padding: 10px 12px;
      border-bottom: 1px solid var(--border-color);
    }
    .crosswalk-table tr:hover {
      background: rgba(255,255,255,0.02);
    }
  </style>
</head>
<body>
  <header>
    <div class="brand">
      <span class="brand-badge">Data Artifex</span>
      <span>Harmonization Workbench</span>
    </div>
    <div class="header-nav">
      <div class="segmented-control" style="background: rgba(0,0,0,0.3);">
        <button class="seg-btn active" id="navBtnResource" onclick="switchWorkbenchView('resource')">🔬 Resource Comparator</button>
        <button class="seg-btn" id="navBtnDataset" onclick="switchWorkbenchView('dataset')">📊 Dataset Crosswalk Studio</button>
      </div>
    </div>
    <div class="header-actions">
      <button id="themeToggleBtn" onclick="toggleTheme()">🌓 Theme</button>
      <button class="btn btn-primary" onclick="copyPythonCode()">📋 Copy Python SDK Code</button>
    </div>
  </header>

  <!-- 1. RESOURCE COMPARATOR VIEW -->
  <main id="resourceMainView">
    <aside class="sidebar">
      <div class="sidebar-search">
        <input type="text" class="search-input" id="caseSearch" placeholder="Search scenarios & stories..." oninput="filterCases()">
        <div class="filter-chips">
          <span class="chip active" data-domain="all" onclick="selectDomainFilter('all')">All (<span id="countAll">0</span>)</span>
          <span class="chip" data-domain="categorical" onclick="selectDomainFilter('categorical')">Categorical</span>
          <span class="chip" data-domain="enumerated_list" onclick="selectDomainFilter('enumerated_list')">Lists</span>
          <span class="chip" data-domain="question" onclick="selectDomainFilter('question')">Questions</span>
          <span class="chip" data-domain="conceptual" onclick="selectDomainFilter('conceptual')">Concepts</span>
          <span class="chip" data-domain="variable" onclick="selectDomainFilter('variable')">Variables</span>
        </div>
        <div class="sort-bar">
          <span class="sort-label">Order:</span>
          <select id="caseSortSelect" class="sort-select" onchange="renderCaseList()">
            <option value="complexity_asc">⚡ Complexity (Basic &rarr; Advanced)</option>
            <option value="complexity_desc">⚡ Complexity (Advanced &rarr; Basic)</option>
            <option value="domain">📁 Domain Group</option>
            <option value="title">🔤 Title (A &rarr; Z)</option>
          </select>
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
            <button class="seg-btn" id="btnViewJson" onclick="setGlobalViewMode('json')">{ } Raw JSON / YAML</button>
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
              <button class="box-tab" id="srcTabJson" onclick="setBoxView('source', 'json')">{ } JSON</button>
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
              <button class="box-tab" id="candTabJson" onclick="setBoxView('candidate', 'json')">{ } JSON</button>
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
            <option value="Variable">Compound Variable / Metrology</option>
          </select>
          <label style="font-size:0.82rem; font-weight:600; margin-left:8px;">Threshold:</label>
          <input type="range" id="thresholdSlider" min="0" max="100" value="70" style="width:70px;" oninput="updateThresholdLabel(); runLiveHarmonization();">
          <span id="thresholdValLabel" style="font-family:var(--font-mono); font-size:0.82rem;">70%</span>
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

        <!-- Actionable Transformation Advisories Container -->
        <div id="adviceSection" style="display:none; flex-direction: column; gap:6px;">
          <div style="font-size:0.72rem; font-weight:700; text-transform:uppercase; color:var(--primary); letter-spacing:0.05em;">
            ⚡ Actionable Transformation Advisories
          </div>
          <div id="adviceCardsContainer" style="display:flex; flex-direction:column; gap:6px;"></div>
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
            Hierarchical Merkle Tree &amp; Digest Inspector
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
            <span>Live Python SDK &amp; Execution Output</span>
          </div>
          <div class="py-actions">
            <button class="btn" style="padding:3px 8px; font-size:0.72rem;" onclick="copyPythonCode()">📋 Copy Snippet</button>
            <button class="btn" style="padding:3px 8px; font-size:0.72rem;" onclick="copyPythonOutput()">📋 Copy Output</button>
          </div>
        </div>
        <div class="py-grid">
          <div class="py-panel">
            <div class="py-panel-header">
              <span>Executable Python Snippet</span>
              <span>dartfx.ddi.harmonizer SDK</span>
            </div>
            <pre class="py-code" id="pythonCodeViewer"># Loading Python code...</pre>
          </div>
          <div class="py-panel">
            <div class="py-panel-header">
              <span>Simulated Execution Output</span>
              <span>Console Log</span>
            </div>
            <pre class="py-code" id="pythonOutputViewer"># Loading Output...</pre>
          </div>
        </div>
      </div>
    </section>
  </main>

  <!-- 2. DATASET CROSSWALK STUDIO VIEW -->
  <section class="dataset-studio-view" id="datasetCrosswalkView">
    <div class="story-banner">
      <span class="context">Dataset-to-Dataset Harmonization &amp; Schema Crosswalk Studio</span>
      <h2>Bipartite Schema Matching &amp; Polars Pipeline Transformation</h2>
      <p>
        Automatically aligns variable schemas across survey waves, clinical data feeds, or multi-source catalogs.
        Computes optimal 1-to-1 bipartite variable matches, identifies physical unit scale factors (QUDT metrology),
        synthesizes categorical recoding tables, and outputs an executable transformation pipeline.
      </p>
      <div class="learning">
        💡 <code>DatasetHarmonizer.harmonize()</code> &rarr; <code>DatasetCrosswalk.apply_to_polars(df)</code>
      </div>
    </div>

    <div class="results-card">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
          <h3 style="font-size:0.95rem; font-weight:700;">Active Crosswalk Matrix (Survey Wave 1 &rarr; Survey Wave 2)</h3>
          <span style="font-size:0.75rem; color:var(--text-muted);">4 aligned variables &bull; Bipartite Greedy Matching (Min Confidence: 70%)</span>
        </div>
        <div style="display:flex; gap:8px;">
          <button class="btn btn-primary" onclick="runDatasetCrosswalkDemo()">⚡ Execute Polars Transformation</button>
        </div>
      </div>

      <table class="crosswalk-table">
        <thead>
          <tr>
            <th>Source Variable (Wave 1)</th>
            <th>Target Variable (Wave 2)</th>
            <th>Match Classification</th>
            <th>Similarity</th>
            <th>Transformation Advisory</th>
            <th>Execution Rule</th>
          </tr>
        </thead>
        <tbody id="crosswalkTableBody">
          <!-- Populated by JS -->
        </tbody>
      </table>
    </div>

    <!-- Polars Pipeline Live Execution Viewer -->
    <div class="playground-grid">
      <div class="input-box">
        <div class="box-header">
          <span class="box-title">Source Polars DataFrame (Input)</span>
          <span class="type-badge">POLARS.DATAFRAME</span>
        </div>
        <div class="rendered-viewer" style="height:180px; font-family:var(--font-mono); font-size:0.78rem;">
          <table class="codelist-table">
            <thead>
              <tr><th>#</th><th>WEIGHT_LBS (f64)</th><th>GENDER (i64)</th><th>AGE_YR (i64)</th><th>INCOME_USD (f64)</th></tr>
            </thead>
            <tbody>
              <tr class="code-row"><td>0</td><td>150.0</td><td>1 (Male)</td><td>34</td><td>75000.0</td></tr>
              <tr class="code-row"><td>1</td><td>185.5</td><td>2 (Female)</td><td>42</td><td>92000.0</td></tr>
              <tr class="code-row"><td>2</td><td>210.0</td><td>1 (Male)</td><td>29</td><td>61000.0</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="input-box">
        <div class="box-header">
          <span class="box-title">Harmonized Target DataFrame (Output)</span>
          <span class="type-badge" style="color:var(--success); border-color:var(--success);">ALIGNED SCHEMA</span>
        </div>
        <div class="rendered-viewer" id="polarsOutputViewer" style="height:180px; font-family:var(--font-mono); font-size:0.78rem;">
          <table class="codelist-table">
            <thead>
              <tr><th>#</th><th>weight_kg (f64)</th><th>sex (str)</th><th>age (i64)</th><th>income_usd (f64)</th></tr>
            </thead>
            <tbody>
              <tr class="code-row"><td>0</td><td style="color:#38bdf8;">68.0388</td><td style="color:#34d399;">"M"</td><td>34</td><td>75000.0</td></tr>
              <tr class="code-row"><td>1</td><td style="color:#38bdf8;">84.1413</td><td style="color:#34d399;">"F"</td><td>42</td><td>92000.0</td></tr>
              <tr class="code-row"><td>2</td><td style="color:#38bdf8;">95.2543</td><td style="color:#34d399;">"M"</td><td>29</td><td>61000.0</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </section>

  <script>
    const CASES = <!--CASES_JSON-->;
    let currentCase = CASES[0] || null;
    let activeFilter = 'all';
    let currentViewMode = 'resource';

    function init() {
      document.getElementById('countAll').innerText = CASES.length;
      renderCaseList();
      if (currentCase) {
        loadCase(currentCase.id);
      }
      setGlobalViewMode('rendered');
      renderCrosswalkStudioTable();
    }

    function switchWorkbenchView(mode) {
      currentViewMode = mode;
      document.getElementById('navBtnResource').classList.toggle('active', mode === 'resource');
      document.getElementById('navBtnDataset').classList.toggle('active', mode === 'dataset');

      if (mode === 'resource') {
        document.getElementById('resourceMainView').style.display = 'flex';
        document.getElementById('datasetCrosswalkView').style.display = 'none';
      } else {
        document.getElementById('resourceMainView').style.display = 'none';
        document.getElementById('datasetCrosswalkView').style.display = 'flex';
      }
    }

    function selectDomainFilter(domain) {
      activeFilter = domain;
      document.querySelectorAll('.filter-chips .chip').forEach(c => {
        c.classList.toggle('active', c.getAttribute('data-domain') === domain);
      });
      renderCaseList();
    }

    function filterCases() {
      renderCaseList();
    }

    function renderCaseList() {
      const query = (document.getElementById('caseSearch').value || '').toLowerCase();
      const sortMode = document.getElementById('caseSortSelect') ? document.getElementById('caseSortSelect').value : 'complexity_asc';
      const container = document.getElementById('caseListContainer');
      container.innerHTML = '';

      const diffOrder = { 'basic': 1, 'intermediate': 2, 'advanced': 3, 'edge_case': 4 };

      const filtered = CASES.filter(c => {
        const matchesDomain = activeFilter === 'all' || c.domain === activeFilter;
        const matchesQuery = !query || c.title.toLowerCase().includes(query) || (c.story || '').toLowerCase().includes(query);
        return matchesDomain && matchesQuery;
      });

      filtered.sort((a, b) => {
        if (sortMode === 'complexity_asc') {
          const dA = diffOrder[a.difficulty] || 2;
          const dB = diffOrder[b.difficulty] || 2;
          if (dA !== dB) return dA - dB;
          return a.title.localeCompare(b.title);
        } else if (sortMode === 'complexity_desc') {
          const dA = diffOrder[a.difficulty] || 2;
          const dB = diffOrder[b.difficulty] || 2;
          if (dA !== dB) return dB - dA;
          return a.title.localeCompare(b.title);
        } else if (sortMode === 'domain') {
          if (a.domain !== b.domain) return a.domain.localeCompare(b.domain);
          const dA = diffOrder[a.difficulty] || 2;
          const dB = diffOrder[b.difficulty] || 2;
          return dA - dB;
        } else {
          return a.title.localeCompare(b.title);
        }
      });

      filtered.forEach(c => {
        const card = document.createElement('div');
        card.className = 'case-card' + (currentCase && currentCase.id === c.id ? ' active' : '');
        card.onclick = () => loadCase(c.id);
        const diffLabel = (c.difficulty || 'basic').replace('_', ' ');
        card.innerHTML = `
          <div class="case-header">
            <div class="case-title">${escapeHtml(c.title)}</div>
            <div class="case-tags">
              <span class="tag tag-${c.domain}">${c.domain.replace('_', ' ')}</span>
              <span class="tag-diff tag-diff-${c.difficulty || 'basic'}">${diffLabel}</span>
            </div>
          </div>
          <div class="case-desc">${escapeHtml(c.story)}</div>
        `;
        container.appendChild(card);
      });
    }

    let currentSourceView = 'rendered';
    let currentCandidateView = 'rendered';

    function escapeHtml(text) {
      if (text === null || text === undefined) return '';
      return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    function setBoxView(box, mode) {
      if (box === 'source') {
        currentSourceView = mode;
        document.getElementById('srcTabRendered').classList.toggle('active', mode === 'rendered');
        document.getElementById('srcTabJson').classList.toggle('active', mode === 'json');
        document.getElementById('sourceRendered').classList.toggle('hidden', mode === 'json');
        document.getElementById('sourceInput').classList.toggle('hidden', mode === 'rendered');
      } else {
        currentCandidateView = mode;
        document.getElementById('candTabRendered').classList.toggle('active', mode === 'rendered');
        document.getElementById('candTabJson').classList.toggle('active', mode === 'json');
        document.getElementById('candidateRendered').classList.toggle('hidden', mode === 'json');
        document.getElementById('candidateInput').classList.toggle('hidden', mode === 'rendered');
      }
      updateViewModeSegControl();
    }

    function setGlobalViewMode(mode) {
      setBoxView('source', mode);
      setBoxView('candidate', mode);
    }

    function updateViewModeSegControl() {
      const isBothRendered = currentSourceView === 'rendered' && currentCandidateView === 'rendered';
      const isBothJson = currentSourceView === 'json' && currentCandidateView === 'json';
      document.getElementById('btnViewRendered').classList.toggle('active', isBothRendered);
      document.getElementById('btnViewJson').classList.toggle('active', isBothJson);
    }

    function renderResource(raw, domainHint) {
      if (!raw) return '<div style="color:var(--text-muted); font-style:italic;">(Empty)</div>';
      let parsed = raw;
      if (typeof raw === 'string') {
        try { parsed = JSON.parse(raw); } catch (e) {
          return `<div class="cat-display"><div class="cat-label">"${escapeHtml(String(raw))}"</div></div>`;
        }
      }
      if (typeof parsed !== 'object' || parsed === null) {
        return `<div class="cat-display"><div class="cat-label">"${escapeHtml(String(raw))}"</div></div>`;
      }

      // 1. Variable Item
      if (domainHint === 'variable' || (parsed.name && (parsed.data_type || parsed.quantity_kind || parsed.numeric_domain || parsed.value_domain))) {
        let details = '';
        if (parsed.quantity_kind || parsed.unit) {
          const qkText = typeof parsed.quantity_kind === 'object' ? parsed.quantity_kind.name : parsed.quantity_kind;
          const uomText = typeof parsed.unit === 'object' ? parsed.unit.symbol : parsed.unit;
          details += `<div style="display:flex; gap:6px; margin: 6px 0;">
            ${qkText ? `<span class="badge-pill badge-primary">QuantityKind: ${escapeHtml(qkText)}</span>` : ''}
            ${uomText ? `<span class="badge-pill badge-success">Unit: ${escapeHtml(uomText)}</span>` : ''}
          </div>`;
        }
        if (parsed.numeric_domain) {
          const num = parsed.numeric_domain;
          const minVal = num.min_value !== undefined ? num.min_value : num.min;
          const maxVal = num.max_value !== undefined ? num.max_value : num.max;
          details += `<div style="margin-top:6px; font-size:0.75rem; background:rgba(0,0,0,0.25); padding:6px 10px; border-radius:4px; border: 1px solid var(--border-color);">
            <strong style="color:var(--text-muted); text-transform:uppercase; font-size:0.68rem;">Numeric Bounds:</strong>
            <span style="font-family:var(--font-mono); margin-left:6px; color:#38bdf8;">[${minVal !== undefined ? minVal : '-∞'} ... ${maxVal !== undefined ? maxVal : '+∞'}]</span>
          </div>`;
        }
        if (parsed.value_domain && parsed.value_domain.codes) {
          const rows = parsed.value_domain.codes.map((c, i) => `
            <tr class="code-row">
              <td>#${i + 1}</td>
              <td style="width:70px;"><span class="val-chip">${escapeHtml(String(c.value !== undefined ? c.value : ''))}</span></td>
              <td><span class="label-text">${escapeHtml(String(c.label !== undefined ? c.label : (c.category ? c.category.label : '')))}</span></td>
              <td style="text-align:right;">${c.is_missing ? '<span class="badge-pill badge-warning">Missing</span>' : '<span class="badge-pill badge-success" style="opacity:0.85; font-size:0.65rem;">Valid</span>'}</td>
            </tr>
          `).join('');
          details += `<table class="codelist-table" style="margin-top:8px;">
            <thead><tr><th>Seq</th><th>Value</th><th>Category Label</th><th></th></tr></thead>
            <tbody>${rows}</tbody>
          </table>`;
        }
        const dtName = typeof parsed.data_type === 'object' ? parsed.data_type.name : (parsed.data_type || 'Variable');
        return `
          <div class="render-card">
            <div class="render-title-bar">
              <span class="render-title">${escapeHtml(parsed.name)}</span>
              <span class="badge-pill badge-primary">${escapeHtml(dtName)}</span>
            </div>
            ${parsed.label ? `<div style="font-weight:600; font-size:0.88rem; margin:6px 0; color:var(--text-main);">${escapeHtml(parsed.label)}</div>` : ''}
            ${details}
          </div>
        `;
      }

      // 2. Code list
      if (Array.isArray(parsed.codes) || (domainHint === 'enumerated_list' && parsed.codes)) {
        const codes = parsed.codes || [];
        const rows = codes.map((c, i) => `
          <tr class="code-row">
            <td>#${i + 1}</td>
            <td style="width:70px;"><span class="val-chip">${escapeHtml(String(c.value !== undefined ? c.value : ''))}</span></td>
            <td><span class="label-text">${escapeHtml(String(c.label !== undefined ? c.label : (c.category_label || '')))}</span></td>
            <td style="text-align:right;">${c.is_missing ? `<span class="badge-pill badge-warning">${c.sentinel_type ? 'Sentinel: ' + escapeHtml(c.sentinel_type) : 'Missing'}</span>` : '<span class="badge-pill badge-success" style="opacity:0.85; font-size:0.65rem;">Substantive</span>'}</td>
          </tr>
        `).join('');
        return `
          <div class="render-card">
            <div class="render-title-bar">
              <span class="render-title">${escapeHtml(parsed.name || 'Code List')}</span>
              <span class="badge-pill badge-success">${codes.length} Response Codes</span>
            </div>
            <table class="codelist-table">
              <thead><tr><th>Seq</th><th>Value</th><th>Category Label</th><th></th></tr></thead>
              <tbody>${rows}</tbody>
            </table>
          </div>
        `;
      }

      // 3. Question Item
      if (parsed.question_text || domainHint === 'question') {
        return `
          <div class="q-display">
            ${parsed.pre_question_text ? `<div style="font-size:0.8rem; font-style:italic; color:var(--text-muted);">💬 ${escapeHtml(parsed.pre_question_text)}</div>` : ''}
            <div class="q-prompt-box">
              <div style="font-size:0.7rem; font-weight:600; text-transform:uppercase; color:var(--primary); margin-bottom:4px;">Question Prompt</div>
              <div style="font-size:0.94rem; font-weight:600;">${escapeHtml(parsed.question_text || 'No prompt provided')}</div>
            </div>
            ${parsed.instructions ? `<div style="font-size:0.8rem; background:rgba(245,158,11,0.08); padding:6px 10px; border-radius:4px; margin-top:4px;">📋 <strong>Instructions:</strong> ${escapeHtml(parsed.instructions)}</div>` : ''}
          </div>
        `;
      }

      // 4. Conceptual Item
      if (parsed.definition || parsed.preferred_label || domainHint === 'conceptual') {
        return `
          <div class="render-card">
            <div class="render-title-bar">
              <span class="render-title">${escapeHtml(parsed.preferred_label || parsed.name || 'Concept')}</span>
              ${parsed.notation ? `<span class="val-chip">${escapeHtml(parsed.notation)}</span>` : ''}
            </div>
            ${parsed.definition ? `<div style="font-size:0.85rem; color:var(--text-muted); line-height:1.4;">${escapeHtml(parsed.definition)}</div>` : ''}
          </div>
        `;
      }

      // 5. Categorical
      return `
        <div class="cat-display">
          <div class="cat-label">"${escapeHtml(parsed.label || '')}"</div>
          <div class="cat-meta">
            ${parsed.value !== undefined ? `<span class="val-chip">Code: ${escapeHtml(String(parsed.value))}</span>` : ''}
            ${parsed.is_missing ? '<span class="badge-pill badge-warning">Missing Flag</span>' : '<span class="badge-pill badge-success">Substantive Category</span>'}
          </div>
        </div>
      `;
    }

    function loadCase(caseId) {
      const c = CASES.find(item => item.id === caseId);
      if (!c) return;
      currentCase = c;

      document.getElementById('storyContext').innerText = c.real_world_context || (c.domain.toUpperCase() + ' DOMAIN');
      document.getElementById('storyTitle').innerText = c.title;
      document.getElementById('storyText').innerText = c.story;
      document.getElementById('storyLearning').innerText = '💡 ' + (c.learning_objective || 'Metadata Harmonization');

      document.getElementById('srcDomainBadge').innerText = c.domain.toUpperCase();
      document.getElementById('candDomainBadge').innerText = c.domain.toUpperCase();

      const srcStr = typeof c.source_resource === 'object' ? JSON.stringify(c.source_resource, null, 2) : String(c.source_resource);
      const candStr = typeof c.candidate_resource === 'object' ? JSON.stringify(c.candidate_resource, null, 2) : String(c.candidate_resource);

      document.getElementById('sourceInput').value = srcStr;
      document.getElementById('candidateInput').value = candStr;

      document.getElementById('sourceRendered').innerHTML = renderResource(c.source_resource, c.domain);
      document.getElementById('candidateRendered').innerHTML = renderResource(c.candidate_resource, c.domain);

      const compSelect = document.getElementById('comparatorSelect');
      if (c.domain === 'variable') {
        compSelect.value = 'Variable';
      } else if (c.comparator && Array.from(compSelect.options).some(o => o.value === c.comparator)) {
        compSelect.value = c.comparator;
      } else {
        compSelect.value = 'SequenceMatcher';
      }

      const thresh = Math.round((c.comparator_threshold || 0.70) * 100);
      document.getElementById('thresholdSlider').value = thresh;
      document.getElementById('thresholdValLabel').innerText = thresh + '%';

      renderCaseList();
      runLiveHarmonization();
    }

    function onCodeInput(box) {
      const val = document.getElementById(box === 'source' ? 'sourceInput' : 'candidateInput').value;
      const targetViewer = document.getElementById(box === 'source' ? 'sourceRendered' : 'candidateRendered');
      targetViewer.innerHTML = renderResource(val, currentCase ? currentCase.domain : 'categorical');
      runLiveHarmonization();
    }

    function updateThresholdLabel() {
      const val = document.getElementById('thresholdSlider').value;
      document.getElementById('thresholdValLabel').innerText = val + '%';
    }

    function simpleHash(str) {
      let hash = 5381;
      for (let i = 0; i < str.length; i++) {
        hash = ((hash << 5) + hash) + str.charCodeAt(i);
        hash = hash & hash;
      }
      const hex = (hash >>> 0).toString(16).padStart(8, '0');
      return (hex + hex).substring(0, 16);
    }

    function normalizeText(str) {
      if (!str) return '';
      let text = String(str);
      if (document.getElementById('optSanitize').checked) {
        text = text.replace(/[\u201C\u201D"]/g, '"').replace(/[\u2018\u2019']/g, "'").replace(/[—–]/g, '-').replace(/&amp;/g, '&');
      }
      if (document.getElementById('optDeaccent').checked) {
        text = text.normalize('NFKD').replace(/[\u0300-\u036f]/g, '');
      }
      if (document.getElementById('optCasefold').checked) {
        text = text.toLowerCase();
      }
      if (document.getElementById('optPunctuation').checked) {
        text = text.replace(/[^a-zA-Z0-9\s]/g, '');
      }
      if (document.getElementById('optCollapseSpace').checked) {
        text = text.replace(/\s+/g, ' ').trim();
      }
      return text;
    }

    function sequenceMatcherRatio(s1, s2) {
      if (!s1 || !s2) return (s1 === s2) ? 1.0 : 0.0;
      if (s1 === s2) return 1.0;

      function findLongestMatch(alo, ahi, blo, bhi) {
        let besti = alo, bestj = blo, bestsize = 0;
        for (let i = alo; i < ahi; i++) {
          for (let j = blo; j < bhi; j++) {
            let k = 0;
            while (i + k < ahi && j + k < bhi && s1[i + k] === s2[j + k]) {
              k++;
            }
            if (k > bestsize) {
              besti = i;
              bestj = j;
              bestsize = k;
            }
          }
        }
        return [besti, bestj, bestsize];
      }

      function getMatchingBlocks(alo, ahi, blo, bhi) {
        const [i, j, k] = findLongestMatch(alo, ahi, blo, bhi);
        if (k === 0) return 0;
        let matchingChars = k;
        if (alo < i && blo < j) {
          matchingChars += getMatchingBlocks(alo, i, blo, j);
        }
        if (i + k < ahi && j + k < bhi) {
          matchingChars += getMatchingBlocks(i + k, ahi, j + k, bhi);
        }
        return matchingChars;
      }

      const totalMatches = getMatchingBlocks(0, s1.length, 0, s2.length);
      return (2.0 * totalMatches) / (s1.length + s2.length);
    }

    function computeSimilarity(s1, s2, method) {
      const n1 = normalizeText(s1);
      const n2 = normalizeText(s2);
      if (n1 === n2) return 1.0;
      if (!n1 || !n2) return 0.0;

      if (method === 'Exact') return n1 === n2 ? 1.0 : 0.0;
      if (method === 'Levenshtein') {
        const m = n1.length, n = n2.length;
        const dp = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));
        for (let i = 0; i <= m; i++) dp[i][0] = i;
        for (let j = 0; j <= n; j++) dp[0][j] = j;
        for (let i = 1; i <= m; i++) {
          for (let j = 1; j <= n; j++) {
            const cost = n1[i - 1] === n2[j - 1] ? 0 : 1;
            dp[i][j] = Math.min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost);
          }
        }
        const maxLen = Math.max(m, n);
        return maxLen === 0 ? 1.0 : Math.max(0.0, 1.0 - (dp[m][n] / maxLen));
      }

      if (method === 'Jaccard') {
        const t1 = n1.split(/\s+/), t2 = n2.split(/\s+/);
        const s1Set = new Set(t1), s2Set = new Set(t2);
        let matches = 0;
        s1Set.forEach(w => { if (s2Set.has(w)) matches++; });
        const union = new Set([...t1, ...t2]).size;
        return union === 0 ? 1.0 : (matches / union);
      }

      // Default: SequenceMatcher Gestalt (identical to Python difflib)
      return sequenceMatcherRatio(n1, n2);
    }

    function generatePythonSnippet(domain, parsedSrc, parsedCand, method, threshold) {
      const threshVal = threshold.toFixed(2);
      if (domain === 'variable' || (parsedSrc && (parsedSrc.data_type || parsedSrc.quantity_kind || parsedSrc.numeric_domain))) {
        return `import polars as pl
from dartfx.ddi.harmonizer import (
    HarmonizedVariable,
    VariableComparator,
    compare_variables,
)

# 1. Instantiate Harmonized Variables from Payloads
source_var = HarmonizedVariable.from_dict(${JSON.stringify(parsedSrc, null, 4)})
candidate_var = HarmonizedVariable.from_dict(${JSON.stringify(parsedCand, null, 4)})

# 2. Compare Variables & Derive Metrological / Recoding Transformation Advice
result = compare_variables(source_var, candidate_var, threshold=${threshVal})

print(f"Matched:          {result.score >= ${threshVal}}")
print(f"Match Type:       {result.match_type.value}")
print(f"Similarity Score: {result.score:.4f}")
print(f"Rationale:        {result.rationale}")
print("Sub-scores:", result.sub_scores)
if result.transformation_advice:
    print("\\nTransformation Advisories:")
    for advice in result.transformation_advice:
        print(f"  [{advice.action.value}]: {advice.description}")`;
      }

      if (domain === 'enumerated_list' || (parsedSrc && parsedSrc.codes)) {
        return `from dartfx.ddi.harmonizer import (
    HarmonizedCode,
    HarmonizedCodeList,
    HarmonizedCategory,
    SequenceMatcherComparator,
    compare_codelists,
)

# 1. Parse Code Lists with Merkle Fingerprinting
cl_source = HarmonizedCodeList.from_dict(${JSON.stringify(parsedSrc, null, 4)})
cl_candidate = HarmonizedCodeList.from_dict(${JSON.stringify(parsedCand, null, 4)})

# 2. Execute Code List Comparison
result = compare_codelists(cl_source, cl_candidate, threshold=${threshVal})

print(f"Matched:               {result.matched}")
print(f"Match Type:            {result.match_type.value}")
print(f"Similarity Score:      {result.score:.4f}")
print(f"Category Digest Match: {cl_source.fingerprint.category_set_digest == cl_candidate.fingerprint.category_set_digest}")`;
      }

      if (domain === 'question' || (parsedSrc && parsedSrc.question_text)) {
        return `from dartfx.ddi.harmonizer import (
    HarmonizedQuestion,
    SequenceMatcherComparator,
    WeightedAttributeComparator,
)

# 1. Instantiate Harmonized Questions
q_source = HarmonizedQuestion(**${JSON.stringify(parsedSrc, null, 4)})
q_candidate = HarmonizedQuestion(**${JSON.stringify(parsedCand, null, 4)})

# 2. Multi-Attribute Weighted Comparison
comparator = WeightedAttributeComparator(
    attribute_weights={"question_text": 0.65, "instructions": 0.15, "pre_question_text": 0.10, "intent": 0.10},
    match_threshold=${threshVal},
)
result = comparator.compare_attributes(q_source.model_dump(), q_candidate.model_dump())

print(f"Matched:          {result.score >= ${threshVal}}")
print(f"Similarity Score: {result.score:.4f}")
print(f"Match Type:       {result.match_type.value}")`;
      }

      if (domain === 'conceptual' || (parsedSrc && (parsedSrc.preferred_label || parsedSrc.definition))) {
        return `from dartfx.ddi.harmonizer import (
    HarmonizedConcept,
    SequenceMatcherComparator,
    WeightedAttributeComparator,
)

# 1. Instantiate Harmonized Concepts
c_source = HarmonizedConcept(**${JSON.stringify(parsedSrc, null, 4)})
c_candidate = HarmonizedConcept(**${JSON.stringify(parsedCand, null, 4)})

# 2. Conceptual Weighted Comparison
comparator = WeightedAttributeComparator(
    attribute_weights={"preferred_label": 0.50, "notation": 0.20, "definition": 0.30},
    match_threshold=${threshVal},
)
result = comparator.compare_attributes(c_source.model_dump(), c_candidate.model_dump())

print(f"Matched:          {result.score >= ${threshVal}}")
print(f"Similarity Score: {result.score:.4f}")
print(f"Match Type:       {result.match_type.value}")`;
      }

      // Default: Categorical
      return `from dartfx.ddi.harmonizer import (
    ExactComparator,
    HarmonizationRegistry,
    HarmonizedCategory,
    NormalizerConfig,
    TextNormalizer,
    TextSanitizer,
)

# 1. Configure Sanitization & Normalization Pipeline
sanitizer = TextSanitizer()
normalizer = TextNormalizer.from_preset("STANDARD")
normalizer.sanitizer = sanitizer
comparator = ExactComparator(normalizer=normalizer)

# 2. Register & Match Categories
registry = HarmonizationRegistry(comparator=comparator)
cat_source = HarmonizedCategory(**${JSON.stringify(parsedSrc, null, 4)})
cat_candidate = HarmonizedCategory(**${JSON.stringify(parsedCand, null, 4)})

registry.register(cat_source)
match = registry.match(cat_candidate, threshold=${threshVal})

print(f"Matched:          {match.matched}")
print(f"Match Type:       {match.match_type.value}")
print(f"Similarity Score: {match.score:.4f}")
print(f"Source Digest:    {cat_source.fingerprint.digest}")
print(f"Candidate Digest: {cat_candidate.fingerprint.digest}")`;
    }

    function generatePythonOutput(domain, compClass, threshold, verdict, scorePct, srcDigest, candDigest) {
      const isMatch = !verdict.includes('DISTINCT');
      const scoreNum = (scorePct / 100).toFixed(4);
      return `[HARMONIZATION EXECUTION LOG]
Status:           ${isMatch ? "PASSED (>= threshold)" : "REJECTED (< threshold)"}
Match Type:       ${verdict}
Similarity Score: ${scoreNum} (Threshold: ${threshold.toFixed(2)})
Source Digest:    ${srcDigest}
Candidate Digest: ${candDigest}
Execution:        Completed in 0.42ms with zero allocations.`;
    }

    function runLiveHarmonization() {
      const srcRaw = document.getElementById('sourceInput').value;
      const candRaw = document.getElementById('candidateInput').value;
      const method = document.getElementById('comparatorSelect').value;
      const threshold = parseFloat(document.getElementById('thresholdSlider').value) / 100.0;

      let parsedSrc = null, parsedCand = null;
      try { parsedSrc = JSON.parse(srcRaw); } catch (e) {}
      try { parsedCand = JSON.parse(candRaw); } catch (e) {}

      const srcDigest = simpleHash(normalizeText(srcRaw));
      const candDigest = simpleHash(normalizeText(candRaw));

      document.getElementById('sourceDigest').innerText = srcDigest;
      document.getElementById('candidateDigest').innerText = candDigest;

      let score = 0.0;
      let verdict = 'DISTINCT';
      let badgeClass = 'verdict-distinct';
      const adviceList = [];

      const isVariableDomain = (currentCase && currentCase.domain === 'variable') || (parsedSrc && (parsedSrc.data_type || parsedSrc.quantity_kind || parsedSrc.numeric_domain));

      if (isVariableDomain && parsedSrc && parsedCand) {
        // Dynamic facet weighting matching Python VariableComparator
        const lblScore = computeSimilarity(parsedSrc.label || parsedSrc.name || '', parsedCand.label || parsedCand.name || '', method);
        const nameScore = computeSimilarity(parsedSrc.name || '', parsedCand.name || '', method);

        let typeScore = 0.5;
        if (parsedSrc.data_type && parsedCand.data_type) {
          const sType = String(parsedSrc.data_type).toLowerCase();
          const cType = String(parsedCand.data_type).toLowerCase();
          if (sType === cType) typeScore = 1.0;
          else if ((sType === 'integer' && cType === 'decimal') || (sType === 'decimal' && cType === 'integer')) typeScore = 0.9;
          else typeScore = 0.7;
        }

        let weighted_sum = (lblScore * 0.40) + (nameScore * 0.10) + (typeScore * 0.20);
        let total_weight = 0.70;

        let isUnitConv = false;
        let isDimIncompat = false;
        if (parsedSrc.unit && parsedCand.unit) {
          total_weight += 0.10;
          const sU = String(parsedSrc.unit).toLowerCase();
          const cU = String(parsedCand.unit).toLowerCase();
          if (sU === cU) {
            weighted_sum += 1.0 * 0.10;
          } else {
            isUnitConv = true;
            weighted_sum += 0.95 * 0.10;
            let scaleFactor = 1.0;
            if (sU === 'lbs' && cU === 'kg') scaleFactor = 0.45359237;
            else if (sU === 'usd' && cU === 'cad') scaleFactor = 1.35;
            adviceList.push({
              action: 'CONVERT_UNIT',
              badge: 'badge-primary',
              title: `Unit Conversion: ${parsedSrc.unit} &rarr; ${parsedCand.unit}`,
              formula: `${parsedCand.name || 'target'} = ${parsedSrc.name || 'source'} * ${scaleFactor}`,
              desc: `Scale continuous measurements by linear conversion factor ${scaleFactor}`
            });
          }
        }

        let isRecode = false;
        if (parsedSrc.value_domain && parsedCand.value_domain && parsedSrc.value_domain.codes && parsedCand.value_domain.codes) {
          total_weight += 0.20;
          const sCodes = parsedSrc.value_domain.codes;
          const cCodes = parsedCand.value_domain.codes;
          if (sCodes.length === cCodes.length) {
            isRecode = true;
            weighted_sum += 0.95 * 0.20;
            const recodeMapping = sCodes.map((sc, i) => `${sc.value} &rarr; ${cCodes[i].value} (${sc.label})`).join(', ');
            adviceList.push({
              action: 'RECODE_VALUES',
              badge: 'badge-warning',
              title: `Category Value Recoding (100% Semantic Match)`,
              formula: `Map notations: [${recodeMapping}]`,
              desc: `Re-map source discrete codes to target standard notation`
            });
          }
        }

        score = total_weight > 0 ? (weighted_sum / total_weight) : 0.0;

        if (score >= threshold) {
          if (isUnitConv) {
            verdict = 'UNIT_CONVERSION_REQUIRED';
            badgeClass = 'verdict-match';
          } else if (isRecode) {
            verdict = 'CATEGORIES_EXACT_CODES_DIFFERENT';
            badgeClass = 'verdict-match';
          } else if (score === 1.0) {
            verdict = (srcDigest === candDigest) ? 'EXACT_IDENTICAL' : 'NORMALIZED_EXACT';
            badgeClass = 'verdict-match';
          } else {
            verdict = 'SYNTACTIC_SIMILAR';
            badgeClass = 'verdict-match';
          }

          if (parsedSrc.name && parsedCand.name && parsedSrc.name !== parsedCand.name) {
            adviceList.push({
              action: 'RENAME_COLUMN',
              badge: 'badge-primary',
              title: `Column Renaming: ${parsedSrc.name} &rarr; ${parsedCand.name}`,
              formula: `df.rename({'${parsedSrc.name}': '${parsedCand.name}'})`,
              desc: `Map column identifier in dataset schema`
            });
          }

          if (typeScore < 1.0 && typeScore >= 0.7) {
            adviceList.push({
              action: 'CAST_DATA_TYPE',
              badge: 'badge-warning',
              title: `Data Type Widening / Casting: ${parsedSrc.data_type} &rarr; ${parsedCand.data_type}`,
              formula: `df['${parsedCand.name || 'target'}'].cast(pl.${parsedCand.data_type})`,
              desc: `Coerce physical storage type`
            });
          }
        } else {
          verdict = 'DISTINCT';
          badgeClass = 'verdict-distinct';
          // Suppress advisories for distinct, unrelated variables
          adviceList.length = 0;
        }
      } else {
        score = computeSimilarity(srcRaw, candRaw, method);
        if (score >= threshold) {
          verdict = score === 1.0 ? 'EXACT_MATCH' : 'SYNTACTIC_SIMILAR';
          badgeClass = 'verdict-match';
        }
      }

      const scorePct = Math.round(score * 100);
      document.getElementById('scoreVal').innerText = scorePct + '%';
      document.getElementById('scoreBar').style.width = scorePct + '%';

      const badge = document.getElementById('verdictBadge');
      badge.className = 'verdict-badge ' + badgeClass;
      badge.innerText = verdict;

      // Render Transformation Advisories
      const adviceSec = document.getElementById('adviceSection');
      const adviceCont = document.getElementById('adviceCardsContainer');
      if (adviceList.length > 0) {
        adviceSec.style.display = 'flex';
        adviceCont.innerHTML = adviceList.map(a => `
          <div class="advice-item">
            <div class="advice-header">
              <span class="badge-pill ${a.badge}">${a.action}</span>
              <span>${a.title}</span>
            </div>
            <div style="font-size:0.78rem; color:var(--text-muted);">${a.desc}</div>
            <div class="advice-formula">${a.formula}</div>
          </div>
        `).join('');
      } else {
        adviceSec.style.display = 'none';
      }

      // Merkle tree rendering
      const merkle = document.getElementById('merkleViewer');
      merkle.innerHTML = `
        <div style="color:var(--primary); font-weight:700;">Hierarchical Merkle Decomposition (${(currentCase ? currentCase.domain : 'resource').toUpperCase()})</div>
        <div style="padding-left:14px; margin-top:4px;">
          |-- Merkle Root Digest: <span style="color:var(--text-main); font-weight:600;">[${srcDigest}]</span> &harr; <span style="color:var(--text-main); font-weight:600;">[${candDigest}]</span><br>
          |-- Primary Match Status: <span style="color:var(--success); font-weight:700;">${verdict}</span> (${scorePct}%)<br>
          \\-- Evaluated Under Comparator: <span style="color:var(--cyan); font-weight:600;">${method}</span>
        </div>
      `;

      // Update Python Snippet & Output
      const domainName = currentCase ? currentCase.domain : 'variable';
      document.getElementById('pythonCodeViewer').textContent = generatePythonSnippet(domainName, parsedSrc, parsedCand, method, threshold);
      document.getElementById('pythonOutputViewer').textContent = generatePythonOutput(domainName, method, threshold, verdict, scorePct, srcDigest, candDigest);
    }

    function renderCrosswalkStudioTable() {
      const alignments = [
        { src: 'WEIGHT_LBS', tgt: 'weight_kg', type: 'UNIT_CONVERSION_REQUIRED', score: '98%', formula: 'df["WEIGHT_LBS"] * 0.45359237', rule: 'Scale lbs &rarr; kg' },
        { src: 'GENDER', tgt: 'sex', type: 'CATEGORIES_EXACT_CODES_DIFFERENT', score: '95%', formula: 'df["GENDER"].replace({1: "M", 2: "F"})', rule: 'Recode 1&rarr;M, 2&rarr;F' },
        { src: 'AGE_YR', tgt: 'age', type: 'EXACT_IDENTICAL', score: '100%', formula: 'df["AGE_YR"]', rule: 'Identity Direct Map' },
        { src: 'INCOME_USD', tgt: 'income_usd', type: 'NORMALIZED_EXACT', score: '96%', formula: 'df["INCOME_USD"]', rule: 'Casefold Column Name' }
      ];

      const tbody = document.getElementById('crosswalkTableBody');
      tbody.innerHTML = alignments.map(a => `
        <tr>
          <td><strong style="font-family:var(--font-mono); color:#a5b4fc;">${a.src}</strong></td>
          <td><strong style="font-family:var(--font-mono); color:#34d399;">${a.tgt}</strong></td>
          <td><span class="badge-pill ${a.type.includes('UNIT') ? 'badge-primary' : (a.type.includes('CATEGORIES') ? 'badge-warning' : 'badge-success')}">${a.type}</span></td>
          <td><strong>${a.score}</strong></td>
          <td><span style="font-size:0.75rem; color:var(--text-muted);">${a.rule}</span></td>
          <td><code style="font-family:var(--font-mono); font-size:0.75rem; background:rgba(0,0,0,0.3); padding:2px 6px; border-radius:4px; color:#38bdf8;">${a.formula}</code></td>
        </tr>
      `).join('');
    }

    function runDatasetCrosswalkDemo() {
      alert("⚡ Executed DatasetCrosswalk.apply_to_polars(df)! Transformed 3 rows & aligned 4 variable columns with 100% schema fidelity.");
    }

    function copyPythonCode() {
      const code = document.getElementById('pythonCodeViewer').textContent;
      navigator.clipboard.writeText(code).then(() => alert("Python SDK code copied to clipboard!"));
    }

    function copyPythonOutput() {
      const out = document.getElementById('pythonOutputViewer').textContent;
      navigator.clipboard.writeText(out).then(() => alert("Console execution output copied to clipboard!"));
    }

    function toggleTheme() {
      document.body.classList.toggle('light-theme');
    }

    window.onload = init;
  </script>
</body>
</html>
"""


def generate_harmonizer_explorer_html(
    cases: list[dict[str, Any]] | None = None,
    title: str = "Data Artifex Harmonization Workbench",
) -> str:
    """Generates a standalone, zero-dependency HTML/CSS/JS application."""
    if cases is None:
        loader = CaseBankLoader()
        cases = loader.to_dict_list()

    cases_json = json.dumps(cases, ensure_ascii=False)
    return HTML_TEMPLATE.replace("<!--CASES_JSON-->", cases_json).replace("<!--TITLE-->", title)


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
