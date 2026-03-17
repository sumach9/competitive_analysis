"""
FFP Smart MVP — End-to-End Pipeline Runner
===========================================
Reads a JSON input file (default: data/sample_startup.json),
runs the full 4-pillar suitability scoring pipeline,
and saves the result to final_report_e2e.json.

Usage:
    python run_end_to_end.py                          # uses sample_startup.json
    python run_end_to_end.py data/my_startup.json     # custom file

Note: Text-based pitch deck parsing (Landing AI ADE) has been replaced
by structured JSON input which maps directly to the spec input schema.
"""

import sys
import os
import json

# Load .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from FINAL_SCORE import get_final_scores


def run_pipeline(file_path: str):
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.", file=sys.stderr)
        sys.exit(1)

    ext = os.path.splitext(file_path)[1].lower()
    if ext != ".json":
        print(
            f"Error: Only JSON input files are supported (got '{ext}').\n"
            "Please provide a structured JSON file matching the spec input schema.\n"
            "See data/sample_startup.json for an example.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Reading startup data from: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        startup_data = json.load(f)

    # Strip comment keys (keys starting with _) before passing to engine
    startup_data = {k: v for k, v in startup_data.items() if not k.startswith("_")}

    print(f"Running scoring pipeline for: {startup_data.get('company_name', 'Unknown')}...")
    report = get_final_scores(startup_data)

    # Save output
    output_file = "final_report_e2e.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n" + "=" * 60)
    print("FINAL SCORING REPORT")
    print("=" * 60)
    print(json.dumps(report, indent=2))
    print("=" * 60)
    print(f"\nReport saved to: {output_file}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join("data", "sample_startup.json")
    run_pipeline(target)
