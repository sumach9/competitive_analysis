from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

feature_name = "FeatureA"
feature_description = "Does X"
query_text = f"{feature_name} {feature_description}".lower().strip()

page_text = "This competitor provides FeatureA. It specifically Does X just like you!".lower()

vectorizer = TfidfVectorizer(stop_words="english")
vectorizer.fit([query_text, page_text])
tfidf_matrix = vectorizer.transform([query_text, page_text])
sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
print(f"Similarity: {sim}")
