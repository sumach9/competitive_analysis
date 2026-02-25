# final_score.py
from modules import Scoring_Engine
from typing import Dict
import json

def get_final_scores(startup_data: Dict) -> Dict:
    """
    Runs the full scoring engine and returns the final report.
    """
    # Run the engine
    results = Scoring_Engine.run_scoring_pipeline(startup_data)
    
    # Calculate a simple aggregate suitability score (0-100)
    # This can be refined based on weights for each pillar
    pillars = results["pillars"]
    
    # Simple Heuristic for Final Suitability Score:
    # USP: Uniqueness Ratio (0-1)
    # Tech: Depth Score (0-100)
    # GTM: AGR Z or EEV % mapping
    # Pricing: Status mapping
    
    usp_score = pillars["usp"].get("final_usp_score", 0)
    tech_score = pillars["proprietary_tech"].get("technical_build_depth_score", 0)
    
    # GTM Weighting
    gtm_signal = pillars["gtm"].get("gtm_signal_strength", "Neutral")
    gtm_map = {"Strong": 100, "Positive": 75, "Neutral": 50, "Weak": 25, "Concerning": 0, "Unable to compute due to insufficient data-points": 50}
    gtm_score = gtm_map.get(gtm_signal, 50)
    
    # Pricing Weighting
    pricing_signal = pillars["pricing_business_model"].get("scoring", "Neutral")
    pricing_map = {"Positive": 100, "Neutral": 50, "Weak": 0}
    pricing_score = pricing_map.get(pricing_signal, 50)
    
    # Weighted Average
    weights = {
        "usp": 0.3,
        "tech": 0.2,
        "gtm": 0.3,
        "pricing": 0.2
    }
    
    final_score = (
        usp_score * weights["usp"] +
        tech_score * weights["tech"] +
        gtm_score * weights["gtm"] +
        pricing_score * weights["pricing"]
    )
    
    results["final_suitability_score"] = round(final_score, 2)
    return results

if __name__ == "__main__":
    # Test with sample data
    import os
    data_path = os.path.join("data", "sample_startup.json")
    with open(data_path, "r") as f:
        data = json.load(f)
    
    final_report = get_final_scores(data)
    print(json.dumps(final_report, indent=2))
