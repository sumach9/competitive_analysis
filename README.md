<<<<<<< HEAD
# Startup Scoring Engine

A multi-pillar scoring system designed for **Pre-Seed** and **Seed** stage startups. This engine extracts and processes metrics from pitch decks and founder forms to provide an aggregate suitability score and detailed pillar reports.

## 🚀 Key Features

- **Four-Pillar Evaluation**:
  1. **USP (Uniqueness)**: Analyzes startup features against competitors using SentenceTransformer embeddings (`all-MiniLM-L6-v2`).
  2. **GTM (Go-To-Market)**: Calculates **AGR** (Audience Growth Rate) for Pre-Seed and **EEV** (Early Engagement Velocity) for Seed.
  3. **Pricing & Business Model**: Calculates **ARPU** and applies guardrails for growth trends and engagement offsets.
  4. **Proprietary Tech**: Evaluates technical build depth and patent status suitability signals.
- **REST API**: Production-ready FastAPI implementation for unified scoring.
- **CLI Mode**: Direct script execution for batch processing.
- **Intelligent Guardrails**: Automatic score adjustments for revenue-precedent startups or those with high engagement despite low initial ARPU.

## 🛠️ Project Structure

- `FINAL_SCORE.py`: Main entry point for CLI scoring.
- `api.py`: FastAPI application exposing the `/score` endpoint.
- `modules/`: Core scoring logic.
  - `Scoring_Engine.py`: Master orchestrator (USP → GTM → Pricing → Tech).
  - `USP.py`, `GTM_StageBased.py`, `Pricing_Seed.py`, `Tech.py`: Pillar modules.
- `utils/`: Utility scripts.
  - `data_parser.py`: Pitch deck text parser.
- `data/`: Sample data and pitch deck examples.
  - `sample_startup.json`, `pitch_deck_example.txt`.
- `tests/`: Verification scripts.

## 🔧 Installation

```bash
pip install fastapi uvicorn pydantic numpy scikit-learn sentence-transformers requests
```

> **Note**: The first run may take up to 60 seconds as the USP module downloads the embedding model.

## 📖 Usage

### Running via API (Recommended)

1. Start the server:
   ```bash
   python api.py
   ```
2. Send a POST request to `http://localhost:8000/score` with your startup data:
   ```json
   {
     "company_name": "Example Startup",
     "company_stage": "Seed",
     "product_type": "B2B SaaS",
### Option 2: API
1. Start the server: `python api.py`
2. Send a request:
   ```bash
   curl -X POST http://127.0.0.1:8000/score -H "Content-Type: application/json" -d @data/sample_startup.json
   ```

### Running via CLI

1. Update `sample_startup.json` with your data.
2. Run the final score script:
   ```bash
   python FINAL_SCORE.py
   ```

## 🐳 Deployment (Docker)

To deploy the scoring engine using Docker for consistent cross-environment behavior:

1. **Build the image**:
   ```bash
   docker build -t scoring-engine .
   ```
2. **Run the container**:
   ```bash
   docker run -p 8000:8000 scoring-engine
   ```

Alternatively, use **Docker Compose**:
```bash
docker-compose up --build
```

The Docker image includes the pre-downloaded embedding model to ensure the first request is fast.

## 📊 Scoring Logic (Appendix)

- **EEV (Early Engagement Velocity)**: `((Δ Waitlist + Δ Beta Users) / Website Visitors) * 100`.
- **AGR (Audience Growth Rate)**: Monthly average of Web and Social growth.
- **ARPU Guardrails**:
  - `Neutral` if ARPU is $0 but model is defined.
  - `Positive` if ARPU is increasing month-over-month.
  - `Positive` if low ARPU is offset by strong engagement (>15% growth).

## 📄 Documentation

For a detailed breakdown of changes and verification results, see [walkthrough.md](walkthrough.md).
=======
https://docs.google.com/document/d/13xW7fnygW9QwYg89WbnNWSqSg6Mwrb4oCbEcxgv8Sug/edit?tab=t.q33557f2wrq2 
>>>>>>> 383adb830ab201b4715afa56edb6f9999da0072c
