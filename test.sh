#!/bin/bash
# ============================================================
# FFP Smart MVP — Realistic Test Run: NovaTech AI (Pre-Seed)
# ============================================================
# Startup:   NovaTech AI — AI-powered contract intelligence
# Stage:     Pre-Seed
# Sector:    B2B SaaS / LegalTech
#
# Usage:
#   1. Start the API:  python api.py
#   2. Run this script: bash run_test_novatech_ai.sh
#   3. Output saved to: novatech_ai_score_result.json
# ============================================================

set -e

API_URL="http://127.0.0.1:8000"
PAYLOAD_FILE="test_payload_novatech_ai.json"
OUTPUT_FILE="novatech_ai_score_result.json"

echo ""
echo "============================================================"
echo "  FFP Smart MVP — Scoring Test: NovaTech AI"
echo "============================================================"

# 1. Health check
echo ""
echo "[1/3] Health check..."
HEALTH=$(curl -s "$API_URL/health")
echo "  → $HEALTH"

# 2. Score the startup
echo ""
echo "[2/3] Sending scoring request..."
echo "  → POST $API_URL/score"
echo "  → Payload: $PAYLOAD_FILE"
echo ""

RESULT=$(curl -s -X POST "$API_URL/score" \
  -H "Content-Type: application/json" \
  -d @"$PAYLOAD_FILE")

# 3. Save and pretty-print
echo "$RESULT" | python3 -m json.tool > "$OUTPUT_FILE"
echo "[3/3] Report saved to: $OUTPUT_FILE"
echo ""

# 4. Quick summary
echo "============================================================"
echo "  SCORE SUMMARY"
echo "============================================================"
echo "$RESULT" | python3 -c "
import json, sys
r = json.load(sys.stdin)
print(f'  Composite Score : {r.get(\"composite_score\", \"N/A\")}')
print(f'  Suitability     : {r.get(\"suitability_label\", \"N/A\")} ({r.get(\"suitability_colour\", \"\")})')
print(f'  Pillars computed: {r.get(\"pillars_computed\", [])}')
print(f'  Pillars skipped : {r.get(\"pillars_unable_to_compute\", [])}')
print()
pillars = r.get('pillar_results', {})
for k, v in pillars.items():
    score = v.get('pillar_score') or v.get('gtm_pillar_score') or v.get('pricing_pillar_score') or v.get('tech_pillar_score') or v.get('USP_Score')
    print(f'  {k:10s}: {score}')
"
echo "============================================================"
echo ""