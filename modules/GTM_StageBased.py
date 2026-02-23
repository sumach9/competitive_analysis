# gtm_stage_based.py

from typing import Dict, List, Optional

# -----------------------------
# Benchmark Lookup for Pre-Seed AGR
# -----------------------------
def get_agr_benchmark(market_type: str, geographic_focus: List[str]) -> Dict:
    """
    Returns a benchmark range (min%, max%) for AGR by market and geography.
    Conservative approach: uses lowest available range if multiple geographies.
    """
    benchmark_config = {
        "B2B SaaS": {"Global": (5, 15), "North America": (5, 15), "Europe": (4, 12)},
        "B2C Consumer": {"Global": (10, 25), "North America": (8, 20), "Europe": (5, 18)},
        "Marketplace": {"Global": (8, 18), "North America": (6, 15)},
        "Fintech": {"Global": (3, 10), "North America": (3, 8)},
        "Healthcare": {"Global": (2, 8), "North America": (2, 7)},
        "Developer Tools": {"Global": (5, 15), "North America": (5, 12)},
    }

    min_vals, max_vals = [], []
    for geo in geographic_focus:
        min_val, max_val = benchmark_config.get(market_type, {}).get(geo, (1, 5))
        min_vals.append(min_val)
        max_vals.append(max_val)
    return {"min": min(min_vals), "max": min(max_vals)}  # conservative

# -----------------------------
# Pre-Seed: Audience Growth Rate
# -----------------------------
def compute_preseed_agr(
    web_growth_rate: Optional[float],
    social_growth_rate: Optional[float],
    market_type: str,
    geographic_focus: List[str]
) -> Dict:
    """
    Computes Pre-Seed Audience Growth Rate and z-score.
    """
    if web_growth_rate is not None and social_growth_rate is not None:
        agr_raw = (web_growth_rate + social_growth_rate) / 2
    elif web_growth_rate is not None:
        agr_raw = web_growth_rate
    elif social_growth_rate is not None:
        agr_raw = social_growth_rate
    else:
        return {
            "AGR_raw": None,
            "AudienceGrowthZ": None,
            "gtm_signal_strength": "Unable to compute due to insufficient data-points",
            "confidence": "Low"
        }

    benchmark = get_agr_benchmark(market_type, geographic_focus)
    min_b, max_b = benchmark["min"], benchmark["max"]
    mean_b = (min_b + max_b) / 2
    std_b = max((max_b - min_b) / 4, 1.0)  # avoid zero std

    agr_z = (agr_raw - mean_b) / std_b

    # Map z-score to signal
    if agr_z >= 1.0:
        signal = "Strong"
    elif agr_z >= 0.25:
        signal = "Positive"
    elif -0.25 < agr_z < 0.25:
        signal = "Neutral"
    elif agr_z > -1.0:
        signal = "Weak"
    else:
        signal = "Concerning"

    confidence = "High" if (web_growth_rate is not None and social_growth_rate is not None) else "Medium"

    return {
        "AGR_raw": round(agr_raw, 2),
        "AudienceGrowthZ": round(agr_z, 2),
        "gtm_signal_strength": signal,
        "confidence": confidence,
        "benchmark_range": f"{min_b}%–{max_b}% monthly ({market_type}, {', '.join(geographic_focus)})"
    }

# -----------------------------
# Seed: Early Engagement Velocity (EEV)
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
    Computes Seed-stage Early Engagement Velocity (EEV) dynamically.
    """
    delta_waitlist = waitlist_curr - waitlist_prev
    delta_beta = beta_curr - beta_prev

    if unique_visitors_curr <= 0:
        return {
            "waitlist_growth_delta": delta_waitlist,
            "beta_user_growth_delta": delta_beta,
            "calculated_early_engagement_velocity": None,
            "gtm_engagement_signal_strength": "Unable to compute: visitors <= 0",
            "confidence": "Low"
        }

    eev = ((delta_waitlist + delta_beta) / unique_visitors_curr) * 100

    # Optional: dynamic benchmark ranges by product type
    benchmark_ranges = {
        "B2B SaaS": (1, 4),
        "B2C Consumer": (2, 6),
        "Marketplace": (1, 5),
        "Fintech": (1, 3),
        "Healthcare": (1, 3),
        "Developer Tools": (1, 4)
    }
    min_b, max_b = benchmark_ranges.get(product_type, (1, 4))

    # Signal mapping
    if eev >= max_b:
        signal = "Strong"
    elif eev >= min_b:
        signal = "Positive"
    elif eev >= 0:
        signal = "Neutral"
    else:
        signal = "Weak"

    confidence = "High" if unique_visitors_curr >= 200 else "Medium"

    return {
        "waitlist_growth_delta": delta_waitlist,
        "beta_user_growth_delta": delta_beta,
        "calculated_early_engagement_velocity": round(eev, 2),
        "gtm_engagement_signal_strength": signal,
        "confidence": confidence,
        "benchmark_range": f"{min_b}%–{max_b}% monthly (Seed-stage {product_type})"
    }

# -----------------------------
# Stage-based Wrapper
# -----------------------------
def compute_gtm_stage(
    company_stage: str,
    inputs: Dict
) -> Dict:
    """
    Stage-aware GTM calculation.
    """
    if company_stage.lower() == "pre-seed":
        return compute_preseed_agr(
            web_growth_rate=inputs.get("web_growth_rate"),
            social_growth_rate=inputs.get("social_growth_rate"),
            market_type=inputs.get("market_type"),
            geographic_focus=inputs.get("geographic_focus", ["Global"])
        )
    elif company_stage.lower() == "seed":
        return compute_seed_eev(
            waitlist_prev=inputs.get("waitlist_prev"),
            waitlist_curr=inputs.get("waitlist_curr"),
            beta_prev=inputs.get("beta_prev"),
            beta_curr=inputs.get("beta_curr"),
            unique_visitors_curr=inputs.get("unique_visitors_curr"),
            product_type=inputs.get("product_type")
        )
    else:
        return {"error": f"Unsupported company_stage: {company_stage}"}

# -----------------------------
# Example Usage
# -----------------------------
if __name__ == "__main__":
    preseed_example = compute_gtm_stage(
        company_stage="Pre-Seed",
        inputs={
            "web_growth_rate": 20,
            "social_growth_rate": 6,
            "market_type": "B2B SaaS",
            "geographic_focus": ["North America"]
        }
    )

    seed_example = compute_gtm_stage(
        company_stage="Seed",
        inputs={
            "waitlist_prev": 600,
            "waitlist_curr": 800,
            "beta_prev": 100,
            "beta_curr": 150,
            "unique_visitors_curr": 5000,
            "product_type": "B2B SaaS"
        }
    )

    print("Pre-Seed GTM Example:")
    for k, v in preseed_example.items():
        print(f"{k}: {v}")

    print("\nSeed GTM Example:")
    for k, v in seed_example.items():
        print(f"{k}: {v}")
