"""
tests/test_suitability.py
==========================
FFP Smart MVP — Automated unit tests for the four suitability pillar modules
and the composite scoring engine.

All external API calls are mocked with unittest.mock — no real network
traffic is required (no Tavily / Gemini / USPTO keys needed to run locally).

Run:
    cd c:\\Users\\polak\\research\\competitive
    python -m pytest tests/test_suitability.py -v
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from unittest.mock import patch, MagicMock


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_tavily_response(content: str):
    """Simulate a successful Tavily Extract response."""
    mock = MagicMock()
    mock.raise_for_status.return_value = None
    mock.json.return_value = {"results": [{"raw_content": content}]}
    return mock


def _make_tavily_empty():
    """Simulate a Tavily response with no content."""
    mock = MagicMock()
    mock.raise_for_status.return_value = None
    mock.json.return_value = {"results": []}
    return mock


def _make_gemini_disputed(*feature_names):
    """Simulate Gemini returning a list of disputed features."""
    import json
    mock = MagicMock()
    mock.raise_for_status.return_value = None
    mock.json.return_value = {
        "candidates": [{
            "content": {"parts": [{"text": json.dumps({"disputed_features": list(feature_names)})}]}
        }]
    }
    return mock


def _make_gemini_no_disputed():
    """Simulate Gemini returning an empty disputed list."""
    import json
    mock = MagicMock()
    mock.raise_for_status.return_value = None
    mock.json.return_value = {
        "candidates": [{
            "content": {"parts": [{"text": json.dumps({"disputed_features": []})}]}
        }]
    }
    return mock


_UNIQUE_FEATURES = [
    {"feature_name": "FeatureA", "description": "Does X"},
    {"feature_name": "FeatureB", "description": "Does Y"},
    {"feature_name": "FeatureC", "description": "Does Z"},
]

_COMPETITORS = [
    {"name": "Comp1", "product_url": "https://comp1.example.com", "domain": "comp1.example.com"},
    {"name": "Comp2", "product_url": "https://comp2.example.com", "domain": "comp2.example.com"},
    {"name": "Comp3", "product_url": "https://comp3.example.com", "domain": "comp3.example.com"},
]


# ─────────────────────────────────────────────────────────────────────────────
# USP Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestUSP:

    def test_usp_score_denominator(self):
        """USP_Score denominator = unique_feature_claim_count (not total_feature_count)."""
        with patch("modules.USP.requests.post") as mock_post:
            # Tavily: 3 successful scrapes
            mock_post.side_effect = [
                _make_tavily_response("Some competitor page text"),
                _make_gemini_no_disputed(),
                _make_tavily_response("Another page"),
                _make_gemini_no_disputed(),
                _make_tavily_response("Third page"),
                _make_gemini_no_disputed(),
            ]
            from modules import USP
            result = USP.compute_usp_score(
                feature_list=["FeatureA", "FeatureB", "FeatureC", "FeatureD", "FeatureE"],  # 5 total
                unique_feature_list=_UNIQUE_FEATURES,  # 3 unique
                competitors=_COMPETITORS,
                tavily_api_key="fake", gemini_api_key="fake",
            )
        # denominator must be 3 (len(unique_feature_list)), not 5
        assert result["unique_feature_claim_count"] == 3

    def test_usp_insufficient_data_empty_unique(self):
        """unique_feature_list=[] → InsufficientData, score=NULL."""
        from modules import USP
        result = USP.compute_usp_score(
            feature_list=["F1"],
            unique_feature_list=[],
            competitors=_COMPETITORS,
        )
        assert result["compute_status"] == "InsufficientData"
        assert result["USP_Score"] is None
        assert result["pillar_score"] is None

    def test_usp_insufficient_data_empty_features(self):
        """feature_list=[] → InsufficientData, score=NULL."""
        from modules import USP
        result = USP.compute_usp_score(
            feature_list=[],
            unique_feature_list=_UNIQUE_FEATURES,
            competitors=_COMPETITORS,
        )
        assert result["compute_status"] == "InsufficientData"
        assert result["USP_Score"] is None

    def test_usp_confidence_high(self):
        """3+ successfully scraped → Confidence_Flag = HIGH."""
        with patch("modules.USP.requests.post") as mock_post:
            mock_post.side_effect = [
                _make_tavily_response("page 1"), _make_gemini_no_disputed(),
                _make_tavily_response("page 2"), _make_gemini_no_disputed(),
                _make_tavily_response("page 3"), _make_gemini_no_disputed(),
            ]
            from modules import USP
            result = USP.compute_usp_score(
                feature_list=["F1"], unique_feature_list=_UNIQUE_FEATURES,
                competitors=_COMPETITORS, tavily_api_key="k", gemini_api_key="k",
            )
        assert result["Confidence_Flag"] == "HIGH"

    def test_usp_confidence_low(self):
        """Fewer than 3 scraped → Confidence_Flag = LOW."""
        with patch("modules.USP.requests.post") as mock_post:
            # All Tavily calls fail
            mock_post.side_effect = Exception("timeout")
            from modules import USP
            result = USP.compute_usp_score(
                feature_list=["F1"], unique_feature_list=_UNIQUE_FEATURES,
                competitors=_COMPETITORS, tavily_api_key="k", gemini_api_key="k",
            )
        assert result["Confidence_Flag"] == "LOW"

    def test_usp_score_all_verified(self):
        """No disputes → USP_Score = 100%, pillar_score = 90."""
        with patch("modules.USP.requests.post") as mock_post:
            mock_post.side_effect = [
                _make_tavily_response("p1"), _make_gemini_no_disputed(),
                _make_tavily_response("p2"), _make_gemini_no_disputed(),
                _make_tavily_response("p3"), _make_gemini_no_disputed(),
            ]
            from modules import USP
            result = USP.compute_usp_score(
                feature_list=["X"], unique_feature_list=_UNIQUE_FEATURES,
                competitors=_COMPETITORS, tavily_api_key="k", gemini_api_key="k",
            )
        assert result["USP_Score"] == 100.0
        assert result["pillar_score"] == 90

    def test_usp_score_all_disputed(self):
        """All 3 features disputed → USP_Score = 0%, pillar_score = 20."""
        with patch("modules.USP.requests.post") as mock_post:
            disputed_all = _make_gemini_disputed("FeatureA", "FeatureB", "FeatureC")
            mock_post.side_effect = [
                _make_tavily_response("p1"), _make_gemini_disputed("FeatureA", "FeatureB", "FeatureC"),
                _make_tavily_response("p2"), _make_gemini_disputed("FeatureA", "FeatureB", "FeatureC"),
                _make_tavily_response("p3"), _make_gemini_disputed("FeatureA", "FeatureB", "FeatureC"),
            ]
            from modules import USP
            result = USP.compute_usp_score(
                feature_list=["X"], unique_feature_list=_UNIQUE_FEATURES,
                competitors=_COMPETITORS, tavily_api_key="k", gemini_api_key="k",
            )
        assert result["USP_Score"] == 0.0
        assert result["pillar_score"] == 20


# ─────────────────────────────────────────────────────────────────────────────
# Tech Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestTech:

    def test_tech_evidence_blocks_at_50(self):
        """custom_build_level=50 + empty evidence_links → ValueError."""
        from modules import Tech
        with pytest.raises(ValueError, match="evidence_links"):
            Tech.calculate_technical_build_depth(
                custom_build_level=50,
                evidence_links=[],
                run_patent_verification=False,
            )

    def test_tech_evidence_blocks_at_75(self):
        """custom_build_level=75 + no evidence_links → ValueError."""
        from modules import Tech
        with pytest.raises(ValueError, match="evidence_links"):
            Tech.calculate_technical_build_depth(
                custom_build_level=75,
                run_patent_verification=False,
            )

    def test_tech_evidence_blocks_at_100(self):
        """custom_build_level=100 + empty links → ValueError."""
        from modules import Tech
        with pytest.raises(ValueError, match="evidence_links"):
            Tech.calculate_technical_build_depth(
                custom_build_level=100,
                evidence_links=[],
                run_patent_verification=False,
            )

    def test_tech_evidence_not_required_below_50(self):
        """custom_build_level=25 with no evidence_links → OK (no error)."""
        from modules import Tech
        result = Tech.calculate_technical_build_depth(
            custom_build_level=25,
            run_patent_verification=False,
        )
        assert result["tech_pillar_score"] == 50

    @pytest.mark.parametrize("level,expected_label,expected_base", [
        (0,   "Neutral",  45),
        (25,  "Neutral",  50),
        (50,  "Positive", 70),
        (75,  "Positive", 78),
        (100, "Positive", 85),
    ])
    def test_tech_base_scores_and_labels(self, level, expected_label, expected_base):
        """All 5 enum levels return correct depth_label and base_score."""
        from modules import Tech
        links = ["https://example.com/code"] if level >= 50 else []
        result = Tech.calculate_technical_build_depth(
            custom_build_level=level,
            evidence_links=links,
            run_patent_verification=False,
        )
        assert result["depth_label"] == expected_label
        assert result["base_score"] == expected_base
        assert result["tech_pillar_score"] == expected_base  # no patent in test mode

    def test_tech_invalid_build_level(self):
        """custom_build_level not in {0,25,50,75,100} → ValueError."""
        from modules import Tech
        with pytest.raises(ValueError):
            Tech.calculate_technical_build_depth(
                custom_build_level=60,
                run_patent_verification=False,
            )

    def test_tech_patent_bonus_granted(self):
        """USPTO-verified Granted → base_score + 10, capped at 100."""
        with patch("modules.Tech.requests.get") as mock_get:
            mock = MagicMock()
            mock.status_code = 200
            mock.json.return_value = {
                "applicationStatus": "Patented Case",
                "patentTitle": "MyPatent",
                "filingDate": "2023-01-15",
                "assigneeEntityName": "SecurePay AI",
            }
            mock_get.return_value = mock
            from modules import Tech
            result = Tech.calculate_technical_build_depth(
                custom_build_level=75,
                patent_status="Granted",
                patent_numbers=["18123456"],
                evidence_links=["https://example.com"],
                company_name="SecurePay AI",
                run_patent_verification=True,
            )
        assert result["patent_verified"] is True
        assert result["patent_bonus"] == 10
        assert result["tech_pillar_score"] == min(78 + 10, 100)

    def test_tech_patent_no_penalty_unverified(self):
        """No match across all 3 steps → base score unchanged, bonus=0."""
        with patch("modules.Tech.requests.get") as mock_get:
            mock_get.side_effect = Exception("not found")
            from modules import Tech
            result = Tech.calculate_technical_build_depth(
                custom_build_level=75,
                patent_status="Pending",
                patent_numbers=["99999999"],
                evidence_links=["https://example.com"],
                company_name="Acme",
                run_patent_verification=True,
            )
        assert result["patent_bonus"] == 0
        assert result["patent_verified"] is False
        assert result["tech_pillar_score"] == 78  # base score unchanged


# ─────────────────────────────────────────────────────────────────────────────
# Pricing Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPricing:

    def test_pricing_prerevenue_forced_50(self):
        """revenue=0 always returns pricing_pillar_score=50 regardless of clarity."""
        from modules import Pricing
        # Even with all fields → PreRevenue forced to 50
        result = Pricing.score_pricing_pipeline(
            pricing_model_type="Subscription",
            target_customer="Enterprises",
            pricing_metric="Per seat",
            revenue_curr_period=0.0,
        )
        assert result["pricing_clarity_label"] == "PreRevenue"
        assert result["pricing_pillar_score"] == 50

    def test_pricing_clarity_clear(self):
        """model_type + target_customer + pricing_metric → Clear, score=65."""
        from modules import Pricing
        result = Pricing.score_pricing_pipeline(
            pricing_model_type="Subscription",
            target_customer="SMBs",
            pricing_metric="Per seat per month",
            revenue_curr_period=5000.0,
        )
        assert result["pricing_clarity_label"] == "Clear"
        assert result["pricing_pillar_score"] == 65

    def test_pricing_clarity_somewhat_clear(self):
        """model_type + target_customer, no pricing_metric → SomewhatClear, score=50."""
        from modules import Pricing
        result = Pricing.score_pricing_pipeline(
            pricing_model_type="Enterprise",
            target_customer="Large banks",
            pricing_metric=None,
            revenue_curr_period=10000.0,
        )
        assert result["pricing_clarity_label"] == "SomewhatClear"
        assert result["pricing_pillar_score"] == 50

    def test_pricing_clarity_unclear(self):
        """No model_type → Unclear, score=35."""
        from modules import Pricing
        result = Pricing.score_pricing_pipeline(
            pricing_model_type=None,
            target_customer=None,
            revenue_curr_period=5000.0,
        )
        assert result["pricing_clarity_label"] == "Unclear"
        assert result["pricing_pillar_score"] == 35

    def test_pricing_paying_segment_stored_not_scored(self):
        """paying_segment is present in output but does not affect score."""
        from modules import Pricing
        result_with = Pricing.score_pricing_pipeline(
            pricing_model_type="Subscription",
            target_customer="SMBs",
            pricing_metric="Per seat",
            revenue_curr_period=5000.0,
            paying_segment="Enterprise tier only",
        )
        result_without = Pricing.score_pricing_pipeline(
            pricing_model_type="Subscription",
            target_customer="SMBs",
            pricing_metric="Per seat",
            revenue_curr_period=5000.0,
            paying_segment=None,
        )
        assert result_with["pricing_pillar_score"] == result_without["pricing_pillar_score"]
        assert result_with["paying_segment"] == "Enterprise tier only"


# ─────────────────────────────────────────────────────────────────────────────
# GTM Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestGTM:

    def test_gtm_unable_to_compute(self):
        """No data at all → UnableToCompute, gtm_pillar_score=None."""
        from modules import GTM_PRESEED
        result = GTM_PRESEED.compute_preseed_gtm(
            market_type="B2B SaaS",
        )
        assert result["status_label"] == "UnableToCompute"
        assert result["gtm_pillar_score"] is None

    def test_gtm_partial_data_multiplier(self):
        """Single channel (web only) → PartialData, score × 0.80."""
        from modules import GTM_PRESEED
        result = GTM_PRESEED.compute_preseed_gtm(
            market_type="B2B SaaS",
            web_visitors_prev=1000,
            web_visitors_curr=1050,
            social_followers_prev=None,
            social_followers_curr=None,
        )
        assert result["status_label"] == "PartialData"
        # Pillar score should be a multiple of 0.80 of a full score
        raw_score_options = {90, 70, 50, 30, 15}
        expected_options = {round(s * 0.80) for s in raw_score_options}
        assert result["gtm_pillar_score"] in expected_options

    def test_gtm_invalid_baseline_web_zero(self):
        """web_prev=0 → InvalidBaselinePrevZero_web flag."""
        from modules import GTM_PRESEED
        result = GTM_PRESEED.compute_preseed_gtm(
            market_type="B2B SaaS",
            web_visitors_prev=0,
            web_visitors_curr=500,
            social_followers_prev=800,
            social_followers_curr=900,
        )
        assert "InvalidBaselinePrevZero_web" in result["flags"]

    def test_gtm_invalid_baseline_social_zero(self):
        """social_prev=0 → InvalidBaselinePrevZero_social flag."""
        from modules import GTM_PRESEED
        result = GTM_PRESEED.compute_preseed_gtm(
            market_type="B2B SaaS",
            web_visitors_prev=1000,
            web_visitors_curr=1100,
            social_followers_prev=0,
            social_followers_curr=200,
        )
        assert "InvalidBaselinePrevZero_social" in result["flags"]

    def test_gtm_needs_human_review_outlier(self):
        """abs(rate) > 300 → NeedsHumanReview flag."""
        from modules import GTM_PRESEED
        result = GTM_PRESEED.compute_preseed_gtm(
            market_type="B2B SaaS",
            web_visitors_prev=100,
            web_visitors_curr=50000,  # 49,900% growth
            social_followers_prev=500,
            social_followers_curr=510,
        )
        assert result["status_label"] == "NeedsHumanReview"
        assert "OUTLIER_DETECTED" in result["flags"]

    def test_gtm_both_channels_normal(self):
        """Both channels present → normal score, no PartialData flag."""
        from modules import GTM_PRESEED
        result = GTM_PRESEED.compute_preseed_gtm(
            market_type="B2B SaaS",
            web_visitors_prev=1800,
            web_visitors_curr=1944,  # 8% growth
            social_followers_prev=1000,
            social_followers_curr=1030,  # 3% growth
        )
        assert result["status_label"] in ("OK", "NeedsHumanReview")  # not PartialData
        assert result["gtm_pillar_score"] is not None


# ─────────────────────────────────────────────────────────────────────────────
# Composite Scoring Engine Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestCompositeEngine:

    def test_composite_weights_sum_to_one(self):
        """USP=0.35, GTM=0.15, PRICING=0.20, TECH=0.30 must sum to 1.0."""
        from config.benchmark_table import PILLAR_WEIGHTS
        assert abs(sum(PILLAR_WEIGHTS.values()) - 1.0) < 1e-9
        assert PILLAR_WEIGHTS["USP"] == pytest.approx(0.35)
        assert PILLAR_WEIGHTS["GTM"] == pytest.approx(0.15)
        assert PILLAR_WEIGHTS["PRICING"] == pytest.approx(0.20)
        assert PILLAR_WEIGHTS["TECH"] == pytest.approx(0.30)

    def test_composite_weight_redistribution(self):
        """One UnableToCompute pillar → remaining weights rescale to sum 1.0."""
        from modules.Scoring_Engine import _redistribute_weights
        from config.benchmark_table import PILLAR_WEIGHTS
        # Remove GTM (weight 0.15)
        new_weights = _redistribute_weights(PILLAR_WEIGHTS, {"GTM"})
        assert abs(sum(new_weights.values()) - 1.0) < 1e-9
        assert "GTM" not in new_weights

    def test_composite_weight_redistribution_two_pillars(self):
        """Two UnableToCompute → remaining two rescale to 1.0."""
        from modules.Scoring_Engine import _redistribute_weights
        from config.benchmark_table import PILLAR_WEIGHTS
        new_weights = _redistribute_weights(PILLAR_WEIGHTS, {"GTM", "USP"})
        assert abs(sum(new_weights.values()) - 1.0) < 1e-9
        assert "GTM" not in new_weights
        assert "USP" not in new_weights

    @pytest.mark.parametrize("score,expected_label", [
        (76,  "Strong Signal"),
        (75,  "Strong Signal"),
        (60,  "Moderate Signal"),
        (55,  "Moderate Signal"),
        (40,  "Weak Signal"),
        (35,  "Weak Signal"),
        (20,  "Insufficient Signal"),
        (0,   "Insufficient Signal"),
    ])
    def test_composite_suitability_thresholds(self, score, expected_label):
        """Score thresholds map correctly to suitability labels."""
        from config.benchmark_table import get_suitability_label
        label, _ = get_suitability_label(score)
        assert label == expected_label

    def test_composite_all_pillars_computed(self):
        """All 4 pillars computed → weight_redistribution_applied = False."""
        from modules.Scoring_Engine import _redistribute_weights
        from config.benchmark_table import PILLAR_WEIGHTS
        weights = _redistribute_weights(PILLAR_WEIGHTS, set())
        assert len(weights) == 4
        assert abs(sum(weights.values()) - 1.0) < 1e-9
