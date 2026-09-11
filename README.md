# DataGuard

DataGuard is a local command-line tool for checking the quality of CSV
datasets against a set of rules described in a JSON file. It reads a CSV
file, validates it against your rules, prints a summary to the terminal,
and writes a detailed JSON report to disk. Everything runs locally against
files on your machine — there is no web UI, database, or remote service
involved.

## Requirements

- Python 3.10 or later

## Installation

From the project root:

```bash
python -m venv .venv
source .venv/Scripts/activate   # on Windows Git Bash / macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
```

This installs the `dataguard` console command inside the virtual
environment. The `[dev]` extra additionally installs `pytest` for running
the test suite.

## CLI usage

```bash
dataguard check <csv_file> --rules <rules_file> --output <report_file> [--overwrite]
```

- `<csv_file>` — path to the input CSV file (UTF-8, with a header row).
  The field delimiter is auto-detected between `,` and `;` (Excel often
  exports CSV with `;`), so both comma- and semicolon-separated files work
  without any extra flag.
- `--rules <rules_file>` — path to the JSON rules file describing the
  checks to run.
- `--output <report_file>` — path where the JSON report will be written.
  If this file already exists, `dataguard` refuses to overwrite it and
  exits with a non-zero status unless `--overwrite` is also given.
- `--overwrite` — allow `--output` to replace an existing file.

Example:

```bash
dataguard check examples/valid_data.csv --rules examples/valid_rules.json --output report.json
```

## Rules file format

The rules file is a single JSON object with up to three keys, all optional:

```json
{
  "required": ["id", "name", "email"],
  "unique": ["id", "email"],
  "types": {
    "id": "integer",
    "age": "integer",
    "score": "number",
    "name": "string",
    "email": "string"
  }
}
```

- **`required`** — list of field names whose value must not be missing.
  A value is considered missing if it is an empty string or contains only
  whitespace.
- **`unique`** — list of field names whose non-empty values must not
  repeat across rows. The second and later occurrence of the same value is
  flagged as `duplicate_value`. Empty values are not checked for
  uniqueness (use `required` for that).

  `required` and `unique` must each list a given field name at most once;
  a repeated field name in either list makes the rules file itself
  invalid and is rejected when the rules are loaded (before any CSV
  checking happens).
- **`types`** — mapping of field name to expected type. Supported types:
  - `integer` — after stripping leading/trailing whitespace, the value
    must represent a whole number (an optional leading `+`/`-` sign
    followed only by digits). `12.5` is **not** a valid integer.
  - `number` — after stripping whitespace, the value must parse as a
    finite decimal number (integers and decimals both accepted).
  - `string` — any non-missing value is accepted; use `required` to
    control whether the field may be blank.

  A missing value is never reported as `invalid_type` — if the field is
  also `required`, only `missing_required` is recorded for that cell.

If a rule refers to a column name that does not exist in the CSV header,
it is reported once as a dataset-level `missing_column` issue (not
repeated for every row), and no row-level checks are run against that
field.

## Checks performed

Row-level issue codes:

- `missing_required` — a required field is empty or blank.
- `duplicate_value` — a unique field's non-empty value repeats an earlier
  row's value.
- `invalid_type` — a value does not match its declared type.

Dataset-level issue codes:

- `missing_column` — a field referenced by the rules is not present in
  the CSV header.

Row numbers in the report match the actual CSV line numbers: the first
data row (right after the header) is row `2`. A row that has at least one
row-level issue counts as an *invalid row*; all other rows are *valid
rows*.

## Terminal output

Running `dataguard check` prints a summary including the input file, the
total number of data rows, the number of valid and invalid rows, a count
per issue code, and the path of the JSON report that was written.

## JSON report structure

```json
{
  "input_file": "...",
  "rules_file": "...",
  "total_rows": 6,
  "valid_rows": 2,
  "invalid_rows": 4,
  "issue_counts": {
    "missing_required": 1,
    "duplicate_value": 1,
    "invalid_type": 2,
    "missing_column": 0
  },
  "dataset_issues": [
    { "field": "phone", "code": "missing_column", "message": "..." }
  ],
  "row_issues": [
    { "row": 3, "field": "name", "code": "missing_required", "message": "..." }
  ]
}
```

## Examples

The `examples/` directory contains two ready-to-run scenarios:

- `valid_data.csv` + `valid_rules.json` — a dataset that fully satisfies
  the rules (0 invalid rows).
- `invalid_data.csv` + `invalid_rules.json` — a dataset that contains a
  missing required value, a duplicate unique value, an invalid integer,
  and an invalid number, all at once.

Run them with:

```bash
dataguard check examples/valid_data.csv --rules examples/valid_rules.json --output examples/valid_report.json
dataguard check examples/invalid_data.csv --rules examples/invalid_rules.json --output examples/invalid_report.json
```

## Running the tests

```bash
python -m pytest
```

The suite in `tests/` covers, among other cases: a fully valid dataset, a
missing required field, a duplicate unique value, an invalid integer, an
invalid number, and rules that reference a column absent from the CSV
header.
