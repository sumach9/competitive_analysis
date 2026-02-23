# proprietary_tech.py

from typing import Dict

def evaluate_proprietary_tech(inputs: Dict) -> Dict:
    """
    Evaluate Proprietary Technology / Technical Build Depth for Pre-Seed & Seed startups.

    Logic:
    - No-code / off-the-shelf = 0 → Neutral
    - Partially custom-built = 50 → Moderate
    - Largely custom-built = 100 → High
    - Any pending or approved patents → Positive signal
    """

    # Map enum input to numeric depth
    build_map = {
        "No – primarily no-code/only configuration": 0,
        "Yes – partially custom-built": 50,
        "Yes – largely custom-built": 100
    }

    custom_build_level = inputs.get("custom_build_level", "")
    patent_status = inputs.get("patent_status", "").lower()  # e.g., "pending", "approved", ""
    
    # Compute depth score
    depth_score = build_map.get(custom_build_level, 0)

    # Classification
    if depth_score == 0:
        classification = "Neutral"
    elif depth_score == 50:
        classification = "Moderate"
    else:  # 100
        classification = "High"

    # Proprietary technology suitability signal
    if depth_score >= 50 or patent_status in ["pending", "approved"]:
        tech_signal = "Positive"
    else:
        tech_signal = "Neutral"

    return {
        "technical_build_depth_score": depth_score,
        "technical_build_depth_classification": classification,
        "proprietary_technology_suitability_signal": tech_signal
    }


# -----------------------------
# Example Usage
# -----------------------------
if __name__ == "__main__":
    example_input = {
        "custom_build_level": "Yes – partially custom-built",
        "company_stage": "Pre-Seed",
        "product_type": "SaaS",
        "patent_status": "pending"
    }

    result = evaluate_proprietary_tech(example_input)
    print("Proprietary Technology Evaluation:", result)
