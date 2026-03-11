import os
import requests
import json
from dotenv import load_dotenv

# Load API keys from .env
load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
TAVILY_EXTRACT_URL = "https://api.tavily.com/extract"

def debug_scrape(url: str):
    """
    Diagnostic script to verify Tavily Extract output for a specific URL.
    """
    if not TAVILY_API_KEY:
        print("Error: TAVILY_API_KEY not found in .env file.")
        return

    print(f"--- Attempting to scrape: {url} ---")
    
    try:
        resp = requests.post(
            TAVILY_EXTRACT_URL,
            headers={"Authorization": f"Bearer {TAVILY_API_KEY}"},
            json={"urls": [url]},
            timeout=20,
        )
        
        print(f"HTTP Status: {resp.status_code}")
        
        if resp.status_code != 200:
            print("Response text:", resp.text)
            return

        data = resp.json()
        results = data.get("results", [])
        failed = data.get("failed_results", [])

        if failed:
            print(f"FAILED to scrape. Reason: {failed[0].get('error', 'Unknown Error')}")
            return

        if not results:
            print("SUCCESS but returned no content.")
            return

        raw_text = results[0].get("raw_content", "")
        print(f"SUCCESS! Retrieved {len(raw_text)} characters.")
        print("-" * 40)
        print("PREVIEW (First 500 characters):")
        print(raw_text[:500] + "...")
        print("-" * 40)
        
        # Save to a temporary file for full inspection
        with open("last_debug_scrape.txt", "w", encoding="utf-8") as f:
            f.write(raw_text)
        print("Full content saved to: last_debug_scrape.txt")

    except Exception as e:
        print(f"An exception occurred: {str(e)}")

if __name__ == "__main__":
    import sys
    # Example usage: python debug_tavily.py https://example.com
    target_url = sys.argv[1] if len(sys.argv) > 1 else "https://ironcladapp.com/product/"
    debug_scrape(target_url)
