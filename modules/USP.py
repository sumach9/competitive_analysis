"""
FFP Smart MVP — Pillar 1: USP / Differentiating Factor
=======================================================
Weight: 35% of composite score (Pre-Seed)

Automation flow:
  1. Receive founder Q1 inputs: feature_list[], unique_feature_list[], competitors[]
  2. For each competitor URL → Tavily Extract API (scrape page text)
  3. For each unique feature claim → TF-IDF vectorization vs relevant competitor pages
  4. Compute USP_Score = (verified_unique / claimed_unique) × 100
  5. Assign Confidence Flag and pillar score via spec-compliant thresholds
  6. Return all stored output fields

CRITICAL: denominator = unique_feature_claim_count (NOT total_feature_count).
"""

import json
import os
import requests
import re
from typing import Optional, List, Dict
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

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
    
    if usp_score >= 60:
        if confidence == "HIGH":
            return 78, "Good differentiation — verified"
        if confidence == "MEDIUM":
            return 62, "Good differentiation — partial verification"
        return 55, "Good differentiation — low confidence verification"

    if usp_score >= 30:
        return 55, "Moderate differentiation"

    if usp_score > 0:
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


def _tfidf_match_verify(
    feature_name: str,
    feature_description: str,
    competitor_pages: List[Dict[str, str]],
) -> List[str]:
    """
    Check if a feature claim is present on competitor pages using TF-IDF and
    cosine similarity matching. A similarity score > 0.65 means the feature
    is DISPUTED (found on a competitor's site), per the spec.
    """
    found_on = []

    # Combine claim name and description to form the target query
    query_text = f"{feature_name} {feature_description}".lower().strip()

    if not query_text:
        return found_on

    vectorizer = TfidfVectorizer(stop_words="english")

    for page in competitor_pages:
        raw_text = page.get('text')
        if not raw_text:
            continue
        page_text = raw_text.lower()
            
        # Fit vectorizer on the corpus: [query, competitor_page_text]
        try:
            tfidf_matrix = vectorizer.fit_transform([query_text, page_text])
            similarity_score = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            # 0.65 is the threshold defined in the spec
            if similarity_score > 0.65:
                found_on.append(page['name'])
        except ValueError:
            # Vectorizer may raise ValueError if the text contains no words
            continue
            
    return found_on





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
            "validation_score": 0,
            "compute_status": "InsufficientData",
            "pillar_score": None,
            "dashboard_status": "Insufficient feature claims for deterministic comparison",
            "data_provenance_note": DATA_PROVENANCE_NOTE
        }



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
        v_score_fail = 0
        if len(competitors) >= 3:
            v_score_fail += 40
        return {
            "USP_Score": 0.0,
            "unique_feature_claim_count": unique_feature_claim_count,
            "verified_unique_feature_count": 0,
            "disputed_features": [],
            "skipped_competitors": skipped_competitors,
            "Confidence_Flag": "LOW",
            "validation_score": min(v_score_fail, 100),
            "compute_status": "AllURLsFailed",
            "pillar_score": 20,
            "dashboard_status": "All URLs unreachable — neutral score assigned",
            "data_provenance_note": DATA_PROVENANCE_NOTE
        }

    # ── Step 3: Verification (TF-IDF vs Scraped Competitors)
    disputed_features_out = []
    verified_count = 0

    for feat in unique_feature_list:
        feat_name = feat.get("feature_name", "")
        feat_desc = feat.get("description", "")
        
        # New function: deterministic TF-IDF scoring against competitor pages
        found_on_comps = _tfidf_match_verify(feat_name, feat_desc, list(scraped_pages.values()))
        
        if found_on_comps:
            disputed_features_out.append({
                "feature": feat_name,
                "found_on": found_on_comps,
                "note": "Feature found on competitor page (similarity > 0.65)"
            })
        else:
            verified_count += 1

    # ── Computations
    disputed_count = unique_feature_claim_count - verified_count
    
    usp_score = (verified_count / unique_feature_claim_count) * 100
    
    # Confidence logic
    confidence_flag = _compute_confidence_flag(
        scraped_count=len(scraped_pages),
        skipped_count=len(skipped_competitors),
        total_competitors=len(competitors)
    )

    # ── Validation Score ──
    v_score = 0
    total_comps = len(competitors)
    if total_comps >= 3:
        v_score += 40
    if total_comps > 0:
        v_score += int(30 * (len(scraped_pages) / total_comps))
    if confidence_flag == "HIGH":
        v_score += 30
    validation_score = min(v_score, 100)

    # Pillar Score
    pillar_score, dashboard_status = _lookup_pillar_score(usp_score, confidence_flag)

    return {
        "USP_Score": round(usp_score, 2),
        "unique_feature_claim_count": unique_feature_claim_count,
        "verified_unique_feature_count": verified_count,
        "disputed_features": disputed_features_out,
        "skipped_competitors": skipped_competitors,
        "Confidence_Flag": confidence_flag,
        "validation_score": validation_score,
        "compute_status": "OK",
        "pillar_score": pillar_score,
        "dashboard_status": dashboard_status,
        "data_provenance_note": DATA_PROVENANCE_NOTE,
    }
