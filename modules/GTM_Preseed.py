# gtm_preseed_optimal.py

from typing import Dict, List

# Example: Dynamic benchmark lookup (replace with DB/API in production)
def get_agr_benchmark(market_type: str, geographic_focus: List[str]) -> Dict:
    """
    Returns a benchmark range (min%, max%) for AGR by market and geography.
    If multiple geographies provided, uses the most conservative (lowest) range.
    """
    benchmark_config = {
        "B2B SaaS": {"Global": (5, 15), "North America": (5, 15), "Europe": (4, 12)},
        "B2C Consumer": {"Global": (10, 25), "North America": (8, 20), "Europe": (5, 18)},
        "Marketplace": {"Global": (8, 18), "North America": (6, 15)},
        "Fintech": {"Global": (3, 10), "North America": (3, 8)},
        "Healthcare": {"Global": (2, 8), "North America": (2, 7)},
        "Developer Tools": {"Global": (5, 15), "North America": (5, 12)},
    }
    # Take the most conservative range across geographies
    min_vals, max_vals = [], []
    for geo in geographic_focus:
        min_val, max_val = benchmark_config.get(market_type, {}).get(geo, (1, 5))
        min_vals.append(min_val)
        max_vals.append(max_val)
    return {"min": min(min_vals), "max": min(max_vals)}  # conservative


def compute_preseed_agr(
    web_growth_rate: float,
    social_growth_rate: float,
    market_type: str,
    geographic_focus: List[str]
) -> Dict:
    """
    Computes Pre-Seed Audience Growth Rate and z-score dynamically.
    """
    # Compute raw AGR
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

    # Get dynamic benchmark
    benchmark = get_agr_benchmark(market_type, geographic_focus)
    min_b, max_b = benchmark["min"], benchmark["max"]
    mean_b = (min_b + max_b) / 2
    std_b = max((max_b - min_b) / 4, 1.0)  # avoid zero std

    # Compute z-score
    agr_z = (agr_raw - mean_b) / std_b

    # Signal mapping
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

    # Confidence flag: higher if both web + social exist
    confidence = "High" if (web_growth_rate is not None and social_growth_rate is not None) else "Medium"

    return {
        "AGR_raw": round(agr_raw, 2),
        "AudienceGrowthZ": round(agr_z, 2),
        "gtm_signal_strength": signal,
        "confidence": confidence,
        "benchmark_range": f"{min_b}%–{max_b}% monthly ({market_type}, {', '.join(geographic_focus)})"
    }


# -----------------------------
# Example Usage
# -----------------------------
if __name__ == "__main__":
    example = compute_preseed_agr(
        web_growth_rate=20,
        social_growth_rate=6,
        market_type="B2B SaaS",
        geographic_focus=["North America"]
    )

    for k, v in example.items():
        print(f"{k}: {v}")
