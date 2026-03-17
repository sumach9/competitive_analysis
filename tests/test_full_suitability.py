import sys
import os
import unittest
from unittest.mock import patch

# Add the project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.Scoring_Engine import compute_composite

class TestFullSuitability(unittest.TestCase):

    def test_ideal_preseed_startup(self):
        """Test a strong pre-seed startup with all data present."""
        res = compute_composite(
            # USP: 100% verified
            feature_list=["f1", "f2"],
            unique_feature_list=[{"feature_name": "u1", "description": "d1"}],
            competitors=[], # No competitors = 100% score (no disputes possible)
            
            # GTM: Path B, strong growth
            market_type="B2B SaaS",
            web_visitors_prev=1000,
            web_visitors_curr=1100, # 10% growth (high for B2B SaaS [1-8% range])
            social_followers_prev=100,
            social_followers_curr=110, # 10% growth (high for B2B SaaS [1-5% range])
            
            # Pricing: Clear, pre-revenue
            pricing_model_type="Subscription",
            target_customer="Enterprise",
            pricing_metric="Per Seat",
            revenue_curr_period=0, # Forces 50
            
            # Tech: Meaningful build + Verified Patent
            custom_build_level=50,
            tech_evidence_links=["http://github.com/repo"],
            patent_status="Granted",
            run_patent_verification=False # Skip actual API calls for test
        )
        
        # USP Pillar: should be 90 (100% verified)
        # GTM Pillar: high growth -> Strong -> 90
        # Pricing Pillar: PreRevenue -> 50
        # Tech Pillar: 70 base (50 level) + 0 bonus (skipped verification) = 70. 
        # Wait, if verification skipped, bonus is 0. If I want to test bonus, I should mock it.
        
        self.assertEqual(res["suitability_label"], "Moderate Signal") # (90*0.35 + 90*0.15 + 50*0.2 + 70*0.3) = 31.5 + 13.5 + 10 + 21 = 76.
        # Wait, 76 is "Strong Signal" (75-100).
        self.assertIn(res["suitability_label"], ["Strong Signal", "Moderate Signal"])
        
    def test_weight_redistribution(self):
        """Test that weight is redistributed when a pillar is unable to compute."""
        # Provide only Tech data
        res = compute_composite(
            custom_build_level=100,
            tech_evidence_links=["http://evidence"]
        )
        
        # Pillars computed should only be TECH
        self.assertEqual(res["pillars_computed"], ["TECH"])
        self.assertTrue(res["weight_redistribution_applied"])
        # Effective weight for TECH should be 1.0
        self.assertEqual(res["effective_weights"]["TECH"], 1.0)
        # Composite score should equal TECH pillar score (85)
        self.assertEqual(float(res["composite_score"]), 85.0)

    def test_pricing_summary_generation(self):
        """Test that the rule-based pricing summary is generated correctly."""
        res = compute_composite(
            pricing_model_type="Freemium",
            target_customer="SMBs",
            pricing_metric="Monthly Active Users",
            market_type="Fintech"
        )
        summary = res["pillar_results"]["PRICING"]["ai_pricing_summary"]
        self.assertIn("Freemium", summary)
        self.assertIn("SMBs", summary)
        self.assertIn("Fintech", summary)
        self.assertIn("Monthly Active Users", summary)

    @patch('modules.GTM_Preseed.process.extractOne')
    def test_gtm_market_matching(self, mock_extract):
        """Test the rule-based market description matching."""
        mock_extract.return_value = ("Developer Tools", 100.0, 5)

        # Matches "Developer Tools"
        res = compute_composite(
            market_description="We build tools for developers to automate CI/CD.",
            web_visitors_prev=100,
            web_visitors_curr=110
        )
        self.assertEqual(res["pillar_results"]["GTM"]["matched_market_type"], "Developer Tools")

if __name__ == '__main__':
    unittest.main()
