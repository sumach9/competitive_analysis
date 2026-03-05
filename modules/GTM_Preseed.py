"""
FFP Smart MVP — Pillar 2: GTM Strategy — Audience Growth Rate
=============================================================
Weight: 15% of composite score (Pre-Seed)

Path A (PitchBook):  webGrowthRate, socialGrowthRate, percentiles → z-scores via invNorm
Path B (GA4 + GSC):  Month-over-month sessions / followers → z-scores via Static Benchmark Table

Gemini 2.0 Flash is used ONLY for fuzzy market_type label matching in Path B when
no exact match exists in the benchmark table. It NEVER generates benchmark values.
"""

import math
import os
import json
import requests
from typing import Optional
from scipy.stats import norm

from config.benchmark_table import BENCHMARK_TABLE, MARKET_TYPE_LABELS


# ──────────────────────────────────────────────
# Utility: inverse normal (percentile 0–100 → z)
# ──────────────────────────────────────────────
def _inv_norm(percentile: float) -> float:
    p = min(max(float(percentile), 0.1), 99.9) / 100.0  # clamp away from ±∞
    return float(norm.ppf(p))


# ──────────────────────────────────────────────
# Utility: z-score from raw rate
# ──────────────────────────────────────────────
def _z_from_rate(rate: float, mean: float, std: float) -> float:
    if std <= 0:
        return 0.0
    return (rate - mean) / std


# ──────────────────────────────────────────────
# Gemini: fuzzy market_type label match (Path B only)
# ──────────────────────────────────────────────
def _gemini_match_market_type(market_description: str, gemini_api_key: str) -> str:
    """
    Ask Gemini 2.0 Flash to map a free-text market description to one of the
    benchmark table labels. Returns the matched label string only.
    Falls back to 'Other' on any error.
    """
    if not gemini_api_key:
        return "Other"
    label_list = ", ".join(MARKET_TYPE_LABELS)
    prompt = (
        f"Given this market description: {market_description}. "
        f"Which of these market types is the closest match: {label_list}? "
        "Return the label only. No explanation."
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 30},
    }
    try:
        gemini_url = (
            "https://generativelanguage.googleapis.com/v1beta"
            f"/models/gemini-2.0-flash:generateContent?key={gemini_api_key}"
        )
        resp = requests.post(
            gemini_url,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=15,
        )
        resp.raise_for_status()
        text = (
            resp.json()
            .get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
            .strip()
        )
        # Validate the returned label exists in the table
        for label in MARKET_TYPE_LABELS:
            if label.lower() in text.lower():
                return label
        return "Other"
    except Exception:
        return "Other"


# ──────────────────────────────────────────────
# Path A — PitchBook API
# ──────────────────────────────────────────────
def _fetch_pitchbook_growth(domain: str, api_key: str) -> Optional[dict]:
    """
    Lookup PitchBook company by domain and retrieve growth metrics.
    Returns raw API dict or None if not found / on error.
    """
    if not domain or not api_key:
        return None
    try:
        lookup = requests.get(
            "https://api.pitchbook.com/companies",
            headers={"Authorization": f"Bearer {api_key}"},
            params={"domain": domain},
            timeout=10,
        )
        lookup.raise_for_status()
        companies = lookup.json().get("data", [])
        if not companies:
            return None
        company_id = companies[0].get("id")
        if not company_id:
            return None
        analytics = requests.get(
            f"https://api.pitchbook.com/companies/{company_id}/social-analytics",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        analytics.raise_for_status()
        return analytics.json()
    except Exception:
        return None


# ──────────────────────────────────────────────
# Path B — GA4 Data API
# ──────────────────────────────────────────────
def _fetch_ga4_sessions(property_id: str, oauth_token: str) -> Optional[dict]:
    """
    Pull two months of GA4 session data via OAuth.
    Returns {"web_visitors_prev": int, "web_visitors_curr": int} or None.
    """
    if not property_id or not oauth_token:
        return None
    try:
        import datetime
        today = datetime.date.today()
        curr_start = today.replace(day=1)
        prev_end = curr_start - datetime.timedelta(days=1)
        prev_start = prev_end.replace(day=1)

        body = {
            "dateRanges": [
                {"startDate": str(prev_start), "endDate": str(prev_end)},
                {"startDate": str(curr_start), "endDate": str(today)},
            ],
            "dimensions": [{"name": "yearMonth"}],
            "metrics": [{"name": "sessions"}],
        }
        resp = requests.post(
            f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport",
            headers={
                "Authorization": f"Bearer {oauth_token}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=15,
        )
        resp.raise_for_status()
        rows = resp.json().get("rows", [])
        sessions = [int(r["metricValues"][0]["value"]) for r in rows]
        if len(sessions) >= 2:
            return {"web_visitors_prev": sessions[0], "web_visitors_curr": sessions[1]}
        return None
    except Exception:
        return None


# ──────────────────────────────────────────────
# Signal bucket → pillar score
# ──────────────────────────────────────────────
def _signal_bucket(z: float) -> tuple[str, int]:
    if z >= 1.0:
        return "Strong", 90
    elif z >= 0.25:
        return "Positive", 70
    elif z >= -0.25:
        return "Neutral", 50
    elif z >= -1.0:
        return "Weak", 30
    else:
        return "Concerning", 15


# ──────────────────────────────────────────────
# Main Entry Point
# ──────────────────────────────────────────────
def compute_preseed_gtm(
    startup_domain: str = "",
    market_type: str = "",
    market_description: str = "",
    # Path A
    pitchbook_api_key: str = "",
    pitchbook_data: Optional[dict] = None,   # inject directly in tests / if pre-fetched
    # Path B — GA4
    ga4_property_id: str = "",
    ga4_oauth_token: str = "",
    ga4_data: Optional[dict] = None,          # inject directly or pass manual
    # Path B — Manual fallback
    web_visitors_prev: Optional[int] = None,
    web_visitors_curr: Optional[int] = None,
    # Social (all paths — manual entry)
    social_followers_prev: Optional[int] = None,
    social_followers_curr: Optional[int] = None,
    # Gemini
    gemini_api_key: str = "",
) -> dict:
    """
    Compute GTM Audience Growth Rate pillar.

    Path selection:
      1. If pitchbook_data supplied (or PitchBook API returns data) → Path A
      2. Else → Path B (GA4 OAuth, then manual fallback)
    """

    compute_path = None
    web_growth_rate: Optional[float] = None
    social_growth_rate: Optional[float] = None
    z_web: Optional[float] = None
    z_soc: Optional[float] = None
    w_web: float = 0.55
    w_soc: float = 0.45
    status_label = "OK"
    confidence_level = "HIGH"
    benchmark_source = None
    matched_market_type = None
    flags: list[str] = []

    # ── Path A: PitchBook ──────────────────────────────────────
    pb_data = pitchbook_data
    if pb_data is None and startup_domain and pitchbook_api_key:
        pb_data = _fetch_pitchbook_growth(startup_domain, pitchbook_api_key)

    if pb_data and (pb_data.get("webGrowthRate") is not None or
                    pb_data.get("socialGrowthRate") is not None):
        compute_path = "PitchBook"
        benchmark_source = "PitchBook API"
        web_growth_rate = pb_data.get("webGrowthRate")
        social_growth_rate = pb_data.get("socialGrowthRate")
        web_pct = pb_data.get("webGrowthRatePercentile")
        soc_pct = pb_data.get("socialGrowthRatePercentile")
        web_size_pct = pb_data.get("webSizeMultiplePercentile", 50)
        soc_size_pct = pb_data.get("socialSizeMultiplePercentile", 50)

        if web_pct is not None and soc_pct is not None:
            # invNorm method
            z_web = _inv_norm(web_pct) if web_pct is not None else None
            z_soc = _inv_norm(soc_pct) if soc_pct is not None else None
            r_web = 0.5 + 0.5 * (web_size_pct / 100)
            r_soc = 0.5 + 0.5 * (soc_size_pct / 100)
            w_web = r_web / (r_web + r_soc)
            w_soc = r_soc / (r_web + r_soc)
        else:
            # Only raw rates — fall to benchmark table for z-scores
            compute_path = "PitchBook (rates only) + Benchmark"
            benchmark_source = "PitchBook rates + Static Benchmark Table"
            pb_data = None  # trigger benchmark logic below

    # ── Path B: GA4 + Benchmark ────────────────────────────────
    if compute_path is None:
        # Try GA4 API first
        ga4 = ga4_data
        if ga4 is None and ga4_property_id and ga4_oauth_token:
            ga4 = _fetch_ga4_sessions(ga4_property_id, ga4_oauth_token)
            if ga4:
                flags.append("WEB_DATA_GA4_API")
                benchmark_source = "GA4 API"

        # Manual fallback if GA4 OAuth declined or not provided
        if ga4 is None:
            if web_visitors_prev is not None and web_visitors_curr is not None:
                ga4 = {
                    "web_visitors_prev": web_visitors_prev,
                    "web_visitors_curr": web_visitors_curr,
                }
                flags.append("WEB_DATA_MANUAL")
                confidence_level = "LOW"
                benchmark_source = "Founder-submitted manual entry"
            else:
                ga4 = {}

        compute_path = "GA4/Manual"

        wv_prev = ga4.get("web_visitors_prev")
        wv_curr = ga4.get("web_visitors_curr")

        # InvalidBaselinePrevZero
        if wv_prev == 0:
            flags.append("InvalidBaselinePrevZero_web")
            wv_prev = None
        if social_followers_prev == 0:
            flags.append("InvalidBaselinePrevZero_social")
            social_followers_prev = None

        if wv_prev and wv_curr and wv_prev > 0:
            web_growth_rate = (wv_curr - wv_prev) / wv_prev * 100
        if social_followers_prev and social_followers_curr and social_followers_prev > 0:
            social_growth_rate = (social_followers_curr - social_followers_prev) / social_followers_prev * 100

        # Match market_type to benchmark table
        resolved_type = market_type if market_type in BENCHMARK_TABLE else None
        if resolved_type is None and market_description:
            resolved_type = _gemini_match_market_type(market_description, gemini_api_key)
            flags.append(f"MARKET_TYPE_GEMINI_MATCHED:{resolved_type}")
        if resolved_type is None:
            resolved_type = "Other"
        matched_market_type = resolved_type

        bm = BENCHMARK_TABLE[resolved_type]
        mean_web = (bm["web_low"] + bm["web_high"]) / 2
        mean_soc = (bm["social_low"] + bm["social_high"]) / 2
        std_web = max((bm["web_high"] - bm["web_low"]) / 4, 1.0)
        std_soc = max((bm["social_high"] - bm["social_low"]) / 4, 1.0)
        w_web = bm["w_web"]
        w_soc = bm["w_soc"]

        z_web = _z_from_rate(web_growth_rate, mean_web, std_web) if web_growth_rate is not None else None
        z_soc = _z_from_rate(social_growth_rate, mean_soc, std_soc) if social_growth_rate is not None else None
        if not benchmark_source:
            benchmark_source = "Static Benchmark Table"

    # ── UnableToCompute guard ───────────────────────────────────
    if web_growth_rate is None and social_growth_rate is None:
        return {
            "AGR_raw": None,
            "AudienceGrowthZ": None,
            "gtm_signal_bucket": "UnableToCompute",
            "gtm_pillar_score": None,
            "compute_path": compute_path,
            "confidence_level": "LOW",
            "status_label": "UnableToCompute",
            "web_growth_rate": None,
            "social_growth_rate": None,
            "benchmark_source": benchmark_source,
            "matched_market_type": matched_market_type,
            "flags": flags,
            "dashboard_note": "Unable to compute due to insufficient data-points.",
        }

    # ── PartialData: single channel ─────────────────────────────
    partial = False
    if web_growth_rate is None or social_growth_rate is None:
        partial = True
        status_label = "PartialData"
        confidence_level = "MEDIUM"
        if web_growth_rate is None:
            z_web = 0.0
        if social_growth_rate is None:
            z_soc = 0.0

    # ── AGR_raw ─────────────────────────────────────────────────
    rates = [r for r in [web_growth_rate, social_growth_rate] if r is not None]
    AGR_raw = round(sum(rates) / len(rates), 2) if rates else None

    # ── Weighted AudienceGrowthZ ────────────────────────────────
    AudienceGrowthZ = round(w_web * (z_web or 0.0) + w_soc * (z_soc or 0.0), 4)

    # ── NeedsHumanReview ───────────────────────────────────────
    if AGR_raw is not None and (abs(AGR_raw) > 300 or abs(AudienceGrowthZ) > 3):
        status_label = "NeedsHumanReview"
        flags.append("OUTLIER_DETECTED")

    # ── Signal bucket ───────────────────────────────────────────
    bucket, raw_pillar_score = _signal_bucket(AudienceGrowthZ)

    # ── PartialData multiplier ──────────────────────────────────
    pillar_score = round(raw_pillar_score * 0.80) if partial else raw_pillar_score

    # ── Social data provenance flag ─────────────────────────────
    if social_followers_prev is None and social_followers_curr is None:
        flags.append("SOCIAL_DATA_MISSING")

    return {
        "AGR_raw": AGR_raw,
        "AudienceGrowthZ": AudienceGrowthZ,
        "web_growth_rate": round(web_growth_rate, 2) if web_growth_rate is not None else None,
        "social_growth_rate": round(social_growth_rate, 2) if social_growth_rate is not None else None,
        "z_web": round(z_web, 4) if z_web is not None else None,
        "z_soc": round(z_soc, 4) if z_soc is not None else None,
        "w_web": round(w_web, 4),
        "w_soc": round(w_soc, 4),
        "gtm_signal_bucket": bucket,
        "gtm_pillar_score": pillar_score,
        "compute_path": compute_path,
        "benchmark_source": benchmark_source,
        "matched_market_type": matched_market_type,
        "confidence_level": confidence_level,
        "status_label": status_label,
        "flags": flags,
        "dashboard_note": None,
    }