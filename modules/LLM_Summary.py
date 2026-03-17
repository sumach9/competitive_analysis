import json
import logging
import boto3
from botocore.exceptions import ClientError 

def generate_local_llm_summary(composite_score: float, suitability_label: str, pillar_results: dict) -> str:
    """
    Generate an executive summary of the startup's performance using an AWS Bedrock Foundation Model.
    Expects AWS credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION) to be configured in the environment.
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
        # Initialize the Bedrock client. Region logic defaults to us-east-1 if not set in AWS setup.
        client = boto3.client('bedrock-runtime', region_name='us-east-1')
        model_id = 'anthropic.claude-3-haiku-20240307-v1:0'
        
        request_body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "temperature": 0.2,
            "messages": [{"role": "user", "content": prompt}]
        })
        
        response = client.invoke_model(
            modelId=model_id,
            body=request_body,
            accept='application/json',
            contentType='application/json'
        )
        
        response_body = json.loads(response.get('body').read())
        return response_body['content'][0]['text'].strip()
        
    except ClientError as e:
        error_msg = e.response.get('Error', {}).get('Message', str(e))
        logging.error(f"AWS Bedrock ClientError: {error_msg}")
        return f"AWS Bedrock Summary generation failed: {error_msg}"
    except Exception as e:
        logging.error(f"Error generating LLM summary via Bedrock: {e}")
        return f"AWS Bedrock Summary generation failed: {str(e)}"
