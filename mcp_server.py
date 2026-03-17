from fastmcp import FastMCP
import json
import FINAL_SCORE

# Initialize the MCP Server
mcp = FastMCP("FFPSmart MVP Scoring MCP")

@mcp.tool()
def evaluate_startup(json_payload: str) -> str:
    """
    Evaluates a pre-seed startup using the FFP Smart MVP Suitability Scoring Pipeline.
    Expects a JSON string representing the full startup payload. 
    Required fields in JSON: 'company_name'. 
    Example fields: 'company_stage', 'market_type', 'feature_list', 'competitors'.
    Returns the final structured score report.
    """
    try:
        data = json.loads(json_payload)
        report = FINAL_SCORE.get_final_scores(data)
        return json.dumps(report, indent=2)
    except Exception as e:
        return f"Error evaluating startup via MCP: {str(e)}"

if __name__ == "__main__":
    # Start the FastMCP server with stdio transport for local use by LLM apps like Claude Desktop.
    mcp.run(transport='stdio')
