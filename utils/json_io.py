import sys
import json
import os
from typing import Dict, Any

def read_json_input() -> Dict[str, Any]:
    """
    Reads JSON from a file specified in sys.argv or from sys.stdin.
    Usage: python script.py data.json 
    OR     cat data.json | python script.py
    """
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        with open(sys.argv[1], "r") as f:
            return json.load(f)
    
    # Check if stdin is not a TTY (i.e., piped input)
    if not sys.stdin.isatty():
        return json.load(sys.stdin)
    
    # If no file and no pipe, return a placeholder or raise error if necessary
    # For now, we'll try to find sample_startup.json in common locations as a fallback
    # but primarily it should error if no input is provided.
    
    potential_sample = os.path.join(os.path.dirname(__file__), "..", "data", "sample_startup.json")
    if os.path.exists(potential_sample):
        with open(potential_sample, "r") as f:
            return json.load(f)
            
    print("Error: No JSON input provided via file argument or stdin.", file=sys.stderr)
    sys.exit(1)

def write_json_output(data: Any):
    """
    Writes data as JSON to stdout.
    """
    print(json.dumps(data, indent=2))
