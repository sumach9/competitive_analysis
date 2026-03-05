"""
FFP Smart MVP — Pillar 1: USP / Differentiating Factor
=======================================================
Weight: 35% of composite score (Pre-Seed)

Automation flow:
  1. Receive founder Q1 inputs: feature_list[], unique_feature_list[], competitors[]
  2. Optionally enrich competitor metadata via PitchBook API (display only, no scoring)
  3. For each competitor URL → Tavily Extract API (scrape page text)
  4. For each scraped page → Gemini 2.0 Flash (temp=0) → disputed_features[]
  5. Compute USP_Score = verified / claimed × 100
  6. Assign Confidence Flag and pillar score via lookup table
  7. Return all stored output fields

CRITICAL: denominator = unique_feature_claim_count (NOT total_feature_count).
"""

import json
import os
import requests
from typing import Optional


# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────
TAVILY_EXTRACT_URL = "https://api.tavily.com/extract"
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta"
    "/models/gemini-2.0-flash:generateContent"
)
DATA_PROVENANCE_NOTE = (
    "Claims auto-verified against competitor pages. "
    "Competitor metadata from PitchBook."
)

# Pillar score lookup table (USP_Score %, Confidence) → pillar_score
# Rows evaluated in order; first match wins.
_PILLAR_SCORE_TABLE = [
    # (usp_min, usp_max, confidence_set or None, pillar_score, dashboard_status)
    (80, 100, None,           90, "Strong differentiation — verified"),
    (60,  79, {"HIGH"},       78, "Good differentiation — verified"),
    (60,  79, {"MEDIUM"},     62, "Good differentiation — partial verification"),
    (30,  59, None,           55, "Moderate differentiation"),
    (1,   29, None,           35, "Limited differentiation — few claims verified"),
    (0,    0, None,           20, "No uniqueness verified — NEUTRAL, not a fail"),
]


# ──────────────────────────────────────────────
# External API helpers
# ──────────────────────────────────────────────

def _tavily_extract(url: str, api_key: str) -> Optional[str]:
    """
    Call Tavily Extract API for a single competitor URL.
    Returns clean page text or None on failure.
    """
    try:
        resp = requests.post(
            TAVILY_EXTRACT_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={"urls": [url]},
            timeout=15,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if results and results[0].get("raw_content"):
            return results[0]["raw_content"]
        return None
    except Exception:
        return None


def _gemini_find_disputed(
    unique_features: list[dict],
    page_text: str,
    api_key: str,
) -> list[str]:
    """
    Call Gemini 2.0 Flash (temperature=0) to identify which claimed unique
    features are EXPLICITLY described in the competitor page text.
    Returns list of disputed feature_name strings.
    """
    system_instruction = (
        "You are a product feature comparator. You receive a list of claimed unique "
        "features and the scraped text of a competitor product page. Your ONLY task: "
        "identify which claimed features are EXPLICITLY DESCRIBED in the competitor "
        "page text. Do NOT infer. Do NOT guess. Only flag a feature if it is clearly "
        "and directly described on the page. Return JSON only: "
        '{"disputed_features": ["feature_name_1"]}. '
        "Return an empty array if none found. No other text."
    )
    feature_payload = json.dumps([
        {"feature_name": f["feature_name"], "description": f["description"]}
        for f in unique_features
    ])
    user_message = (
        f"UNIQUE FEATURES TO CHECK:\n{feature_payload}\n\n"
        f"COMPETITOR PAGE TEXT:\n{page_text[:8000]}\n\n"  # guard token limit
        "Return JSON only."
    )
    payload = {
        "system_instruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"parts": [{"text": user_message}]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 512},
    }
    try:
        resp = requests.post(
            f"{GEMINI_URL}?key={api_key}",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=20,
        )
        resp.raise_for_status()
        raw = (
            resp.json()
            .get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "{}")
        )
        # Strip markdown fences if present
        raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        data = json.loads(raw)
        return data.get("disputed_features", [])
    except Exception:
        return []


def _pitchbook_enrich(domain: str, api_key: str) -> dict:
    """
    Enrich a competitor entry via PitchBook API by domain.
    Returns display metadata only — NOT used in scoring.
    """
    if not domain or not api_key:
        return {}
    try:
        # Step 1: lookup company ID by domain
        lookup = requests.get(
            "https://api.pitchbook.com/companies",
            headers={"Authorization": f"Bearer {api_key}"},
            params={"domain": domain},
            timeout=10,
        )
        lookup.raise_for_status()
        companies = lookup.json().get("data", [])
        if not companies:
            return {}
        company_id = companies[0].get("id")
        if not company_id:
            return {}
        # Step 2: fetch enrichment
        detail = requests.get(
            f"https://api.pitchbook.com/companies/{company_id}",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        detail.raise_for_status()
        d = detail.json()
        return {
            "sector": d.get("primarySector"),
            "stage": d.get("stage"),
            "description": d.get("shortDescription"),
        }
    except Exception:
        return {}


# ──────────────────────────────────────────────
# Confidence Flag Logic
# ──────────────────────────────────────────────

def _compute_confidence_flag(
    competitors_submitted: int,
    scraped_count: int,
    skipped_count: int,
) -> str:
    """
    HIGH  — ≥3 competitor URLs successfully scraped
    MEDIUM — ≥3 competitors submitted but exactly 1 SKIPPED (≥2 scraped)
    LOW   — fewer than 3 competitors successfully scraped
    """
    if scraped_count >= 3:
        return "HIGH"
    if competitors_submitted >= 3 and skipped_count == 1 and scraped_count >= 2:
        return "MEDIUM"
    return "LOW"


# ──────────────────────────────────────────────
# Pillar Score Lookup
# ──────────────────────────────────────────────

def _lookup_pillar_score(usp_score: float, confidence: str) -> tuple[int, str]:
    """Map (USP_Score, Confidence) → (pillar_score, dashboard_status)."""
    for usp_min, usp_max, conf_set, score, status in _PILLAR_SCORE_TABLE:
        if usp_min <= usp_score <= usp_max:
            if conf_set is None or confidence in conf_set:
                return score, status
    return 20, "No uniqueness verified — NEUTRAL, not a fail"


# ──────────────────────────────────────────────
# Main Entry Point
# ──────────────────────────────────────────────

def compute_usp_score(
    feature_list: list[str],
    unique_feature_list: list[dict],
    competitors: list[dict],
    tavily_api_key: str = "",
    gemini_api_key: str = "",
    pitchbook_api_key: str = "",
) -> dict:
    """
    Compute the USP pillar score.

    Parameters
    ----------
    feature_list : list[str]
        All product features (unique and non-unique). Used for context only.
    unique_feature_list : list[dict]
        Each entry: {feature_name, description, not_in_competitors[], own_product_url?}
    competitors : list[dict]
        Each entry: {name, product_url, domain?}
    tavily_api_key : str
        Tavily Extract API key (Bearer token).
    gemini_api_key : str
        Gemini 2.0 Flash API key (Google AI Studio).
    pitchbook_api_key : str
        PitchBook Direct Data API key. Optional — used for display enrichment only.

    Returns
    -------
    dict with all stored output fields defined in the spec.
    """
    # ── Guard: InsufficientData
    if not feature_list or not unique_feature_list:
        return {
            "USP_Score": None,
            "unique_feature_claim_count": len(unique_feature_list),
            "verified_unique_feature_count": None,
            "disputed_features": [],
            "skipped_competitors": [],
            "Confidence_Flag": "LOW",
            "pitchbook_competitor_data": [],
            "compute_status": "InsufficientData",
            "pillar_score": None,
            "dashboard_status": "InsufficientData",
            "data_provenance_note": DATA_PROVENANCE_NOTE,
        }

    unique_feature_claim_count = len(unique_feature_list)

    # ── PitchBook enrichment (display only)
    pitchbook_competitor_data = []
    for comp in competitors:
        domain = comp.get("domain", "")
        meta = _pitchbook_enrich(domain, pitchbook_api_key)
        pitchbook_competitor_data.append({
            "name": comp.get("name"),
            "sector": meta.get("sector"),
            "stage": meta.get("stage"),
            "description": meta.get("description"),
        })

    # ── Tavily Extract per competitor URL
    scraped_pages: list[dict] = []   # {name, url, text}
    skipped_competitors: list[dict] = []

    for comp in competitors:
        url = comp.get("product_url", "")
        name = comp.get("name", "")
        if not url:
            skipped_competitors.append({"name": name, "url": url, "reason": "No URL provided"})
            continue

        text = _tavily_extract(url, tavily_api_key)
        if text:
            scraped_pages.append({"name": name, "url": url, "text": text})
        else:
            # Retry once
            text = _tavily_extract(url, tavily_api_key)
            if text:
                scraped_pages.append({"name": name, "url": url, "text": text})
            else:
                skipped_competitors.append({
                    "name": name, "url": url,
                    "reason": "Timeout / 403 / bot-block / empty content",
                })

    # ── Guard: AllURLsFailed
    if not scraped_pages:
        return {
            "USP_Score": None,
            "unique_feature_claim_count": unique_feature_claim_count,
            "verified_unique_feature_count": None,
            "disputed_features": [],
            "skipped_competitors": skipped_competitors,
            "Confidence_Flag": "LOW",
            "pitchbook_competitor_data": pitchbook_competitor_data,
            "compute_status": "AllURLsFailed",
            "pillar_score": None,
            "dashboard_status": "AllURLsFailed — no competitor pages could be scraped",
            "data_provenance_note": DATA_PROVENANCE_NOTE,
        }

    # ── Gemini comparison per scraped page
    disputed_by_feature: dict[str, list[str]] = {}  # feature_name → [competitor_names]

    for page in scraped_pages:
        disputed = _gemini_find_disputed(unique_feature_list, page["text"], gemini_api_key)
        for feat_name in disputed:
            disputed_by_feature.setdefault(feat_name, []).append(page["name"])

    # ── Aggregate disputed features (deduplicated by feature_name)
    disputed_features_out = [
        {"feature_name": k, "found_on_competitor": v}
        for k, v in disputed_by_feature.items()
    ]

    disputed_feature_count = len(disputed_by_feature)
    verified_unique_feature_count = unique_feature_claim_count - disputed_feature_count

    # ── USP Score
    usp_score = (verified_unique_feature_count / unique_feature_claim_count) * 100
    usp_score = round(max(usp_score, 0.0), 2)

    # ── Confidence Flag
    confidence_flag = _compute_confidence_flag(
        competitors_submitted=len(competitors),
        scraped_count=len(scraped_pages),
        skipped_count=len(skipped_competitors),
    )

    # ── Pillar score from lookup table
    pillar_score, dashboard_status = _lookup_pillar_score(usp_score, confidence_flag)

    # ── NULL score when 0% USP with no competitor pages scraped? — handled above
    compute_status = "OK"

    return {
        "USP_Score": usp_score,
        "unique_feature_claim_count": unique_feature_claim_count,
        "verified_unique_feature_count": verified_unique_feature_count,
        "disputed_features": disputed_features_out,
        "skipped_competitors": skipped_competitors,
        "Confidence_Flag": confidence_flag,
        "pitchbook_competitor_data": pitchbook_competitor_data,
        "compute_status": compute_status,
        "pillar_score": pillar_score,
        "dashboard_status": dashboard_status,
        "data_provenance_note": DATA_PROVENANCE_NOTE,
    }