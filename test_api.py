import requests
import json
import time
import subprocess
import os

def test_api():
    # Start the API in the background
    print("Starting API server (waiting for model loading)...")
    with open("api_logs.txt", "w") as log_file:
        api_process = subprocess.Popen(["python", "api.py"], stdout=log_file, stderr=log_file)
    
    time.sleep(20) # Increase wait time for model loading
    
    # Load sample data
    with open("sample_startup.json", "r") as f:
        payload = json.load(f)
    
    try:
        print("Sending request to /score endpoint...")
        response = requests.post("http://127.0.0.1:8000/score", json=payload)
        
        if response.status_code == 200:
            result = response.json()
            print("\n--- API Response (Unified Scoring) ---")
            print(json.dumps(result, indent=2))
            
            # Verify Pillar Order
            pillars = list(result["pillars"].keys())
            expected_order = ["usp", "gtm", "pricing_business_model", "proprietary_tech"]
            print(f"\nPillar Order Check: {pillars}")
            if pillars == expected_order:
                print("✅ Pillar order is correct (USP, GTM, Pricing, Tech)")
            else:
                print("❌ Pillar order mismatch!")
                
            print(f"\nFinal Suitability Score: {result['final_suitability_score']}")
        else:
            print(f"❌ API Error: {response.status_code}")
            print(response.text)
            
    finally:
        print("\nShutting down API server...")
        api_process.terminate()

if __name__ == "__main__":
    test_api()
