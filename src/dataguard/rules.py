"""Loading and validating DataGuard rule files."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .models import SUPPORTED_TYPES, Rules


class RulesError(ValueError):
    """Raised when a rules file cannot be parsed or is structurally invalid."""


def load_rules(rules_path: str | Path) -> Rules:
    path = Path(rules_path)
    if not path.is_file():
        raise RulesError(f"Rules file not found: {path}")

    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RulesError(f"Could not read rules file: {path} ({exc})") from exc

    try:
        data: Any = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RulesError(f"Rules file is not valid JSON: {path} ({exc})") from exc

    if not isinstance(data, dict):
        raise RulesError("Rules file must contain a JSON object at the top level.")

    required = _parse_string_list(data.get("required", []), "required")
    unique = _parse_string_list(data.get("unique", []), "unique")
    types = _parse_types(data.get("types", {}))

    return Rules(required=required, unique=unique, types=types)


def _parse_string_list(value: Any, key: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise RulesError(f"Rules field '{key}' must be a list of field names (strings).")

    duplicates = sorted({item for item, count in Counter(value).items() if count > 1})
    if duplicates:
        raise RulesError(
            f"Rules field '{key}' contains duplicate field name(s): {', '.join(duplicates)}."
        )

    return list(value)


def _parse_types(value: Any) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise RulesError("Rules field 'types' must be an object mapping field name to type.")

    result: dict[str, str] = {}
    for field_name, type_name in value.items():
        if not isinstance(field_name, str) or not isinstance(type_name, str):
            raise RulesError("Rules field 'types' must map string field names to string type names.")
        if type_name not in SUPPORTED_TYPES:
            raise RulesError(
                f"Unsupported type '{type_name}' for field '{field_name}'. "
                f"Supported types: {', '.join(SUPPORTED_TYPES)}."
            )
        result[field_name] = type_name
    return result
