"""Data structures shared across DataGuard modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# Issue codes
MISSING_REQUIRED = "missing_required"
DUPLICATE_VALUE = "duplicate_value"
INVALID_TYPE = "invalid_type"
MISSING_COLUMN = "missing_column"

ROW_ISSUE_CODES = (MISSING_REQUIRED, DUPLICATE_VALUE, INVALID_TYPE)
DATASET_ISSUE_CODES = (MISSING_COLUMN,)

SUPPORTED_TYPES = ("integer", "number", "string")


@dataclass
class DatasetIssue:
    field: str
    code: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {"field": self.field, "code": self.code, "message": self.message}


@dataclass
class RowIssue:
    row: int
    field: str
    code: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "row": self.row,
            "field": self.field,
            "code": self.code,
            "message": self.message,
        }


@dataclass
class Rules:
    required: list[str] = field(default_factory=list)
    unique: list[str] = field(default_factory=list)
    types: dict[str, str] = field(default_factory=dict)

    def referenced_fields(self) -> list[str]:
        """All fields referenced anywhere in the rules, in a stable order."""
        seen: list[str] = []
        for name in (*self.required, *self.unique, *self.types.keys()):
            if name not in seen:
                seen.append(name)
        return seen


@dataclass
class CheckReport:
    input_file: str
    rules_file: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    issue_counts: dict[str, int]
    dataset_issues: list[DatasetIssue]
    row_issues: list[RowIssue]

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_file": self.input_file,
            "rules_file": self.rules_file,
            "total_rows": self.total_rows,
            "valid_rows": self.valid_rows,
            "invalid_rows": self.invalid_rows,
            "issue_counts": self.issue_counts,
            "dataset_issues": [issue.to_dict() for issue in self.dataset_issues],
            "row_issues": [issue.to_dict() for issue in self.row_issues],
        }
