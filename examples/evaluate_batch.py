import sys
import os
import json

# Add the project root to the path so we can import from the root directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from FINAL_SCORE import get_final_scores

def run_batch_evaluation(file_path: str):
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.", file=sys.stderr)
        sys.exit(1)

    print(f"Reading batch startup data from: {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        startups = json.load(f)

    if not isinstance(startups, list):
        print("Error: Batch evaluation requires a JSON file containing a list of startup objects.")
        sys.exit(1)

    print(f"Loaded {len(startups)} startups for evaluation.")
    
    batch_results = []
    
    for idx, startup_data in enumerate(startups):
        name = startup_data.get('company_name', f'Unknown_{idx}')
        print(f"\n[{idx+1}/{len(startups)}] Scoring: {name}...")
        
        # Strip comment keys (keys starting with _) before passing to engine
        cleaned_data = {k: v for k, v in startup_data.items() if not k.startswith("_")}
        
        try:
            report = get_final_scores(cleaned_data)
            batch_results.append({
                "startup": name,
                "composite_score": report.get("composite_score"),
                "suitability_label": report.get("suitability_label"),
                "ai_executive_summary": report.get("ai_executive_summary"),
                "raw_report": report
            })
            print(f"  -> Success! Score: {report.get('composite_score')} ({report.get('suitability_label')})")
        except Exception as e:
            print(f"  -> FAILED to evaluate {name}: {e}")
            batch_results.append({
                "startup": name,
                "error": str(e)
            })

    # Save output
    output_file = "final_batch_report.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(batch_results, f, indent=2)

    print("\n" + "=" * 60)
    print("BATCH EVALUATION COMPLETE")
    print("=" * 60)
    print(f"Evaluated {len(startups)} startups.")
    print(f"Batch report saved to: {output_file}")


if __name__ == "__main__":
    target = os.path.join("data", "10_sample_startups.json")
    run_batch_evaluation(target)
