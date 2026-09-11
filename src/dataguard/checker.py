"""Core CSV dataset quality-check logic for DataGuard."""

from __future__ import annotations

import csv
import math
from pathlib import Path

from .models import (
    DUPLICATE_VALUE,
    INVALID_TYPE,
    MISSING_COLUMN,
    MISSING_REQUIRED,
    CheckReport,
    DatasetIssue,
    Rules,
    RowIssue,
)

# First data row (right after the header) is row 2, matching the actual CSV line number.
FIRST_DATA_ROW_NUMBER = 2


class DataGuardError(ValueError):
    """Raised for problems reading the input CSV file."""


def is_missing(value: str | None) -> bool:
    """Empty string and whitespace-only strings both count as missing."""
    return value is None or value.strip() == ""


def is_valid_integer(value: str) -> bool:
    stripped = value.strip()
    if stripped == "":
        return False
    body = stripped[1:] if stripped[0] in "+-" else stripped
    return body.isdigit()


def is_valid_number(value: str) -> bool:
    stripped = value.strip()
    if stripped == "":
        return False
    try:
        parsed = float(stripped)
    except ValueError:
        return False
    return math.isfinite(parsed)


def _detect_delimiter(sample: str) -> str:
    """Sniff whether the CSV uses ',' or ';' as its field delimiter.

    Excel often exports CSV files with ';' instead of ','. Fall back to ','
    when the sample is too short/ambiguous for the sniffer to decide.
    """
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;")
        return dialect.delimiter
    except csv.Error:
        return ","


def _read_csv_rows(csv_path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not csv_path.is_file():
        raise DataGuardError(f"Input CSV file not found: {csv_path}")

    try:
        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            sample = handle.read(4096)
            handle.seek(0)
            delimiter = _detect_delimiter(sample)

            reader = csv.DictReader(handle, delimiter=delimiter)
            fieldnames = reader.fieldnames
            if not fieldnames:
                raise DataGuardError(f"CSV file has no header row: {csv_path}")
            rows = list(reader)
    except UnicodeDecodeError as exc:
        raise DataGuardError(
            f"CSV file is not valid UTF-8 encoded text: {csv_path} ({exc}). "
            "Re-save the file as UTF-8 and try again."
        ) from exc

    return list(fieldnames), rows


def run_checks(csv_path: str | Path, rules: Rules) -> CheckReport:
    path = Path(csv_path)
    headers, rows = _read_csv_rows(path)
    header_set = set(headers)

    dataset_issues: list[DatasetIssue] = []
    for missing_field in rules.referenced_fields():
        if missing_field not in header_set:
            dataset_issues.append(
                DatasetIssue(
                    field=missing_field,
                    code=MISSING_COLUMN,
                    message=f"Column '{missing_field}' referenced in rules is missing from the CSV header.",
                )
            )

    # Only check fields that actually exist in the CSV header.
    active_required = [f for f in rules.required if f in header_set]
    active_unique = [f for f in rules.unique if f in header_set]
    active_types = {f: t for f, t in rules.types.items() if f in header_set}

    row_issues: list[RowIssue] = []
    seen_values: dict[str, set[str]] = {f: set() for f in active_unique}
    invalid_row_numbers: set[int] = set()

    for offset, row in enumerate(rows):
        row_number = FIRST_DATA_ROW_NUMBER + offset

        for field_name in active_required:
            value = row.get(field_name)
            if is_missing(value):
                row_issues.append(
                    RowIssue(
                        row=row_number,
                        field=field_name,
                        code=MISSING_REQUIRED,
                        message=f"Required field '{field_name}' is missing or blank.",
                    )
                )
                invalid_row_numbers.add(row_number)

        for field_name in active_unique:
            value = row.get(field_name)
            if is_missing(value):
                continue
            seen = seen_values[field_name]
            if value in seen:
                row_issues.append(
                    RowIssue(
                        row=row_number,
                        field=field_name,
                        code=DUPLICATE_VALUE,
                        message=f"Value '{value}' for unique field '{field_name}' has already appeared.",
                    )
                )
                invalid_row_numbers.add(row_number)
            else:
                seen.add(value)

        for field_name, type_name in active_types.items():
            value = row.get(field_name)
            if is_missing(value):
                # Missing values are reported (if applicable) via missing_required
                # above; do not additionally flag them as an invalid type.
                continue

            valid = True
            if type_name == "integer":
                valid = is_valid_integer(value)
            elif type_name == "number":
                valid = is_valid_number(value)
            # "string" accepts any non-missing value.

            if not valid:
                row_issues.append(
                    RowIssue(
                        row=row_number,
                        field=field_name,
                        code=INVALID_TYPE,
                        message=f"Value '{value}' for field '{field_name}' is not a valid {type_name}.",
                    )
                )
                invalid_row_numbers.add(row_number)

    total_rows = len(rows)
    invalid_rows = len(invalid_row_numbers)
    valid_rows = total_rows - invalid_rows

    issue_counts = {
        MISSING_REQUIRED: 0,
        DUPLICATE_VALUE: 0,
        INVALID_TYPE: 0,
        MISSING_COLUMN: 0,
    }
    for issue in row_issues:
        issue_counts[issue.code] += 1
    for issue in dataset_issues:
        issue_counts[issue.code] += 1

    return CheckReport(
        input_file=str(path),
        rules_file="",
        total_rows=total_rows,
        valid_rows=valid_rows,
        invalid_rows=invalid_rows,
        issue_counts=issue_counts,
        dataset_issues=dataset_issues,
        row_issues=row_issues,
    )
