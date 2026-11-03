
from pathlib import Path
import csv

try:
    import pandas as pd
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    pd = None
    TfidfVectorizer = None
    cosine_similarity = None
    SKLEARN_AVAILABLE = False


# Coursera dataset path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = PROJECT_ROOT / "recommendation" / "data" / "Coursera.csv"


def load_courses():
    """Load the existing Coursera dataset."""
    if not SKLEARN_AVAILABLE:
        return None
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


if SKLEARN_AVAILABLE:
    df = load_courses()
    tfidf = TfidfVectorizer(
        stop_words="english",
        max_features=5000
    )
    tfidf_matrix = tfidf.fit_transform(df["combined_features"])
else:
    df = None
    tfidf = None
    tfidf_matrix = None





def recommend_courses(query, top_n=5):
    """Recommend courses based on keyword similarity."""

    if not isinstance(query, str) or not query.strip():
        return []

    if not isinstance(top_n, int) or not 1 <= top_n <= 5:
        return []

    if not SKLEARN_AVAILABLE or tfidf is None:
        return []


    analyzer = tfidf.build_analyzer()
    query_terms = set(analyzer(query.strip()))

    if not query_terms:
        return []

    query_vector = tfidf.transform([query.strip()])

    similarity_scores = cosine_similarity(
        query_vector,
        tfidf_matrix
    ).flatten()

    course_terms = [
        set(analyzer(text))
        for text in df["combined_features"]
    ]

    overlap_scores = [
        len(query_terms & terms) / len(query_terms)
        for terms in course_terms
    ]

    ranked_indices = similarity_scores.argsort()[::-1]
    recommendations = []

    for index in ranked_indices:
        score = float(similarity_scores[index])

        if overlap_scores[index] == 0:
            continue

        if score < 0.10:
            break

        course = df.iloc[index]

        recommendations.append({
            "course_name": str(course["Course Name"]),
            "university": (
                None if pd.isna(course["University"])
                else str(course["University"])
            ),
            "difficulty_level": (
                None if pd.isna(course["Difficulty Level"])
                else str(course["Difficulty Level"])
            ),
            "course_rating": (
                None if pd.isna(course["Course Rating"])
                else float(course["Course Rating"])
            ),
            "course_url": (
                None if pd.isna(course["Course URL"])
                else str(course["Course URL"])
            ),
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
