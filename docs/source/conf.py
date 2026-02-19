# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import builtins
import os
import sys
from typing import Any

# Add Any to builtins to fix Sphinx 9.1.0 napoleon bug where Any is not defined in skip_member
builtins.Any = Any

sys.path.insert(0, os.path.abspath("../../src"))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Data Artifex DDI Toolkit"
copyright = "2024-2025, Pascal L.G.A. Heus"
author = "Pascal Heus"
release = "0.0.2"
version = "0.0.2"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.autosummary",
    "sphinx.ext.coverage",
    "myst_parser",
]

# Autodoc configuration
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
    "special-members": "__init__",
}

# Mock imports for problematic modules
autodoc_mock_imports = [
    "dartfx.rdf",
    "sempyro",
    "rdflib",
    "lxml",
    "dartfx.ddi.ddicdi.specification",
]

# Skip autodoc errors for modules that can't be imported
autodoc_typehints = "description"
autodoc_typehints_description_target = "documented"

# Suppress warnings for missing modules
suppress_warnings = ["autodoc.import_error"]

# Napoleon configuration
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
    "rdflib": ("https://rdflib.readthedocs.io/en/stable/", None),
}

# Todo extension
todo_include_todos = True

templates_path = ["_templates"]
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
html_theme_options = {
    "navigation_depth": 4,
    "collapse_navigation": False,
    "sticky_navigation": True,
    "includehidden": True,
    "titles_only": False,
}

# Add custom CSS
html_css_files = [
    "custom.css",
]

# -- Custom Setup -----------------------------------------------------------


def setup(app):
    """
    Custom Sphinx setup to handle Pydantic internal attributes and other issues.
    """

    def skip_pydantic_members(_app, _what, name, _obj, skip, _options):
        # Skip Pydantic internal attributes that cause issues with Sphinx inspection
        # particularly when using mock imports or advanced type hints
        if name.startswith("__pydantic_"):
            return True
        return skip

    # Connect with high priority (lower number) to run before other handlers
    app.connect("autodoc-skip-member", skip_pydantic_members, priority=100)
