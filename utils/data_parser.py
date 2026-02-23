import re
from typing import Dict, List

def parse_pitch_deck_text(text: str) -> Dict:
    """
    Very basic heuristic parser to extract scoring features from pitch deck text.
    In a real scenario, this would use an LLM or more robust NLP.
    """
    data = {
        "startup_features": [],
        "competitors": [],
        "custom_build_level": "Yes – partially custom-built",
        "company_stage": "Seed"
    }
    
    # Heuristic for features: lines starting with bullet points or "Feature:"
    feature_matches = re.findall(r"(?:^|\n)[-•*]\s*(.*)", text)
    data["startup_features"] = [f.strip() for f in feature_matches if len(f) > 5]
    
    # Heuristic for competitors: "Competitors: A, B, C" or "Comp A: ..."
    comp_matches = re.finditer(r"Competitor:\s*([^\n]*)", text, re.IGNORECASE)
    for m in comp_matches:
        comp_name = m.group(1).strip()
        data["competitors"].append({"name": comp_name, "feature_list": ["Similar product"]})
        
    return data

if __name__ == "__main__":
    example_text = """
    Pitch Deck: AI Health Tracker
    Features:
    - Real-time heart rate monitoring
    - Predictive diet suggestions
    - Peer-to-peer fitness challenges
    
    Competitors:
    - Competitor: Fitbit
    - Competitor: Apple Health
    """
    print(parse_pitch_deck_text(example_text))
