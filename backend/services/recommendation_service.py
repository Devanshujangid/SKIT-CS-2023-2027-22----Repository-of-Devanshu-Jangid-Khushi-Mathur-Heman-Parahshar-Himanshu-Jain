import logging
from pathlib import Path
import csv

import joblib

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

logger = logging.getLogger(__name__)


# Locate the CSV and cache directory from the repository root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = PROJECT_ROOT / "backend" / ".cache"
CACHE_PATH = CACHE_DIR / "coursera_tfidf.joblib"
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
        if not DATASET_PATH.is_file():
            raise FileNotFoundError(
                f"Recommendation dataset not found: {DATASET_PATH}"
            )

        stat = DATASET_PATH.stat()
        fingerprint = {
            "size": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
        }

        if not SKLEARN_AVAILABLE:
            self.courses = []
            try:
                with open(DATASET_PATH, mode="r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        self.courses.append(row)
                logger.info("Loaded Coursera dataset with standard parser (%d courses)", len(self.courses))
            except Exception:
                logger.warning("Failed to parse Coursera.csv in fallback mode", exc_info=True)
            return

        if CACHE_PATH.is_file():
            try:
                cached = joblib.load(CACHE_PATH)

                if cached.get("fingerprint") == fingerprint:
                    self.df = cached["df"]
                    self.tfidf = cached["tfidf"]
                    self.tfidf_matrix = cached["tfidf_matrix"]
                    logger.info("Loaded recommendation artifacts from cache")
                    return

            except Exception:
                logger.warning(
                    "Recommendation cache is invalid; rebuilding it",
                    exc_info=True,
                )

        self.df = pd.read_csv(DATASET_PATH)

        missing = set(REQUIRED_COLUMNS) - set(self.df.columns)
        if missing:
            raise ValueError(
                f"Coursera.csv is missing columns: {sorted(missing)}"
            )

        self.df["combined_features"] = (
            self.df["Course Name"].fillna("").astype(str) + " "
            + self.df["Course Description"].fillna("").astype(str) + " "
            + self.df["Skills"].fillna("").astype(str)
        )

        self.tfidf = TfidfVectorizer(
            stop_words="english",
            max_features=5000,
        )

        self.tfidf_matrix = self.tfidf.fit_transform(
            self.df["combined_features"]
        )

        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            joblib.dump(
                {
                    "fingerprint": fingerprint,
                    "df": self.df,
                    "tfidf": self.tfidf,
                    "tfidf_matrix": self.tfidf_matrix,
                },
                CACHE_PATH,
            )
            logger.info("Built and saved recommendation cache")
        except Exception:
            logger.warning("Failed to save recommendation cache to disk", exc_info=True)

    def recommend_courses(self, query: str, top_n: int = 5) -> list:
        """Return relevant courses or an empty list when no match exists."""
        if not isinstance(query, str) or not query.strip():
            return []

        if not isinstance(top_n, int) or top_n < 1:
            return []

        if not SKLEARN_AVAILABLE:
            query_words = [w for w in query.lower().split() if len(w) > 2]
            matches = []
            for course in getattr(self, "courses", []):
                text = (f"{course.get('Course Name', '')} {course.get('Course Description', '')} {course.get('Skills', '')}").lower()
                matched_count = sum(1 for w in query_words if w in text)
                if matched_count > 0:
                    score = min(1.0, 0.25 + (matched_count * 0.12))
                    try:
                        rating = float(course.get("Course Rating", 0))
                    except (ValueError, TypeError):
                        rating = None
                    matches.append({
                        "course_name": str(course.get("Course Name", "")),
                        "university": str(course.get("University", "")),
                        "difficulty_level": str(course.get("Difficulty Level", "")),
                        "course_rating": rating,
                        "course_url": str(course.get("Course URL", "")),
                        "similarity_score": round(score, 4),
                    })
            matches.sort(key=lambda x: x["similarity_score"], reverse=True)
            return matches[:top_n]


        try:
            query_vector = self.tfidf.transform([query.strip()])

            scores = cosine_similarity(
                query_vector,
                self.tfidf_matrix,
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
            logger.exception("Recommendation engine failed")
            raise


# Reuse one initialized service throughout this process.
recommendation_service = RecommendationService()
