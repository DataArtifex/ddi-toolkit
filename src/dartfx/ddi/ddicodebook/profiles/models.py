# SPDX-FileCopyrightText: 2026 Data Artifex
# SPDX-License-Identifier: MIT

"""Pydantic models for DDI validation profiles."""

from enum import StrEnum

from pydantic import BaseModel, Field


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
        description="Rule check type: 'required', 'min_count', 'ncname', 'pattern', or 'prohibited'",
    )
    min_count: int | None = Field(default=None, description="Minimum count for 'min_count' rules")
    pattern: str | None = Field(default=None, description="Regex pattern for 'pattern' rules")
    when: str | None = Field(
        default=None,
        description="Optional guard condition on context item; rule is only checked if this target is truthy",
    )
    severity: ValidationSeverity = Field(
        default=ValidationSeverity.WARNING,
        description="Issue severity: 'error', 'warning', or 'info'",
    )
    message: str = Field(description="Human-readable issue message when rule condition is violated")


class ProfileDefinition(BaseModel):
    """Complete profile definition containing metadata and constraint rules."""

    profile: ProfileMetadata
    rules: list[ProfileRule] = Field(default_factory=list)
