# pricing_seed.py

from typing import Dict

def collect_pricing_seed(inputs: Dict) -> Dict:
    """
    Capture Pricing & Business Model details for Seed-stage startups.
    Seed-stage requires at least one paying segment for scoring.
    """

    # Expected input fields
    pricing_model_type = inputs.get("pricing_model_type")  # e.g., 'Subscription', 'Freemium', 'One-time'
    target_customer = inputs.get("target_customer")        # e.g., 'SMB', 'Enterprise', 'Developers'
    pricing_metric = inputs.get("pricing_metric")          # e.g., 'per seat', 'usage-based', 'flat fee'
    price_range = inputs.get("price_range")                # e.g., '$10–$50', 'Contact Sales'
    paying_segment = inputs.get("paying_segment")          # Seed stage: should have at least one paying segment

    admin_notes = inputs.get("admin_notes", "")

    # -----------------------------
    # Status / Scoring
    # -----------------------------
    if paying_segment:
        scoring = "Positive"
        status = "At least one paying segment confirmed"
    else:
        scoring = "Neutral"
        status = "No paying segment yet; may need follow-up"

    return {
        "pricing_model_type": pricing_model_type or "Not provided",
        "target_customer": target_customer or "Not provided",
        "pricing_metric": pricing_metric or "Not provided",
        "price_range": price_range or "Not provided",
        "paying_segment": paying_segment or "Not provided",
        "notes": admin_notes,
        "scoring": scoring,
        "status": status
    }


# -----------------------------
# Example Usage
# -----------------------------
if __name__ == "__main__":
    founder_input = {
        "pricing_model_type": "Subscription",
        "target_customer": "Enterprise",
        "pricing_metric": "per seat",
        "price_range": "$200–$500",
        "paying_segment": "1 enterprise customer",
        "admin_notes": "First paying client signed this month."
    }

    result = collect_pricing_seed(founder_input)
    print("Seed Pricing & Business Model:", result)
