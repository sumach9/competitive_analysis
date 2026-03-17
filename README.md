# Founder Fit Platform (FFP) — Smart MVP

An automated, heavily-deterministic startup suitability evaluation pipeline built for Venture Capital and Pre-Seed market analysis. 

The application evaluates startup viability across 4 core competitive pillars using a combination of verified data ingestion (Google Analytics, USPTO), web scraping (Tavily), deterministic logic, and AI-driven executive synthesis (AWS Bedrock).

## 🏛️ Scoring Architecture (4 Pillars)

### 1. Differentiating Factor / USP (35%)
Scores technical moats and unique capabilities by scraping target competitors via the **Tavily Extract API** and algorithmically verifying claims locally utilizing `scikit-learn`'s TF-IDF vectorization and cosine similarity boundaries (`similarity <= 0.65`).

### 2. Go-to-Market Strategy (15%)
Signals early market traction by mapping founder market descriptions using `rapidfuzz` string matching (threshold `70`) against defined VC benchmark tables. Applies absolute Audience Growth Rate (AGR) thresholds directly into mathematical scoring buckets.

### 3. Pricing & Business Model (20%)
Applies declarative rule-based logic to evaluate pricing model clarity (Clear / SomewhatClear / Unclear) accounting for "Enterprise + Contact Sales" exceptions. Calculates an ARPU (Average Revenue Per User) Month-over-Month growth bonus (+5 pts). Evaluates market benchmarks passively.

### 4. Proprietary Technology (30%)
Validates deep IP defensively using a 3-step, pure-deterministic public fallback chain bypassing AI hallucination completely:
1. **USPTO Open Data Portal** (Application verification)
2. **PatentsView API** (Inventor/Assignee lookup)
3. **Patent Assignment Search** (Corporate assignments)

## 🧠 AI Executive Summary
The platform connects with **AWS Bedrock** (specifically invoking `anthropic.claude-3-haiku-20240307-v1:0`) at the end of the scoring cycle. It reads the unadulterated metric outputs across all four pillars and generates a professional, VC-ready executive summary paragraph alongside a bulleted pillar breakdown explaining the core drivers behind the assigned score.

## 🔒 Advanced Integrations
- **FastMCP Protocol**: Exposed locally as a Model Context Protocol tool endpoint (`mcp_server.py`), allowing external Assistants (like Claude Desktop) to invoke the startup pipeline securely format structures.
- **FastAI Tabular Mapping**: Baseline model initialization for predictive outcomes utilizing `fastai` for future mass-data training runs based on these engineered pillars.

---

## 🚀 Getting Started

### Prerequisites
- Python 3.12+
- Valid AWS Credentials (configured via AWS CLI or ENV variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`).
- API Keys: `TAVILY_API_KEY` (required for Pillar 1).

### Setup
```bash
# Enter the project directory
cd competitive

# Activate the local virtual environment
.\.venv\Scripts\activate

# Ensure baseline packages are installed
pip install -r requirements.txt
```

### Running the Pipeline
To execute a full end-to-end evaluation, run the sample pipeline located in the `examples` folder:
```bash
python examples/run_end_to_end.py
```
This generates a master JSON report containing the resulting composite score, individual pillar mathematical breakdowns, evidence logic, validation limits, and the AWS Bedrock synthesized memo.

## 🧪 Testing
The project includes a robust, deterministic testing architecture specifically designed for standard CI pipelines with 100% API edge-case mocking.

```bash
# Run the entire automated test suite
pytest tests/ -v
```
Integration capabilities ensure logic involving `rapidfuzz` classifications, rule boundaries, and `scikit-learn` formulas successfully execute completely hermetically.
