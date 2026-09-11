"""Command-line interface for DataGuard."""

from __future__ import annotations

import argparse
import sys

from .checker import DataGuardError, run_checks
from .report import OutputExistsError, format_summary, write_report
from .rules import RulesError, load_rules


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dataguard",
        description="DataGuard - local CSV dataset quality checker.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser("check", help="Check a CSV file against a rules JSON file.")
    check_parser.add_argument("csv_file", help="Path to the input CSV file.")
    check_parser.add_argument("--rules", required=True, help="Path to the rules JSON file.")
    check_parser.add_argument("--output", required=True, help="Path to write the JSON report to.")
    check_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting --output if it already exists (default: refuse and error out).",
    )

    return parser


def run_check_command(csv_file: str, rules_file: str, output_file: str, overwrite: bool = False) -> int:
    try:
        rules = load_rules(rules_file)
        report = run_checks(csv_file, rules)
    except (RulesError, DataGuardError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    report.rules_file = rules_file

    try:
        write_report(report, output_file, overwrite=overwrite)
    except OutputExistsError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(format_summary(report, output_file))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "check":
        return run_check_command(args.csv_file, args.rules, args.output, args.overwrite)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
