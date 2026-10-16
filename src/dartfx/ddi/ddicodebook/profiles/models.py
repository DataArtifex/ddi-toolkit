# SPDX-FileCopyrightText: 2026 Data Artifex
# SPDX-License-Identifier: MIT

"""Pydantic models for DDI validation profiles."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class ValidationSeverity(StrEnum):
    """Severity level of a profile validation issue."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationProfile(StrEnum):
    """Standard built-in validation profiles for DDI-Codebook."""

    RECOMMENDED = "recommended"
    CDIF = "cdif"
    SCHEMA = "schema"


class ProfileMetadata(BaseModel):
    """Metadata describing a validation profile."""

    id: str = Field(description="Unique profile identifier, e.g. 'recommended' or 'cdif'")
    name: str = Field(description="Human-readable title of the profile")
    description: str | None = Field(default=None, description="Detailed explanation of the profile's purpose")
    version: str = Field(default="1.0", description="Profile schema version")
    target_standard: str = Field(default="DDI-C 2.6", description="Target standard specification")


class ProfileRule(BaseModel):
    """A single declarative constraint rule within a validation profile."""

    id: str = Field(description="Unique rule code, e.g. 'codebook.missing_id'")
    target: str = Field(description="Target attribute or element XPath-like path to validate")
    context: str | None = Field(
        default=None,
        description="Optional repeating context scope (e.g. 'codeBook/fileDscr'). If given, evaluates rule per item.",
    )
    rule: str = Field(
        default="required",
        description=(
            "Rule check type: 'required' (mandatory), 'recommended', 'optional', "
            "'min_count', 'min_coverage', 'ncname', 'pattern', or 'prohibited'"
        ),
    )
    min_count: int | None = Field(default=None, description="Minimum count for 'min_count' rules")
    min_coverage: float | None = Field(
        default=None, description="Minimum coverage percentage (0.0 to 100.0) across context items"
    )
    pattern: str | None = Field(default=None, description="Regex pattern for 'pattern' rules")
    when: str | None = Field(
        default=None,
        description="Optional guard condition on context item; rule is only checked if this target is truthy",
    )
    severity: ValidationSeverity | None = Field(
        default=None,
        description="Issue severity: 'error', 'warning', or 'info' (auto-assigned based on rule if omitted)",
    )
    message: str = Field(description="Human-readable issue message when rule condition is violated")

    @model_validator(mode="after")
    def _apply_default_severity(self) -> ProfileRule:
        if self.severity is None:
            rule_norm = self.rule.strip().lower()
            if rule_norm == "recommended":
                self.severity = ValidationSeverity.WARNING
            elif rule_norm == "optional":
                self.severity = ValidationSeverity.INFO
            else:
                self.severity = ValidationSeverity.ERROR
        return self


class ProfileDefinition(BaseModel):
    """Complete profile definition containing metadata and constraint rules."""

    profile: ProfileMetadata
    rules: list[ProfileRule] = Field(default_factory=list)
