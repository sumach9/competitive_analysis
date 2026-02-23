import Tech
import GTM_StageBased
import Pricing_Seed
import Pricing_Preseed
import json

def test_simplified_pipeline():
    with open("sample_startup.json", "r") as f:
        data = json.load(f)
    
    stage = data.get("company_stage", "Seed")
    
    # Pillar results
    tech_results = Tech.evaluate_proprietary_tech(data)
    gtm_results = GTM_StageBased.compute_gtm_stage(stage, data)
    
    if stage.lower() == "seed":
        pricing_results = Pricing_Seed.collect_pricing_seed(data)
    else:
        pricing_results = Pricing_Preseed.collect_pricing_preseed(data)
        
    print("--- Simplified Scoring Report (No USP) ---")
    print(f"Proprietary Tech: {json.dumps(tech_results, indent=2)}")
    print(f"GTM: {json.dumps(gtm_results, indent=2)}")
    print(f"Pricing: {json.dumps(pricing_results, indent=2)}")

if __name__ == "__main__":
    test_simplified_pipeline()
