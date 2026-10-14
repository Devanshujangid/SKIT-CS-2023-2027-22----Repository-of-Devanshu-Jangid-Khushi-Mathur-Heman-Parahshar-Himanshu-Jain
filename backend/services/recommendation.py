
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# Coursera dataset path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = PROJECT_ROOT / "recommendation" / "data" / "Coursera.csv"


def load_courses():
    """Load the existing Coursera dataset."""
    df = pd.read_csv(DATASET_PATH)

    # Recreate combined_features if it is not already present.
    if "combined_features" not in df.columns:
        df["combined_features"] = (
            df["Course Name"].fillna("").astype(str)
            + " "
            + df["Course Description"].fillna("").astype(str)
            + " "
            + df["Skills"].fillna("").astype(str)
        )

    df["combined_features"] = df["combined_features"].fillna("")
    return df


# Load and vectorize courses once when this module is imported.
df = load_courses()

tfidf = TfidfVectorizer(
    stop_words="english",
    max_features=5000
)

tfidf_matrix = tfidf.fit_transform(df["combined_features"])



def recommend_courses(query, top_n=5):
    """Recommend courses based on keyword similarity."""

    if not isinstance(query, str) or not query.strip():
        return []

    if top_n < 1:
        return []

    # Convert the user's query into a TF-IDF vector.
    query_vector = tfidf.transform([query.strip()])

    # Compare the query against all course vectors.
    similarity_scores = cosine_similarity(
        query_vector,
        tfidf_matrix
    ).flatten()

    # Sort courses from most relevant to least relevant.
    ranked_indices = similarity_scores.argsort()[::-1]

    recommendations = []

    for index in ranked_indices:
        score = float(similarity_scores[index])

        # Skip courses that have no textual match.
        # Skip courses with very low textual similarity.
        if score < 0.10:
          continue

        course = df.iloc[index]

        recommendations.append({
            "course_name": course["Course Name"],
            "university": course["University"],
            "difficulty": course["Difficulty Level"],
            "rating": course["Course Rating"],
            "url": course["Course URL"],
            "description": course["Course Description"],
            "skills": course["Skills"],
            "similarity_score": round(score, 4),
        })

        if len(recommendations) >= top_n:
            break

    return recommendations



def warmup_recommendation_cache():
    """Verify that the course dataset and TF-IDF matrix are loaded."""
    return {
        "course_count": len(df),
        "tfidf_shape": tfidf_matrix.shape,
    }
