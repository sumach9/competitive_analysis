print("API Script Starting...")
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
from modules import Scoring_Engine
import FINAL_SCORE

app = FastAPI(title="Startup Scoring API")

class Competitor(BaseModel):
    name: str
    feature_list: List[str]

class StartupData(BaseModel):
    company_name: str
    company_stage: str
    product_type: str
    market_type: str
    geographic_focus: List[str]
    
    # Tech
    custom_build_level: str
    patent_status: Optional[str] = ""
    
    # USP
    startup_features: List[str]
    competitors: List[Competitor]
    
    # GTM
    waitlist_prev: Optional[int] = 0
    waitlist_curr: Optional[int] = 0
    beta_prev: Optional[int] = 0
    beta_curr: Optional[int] = 0
    unique_visitors_curr: Optional[int] = 0
    web_growth_rate: Optional[float] = None
    social_growth_rate: Optional[float] = None
    
    # Pricing
    total_revenue: Optional[float] = 0.0
    active_users: Optional[int] = 0
    prev_revenue: Optional[float] = None
    pricing_model_type: Optional[str] = "Subscription"
    paying_segment: Optional[str] = None

@app.get("/")
def read_root():
    return {"message": "Startup Scoring API is active. Use /score to evaluate a startup."}

@app.post("/score")
def get_score(data: StartupData):
    try:
        # Convert Pydantic model to Dict
        input_dict = data.dict()
        
        # Run the full scoring engine
        report = FINAL_SCORE.get_final_scores(input_dict)
        
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
