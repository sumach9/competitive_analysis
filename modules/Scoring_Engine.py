from modules import Tech
from modules import USP
from modules import GTM_StageBased
from modules import Pricing_Seed
from modules import Pricing_Preseed
from typing import Dict, List

def run_scoring_pipeline(company_data: Dict) -> Dict:
    """
    Orchestrate the full scoring pipeline in the specified order:
    1. USP, 2. GTM, 3. Pricing, 4. Tech
    """
    stage = company_data.get("company_stage", "Pre-Seed")
    
    # 1. USP Scoring
    startup_features = company_data.get("startup_features", [])
    competitors = company_data.get("competitors", [])
    usp_results = USP.compute_usp_score(startup_features, competitors)
    
    # 2. GTM Scoring
    gtm_results = GTM_StageBased.compute_gtm_stage(stage, company_data)
    
    # 3. Pricing & Business Model Scoring
    if stage.lower() == "seed":
        pricing_results = Pricing_Seed.collect_pricing_seed(company_data)
    else:
        pricing_results = Pricing_Preseed.collect_pricing_preseed(company_data)
        
    # 4. Tech Scoring
    tech_results = Tech.evaluate_proprietary_tech(company_data)
    
    # Aggregate Final Results in the exact requested order
    from collections import OrderedDict
    results = OrderedDict([
        ("company_name", company_data.get("company_name", "Unknown Startup")),
        ("stage", stage),
        ("pillars", OrderedDict([
            ("usp", usp_results),
            ("gtm", gtm_results),
            ("pricing_business_model", pricing_results),
            ("proprietary_tech", tech_results)
        ]))
    ])
    
    return dict(results) # Convert back to dict for generic use, order is preserved in Python 3.7+

if __name__ == "__main__":
    # Example test run with Appendix data
    sample_data = {
        "company_name": "Test Startup",
        "company_stage": "Seed",
        "product_type": "B2B SaaS",
        "market_type": "B2B SaaS",
        "geographic_focus": ["North America"],
        
        # Tech
        "custom_build_level": "Yes – largely custom-built",
        "patent_status": "pending",
        
        # USP
        "startup_features": ["AI-powered fraud detection", "Automated compliance"],
        "competitors": [
            {"name": "Comp A", "feature_list": ["Manual fraud detection"]}
        ],
        
        # GTM (Seed EEV example)
        "waitlist_prev": 600,
        "waitlist_curr": 800,
        "beta_prev": 100,
        "beta_curr": 150,
        "unique_visitors_curr": 5000,
        
        # Pricing
        "total_revenue": 50000.0,
        "active_users": 1000,
        "pricing_model_type": "Subscription",
        "paying_segment": "10 enterprise customers"
    }
    
    results = run_scoring_pipeline(sample_data)
    import json
    print(json.dumps(results, indent=2))
