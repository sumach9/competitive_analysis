import sys
import os
import unittest
from unittest.mock import patch

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.USP import compute_usp_score, _compute_confidence_flag, _lookup_pillar_score

class TestUSPRefinement(unittest.TestCase):

    def test_insufficient_data(self):
        # Rule: If unique_feature_claim_count = 0 or total_feature_count = 0 -> status = InsufficientData, score = NULL
        res = compute_usp_score([], [], [])
        self.assertEqual(res["compute_status"], "InsufficientData")
        self.assertIsNone(res["USP_Score"])
        self.assertEqual(res["Confidence_Flag"], "LOW")

    def test_all_urls_failed(self):
        # If a competitor URL is unreachable -> SKIP that competitor. No penalty. 
        # But if ALL fail, score should be neutral (0 or baseline). 
        # Spec says: "If a competitor URL is unreachable -> SKIP that competitor. No penalty. Lower Confidence Flag if too many skipped."
        # My implementation returns AllURLsFailed status.
        with patch('modules.USP._tavily_extract', return_value=None):
            res = compute_usp_score(["f1"], [{"feature_name": "u1"}], [{"name": "c1", "product_url": "http://x.com"}])
            self.assertEqual(res["compute_status"], "AllURLsFailed")
            self.assertEqual(res["USP_Score"], 0.0)
            self.assertEqual(res["pillar_score"], 20)

    def test_confidence_flag_logic(self):
        # HIGH: >= 3 scraped
        self.assertEqual(_compute_confidence_flag(3, 0, 3), "HIGH")
        self.assertEqual(_compute_confidence_flag(4, 0, 4), "HIGH")
        # MEDIUM: >= 3 submitted, 1 skipped
        self.assertEqual(_compute_confidence_flag(2, 1, 3), "MEDIUM")
        # LOW: < 3 successfully scraped (and not exactly 1 skipped from 3+)
        self.assertEqual(_compute_confidence_flag(1, 0, 1), "LOW")
        self.assertEqual(_compute_confidence_flag(1, 2, 3), "LOW")

    def test_pillar_score_mapping(self):
        # 80-100% HIGH -> 90
        score, status = _lookup_pillar_score(85, "HIGH")
        self.assertEqual(score, 90)
        
        # 60-79% HIGH -> 78
        score, status = _lookup_pillar_score(70, "HIGH")
        self.assertEqual(score, 78)
        
        # 60-79% MEDIUM -> 62
        score, status = _lookup_pillar_score(70, "MEDIUM")
        self.assertEqual(score, 62)
        
        # 30-59% HIGH -> 55
        score, status = _lookup_pillar_score(45, "HIGH")
        self.assertEqual(score, 55)
        
        # 1-29% Any -> 35
        score, status = _lookup_pillar_score(15, "LOW")
        self.assertEqual(score, 35)
        
        # 0% Any -> 20
        score, status = _lookup_pillar_score(0, "LOW")
        self.assertEqual(score, 20)

    def test_explicit_text_matching(self):
        # Test that fuzzy matching is strict
        from modules.USP import _fuzzy_match_verify
        
        pages = [{"name": "Comp1", "text": "We offer high-speed blockchain transactions."}]
        
        # Explicit match (feature name)
        disputed = _fuzzy_match_verify("blockchain transactions", "desc", pages)
        self.assertIn("Comp1", disputed)
        
        # Explicit match (significant tokens in description)
        # "Blockchain" and "transactions" are tokens (len >= 4)
        disputed = _fuzzy_match_verify("Other", "Blockchain transactions focus", pages)
        self.assertIn("Comp1", disputed)
        
        # No match (inference/low overlap)
        disputed = _fuzzy_match_verify("Other", "We do things efficiently and quickly", pages)
        self.assertEqual(disputed, [])

    def test_provenance_note(self):
        res = compute_usp_score(["f1"], [{"feature_name": "u1"}], [])
        self.assertEqual(res["data_provenance_note"], "Based on founder-submitted claims, auto-verified against competitor pages.")

if __name__ == '__main__':
    unittest.main()
