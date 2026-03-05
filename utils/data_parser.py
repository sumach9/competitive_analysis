import os
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class Competitor(BaseModel):
    name: str
    feature_list: List[str]

class ExtractionSchema(BaseModel):
    company_name: str = Field(description="The name of the company")
    company_stage: str = Field(description="The funding stage of the company (e.g., Pre-Seed, Seed, Series A)", default="Seed")
    product_type: str = Field(description="The type of product (e.g., B2B SaaS, Marketplace)", default="B2B SaaS")
    market_type: str = Field(description="The market category", default="B2B SaaS")
    geographic_focus: List[str] = Field(description="Geographic focus areas", default=["Global"])
    startup_features: List[str] = Field(description="Key features of the startup's product")
    competitors: List[Competitor] = Field(description="List of competitors and their features")
    custom_build_level: str = Field(description="Technical build depth (e.g., 'Yes - largely custom-built', 'Yes - partially custom-built')", default="Yes - partially custom-built")
    patent_status: Optional[str] = Field(description="Patent status (e.g., 'pending', 'approved')", default="")
    waitlist_prev: Optional[int] = Field(description="Previous waitlist count", default=0)
    waitlist_curr: Optional[int] = Field(description="Current waitlist count", default=0)
    beta_prev: Optional[int] = Field(description="Previous beta user count", default=0)
    beta_curr: Optional[int] = Field(description="Current beta user count", default=0)
    unique_visitors_curr: Optional[int] = Field(description="Current unique website visitors", default=0)
    total_revenue: Optional[float] = Field(description="Total revenue", default=0.0)
    prev_revenue: Optional[float] = Field(description="Previous period revenue", default=None)
    active_users: Optional[int] = Field(description="Number of active users", default=0)
    web_growth_rate: Optional[float] = Field(description="Web growth rate (percentage)", default=None)
    social_growth_rate: Optional[float] = Field(description="Social growth rate (percentage)", default=None)
    time_window: Optional[str] = Field(description="Time window for growth metrics (e.g., 30 days, last month)", default="30 days")
    percentiles: Optional[str] = Field(description="Optional percentile data for benchmarking", default=None)
    pricing_model_type: Optional[str] = Field(description="Pricing model (e.g., Subscription, Usage-based)", default="Subscription")
    target_customer: Optional[str] = Field(description="Target customer segment", default=None)
    pricing_metric: Optional[str] = Field(description="What the pricing is based on (e.g., per seat, usage-based, etc.)", default=None)
    price_range: Optional[str] = Field(description="The price range or starting price (e.g., $10/month, Contact Sales)", default=None)
    paying_segment: Optional[str] = Field(description="The specific segment that is paying", default=None)

def parse_pitch_deck_text(text: str) -> Dict:
    """
    Use Landing AI ADE to extract structured data from pitch deck text.
    """
    api_key = os.environ.get("LANDING_AI_API_KEY")
    if not api_key:
        raise ValueError("LANDING_AI_API_KEY environment variable is not set.")

    from landingai_ade import LandingAIADE
    client = LandingAIADE(apikey=api_key)
    
    # ADE extraction
    import json
    # Use model_json_schema() for Pydantic V2 or schema() for V1 (dep   recated)
    try:
        schema_dict = ExtractionSchema.model_json_schema()
        schema_json = json.dumps(schema_dict)
    except AttributeError:
        schema_json = ExtractionSchema.schema_json()

    result = client.extract(
        markdown=text,
        schema=schema_json
    )
    
    # Extract the data from the extraction field
    data = result.to_dict().get("extraction", {})
    
    # Ensure mandatory fields have defaults if extraction failed to find them
    if not data.get("company_stage"):
        data["company_stage"] = "Seed"
    if not data.get("company_name"):
        data["company_name"] = "Unknown Startup"
        
    return data

def parse_pitch_deck_document(file_path: str) -> Dict:
    """
    Use Landing AI ADE to parse a document file (PDF, etc.) directly.
    """
    api_key = os.environ.get("LANDING_AI_API_KEY")
    if not api_key:
        raise ValueError("LANDING_AI_API_KEY environment variable is not set.")

    from landingai_ade import LandingAIADE
    client = LandingAIADE(apikey=api_key)

    import json
    try:
        schema_dict = ExtractionSchema.model_json_schema()
        schema_json = json.dumps(schema_dict)
    except AttributeError:
        schema_json = ExtractionSchema.schema_json()

    # ADE extraction from file
    result = client.extract(
        markdown=file_path,
        schema=schema_json
    )
    
    data = result.to_dict().get("extraction", {})
    return data

if __name__ == "__main__":
    # Example usage (requires API key set in env)
    example_text = """
    Pitch Deck: AI Health Tracker
    Stage: Seed
    Features:
    - Real-time heart rate monitoring
    - Predictive diet suggestions
    - Peer-to-peer fitness challenges
    
    Competitors:
    - Competitor: Fitbit (Features: Step tracking, Sleep analysis)
    - Competitor: Apple Health (Features: Health dashboard, Integration with iPhone)
    
    Metrics:
    Waitlist: Grew from 500 to 1,200
    Revenue: $10,000 from $5,000 prev
    Active Users: 500
    """
    try:
        data = parse_pitch_deck_text(example_text)
        import json
        print(json.dumps(data, indent=2))
    except Exception as e:
        print(f"Error: {e}")
