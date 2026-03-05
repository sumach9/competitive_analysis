"""
FFP Smart MVP — FastAPI Scoring Endpoint v2
============================================
POST /score  — runs the full 4-pillar suitability evaluation
GET  /health — liveness check
GET  /docs   — Swagger UI

API keys are loaded from .env on startup.
They are NEVER passed from the client.
"""

import os

# Load .env if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # keys must be set in system environment directly

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
import FINAL_SCORE

app = FastAPI(
    title="FFP Smart MVP — Suitability Scoring API",
    description="Four-pillar suitability evaluation for Pre-Seed startups.",
    version="2.0.0",
)


# ─────────────────────────────────────────────────────────────────────────────
# Request Models
# ─────────────────────────────────────────────────────────────────────────────

class UniqueFeature(BaseModel):
    feature_name: str
    description: str
    not_in_competitors: List[str] = []
    own_product_url: Optional[str] = None


class Competitor(BaseModel):
    name: str
    product_url: str
    domain: Optional[str] = None


class InventorName(BaseModel):
    first: str
    last: str


class StartupData(BaseModel):
    # Identity
    company_name: str
    company_stage: str = "Pre-Seed"
    startup_domain: Optional[str] = None

    # Market
    market_type: Optional[str] = None
    market_description: Optional[str] = None
    geographic_focus: Optional[str] = None

    # Pillar 1 — USP
    feature_list: List[str] = []
    unique_feature_list: List[UniqueFeature] = []
    competitors: List[Competitor] = []

    # Pillar 2 — GTM
    ga4_property_id: Optional[str] = None
    ga4_oauth_token: Optional[str] = None
    web_visitors_prev: Optional[int] = None
    web_visitors_curr: Optional[int] = None
    social_followers_prev: Optional[int] = None
    social_followers_curr: Optional[int] = None

    # Pillar 3 — Pricing
    pricing_model_type: Optional[str] = None
    target_customer: Optional[str] = None
    pricing_metric: Optional[str] = None
    price_range: Optional[str] = None
    who_pays_vs_who_uses: Optional[str] = None
    paying_segment: Optional[str] = None
    pricing_evidence_links: Optional[List[str]] = None
    analyst_notes: Optional[str] = None
    total_revenue: float = 0.0

    # Pillar 4 — Tech
    custom_build_level: int = Field(default=0, description="0 / 25 / 50 / 75 / 100")
    patent_status: Optional[str] = None
    patent_numbers: Optional[List[str]] = None
    inventor_names: Optional[List[InventorName]] = None
    assignee_company_name: Optional[str] = None
    tech_evidence_links: Optional[List[str]] = None
    tech_description: Optional[str] = None
    run_patent_verification: bool = True


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/")
def root():
    return {
        "message": "FFP Smart MVP Suitability Scoring API v2.0",
        "endpoints": {
            "POST /score": "Run the full 4-pillar suitability evaluation",
            "GET /health": "Liveness check",
            "GET /docs": "Swagger UI — interactive schema + test form",
        },
    }


@app.post("/score")
def score_startup(data: StartupData):
    """
    Run the full suitability scoring pipeline.
    Returns composite_score, suitability_label, and all four pillar results.
    """
    try:
        payload = data.model_dump()
        payload["unique_feature_list"] = [f.model_dump() for f in data.unique_feature_list]
        payload["competitors"] = [c.model_dump() for c in data.competitors]
        if data.inventor_names:
            payload["inventor_names"] = [i.model_dump() for i in data.inventor_names]

        report = FINAL_SCORE.get_final_scores(payload)
        return report

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
