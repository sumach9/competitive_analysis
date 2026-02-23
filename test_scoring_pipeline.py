import FINAL_SCORE
import json

def test_pipeline():
    with open("sample_startup.json", "r") as f:
        data = json.load(f)
    
    report = FINAL_SCORE.get_final_scores(data)
    
    print("--- Final Scoring Report ---")
    print(f"Company: {report['company_name']}")
    print(f"Stage: {report['stage']}")
    print(f"Final Suitability Score: {report['final_suitability_score']}")
    
    print("\n--- Pillar Breakdowns ---")
    for pillar, details in report['pillars'].items():
        print(f"\n[{pillar}]")
        print(json.dumps(details, indent=2))

if __name__ == "__main__":
    test_pipeline()
