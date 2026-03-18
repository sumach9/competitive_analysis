import json
import logging
import os
import requests

def generate_local_llm_summary(composite_score: float, suitability_label: str, pillar_results: dict) -> str:
    """
    Generate an executive summary of the startup's performance using Groq API.
    Expects GROQ_API_KEY to be configured in the environment or uses the default provided.
    """
    
    # Construct a prompt based on the score and pillars
    usp_score = pillar_results.get("USP", {}).get("pillar_score", "N/A")
    gtm_score = pillar_results.get("GTM", {}).get("gtm_pillar_score", "N/A")
    pricing_score = pillar_results.get("PRICING", {}).get("pricing_pillar_score", "N/A")
    tech_score = pillar_results.get("TECH", {}).get("tech_pillar_score", "N/A")
    
    prompt = f"""
You are an expert Venture Capital Analyst. Please write a comprehensive executive summary for a startup investment memo based on the following automated scoring results. 
Provide a brief overall synthesis, and then a 1-2 sentence summary for EACH pillar explaining its score for understanding.

- Final Suitability Score: {composite_score}/100 ({suitability_label})

PILLAR 1: USP & Differentiation
Score: {usp_score}/100
Context Data: {json.dumps(pillar_results.get("USP", {}))}

PILLAR 2: Go-to-Market (GTM)
Score: {gtm_score}/100
Context Data: {json.dumps(pillar_results.get("GTM", {}))}

PILLAR 3: Pricing & Business Model
Score: {pricing_score}/100
Context Data: {json.dumps(pillar_results.get("PRICING", {}))}

PILLAR 4: Technical Build Depth
Score: {tech_score}/100
Context Data: {json.dumps(pillar_results.get("TECH", {}))}

Please structure your response with an 'Overall Summary' paragraph, followed by a 'Pillar Breakdown' section containing four bullet points (one for each pillar) explaining the core drivers of that pillar's score. Keep it highly professional and data-driven.
"""

    try:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is missing")
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        request_body = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1000,
            "temperature": 0.2
        }
        
        response = requests.post(url, headers=headers, json=request_body)
        response.raise_for_status()
        
        response_data = response.json()
        return response_data['choices'][0]['message']['content'].strip()
        
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_msg = e.response.json().get('error', {}).get('message', e.response.text)
            except ValueError:
                error_msg = e.response.text
        logging.error(f"Groq API Error: {error_msg}")
        return f"Groq Summary generation failed: {error_msg}"
    except Exception as e:
        logging.error(f"Error generating LLM summary via Groq: {e}")
        return f"Groq Summary generation failed: {str(e)}"
