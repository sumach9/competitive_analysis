# pricing_preseed.py

from typing import Dict, Optional

def collect_pricing_preseed(inputs: Dict) -> Dict:
    """
    Capture Pricing & Business Model details for Pre-Seed startups.
    This is a manual/admin review step, no numeric scoring required.
    """

    # Expected input fields
    pricing_model_type = inputs.get("pricing_model_type")  # e.g., 'Subscription', 'Freemium', 'One-time'
    target_customer = inputs.get("target_customer")        # e.g., 'SMB', 'Enterprise', 'Developers'
    pricing_metric = inputs.get("pricing_metric")          # e.g., 'per seat', 'usage-based', 'flat fee'
    price_range = inputs.get("price_range")                # e.g., '$10–$50', 'Contact Sales'
    paying_segment = inputs.get("paying_segment")          # Optional for Pre-Seed, required at Seed

    # Status/notes can be collected by admin
    admin_notes = inputs.get("admin_notes", "")

    return {
        "pricing_model_type": pricing_model_type or "Not provided",
        "target_customer": target_customer or "Not provided",
        "pricing_metric": pricing_metric or "Not provided",
        "price_range": price_range or "Not provided",
        "paying_segment": paying_segment or "Not provided",
        "notes": admin_notes,
        "scoring": "Neutral",  # do not penalize for missing info at Pre-Seed
        "status": "Collected"
    }


# -----------------------------
# Example Usage
# -----------------------------
if __name__ == "__main__":
    founder_input = {
        "pricing_model_type": "Freemium",
        "target_customer": "SMB",
        "pricing_metric": "per seat",
        "price_range": "$10–$50",
        "paying_segment": None,
        "admin_notes": "Founder plans to launch paid tier next quarter."
    }

    result = collect_pricing_preseed(founder_input)
    print("Pre-Seed Pricing & Business Model:", result)
