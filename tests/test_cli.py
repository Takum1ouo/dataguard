"""End-to-end tests for the `dataguard check` command."""

from __future__ import annotations

import json
from pathlib import Path

from dataguard.cli import main


def test_check_command_writes_report(tmp_path: Path, capsys) -> None:
    csv_path = tmp_path / "data.csv"
    csv_path.write_text(
        "id,name,email\n1,Alice,alice@example.com\n2,Bob,bob@example.com\n",
        encoding="utf-8",
    )
    rules_path = tmp_path / "rules.json"
    rules_path.write_text(
        json.dumps({"required": ["id", "name", "email"], "unique": ["id"], "types": {"id": "integer"}}),
        encoding="utf-8",
    )
    output_path = tmp_path / "report.json"

    exit_code = main(["check", str(csv_path), "--rules", str(rules_path), "--output", str(output_path)])

    assert exit_code == 0
    assert output_path.is_file()

    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["total_rows"] == 2
    assert report["valid_rows"] == 2
    assert report["invalid_rows"] == 0

    captured = capsys.readouterr()
    assert "DataGuard check summary" in captured.out
    assert str(output_path) in captured.out


def test_check_command_refuses_to_overwrite_existing_output(tmp_path: Path, capsys) -> None:
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("id,name,email\n1,Alice,alice@example.com\n", encoding="utf-8")
    rules_path = tmp_path / "rules.json"
    rules_path.write_text(json.dumps({"required": ["id"]}), encoding="utf-8")
    output_path = tmp_path / "report.json"
    output_path.write_text('{"pre-existing": true}', encoding="utf-8")

    exit_code = main(["check", str(csv_path), "--rules", str(rules_path), "--output", str(output_path)])

    assert exit_code != 0
    captured = capsys.readouterr()
    assert "already exists" in captured.err
    # The pre-existing file must be left untouched.
    assert output_path.read_text(encoding="utf-8") == '{"pre-existing": true}'


def test_check_command_overwrite_flag_replaces_existing_output(tmp_path: Path, capsys) -> None:
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("id,name,email\n1,Alice,alice@example.com\n", encoding="utf-8")
    rules_path = tmp_path / "rules.json"
    rules_path.write_text(json.dumps({"required": ["id"]}), encoding="utf-8")
    output_path = tmp_path / "report.json"
    output_path.write_text('{"pre-existing": true}', encoding="utf-8")

    exit_code = main(
        ["check", str(csv_path), "--rules", str(rules_path), "--output", str(output_path), "--overwrite"]
    )

    assert exit_code == 0
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["total_rows"] == 1


def test_check_command_detects_semicolon_delimiter(tmp_path: Path) -> None:
    csv_path = tmp_path / "excel_export.csv"
    csv_path.write_text(
        "id;name;email\n1;Alice;alice@example.com\n2;Bob;bob@example.com\n",
        encoding="utf-8",
    )
    rules_path = tmp_path / "rules.json"
    rules_path.write_text(
        json.dumps({"required": ["id", "name", "email"], "unique": ["id"]}),
        encoding="utf-8",
    )
    output_path = tmp_path / "report.json"

    exit_code = main(["check", str(csv_path), "--rules", str(rules_path), "--output", str(output_path)])

    assert exit_code == 0
    report = json.loads(output_path.read_text(encoding="utf-8"))
    # If the delimiter were not detected, the whole line would collapse into
    # a single column and none of the rule fields would exist in the header.
    assert report["dataset_issues"] == []
    assert report["total_rows"] == 2
    assert report["valid_rows"] == 2


def test_check_command_reports_missing_csv_file(tmp_path: Path, capsys) -> None:
    csv_path = tmp_path / "does_not_exist.csv"
    rules_path = tmp_path / "rules.json"
    rules_path.write_text(json.dumps({"required": ["id"]}), encoding="utf-8")
    output_path = tmp_path / "report.json"

    exit_code = main(["check", str(csv_path), "--rules", str(rules_path), "--output", str(output_path)])

    assert exit_code != 0
    captured = capsys.readouterr()
    assert "not found" in captured.err
    assert not output_path.exists()


def test_check_command_reports_missing_rules_file(tmp_path: Path, capsys) -> None:
    csv_path = tmp_path / "data.csv"
    csv_path.write_text("id,name\n1,Alice\n", encoding="utf-8")
    rules_path = tmp_path / "does_not_exist.json"
    output_path = tmp_path / "report.json"

    exit_code = main(["check", str(csv_path), "--rules", str(rules_path), "--output", str(output_path)])

    assert exit_code != 0
    captured = capsys.readouterr()
    assert "not found" in captured.err
    assert not output_path.exists()


def test_check_command_reports_csv_without_header(tmp_path: Path, capsys) -> None:
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("", encoding="utf-8")
    rules_path = tmp_path / "rules.json"
    rules_path.write_text(json.dumps({"required": ["id"]}), encoding="utf-8")
    output_path = tmp_path / "report.json"

    exit_code = main(["check", str(csv_path), "--rules", str(rules_path), "--output", str(output_path)])

    assert exit_code != 0
    captured = capsys.readouterr()
    assert "no header row" in captured.err
    assert not output_path.exists()


def test_check_command_reports_non_utf8_csv_cleanly(tmp_path: Path, capsys) -> None:
    csv_path = tmp_path / "gbk_data.csv"
    csv_path.write_bytes("id,name,city\n1,张三,北京\n".encode("gbk"))
    rules_path = tmp_path / "rules.json"
    rules_path.write_text(json.dumps({"required": ["id", "name"]}), encoding="utf-8")
    output_path = tmp_path / "report.json"

    exit_code = main(["check", str(csv_path), "--rules", str(rules_path), "--output", str(output_path)])

    assert exit_code != 0
    captured = capsys.readouterr()
    assert "Error:" in captured.err
    assert "not valid UTF-8" in captured.err
    assert not output_path.exists()
