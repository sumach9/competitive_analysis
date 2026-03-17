"""
FFP Smart MVP — Shared Configuration
=====================================
Hardcoded Static Benchmark Table for GTM Path B z-score computation.
Reviewed annually.

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
# Static Benchmark Table (AGR Absolute Thresholds)
# ──────────────────────────────────────────────
BENCHMARK_TABLE: dict[str, dict] = {
    "B2B SaaS":                {"benchmark_min": 1.0, "benchmark_mean": 3.0, "benchmark_max": 8.0},
    "B2C Consumer":            {"benchmark_min": 3.0, "benchmark_mean": 8.0, "benchmark_max": 20.0},
    "Marketplace":             {"benchmark_min": 2.0, "benchmark_mean": 5.0, "benchmark_max": 12.0},
    "Fintech":                 {"benchmark_min": 2.0, "benchmark_mean": 4.0, "benchmark_max": 10.0},
    "Healthcare / HealthTech": {"benchmark_min": 1.0, "benchmark_mean": 2.5, "benchmark_max": 5.0},
    "Developer Tools":         {"benchmark_min": 2.0, "benchmark_mean": 4.0, "benchmark_max": 10.0},
    "eCommerce / Retail":      {"benchmark_min": 3.0, "benchmark_mean": 7.0, "benchmark_max": 18.0},
    "EdTech":                  {"benchmark_min": 2.0, "benchmark_mean": 4.5, "benchmark_max": 10.0},
    "DeepTech / Hardware":     {"benchmark_min": 1.0, "benchmark_mean": 2.0, "benchmark_max": 4.0},
    "Other":                   {"benchmark_min": 2.0, "benchmark_mean": 4.0, "benchmark_max": 10.0},
}

# Canonical list of market type labels (used for label matching in GTM)
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
