"""Tests for DataGuard's rules-file loading and validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dataguard.rules import RulesError, load_rules


def write_rules(tmp_path: Path, data: dict) -> Path:
    rules_path = tmp_path / "rules.json"
    rules_path.write_text(json.dumps(data), encoding="utf-8")
    return rules_path


def test_load_valid_rules(tmp_path: Path) -> None:
    rules_path = write_rules(
        tmp_path,
        {"required": ["id", "name"], "unique": ["id"], "types": {"id": "integer"}},
    )

    rules = load_rules(rules_path)

    assert rules.required == ["id", "name"]
    assert rules.unique == ["id"]
    assert rules.types == {"id": "integer"}


def test_duplicate_field_in_required_is_rejected(tmp_path: Path) -> None:
    rules_path = write_rules(tmp_path, {"required": ["id", "name", "id"]})

    with pytest.raises(RulesError, match="duplicate"):
        load_rules(rules_path)


def test_duplicate_field_in_unique_is_rejected(tmp_path: Path) -> None:
    rules_path = write_rules(tmp_path, {"unique": ["email", "email"]})

    with pytest.raises(RulesError, match="duplicate"):
        load_rules(rules_path)
