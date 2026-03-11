"""
FFP Smart MVP — Pillar 1: USP / Differentiating Factor
=======================================================
Weight: 35% of composite score (Pre-Seed)

Automation flow:
  1. Receive founder Q1 inputs: feature_list[], unique_feature_list[], competitors[]
  2. Optionally enrich competitor metadata via PitchBook API (display only, no scoring)
  3. For each competitor URL → Tavily Extract API (scrape page text)
  4. For each unique feature claim → Fuzzy verification vs relevant competitor pages
  5. Compute USP_Score = (verified_unique / claimed_unique) × 100
  6. Assign Confidence Flag and pillar score via spec-compliant thresholds
  7. Return all stored output fields

CRITICAL: denominator = unique_feature_claim_count (NOT total_feature_count).
"""

import json
import os
import requests
import re
from typing import Optional, List, Dict

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────
TAVILY_EXTRACT_URL = "https://api.tavily.com/extract"

DATA_PROVENANCE_NOTE = "Based on founder-submitted claims, auto-verified against competitor pages."

# Spec-compliant scoring:
# USP_Score % | Confidence | Pillar Score | Dashboard Status
# 80–100%     | HIGH       | 90           | Strong differentiation — verified
# 60–79%      | HIGH       | 78           | Good differentiation — verified
# 60–79%      | MEDIUM     | 62           | Good differentiation — partial verification
# 30–59%      | HIGH/MED   | 55           | Moderate differentiation
# 1–29%       | Any        | 35           | Limited differentiation — few claims verified
# 0%          | Any        | 20           | No uniqueness verified — NEUTRAL, not a fail
# NULL        | N/A        | NULL         | InsufficientData

def _lookup_pillar_score(usp_score: float, confidence: str) -> tuple[Optional[int], str]:
    """Map USP_Score % and Confidence to (pillar_score, dashboard_status)."""
    if usp_score is None:
        return None, "InsufficientData — excluded from composite"

    if usp_score >= 80:
        if confidence == "HIGH":
            return 90, "Strong differentiation — verified"
        else:
            # Fallback for lower confidence but high score
            return 78, "Strong differentiation — partially verified"
    
    if 60 <= usp_score <= 79:
        if confidence == "HIGH":
            return 78, "Good differentiation — verified"
        if confidence == "MEDIUM":
            return 62, "Good differentiation — partial verification"
        return 55, "Good differentiation — low confidence verification"

    if 30 <= usp_score <= 59:
        return 55, "Moderate differentiation"

    if 1 <= usp_score <= 29:
        return 35, "Limited differentiation — few claims verified"

    return 20, "No uniqueness verified — NEUTRAL, not a fail"


# ──────────────────────────────────────────────
# External API helpers
# ──────────────────────────────────────────────

def _tavily_extract(url: str, api_key: str) -> Optional[str]:
    """Scrape clean page text using Tavily Extract."""
    if not api_key:
        return None
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


def _fuzzy_match_verify(
    feature_name: str,
    feature_description: str,
    competitor_pages: List[Dict[str, str]],
) -> List[str]:
    """
    Check if a feature claim is present on competitor pages using explicit text matching.
    Returns names of competitors found to have explicit mentions.
    
    Task: explicit text matching only — no inference.
    """
    found_on = []
    
    # Tokenize feature claim for strict comparison
    # Focus on significant words (len > 3) to reduce noise
    # We use a higher threshold to ensure "explicit" matching
    name_clean = feature_name.lower().strip()
    desc_clean = feature_description.lower().strip()
    
    # Significant tokens from description
    # Changed from {5,} to {4,} to catch words like 'risk', 'maps', 'data'
    desc_tokens = set(re.findall(r'\b[a-z]{4,}\b', desc_clean))
    
    for page in competitor_pages:
        page_text = page.get('text', '').lower()
        if not page_text:
            continue
            
        # 1. Check for Feature Name (Strongest indicator)
        # If the feature name (word-for-word) exists, it's disputed.
        if name_clean and name_clean in page_text:
            found_on.append(page['name'])
            continue

        # 2. Check for token density (Fall back)
        # Lowered from 0.75 to 0.50 to catch more matches while remaining "explicit"
        if not desc_tokens:
            continue
            
        match_count = sum(1 for token in desc_tokens if token in page_text)
        match_rate = match_count / len(desc_tokens)
        
        if match_rate >= 0.50: 
            found_on.append(page['name'])
            
    return found_on


def _pitchbook_enrich(domain: str, api_key: str) -> dict:
    """Enrich competitor metadata (display only)."""
    if not domain or not api_key:
        return {}
    try:
        # Note: Spec says GET /companies/{id} by domain. 
        # Usually requires a search first if ID isn't known.
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
        
        # Get details for first match
        company_id = companies[0].get("id")
        if not company_id:
            return {}
            
        detail = requests.get(
            f"https://api.pitchbook.com/companies/{company_id}",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        detail.raise_for_status()
        d = detail.json()
        return {
            "name": d.get("companyName"),
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
    scraped_count: int,
    skipped_count: int,
    total_competitors: int
) -> str:
    """
    HIGH   — ≥3 competitor URLs successfully scraped
    MEDIUM — ≥3 competitors submitted but 1 URL was SKIPPED (≥2 scraped)
    LOW    — Fewer than 3 competitors successfully scraped
    """
    if scraped_count >= 3:
        return "HIGH"
    if total_competitors >= 3 and skipped_count == 1 and scraped_count >= 2:
        return "MEDIUM"
    return "LOW"


# ──────────────────────────────────────────────
# Main Entry Point
# ──────────────────────────────────────────────

def compute_usp_score(
    feature_list: List[str],
    unique_feature_list: List[Dict],
    competitors: List[Dict],
    tavily_api_key: str = "",
    pitchbook_api_key: str = "",
) -> Dict:
    """
    Compute the USP pillar score based on validation against competitor pages.
    """
    unique_feature_claim_count = len(unique_feature_list)
    total_feature_count = len(feature_list)

    # ── Rule: If unique_feature_claim_count = 0 or total_feature_count = 0 → status = InsufficientData
    if unique_feature_claim_count == 0 or total_feature_count == 0:
        return {
            "USP_Score": None,
            "unique_feature_claim_count": unique_feature_claim_count,
            "verified_unique_feature_count": 0,
            "disputed_features": [],
            "skipped_competitors": [],
            "Confidence_Flag": "LOW",
            "compute_status": "InsufficientData",
            "pillar_score": None,
            "dashboard_status": "InsufficientData",
            "data_provenance_note": DATA_PROVENANCE_NOTE,
            "pitchbook_competitor_data": []
        }

    # ── PitchBook enrichment (display only)
    pitchbook_competitor_data = []
    for comp in competitors:
        domain = comp.get("domain", "")
        meta = {}
        if pitchbook_api_key and domain:
            meta = _pitchbook_enrich(domain, pitchbook_api_key)
        
        pitchbook_competitor_data.append({
            "name": comp.get("name"),
            "sector": meta.get("sector"),
            "stage": meta.get("stage"),
            "description": meta.get("description"),
        })

    # ── Tavily Extract per competitor URL
    scraped_pages: Dict[str, Dict] = {} # name -> {url, text}
    skipped_competitors: List[Dict] = []

    for comp in competitors:
        url = comp.get("product_url", "")
        name = comp.get("name", "")
        if not url:
            skipped_competitors.append({"name": name, "url": url, "reason": "No URL provided"})
            continue

        text = _tavily_extract(url, tavily_api_key)
        if not text:
            # Retry once
            text = _tavily_extract(url, tavily_api_key)
            
        if text:
            scraped_pages[name] = {"name": name, "url": url, "text": text}
        else:
            skipped_competitors.append({
                "name": name, "url": url,
                "reason": "Extraction failed (timeout/403/block)"
            })

    # ── Guard: All URLs failed
    if not scraped_pages and competitors:
        return {
            "USP_Score": 0.0,
            "unique_feature_claim_count": unique_feature_claim_count,
            "verified_unique_feature_count": 0,
            "disputed_features": [],
            "skipped_competitors": skipped_competitors,
            "Confidence_Flag": "LOW",
            "compute_status": "AllURLsFailed",
            "pillar_score": 20,
            "dashboard_status": "All URLs unreachable — neutral score assigned",
            "data_provenance_note": DATA_PROVENANCE_NOTE,
            "pitchbook_competitor_data": pitchbook_competitor_data
        }

    # ── Verify Unique Claims
    disputed_features_out = []
    scraped_list = list(scraped_pages.values())
    
    # We check each claimed unique feature against ALL successfully scraped competitor pages
    # Note: Founder can specify 'not_in_competitors', but spec says "check against EACH scraped competitor page"
    # to find if it is disputed.
    
    disputed_feature_names = set()
    for feat in unique_feature_list:
        feat_name = feat.get("feature_name", "Unnamed Feature")
        feat_desc = feat.get("description", "")
        
        found_on = _fuzzy_match_verify(feat_name, feat_desc, scraped_list)
        
        if found_on:
            disputed_feature_names.add(feat_name)
            for comp_name in found_on:
                disputed_features_out.append({
                    "feature_name": feat_name,
                    "found_on_competitor": comp_name
                })

    # ── Computations
    disputed_count = len(disputed_feature_names)
    verified_count = unique_feature_claim_count - disputed_count
    
    usp_score = (verified_count / unique_feature_claim_count) * 100
    
    # Confidence logic
    confidence_flag = _compute_confidence_flag(
        scraped_count=len(scraped_pages),
        skipped_count=len(skipped_competitors),
        total_competitors=len(competitors)
    )

    # Pillar Score
    pillar_score, dashboard_status = _lookup_pillar_score(usp_score, confidence_flag)

    return {
        "USP_Score": round(usp_score, 2),
        "unique_feature_claim_count": unique_feature_claim_count,
        "verified_unique_feature_count": verified_count,
        "disputed_features": disputed_features_out,
        "skipped_competitors": skipped_competitors,
        "Confidence_Flag": confidence_flag,
        "pitchbook_competitor_data": pitchbook_competitor_data,
        "compute_status": "OK",
        "pillar_score": pillar_score,
        "dashboard_status": dashboard_status,
        "data_provenance_note": DATA_PROVENANCE_NOTE,
    }
