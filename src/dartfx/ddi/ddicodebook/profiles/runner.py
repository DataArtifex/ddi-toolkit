# SPDX-FileCopyrightText: 2026 Data Artifex
# SPDX-License-Identifier: MIT

"""Rule evaluator and profile loader for DDI-Codebook validation profiles."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from .models import (
    ProfileDefinition,
    ValidationSeverity,
)

if TYPE_CHECKING:
    from ..model import codeBookType

_NCNAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]*$")


def is_valid_ncname(value: str) -> bool:
    """Validate that a string conforms to the W3C NCName specification."""
    return bool(_NCNAME_RE.fullmatch(value)) and ":" not in value


def get_builtin_profile(name: str) -> ProfileDefinition:
    """Load a built-in profile by name ('recommended', 'cdif', 'schema')."""
    normalized = name.strip().lower()
    builtin_dir = Path(__file__).parent / "builtin"
    file_path = builtin_dir / f"{normalized}.yaml"

    if not file_path.exists():
        valid_profiles = [p.stem for p in builtin_dir.glob("*.yaml")]
        raise ValueError(f"Unknown built-in profile: '{name}'. Available: {', '.join(sorted(valid_profiles))}")

    content = file_path.read_text(encoding="utf-8")
    data = yaml.safe_load(content)
    return ProfileDefinition.model_validate(data)


def load_profile(source: ProfileDefinition | str | Path | None) -> ProfileDefinition:
    """Load a validation profile from a model, a built-in name, or a YAML file path."""
    if source is None:
        return get_builtin_profile("recommended")

    if isinstance(source, ProfileDefinition):
        return source

    if isinstance(source, Path):
        content = source.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        return ProfileDefinition.model_validate(data)

    if isinstance(source, str):
        normalized = source.strip().lower()
        if normalized in ("none", "null"):
            return get_builtin_profile("schema")
        if normalized in ("recommended", "cdif", "schema"):
            return get_builtin_profile(normalized)

        path = Path(source)
        if path.exists() or source.endswith((".yaml", ".yml")):
            content = path.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
            return ProfileDefinition.model_validate(data)

        # Try built-in if no file matched
        return get_builtin_profile(source)

    raise TypeError(f"Invalid profile source type: {type(source).__name__}")


def _normalize_name(name: str) -> str:
    return name.lstrip("@").replace(":", "_").replace("-", "_").lower()


def _get_field_name_for_token(obj: Any, token: str) -> str | None:
    """Locate the attribute or Pydantic field name for an XML element or attribute token."""
    raw = token.lstrip("@")
    if hasattr(obj, raw):
        return raw

    norm = _normalize_name(token)
    model_fields = getattr(obj.__class__, "model_fields", None)
    if model_fields:
        for f_name, f_info in model_fields.items():
            if f_name.lower() == norm:
                return f_name
            if f_info.alias and (f_info.alias == raw or _normalize_name(f_info.alias) == norm):
                return f_name

    for attr in dir(obj):
        if attr.lower() == norm and not attr.startswith("_"):
            return attr

    return None


def _resolve_context_elements(root: Any, context_path: str) -> list[tuple[Any, str]]:
    """Resolve context path into a list of (element, xpath_location) pairs."""
    tokens = [t for t in context_path.strip("/").split("/") if t]
    if tokens and tokens[0].lower() in ("codebook", "codebooktype"):
        tokens = tokens[1:]

    current: list[tuple[Any, str]] = [(root, "codeBook")]

    for token in tokens:
        next_step: list[tuple[Any, str]] = []
        for obj, current_loc in current:
            field = _get_field_name_for_token(obj, token)
            if not field:
                continue
            val = getattr(obj, field, None)
            if val is None:
                continue
            if isinstance(val, list):
                for index, item in enumerate(val, start=1):
                    next_step.append((item, f"{current_loc}/{token}[{index}]"))
            else:
                next_step.append((val, f"{current_loc}/{token}"))
        current = next_step

    return current


def _resolve_target_values(obj: Any, target_path: str, base_loc: str) -> list[tuple[Any, str]]:
    """Resolve target path starting from obj to retrieve (value, xpath_location) pairs."""
    tokens = [t for t in target_path.strip("/").split("/") if t]
    if tokens and tokens[0].lower() in ("codebook", "codebooktype") and base_loc == "codeBook":
        tokens = tokens[1:]

    current: list[tuple[Any, str]] = [(obj, base_loc)]

    for token in tokens:
        next_step: list[tuple[Any, str]] = []
        is_attr = token.startswith("@")
        for curr_obj, curr_loc in current:
            field = _get_field_name_for_token(curr_obj, token)
            if not field:
                # Special convenience: variables search
                if token.lower() in ("var", "variable") and hasattr(curr_obj, "search_variables"):
                    vars_found = curr_obj.search_variables()
                    next_step.append((vars_found, f"{curr_loc}/dataDscr"))
                    continue
                next_step.append((None, f"{curr_loc}/{token}"))
                continue

            val = getattr(curr_obj, field, None)
            loc_token = token if is_attr else token
            if isinstance(val, list):
                # When reaching leaf or intermediate list
                next_step.append((val, f"{curr_loc}/{loc_token}"))
            else:
                next_step.append((val, f"{curr_loc}/{loc_token}"))
        current = next_step

    return current


def _is_value_missing(val: Any) -> bool:
    """Determine if a target value is considered absent/empty."""
    if val is None:
        return True
    if isinstance(val, str) and not val.strip():
        return True
    if isinstance(val, (list, tuple, set, dict)) and len(val) == 0:
        return True
    content = getattr(val, "content", None)
    if content is not None and not str(content).strip():
        return True
    return False


def run_profile_rules(
    codebook: codeBookType,
    profile: ProfileDefinition,
) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], list[str]]:
    """Evaluate profile rules against a codeBookType model.

    Returns:
        tuple containing (errors, warnings, infos, checked_rule_ids)
    """
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    infos: list[dict[str, str]] = []
    checked_rules: list[str] = []

    for rule in profile.rules:
        checked_rules.append(rule.id)

        # 1. Resolve context elements
        if rule.context:
            contexts = _resolve_context_elements(codebook, rule.context)
        else:
            contexts = [(codebook, "codeBook")]

        for ctx_obj, ctx_loc in contexts:
            # Check conditional guard 'when' if specified
            if rule.when:
                guard_vals = _resolve_target_values(ctx_obj, rule.when, ctx_loc)
                if not guard_vals or all(_is_value_missing(gv[0]) for gv in guard_vals):
                    continue

            # Resolve targets on this context
            target_results = _resolve_target_values(ctx_obj, rule.target, ctx_loc)

            for target_val, target_loc in target_results:
                violation = False

                rule_type = rule.rule.strip().lower()
                if rule_type in ("required", "mandatory", "recommended", "optional"):
                    if _is_value_missing(target_val):
                        violation = True

                elif rule.rule == "min_count":
                    min_c = rule.min_count if rule.min_count is not None else 1
                    if isinstance(target_val, (list, tuple, set)):
                        count = len(target_val)
                    else:
                        count = 0 if target_val is None else 1
                    if count < min_c:
                        violation = True

                elif rule.rule == "ncname":
                    if target_val and not is_valid_ncname(str(target_val)):
                        violation = True

                elif rule.rule == "pattern" and rule.pattern:
                    if target_val and not re.search(rule.pattern, str(target_val)):
                        violation = True

                elif rule.rule == "prohibited":
                    if not _is_value_missing(target_val):
                        violation = True

                if violation:
                    issue = {
                        "code": rule.id,
                        "message": rule.message,
                        "location": target_loc,
                    }
                    if rule.severity == ValidationSeverity.ERROR:
                        errors.append(issue)
                    elif rule.severity == ValidationSeverity.WARNING:
                        warnings.append(issue)
                    else:
                        infos.append(issue)

    return errors, warnings, infos, checked_rules
