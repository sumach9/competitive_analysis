# gtm_ga4_free.py

import requests
from typing import Dict, List, Optional
import numpy as np

# -----------------------------
# GA4 Helper
# -----------------------------
def fetch_ga4_metrics(property_id: str, start_date: str, end_date: str, oauth_token: str) -> Dict:
    """
    Fetch website metrics from GA4 using the runReport API.
    Returns total active users per channel for web/social growth computation.
    """
    url = f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"
    headers = {"Authorization": f"Bearer {oauth_token}"}
    
    payload = {
        "dateRanges": [{"startDate": start_date, "endDate": end_date}],
        "metrics": [{"name": "activeUsers"}],
        "dimensions": [{"name": "channelGrouping"}]  # or adjust as needed
    }
    
    resp = requests.post(url, headers=headers, json=payload)
    data = resp.json()
    
    # Parse example: web vs social channels
    # Adjust if GA4 returns different structure
    web_prev = int(data["rows"][0]["metricValues"][0]["value"])
    web_curr = int(data["rows"][1]["metricValues"][0]["value"])
    web_growth_rate = ((web_curr - web_prev) / web_prev) * 100
    
    social_growth_rate = None  # optional if GA4 channel data not detailed
    
    return {
        "web_growth_rate": web_growth_rate,
        "social_growth_rate": social_growth_rate
    }

# -----------------------------
# Pre-Seed GTM: Audience Growth Rate
# -----------------------------
def compute_preseed_agr(
    web_growth_rate: float,
    social_growth_rate: Optional[float],
    market_type: str,
    geographic_focus: List[str]
) -> Dict:
    """
    Compute pre-seed Audience Growth Rate (AGR) and AudienceGrowthZ
    """
    if web_growth_rate is None and social_growth_rate is None:
        return {"error": "Insufficient data to compute AGR"}
    
    # Use available growth rates
    rates = [r for r in [web_growth_rate, social_growth_rate] if r is not None]
    agr_raw = np.mean(rates)
    
    # Example benchmark (replace with real norms per market_type/geography)
    benchmark_min = 5
    benchmark_max = 15
    mean_percent = (benchmark_min + benchmark_max) / 2
    std_percent = max((benchmark_max - benchmark_min) / 4, 1)
    
    z_scores = [(r - mean_percent)/std_percent for r in rates]
    
    # Weighted by market_type
    weights = {
        "B2B SaaS": [0.65, 0.35],
        "B2C Consumer": [0.45, 0.55],
        "Marketplace": [0.55, 0.45],
        "Fintech": [0.60, 0.40],
        "Healthcare": [0.60, 0.40],
        "Developer Tools": [0.70, 0.30]
    }
    w_web, w_social = weights.get(market_type, [0.5, 0.5])
    z_web = z_scores[0]
    z_social = z_scores[1] if len(z_scores) > 1 else z_web
    audience_growth_z = w_web * z_web + w_social * z_social
    
    # Signal buckets
    if audience_growth_z >= 1.0:
        signal = "Strong"
    elif 0.25 <= audience_growth_z < 1.0:
        signal = "Positive"
    elif -0.25 < audience_growth_z < 0.25:
        signal = "Neutral"
    elif -1.0 < audience_growth_z <= -0.25:
        signal = "Weak"
    else:
        signal = "Concerning"
    
    return {
        "web_growth_rate_input": f"{web_growth_rate:.1f}%",
        "social_growth_rate_input": f"{social_growth_rate:.1f}%" if social_growth_rate is not None else "N/A",
        "calculated_audience_growth_rate": f"{audience_growth_z:.2f}z",
        "benchmark_growth_range_for_stage": f"{benchmark_min}%–{benchmark_max}% monthly (Pre-Seed {market_type}, {geographic_focus[0]})",
        "gtm_signal_strength": signal
    }

# -----------------------------
# Seed GTM: Early Engagement Velocity
# -----------------------------
def compute_seed_eev(
    waitlist_prev: int,
    waitlist_curr: int,
    beta_prev: int,
    beta_curr: int,
    unique_visitors_curr: int,
    product_type: str
) -> Dict:
    """
    Compute Early Engagement Velocity (EEV) for Seed-stage companies
    """
    if None in [waitlist_prev, waitlist_curr, beta_prev, beta_curr, unique_visitors_curr] or unique_visitors_curr <= 0:
        return {"error": "Insufficient data to compute EEV"}
    
    delta_waitlist = waitlist_curr - waitlist_prev
    delta_beta = beta_curr - beta_prev
    eev = ((delta_waitlist + delta_beta) / unique_visitors_curr) * 100
    
    # Example benchmark ranges (conceptual)
    benchmark_min, benchmark_max = 1, 4  # percent per month
    if eev > benchmark_max:
        signal = "Strong"
    elif benchmark_min <= eev <= benchmark_max:
        signal = "Positive"
    elif 0 < eev < benchmark_min:
        signal = "Neutral"
    elif eev == 0:
        signal = "Weak"
    else:
        signal = "Concerning"
    
    return {
        "waitlist_growth_delta": str(delta_waitlist),
        "beta_user_growth_delta": str(delta_beta),
        "calculated_early_engagement_velocity": f"{eev:.1f}%",
        "benchmark_engagement_range_for_stage": f"{benchmark_min}%–{benchmark_max}% monthly (Seed-stage {product_type})",
        "gtm_engagement_signal_strength": signal
    }

# -----------------------------
# Stage-aware wrapper
# -----------------------------
def compute_gtm_free_stage(inputs: Dict, company_stage: str, ga4_config: Optional[Dict] = None) -> Dict:
    """
    Stage-aware GTM computation (Pre-Seed vs Seed) using only GA4 + founder inputs
    """
    company_stage = company_stage.lower()
    
    if company_stage == "pre-seed":
        # Fetch GA4 if needed
        web_growth_rate = inputs.get("web_growth_rate")
        social_growth_rate = inputs.get("social_growth_rate")
        if (web_growth_rate is None or social_growth_rate is None) and ga4_config:
            ga4_data = fetch_ga4_metrics(**ga4_config)
            web_growth_rate = web_growth_rate or ga4_data.get("web_growth_rate")
            social_growth_rate = social_growth_rate or ga4_data.get("social_growth_rate")
        
        return compute_preseed_agr(
            web_growth_rate=web_growth_rate,
            social_growth_rate=social_growth_rate,
            market_type=inputs.get("market_type"),
            geographic_focus=inputs.get("geographic_focus", ["Global"])
        )
    
    elif company_stage == "seed":
        return compute_seed_eev(
            waitlist_prev=inputs.get("waitlist_prev"),
            waitlist_curr=inputs.get("waitlist_curr"),
            beta_prev=inputs.get("beta_prev"),
            beta_curr=inputs.get("beta_curr"),
            unique_visitors_curr=inputs.get("unique_visitors_curr"),
            product_type=inputs.get("product_type")
        )
    
    else:
        return {"error": "Unsupported company_stage"}

# -----------------------------
# Example Usage
# -----------------------------
if __name__ == "__main__":
    # Pre-Seed Example
    preseed_inputs = {"market_type": "B2B SaaS", "geographic_focus": ["North America"]}
    ga4_cfg = {"property_id": "123456", "start_date": "2026-01-01", "end_date": "2026-01-31", "oauth_token": "YOUR_TOKEN"}
    preseed_result = compute_gtm_free_stage(preseed_inputs, "Pre-Seed", ga4_config=ga4_cfg)
    print("Pre-Seed GTM:", preseed_result)
    
    # Seed Example
    seed_inputs = {"waitlist_prev": 600, "waitlist_curr": 800, "beta_prev": 100, "beta_curr": 150, "unique_visitors_curr": 5000, "product_type": "B2B SaaS"}
    seed_result = compute_gtm_free_stage(seed_inputs, "Seed")
    print("Seed GTM:", seed_result)
