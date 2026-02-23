from typing import Dict

def compute_arpu(revenue: float, active_users: int) -> float:
    """
    Compute ARPU (Average Revenue Per User)
    Formula: Total revenue / Active users (same period)
    """
    if active_users <= 0:
        return 0.0
    return revenue / active_users

def collect_pricing_seed(inputs: Dict) -> Dict:
    """
    Capture Pricing & Business Model details for Seed-stage startups.
    Seed-stage requires at least one paying segment for scoring.
    """

    # Expected input fields
    pricing_model_type = inputs.get("pricing_model_type")  # e.g., 'Subscription', 'Freemium'
    target_customer = inputs.get("target_customer")
    pricing_metric = inputs.get("pricing_metric")
    price_range = inputs.get("price_range")
    paying_segment = inputs.get("paying_segment")
    
    # ARPU and Engagement inputs for guardrails
    revenue = inputs.get("total_revenue", 0.0)
    active_users = inputs.get("active_users", 0)
    prev_revenue = inputs.get("prev_revenue") # For MoM trend
    
    # Engagement signals for guardrail b
    web_growth = inputs.get("web_growth_rate", 0)
    social_growth = inputs.get("social_growth_rate", 0)
    waitlist_delta = inputs.get("waitlist_curr", 0) - inputs.get("waitlist_prev", 0)
    
    arpu = compute_arpu(revenue, active_users)
    
    admin_notes = inputs.get("admin_notes", "")

    # -----------------------------
    # Status / Scoring with Guardrails
    # -----------------------------
    
    # Rule c: Increasing MoM -> Positive
    mom_increasing = prev_revenue is not None and revenue > prev_revenue
    
    # Rule b: Low ARPU but strong engagement -> Do not penalize
    strong_engagement = (web_growth + social_growth) > 15 or waitlist_delta > 100
    
    if arpu > 50 or mom_increasing:
        scoring = "Positive"
        status = "Strong pricing signals (high ARPU or growth)"
    elif arpu == 0 and pricing_model_type:
        # Rule a: ARPU = 0 but model defined -> Neutral
        scoring = "Neutral"
        status = "Revenue not yet started, but model defined"
    elif arpu < 50 and strong_engagement:
        # Rule b: Low ARPU but strong engagement
        scoring = "Positive"
        status = "Low ARPU offset by strong engagement signals"
    elif paying_segment:
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
        "arpu": f"${arpu:.2f}",
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
