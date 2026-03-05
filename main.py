import sys
import os
import json
from FINAL_SCORE import get_final_scores
from utils.json_io import read_json_input, write_json_output

def main():
    """
    Main entry point for the Startup Scoring System.
    Accepts JSON input from a file or stdin and outputs a complete scoring report.
    """
    try:
        # 1. Read input data
        # Use stderr for status messages to keep stdout clean for JSON output
        print("Scoring System Starting...", file=sys.stderr)
        data = read_json_input()
        
        # 2. Run scoring engine
        print(f"Calculating scores for: {data.get('company_name', 'Unknown Startup')}...", file=sys.stderr)
        report = get_final_scores(data)
        
        # 3. Output results
        print("Success! Generating final report...", file=sys.stderr)
        write_json_output(report)
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
