"""Read one JSON scenario and print a JSON assessment to stdout."""

import argparse
import json
import sys
from decimal import Decimal, DecimalException
from pathlib import Path

from .core import analyze


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline ERP scenario checks; no automatic decisions.")
    parser.add_argument("scenario", type=Path, help="JSON scenario path")
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.scenario.read_text(encoding="utf-8-sig"), parse_float=Decimal,
                          object_pairs_hook=unique_object)
        result = analyze(data)
    except (OSError, ValueError, UnicodeError, DecimalException, RecursionError):
        # Do not echo input values, filesystem paths, or credentials on failure.
        print("Invalid scenario: check the JSON structure, fields, and finite numeric values.", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=True, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
