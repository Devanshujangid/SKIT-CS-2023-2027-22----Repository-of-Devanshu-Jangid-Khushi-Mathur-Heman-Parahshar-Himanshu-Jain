
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# Locate the CSV from the repository root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = PROJECT_ROOT / "recommendation" / "data" / "Coursera.csv"

REQUIRED_COLUMNS = [
    "Course Name",
    "Course Description",
    "Skills",
    "University",
    "Difficulty Level",
    "Course Rating",
    "Course URL",
]


class RecommendationService:
    def __init__(self):
        # Load the dataset once when the service initializes.
        if not DATASET_PATH.is_file():
            raise FileNotFoundError(
                f"Recommendation dataset not found: {DATASET_PATH}"
            )

        self.df = pd.read_csv(DATASET_PATH)

        missing = set(REQUIRED_COLUMNS) - set(self.df.columns)
        if missing:
            raise ValueError(
                f"Coursera.csv is missing columns: {sorted(missing)}"
            )

        # Combine course information for better text matching.
        self.df["combined_features"] = (
            self.df["Course Name"].fillna("").astype(str) + " " +
            self.df["Course Description"].fillna("").astype(str) + " " +
            self.df["Skills"].fillna("").astype(str)
        )

        # Build the TF-IDF matrix once.
        self.tfidf = TfidfVectorizer(
            stop_words="english",
            max_features=5000
        )
        self.tfidf_matrix = self.tfidf.fit_transform(
            self.df["combined_features"]
        )

    def recommend_courses(self, query: str, top_n: int = 5) -> list:
        query_vector = self.tfidf.transform([query])

        scores = cosine_similarity(
            query_vector,
            self.tfidf_matrix
        ).flatten()

        # Return the highest-scoring courses first.
        top_indices = scores.argsort()[-top_n:][::-1]

        recommendations = []

        for index in top_indices:
            course = self.df.iloc[index]

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
                "similarity_score": float(scores[index]),
            })

        return recommendations


# Reuse one initialized service throughout this process.
recommendation_service = RecommendationService()
