"""
FFP Smart MVP — Pillar 4: Proprietary Technology — Technical Build Depth
========================================================================
Weight: 30% of composite score (Pre-Seed)

Scoring: Pure deterministic rule-based logic — NO AI used anywhere.
Patent verification: additive signal only (USPTO → PatentsView → Assignment Search).
  - Verified patent: bonus points on top of base score (capped at 100).
  - No patent / unverified claim: zero penalty, base score unchanged.

Evidence links are REQUIRED when custom_build_level >= 50.
Form submission is BLOCKED (ValueError raised) if evidence_links is empty at that level.
"""

import os
import requests
import xml.etree.ElementTree as ET
from typing import Optional
import asyncio
import concurrent.futures


# ──────────────────────────────────────────────
# Build Depth Map (deterministic)
# ──────────────────────────────────────────────
_BUILD_DEPTH_MAP: dict[int, dict] = {
    0:   {"depth_label": "Neutral",   "base_score": 45},
    25:  {"depth_label": "Neutral",   "base_score": 50},
    50:  {"depth_label": "Positive",  "base_score": 70},
    75:  {"depth_label": "Positive",  "base_score": 78},
    100: {"depth_label": "Positive",  "base_score": 85},
}

VALID_BUILD_LEVELS = {0, 25, 50, 75, 100}


# ──────────────────────────────────────────────
# Patent API Endpoints
# ──────────────────────────────────────────────
USPTO_APP_URL = "https://data.uspto.gov/apis/patent-file-wrapper/application-data/{app_num}"
PATENTSVIEW_URL = "https://api.patentsview.org/patents/query"
ASSIGNMENT_URL = "https://assignment-api.uspto.gov/patent/search"


# ──────────────────────────────────────────────
# Patent Verification — Step 1: USPTO by app/patent number
# ──────────────────────────────────────────────
def _verify_step1_uspto(patent_numbers: list[str]) -> Optional[dict]:
    """
    Check USPTO Open Data Portal for each application/patent number.
    Returns first match found, or None.
    """
    for app_num in patent_numbers:
        try:
            resp = requests.get(
                USPTO_APP_URL.format(app_num=app_num.strip()),
                timeout=15,
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
            status = data.get("applicationStatus", "") or ""
            title = data.get("patentTitle") or data.get("applicationTitle") or ""
            filing_date = data.get("filingDate", "")
            assignee = data.get("assigneeEntityName", "")

            if "Patented" in status or "patent" in status.lower():
                return {
                    "step": "USPTO_AppNumber",
                    "patent_status": "Granted",
                    "patent_number_verified": app_num,
                    "display_label": "USPTO-verified (Granted)",
                    "bonus": 10,
                    "detail": {"title": title, "filing_date": filing_date, "assignee": assignee},
                }
            elif "pending" in status.lower() or "Pending" in status:
                return {
                    "step": "USPTO_AppNumber",
                    "patent_status": "Pending",
                    "patent_number_verified": app_num,
                    "display_label": "USPTO-verified (Pending)",
                    "bonus": 8,
                    "detail": {"title": title, "filing_date": filing_date, "assignee": assignee},
                }
        except Exception:
            continue
    return None


# ──────────────────────────────────────────────
# Patent Verification — Step 2: PatentsView
# ──────────────────────────────────────────────
def _verify_step2_patentsview(
    company_name: str,
    inventor_names: list[dict],  # [{first, last}, ...]
) -> Optional[dict]:
    """
    Search PatentsView by assignee organization or inventor name.
    Returns first verifiable match, or None.
    """
    queries = []
    if company_name:
        queries.append({"q": f'{{"assignee_organization":"{company_name}"}}',
                         "f": '["patent_number","patent_title","patent_date","assignee_organization"]'})
    for inv in inventor_names[:3]:  # limit attempts
        last = inv.get("last", "")
        first = inv.get("first", "")
        if last:
            queries.append({"q": f'{{"inventor_last_name":"{last}","inventor_first_name":"{first}"}}',
                             "f": '["patent_number","patent_title","patent_date"]'})
    for q in queries:
        try:
            resp = requests.get(PATENTSVIEW_URL, params=q, timeout=15)
            if resp.status_code != 200:
                continue
            patents = resp.json().get("patents") or []
            if patents:
                p = patents[0]
                if p.get("patent_date"):
                    return {
                        "step": "PatentsView",
                        "patent_status": "Granted",
                        "patent_number_verified": p.get("patent_number", ""),
                        "display_label": "Patent found — PatentsView verified",
                        "bonus": 8,
                        "detail": {"title": p.get("patent_title"), "date": p.get("patent_date")},
                    }
        except Exception:
            continue
    return None


# ──────────────────────────────────────────────
# Patent Verification — Step 3: Assignment Search
# ──────────────────────────────────────────────
def _verify_step3_assignment(
    company_name: str,
    assignee_company_name: str,
    patent_numbers: list[str],
) -> Optional[dict]:
    """
    Check USPTO Patent Assignment Search by assignee name or patent number.
    Parses XML response.
    """
    search_names = [n for n in [company_name, assignee_company_name] if n]
    queries = [{"assignee": n} for n in search_names]
    queries += [{"patent-number": pn.strip()} for pn in patent_numbers[:3]]

    for params in queries:
        try:
            resp = requests.get(ASSIGNMENT_URL, params=params, timeout=15)
            if resp.status_code != 200:
                continue
            # Parse XML
            root = ET.fromstring(resp.text)
            assignments = root.findall(".//{*}assignment") or root.findall(".//assignment")
            if assignments:
                first = assignments[0]
                assignee_el = first.find(".//{*}assignee-name") or first.find(".//assignee-name")
                pat_el = first.find(".//{*}patent-number") or first.find(".//patent-number")
                return {
                    "step": "Assignment",
                    "patent_status": "Assigned",
                    "patent_number_verified": pat_el.text if pat_el is not None else "",
                    "display_label": "Assigned to company — USPTO-verified",
                    "bonus": 8,
                    "detail": {
                        "assignee": assignee_el.text if assignee_el is not None else "",
                    },
                }
        except Exception:
            continue
    return None


# ──────────────────────────────────────────────
# 3-Step Async Patent Verification
# ──────────────────────────────────────────────
def _run_patent_verification(
    patent_numbers: list[str],
    inventor_names: list[dict],
    company_name: str,
    assignee_company_name: str,
    patent_status_declared: str,
) -> dict:
    """
    Run Steps 1 → 2 → 3 in order. Stop at first success.
    Non-blocking: called from thread pool by the async wrapper.

    Returns a result dict with verification outcome fields.
    """
    # Step 1 — USPTO by application/patent number
    if patent_numbers:
        result = _verify_step1_uspto(patent_numbers)
        if result:
            return result

    # Step 2 — PatentsView
    result = _verify_step2_patentsview(company_name, inventor_names)
    if result:
        return result

    # Step 3 — Assignment Search
    result = _verify_step3_assignment(company_name, assignee_company_name, patent_numbers)
    if result:
        return result

    # No match across all 3 steps
    if patent_status_declared == "Granted":
        note = "Founder-declared — unverified (pending public record)"
    else:
        note = "Founder-declared — unverified (apps take 12–18 months to appear)"

    return {
        "step": "NotFound",
        "patent_status": patent_status_declared,
        "patent_number_verified": "",
        "display_label": note,
        "bonus": 0,
        "detail": {},
    }


# ──────────────────────────────────────────────
# Main Entry Point
# ──────────────────────────────────────────────
def calculate_technical_build_depth(
    custom_build_level: int,
    patent_status: Optional[str] = None,      # None / "Pending" / "Granted"
    patent_numbers: Optional[list[str]] = None,
    inventor_names: Optional[list[dict]] = None,  # [{first, last}, ...]
    assignee_company_name: Optional[str] = None,
    company_name: str = "",
    evidence_links: Optional[list[str]] = None,
    tech_description: Optional[str] = None,
    run_patent_verification: bool = True,     # set False in unit tests
) -> dict:
    """
    Compute the Proprietary Technology pillar score.

    Parameters
    ----------
    custom_build_level : int
        Must be one of: 0, 25, 50, 75, 100.
    patent_status : str or None
        One of: None, "Pending", "Granted". If provided, patent verification runs.
    patent_numbers : list[str]
        USPTO application or patent numbers. Required if patent_status is set.
    inventor_names : list[dict]
        [{first: str, last: str}, ...]. Fallback search if no patent number.
    assignee_company_name : str or None
        Holding entity name if patent is not assigned directly to startup.
    company_name : str
        Startup legal entity name — used in PatentsView and Assignment Search.
    evidence_links : list[str]
        REQUIRED if custom_build_level >= 50. Form submission is BLOCKED otherwise.
    tech_description : str or None
        Optional text describing the custom build and moat.
    run_patent_verification : bool
        Set to False to skip API calls (for unit testing deterministic logic).

    Returns
    -------
    dict with all stored output fields defined in the spec.

    Raises
    ------
    ValueError
        If custom_build_level >= 50 and evidence_links is empty.
    ValueError
        If custom_build_level is not one of {0, 25, 50, 75, 100}.
    """
    evidence_links = evidence_links or []
    patent_numbers = patent_numbers or []
    inventor_names = inventor_names or []

    # ── Validate build level
    if custom_build_level not in VALID_BUILD_LEVELS:
        raise ValueError(
            f"custom_build_level must be one of {sorted(VALID_BUILD_LEVELS)}, "
            f"got {custom_build_level}"
        )

    # ── Block form submission if evidence required but absent
    if custom_build_level >= 50 and not evidence_links:
        raise ValueError(
            f"evidence_links[] is required when custom_build_level >= 50 "
            f"(current level: {custom_build_level}). Please provide at least one URL."
        )

    depth_info = _BUILD_DEPTH_MAP[custom_build_level]
    depth_label: str = depth_info["depth_label"]
    base_score: int = depth_info["base_score"]

    # ── Base score always computed immediately
    patent_verified = False
    patent_verification_step = None
    patent_display_label = None
    patent_number_verified = ""
    patent_bonus = 0
    patent_detail = {}

    # ── Patent verification (async, non-blocking in production)
    if patent_status in ("Pending", "Granted") and run_patent_verification:
        # Run synchronously here; callers wanting true async should call
        # _run_patent_verification in a thread pool and apply the bonus when done.
        verification = _run_patent_verification(
            patent_numbers=patent_numbers,
            inventor_names=inventor_names,
            company_name=company_name,
            assignee_company_name=assignee_company_name or "",
            patent_status_declared=patent_status,
        )
        if verification["step"] != "NotFound":
            patent_verified = True
            patent_bonus = verification["bonus"]
        patent_verification_step = verification["step"]
        patent_display_label = verification["display_label"]
        patent_number_verified = verification.get("patent_number_verified", "")
        patent_detail = verification.get("detail", {})

    elif patent_status in ("Pending", "Granted") and not run_patent_verification:
        # Test mode — skip API calls
        patent_verification_step = "Skipped_TestMode"
        patent_display_label = "Verification skipped (test mode)"

    # ── Final pillar score with patent bonus
    pillar_score = min(base_score + patent_bonus, 100)

    # ── Data provenance note
    if patent_status is None:
        pat_note = "Patent status: Not declared"
    elif patent_verified:
        label_str = patent_display_label or patent_status
        pat_note = f"Patent status: {label_str}"
    else:
        pat_note = f"Patent status: Founder-declared {patent_status}, unverified"

    data_provenance_note = (
        f"Build depth: founder-submitted, evidence required at level ≥50. "
        f"{pat_note}."
    )

    return {
        "custom_build_level": custom_build_level,
        "depth_label": depth_label,
        "base_score": base_score,
        "patent_status_declared": patent_status,
        "patent_verified": patent_verified,
        "patent_verification_step": patent_verification_step,
        "patent_display_label": patent_display_label,
        "patent_number_verified": patent_number_verified,
        "patent_bonus": patent_bonus,
        "tech_pillar_score": pillar_score,
        "evidence_links": evidence_links,
        "tech_description": tech_description,
        "data_provenance_note": data_provenance_note,
    }