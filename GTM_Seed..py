#gtm_seed_optimal.py

from typing import Dict, Tuple

# Example: Benchmark lookup function (can be replaced with DB/API)
def get_benchmark_range(product_type: str, company_stage: str) -> Tuple[float, float]:
    """
    Returns min/max benchmark % for the given stage and product type dynamically.
    Replace this with real-time config lookup in production.
    """
    benchmark_config = {
        "Seed": {
            "B2B SaaS": (1, 4),
            "B2C Consumer": (2, 5),
            "Marketplace": (2, 6),
            "Fintech": (1, 3),
            "Developer Tools": (1, 4),
            "Healthcare": (1, 3)
        }
    }
    return benchmark_config.get(company_stage, {}).get(product_type, (1, 4))


def compute_eev_dynamic(
    waitlist_prev: int,
    waitlist_curr: int,
    beta_prev: int,
    beta_curr: int,
    unique_visitors_curr: int,
    product_type: str,
    company_stage: str = "Seed"
) -> Dict:
    """
    Optimized Seed GTM calculation using dynamic benchmarks.
    """
    # Guardrails
    if unique_visitors_curr <= 0:
        return {
            "waitlist_growth_delta": None,
            "beta_user_growth_delta": None,
            "calculated_early_engagement_velocity": None,
            "benchmark_engagement_range_for_stage": None,
            "gtm_engagement_signal_strength": "Unable to compute due to insufficient data-points",
            "confidence": "Low"
        }

    # Compute deltas
    delta_waitlist = waitlist_curr - waitlist_prev
    delta_beta = beta_curr - beta_prev

    # Compute EEV %
    eev = ((delta_waitlist + delta_beta) / unique_visitors_curr) * 100

    # Confidence flag based on sample size
    confidence = "Low" if unique_visitors_curr < 200 else "High"

    # Dynamic benchmark
    min_b, max_b = get_benchmark_range(product_type, company_stage)

    # Compute z-score like normalized engagement
    if max_b - min_b == 0:
        z_score = 0
    else:
        z_score = (eev - ((min_b + max_b) / 2)) / ((max_b - min_b) / 4)  # similar to std dev

    # Map z-score to signal dynamically
    if z_score >= 1.0:
        signal = "Strong"
    elif z_score >= 0.25:
        signal = "Positive"
    elif -0.25 < z_score < 0.25:
        signal = "Neutral"
    elif z_score > -1.0:
        signal = "Weak"
    else:
        signal = "Concerning"

    return {
        "waitlist_growth_delta": str(delta_waitlist),
        "beta_user_growth_delta": str(delta_beta),
        "calculated_early_engagement_velocity": f"{round(eev,2)}%",
        "benchmark_engagement_range_for_stage": f"{min_b}%–{max_b}% monthly ({company_stage} {product_type})",
        "gtm_engagement_signal_strength": signal,
        "confidence": confidence,
        "audience_growth_z": round(z_score, 2)
    }


# -----------------------------
# Example Usage
# -----------------------------
if __name__ == "__main__":
    example = compute_eev_dynamic(
        waitlist_prev=600,
        waitlist_curr=800,
        beta_prev=100,
        beta_curr=150,
        unique_visitors_curr=5000,
        product_type="B2B SaaS",
        company_stage="Seed"
    )

    for k, v in example.items():
        print(f"{k}: {v}")
