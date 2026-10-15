
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
        """Return relevant courses or an empty list when no match exists."""

        if not isinstance(query, str) or not query.strip():
            return []

        if not isinstance(top_n, int) or top_n < 1:
            return []

        try:
            query_vector = self.tfidf.transform([query.strip()])

            scores = cosine_similarity(
                query_vector,
                self.tfidf_matrix
            ).flatten()

            # No relevant course found.
            if len(scores) == 0 or scores.max() < 0.10:
                return []

            ranked_indices = scores.argsort()[::-1]
            recommendations = []

            for index in ranked_indices:
                score = float(scores[index])

                # Skip courses with very low similarity.
                if score < 0.10:
                    break

                course = self.df.iloc[index]
                rating_value = course["Course Rating"]

                # Handle ratings such as "Not Calibrated".
                try:
                    rating = (
                        None if pd.isna(rating_value)
                        else float(rating_value)
                    )
                except (TypeError, ValueError):
                    rating = None

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
                    "course_rating": rating,
                    "course_url": (
                        None if pd.isna(course["Course URL"])
                        else str(course["Course URL"])
                    ),
                    "similarity_score": score,
                })

                if len(recommendations) >= top_n:
                    break

            return recommendations

        except Exception:
            import logging

            logging.getLogger(__name__).exception(
                "Recommendation engine failed"
            )
            raise



# Reuse one initialized service throughout this process.
recommendation_service = RecommendationService()
