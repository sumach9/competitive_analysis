import re
import numpy as np
from typing import List, Dict
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from difflib import SequenceMatcher

# Load embedding model once
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# -----------------------------
# Utility Functions
# -----------------------------

def normalize_feature(text: str) -> str:
    """
    Clean and normalize feature text by removing marketing adjectives and punctuation
    """
    text = text.lower()
    
    marketing_words = [
        "ai-powered", "advanced", "best", "next-gen",
        "cutting-edge", "real-time", "powerful",
        "innovative", "seamless", "intelligent", "smart",
        "revolutionary", "state-of-the-art", "world-class",
        "high-performance", "robust", "scalable", "dynamic",
        "flexible", "fast", "easy-to-use", "game-changing",
        "predictive", "automated", "effortless", "proactive",
        "integrated", "modular", "cloud-based", "ultra-fast",
        "hyper-personalized", "multi-platform", "enterprise-grade",
        "next-level", "leading", "optimized"
    ]
    
    for word in marketing_words:
        text = text.replace(word, "")
    
    text = re.sub(r'[^a-z0-9\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def token_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()

# -----------------------------
# USP Engine
# -----------------------------

def compute_usp_score(startup_features: List[str],
                      competitors: List[Dict]) -> Dict:
    
    # Step 1: Normalize & deduplicate
    startup_features = list(set(normalize_feature(f) for f in startup_features if f.strip()))
    total_features = len(startup_features)
    if total_features == 0:
        return {
            "total_feature_count": 0,
            "validated_unique_feature_count": 0,
            "overlap_feature_count": 0,
            "uniqueness_ratio": 0,
            "confidence_score": 0,
            "final_usp_score": 0,
            "borderline_features": [],
            "needs_human_review": True
        }
    
    if len(startup_features) > 25:  # Cap features to prevent inflation
        startup_features = startup_features[:25]
        total_features = len(startup_features)
    
    # Step 2: Collect competitor features
    competitor_features = []
    for comp in competitors:
        competitor_features.extend(normalize_feature(f) for f in comp.get("feature_list", []))
    competitor_features = list(set(competitor_features))
    
    # Step 2A: Token matching
    overlap_features = set()
    remaining_features = []
    for sf in startup_features:
        if any(sf == cf or token_similarity(sf, cf) > 0.70 for cf in competitor_features):
            overlap_features.add(sf)
        else:
            remaining_features.append(sf)
    
    # Step 2B: Embedding similarity
    borderline_features = []
    unique_features = []
    if competitor_features and remaining_features:
        comp_embeddings = embedding_model.encode(competitor_features)
        for sf in remaining_features:
            sf_embedding = embedding_model.encode([sf])
            similarities = cosine_similarity(sf_embedding, comp_embeddings)[0]
            max_sim = np.max(similarities)
            if max_sim >= 0.80:
                overlap_features.add(sf)
            elif 0.75 <= max_sim < 0.80:
                borderline_features.append(sf)
                unique_features.append(sf)
            else:
                unique_features.append(sf)
    else:
        unique_features = remaining_features
    
    validated_unique_count = len(unique_features)
    overlap_count = total_features - validated_unique_count
    uniqueness_ratio = validated_unique_count / total_features  # 0–1
    
    # -----------------------------
    # Dynamic confidence scoring
    # -----------------------------
    # Factors: competitor count, feature coverage, validated uniqueness
    
    competitor_factor = min(len(competitors) / 5, 1.0)   # >=5 competitors → 1
    coverage_factor = min(len(competitor_features) / (total_features * 2), 1.0)  # how well competitor features cover domain
    uniqueness_factor = uniqueness_ratio  # higher unique features → higher confidence
    
    # Combine dynamically
    confidence_score = (0.4 * competitor_factor + 0.4 * coverage_factor + 0.2 * uniqueness_factor)
    
    # Final USP Score = uniqueness_ratio * confidence_score
    final_usp_score = uniqueness_ratio * confidence_score * 100  # percentage
    
    # -----------------------------
    # Human review conditions
    # -----------------------------
    needs_review = len(borderline_features) >= 2 or len(competitors) < 2 or total_features > 25
    
    return {
        "total_feature_count": total_features,
        "validated_unique_feature_count": validated_unique_count,
        "overlap_feature_count": overlap_count,
        "uniqueness_ratio": round(uniqueness_ratio*100, 2),
        "confidence_score": round(confidence_score, 2),
        "final_usp_score": round(final_usp_score, 2),
        "borderline_features": borderline_features,
        "needs_human_review": needs_review
    }
    # -----------------------------
# Example Usage
# -----------------------------
if __name__ == "__main__":
    startup_features = [
        "AI-powered fraud detection dashboard",
        "Automated compliance reporting",
        "Multi-bank integration"
    ]

    competitors = [
        {"name": "Comp A", "feature_list": ["Fraud detection", "Compliance reporting", "Payment gateway integration"]},
        {"name": "Comp B", "feature_list": ["Real-time fraud monitoring", "Automated reports"]}
    ]

    result = compute_usp_score(startup_features, competitors)
    print(result)
