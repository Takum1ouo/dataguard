"""Core-logic tests for DataGuard's checker module."""

from __future__ import annotations

from pathlib import Path

import pytest

from dataguard.checker import run_checks
from dataguard.models import (
    DUPLICATE_VALUE,
    INVALID_TYPE,
    MISSING_COLUMN,
    MISSING_REQUIRED,
    Rules,
)

BASE_RULES = Rules(
    required=["id", "name", "email"],
    unique=["id", "email"],
    types={"id": "integer", "age": "integer", "score": "number"},
)


def write_csv(tmp_path: Path, content: str) -> Path:
    csv_path = tmp_path / "data.csv"
    csv_path.write_text(content, encoding="utf-8")
    return csv_path


def test_fully_valid_dataset(tmp_path: Path) -> None:
    csv_path = write_csv(
        tmp_path,
        "id,name,email,age,score\n"
        "1,Alice,alice@example.com,30,88.5\n"
        "2,Bob,bob@example.com,25,91\n",
    )

    report = run_checks(csv_path, BASE_RULES)

    assert report.total_rows == 2
    assert report.valid_rows == 2
    assert report.invalid_rows == 0
    assert report.row_issues == []
    assert report.dataset_issues == []
    assert all(count == 0 for count in report.issue_counts.values())


def test_missing_required_field(tmp_path: Path) -> None:
    csv_path = write_csv(
        tmp_path,
        "id,name,email,age,score\n"
        "1,,alice@example.com,30,88.5\n"
        "2,Bob,bob@example.com,25,91\n",
    )

    report = run_checks(csv_path, BASE_RULES)

    assert report.invalid_rows == 1
    assert report.valid_rows == 1
    codes_by_row = [(i.row, i.code, i.field) for i in report.row_issues]
    assert (2, MISSING_REQUIRED, "name") in codes_by_row
    assert report.issue_counts[MISSING_REQUIRED] == 1


def test_duplicate_unique_value(tmp_path: Path) -> None:
    csv_path = write_csv(
        tmp_path,
        "id,name,email,age,score\n"
        "1,Alice,alice@example.com,30,88.5\n"
        "1,Bob,bob@example.com,25,91\n",
    )

    report = run_checks(csv_path, BASE_RULES)

    assert report.invalid_rows == 1
    dup_issues = [i for i in report.row_issues if i.code == DUPLICATE_VALUE]
    assert len(dup_issues) == 1
    assert dup_issues[0].row == 3
    assert dup_issues[0].field == "id"
    assert report.issue_counts[DUPLICATE_VALUE] == 1


def test_invalid_integer_type(tmp_path: Path) -> None:
    csv_path = write_csv(
        tmp_path,
        "id,name,email,age,score\n"
        "1,Alice,alice@example.com,12.5,88.5\n"
        "2,Bob,bob@example.com,25,91\n",
    )

    report = run_checks(csv_path, BASE_RULES)

    invalid_type_issues = [i for i in report.row_issues if i.code == INVALID_TYPE and i.field == "age"]
    assert len(invalid_type_issues) == 1
    assert invalid_type_issues[0].row == 2
    assert report.invalid_rows == 1


def test_invalid_number_type(tmp_path: Path) -> None:
    csv_path = write_csv(
        tmp_path,
        "id,name,email,age,score\n"
        "1,Alice,alice@example.com,30,not-a-number\n"
        "2,Bob,bob@example.com,25,91\n",
    )

    report = run_checks(csv_path, BASE_RULES)

    invalid_type_issues = [i for i in report.row_issues if i.code == INVALID_TYPE and i.field == "score"]
    assert len(invalid_type_issues) == 1
    assert invalid_type_issues[0].row == 2
    assert report.invalid_rows == 1


def test_rule_references_missing_column(tmp_path: Path) -> None:
    csv_path = write_csv(
        tmp_path,
        "id,name,email\n"
        "1,Alice,alice@example.com\n"
        "2,Bob,bob@example.com\n",
    )
    rules = Rules(required=["id", "name", "email", "phone"], unique=["id"], types={"age": "integer"})

    report = run_checks(csv_path, rules)

    dataset_codes = [(i.field, i.code) for i in report.dataset_issues]
    assert ("phone", MISSING_COLUMN) in dataset_codes
    assert ("age", MISSING_COLUMN) in dataset_codes
    # missing_column issues must not be repeated per data row
    assert report.issue_counts[MISSING_COLUMN] == 2
    row_level_missing_column = [i for i in report.row_issues if i.code == MISSING_COLUMN]
    assert row_level_missing_column == []
    # Rows are otherwise valid since phone/age checks are skipped for the absent columns.
    assert report.invalid_rows == 0


def test_missing_value_does_not_double_report_invalid_type(tmp_path: Path) -> None:
    csv_path = write_csv(
        tmp_path,
        "id,name,email,age,score\n"
        "1,,alice@example.com,,88.5\n",
    )

    report = run_checks(csv_path, BASE_RULES)

    age_issues = [i for i in report.row_issues if i.field == "age"]
    name_issues = [i for i in report.row_issues if i.field == "name"]
    assert age_issues == []  # age has no required rule, blank is skipped for type check
    assert len(name_issues) == 1
    assert name_issues[0].code == MISSING_REQUIRED


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
