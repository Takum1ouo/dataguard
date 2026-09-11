"""Report writing and terminal summary rendering for DataGuard."""

from __future__ import annotations

import json
from pathlib import Path

from .models import CheckReport


class OutputExistsError(FileExistsError):
    """Raised when the report output path already exists and --overwrite was not given."""


def write_report(report: CheckReport, output_path: str | Path, overwrite: bool = False) -> None:
    path = Path(output_path)
    if path.exists() and not overwrite:
        raise OutputExistsError(
            f"Output file already exists: {path}. Use --overwrite to replace it."
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(report.to_dict(), handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def format_summary(report: CheckReport, output_path: str | Path) -> str:
    lines = [
        "DataGuard check summary",
        "------------------------",
        f"Input file:    {report.input_file}",
        f"Total rows:    {report.total_rows}",
        f"Valid rows:    {report.valid_rows}",
        f"Invalid rows:  {report.invalid_rows}",
        "",
        "Issue counts:",
    ]
    for code, count in report.issue_counts.items():
        lines.append(f"  {code}: {count}")

    if report.dataset_issues:
        lines.append("")
        lines.append("Dataset-level issues:")
        for issue in report.dataset_issues:
            lines.append(f"  [{issue.code}] field='{issue.field}': {issue.message}")

    lines.append("")
    lines.append(f"Report written to: {Path(output_path)}")
    return "\n".join(lines)
