"""
FFP Smart MVP — Shared Configuration
=====================================
Hardcoded Static Benchmark Table for GTM Path B z-score computation.
Gemini only fuzzy-matches market_type labels to table rows — it NEVER
generates these benchmark values. Reviewed annually.

Source basis:
  - SaaS Capital 2025 benchmarks (median SaaS ~25% annual ≈ 2%/month)
  - ChartMogul 2024–25 growth data
  - First Page Sage B2B SaaS reports
Ranges set conservatively for Pre-Seed where audiences are small.
"""

# ──────────────────────────────────────────────
# Pillar Weights  (Pre-Seed)
# ──────────────────────────────────────────────
PILLAR_WEIGHTS = {
    "USP":     0.35,
    "GTM":     0.15,
    "PRICING": 0.20,
    "TECH":    0.30,
}

# ──────────────────────────────────────────────
# Static Benchmark Table
# Keys: web_low, web_high, social_low, social_high  (all in %)
#        w_web, w_soc  (channel reliability weights, sum = 1.0)
# ──────────────────────────────────────────────
BENCHMARK_TABLE: dict[str, dict] = {
    "B2B SaaS": {
        "web_low": 1.0, "web_high": 8.0,
        "social_low": 1.0, "social_high": 5.0,
        "w_web": 0.65, "w_soc": 0.35,
    },
    "B2C Consumer": {
        "web_low": 4.0, "web_high": 20.0,
        "social_low": 3.0, "social_high": 15.0,
        "w_web": 0.40, "w_soc": 0.60,
    },
    "Marketplace": {
        "web_low": 3.0, "web_high": 12.0,
        "social_low": 2.0, "social_high": 8.0,
        "w_web": 0.50, "w_soc": 0.50,
    },
    "Fintech": {
        "web_low": 2.0, "web_high": 10.0,
        "social_low": 2.0, "social_high": 7.0,
        "w_web": 0.60, "w_soc": 0.40,
    },
    "Healthcare / HealthTech": {
        "web_low": 1.0, "web_high": 5.0,
        "social_low": 1.0, "social_high": 4.0,
        "w_web": 0.65, "w_soc": 0.35,
    },
    "Developer Tools": {
        "web_low": 3.0, "web_high": 10.0,
        "social_low": 2.0, "social_high": 8.0,
        "w_web": 0.60, "w_soc": 0.40,
    },
    "eCommerce / Retail": {
        "web_low": 4.0, "web_high": 18.0,
        "social_low": 3.0, "social_high": 12.0,
        "w_web": 0.45, "w_soc": 0.55,
    },
    "EdTech": {
        "web_low": 2.0, "web_high": 10.0,
        "social_low": 2.0, "social_high": 10.0,
        "w_web": 0.50, "w_soc": 0.50,
    },
    "DeepTech / Hardware": {
        "web_low": 1.0, "web_high": 4.0,
        "social_low": 1.0, "social_high": 3.0,
        "w_web": 0.70, "w_soc": 0.30,
    },
    "Other": {
        "web_low": 2.0, "web_high": 10.0,
        "social_low": 2.0, "social_high": 8.0,
        "w_web": 0.55, "w_soc": 0.45,
    },
}

# Canonical list of market type labels (used in Gemini fuzzy-match prompt)
MARKET_TYPE_LABELS: list[str] = list(BENCHMARK_TABLE.keys())

# ──────────────────────────────────────────────
# Suitability Composite Thresholds
# ──────────────────────────────────────────────
SUITABILITY_THRESHOLDS = [
    (75, 100, "Strong Signal",      "Green"),
    (55,  74, "Moderate Signal",    "Amber"),
    (35,  54, "Weak Signal",        "Orange"),
    (0,   34, "Insufficient Signal","Red"),
]


def get_suitability_label(score: float) -> tuple[str, str]:
    """Return (label, colour) for a composite score."""
    for low, high, label, colour in SUITABILITY_THRESHOLDS:
        if low <= score <= high:
            return label, colour
    return "Insufficient Signal", "Red"
