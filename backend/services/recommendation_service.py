
import csv
import logging
from pathlib import Path

import joblib

from database import get_db

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

ADMIN_RESOURCE_COLUMNS = (
    "id,title,description,url,category,subject,tags,is_active"
)

SIMILARITY_THRESHOLD = 0.10


class RecommendationService:

    def __init__(self):
        if not DATASET_PATH.is_file():
            raise FileNotFoundError(
                f"Recommendation dataset not found: {DATASET_PATH}"
            )

        self.courses = []
        self.admin_resources = []
        self.df = None
        self.tfidf = None
        self.tfidf_matrix = None
        self._resource_signature = None

        self._load_coursera_dataset()
        self._refresh_index(self.admin_resources)

    def _load_coursera_dataset(self):
        """Load the existing Coursera dataset."""

        if SKLEARN_AVAILABLE:
            self.df = pd.read_csv(DATASET_PATH)

            missing = set(REQUIRED_COLUMNS) - set(self.df.columns)

            if missing:
                raise ValueError(
                    f"Coursera.csv is missing columns: {sorted(missing)}"
                )

            for _, row in self.df.iterrows():
                self.courses.append({
                    "id": None,
                    "course_name": str(row["Course Name"] or ""),
                    "description": str(
                        row["Course Description"]
                        if pd.notna(row["Course Description"])
                        else ""
                    ),
                    "skills": str(
                        row["Skills"]
                        if pd.notna(row["Skills"])
                        else ""
                    ),
                    "university": (
                        None if pd.isna(row["University"])
                        else str(row["University"])
                    ),
                    "difficulty_level": (
                        None if pd.isna(row["Difficulty Level"])
                        else str(row["Difficulty Level"])
                    ),
                    "course_rating": self._parse_rating(
                        row["Course Rating"]
                    ),
                    "course_url": (
                        None if pd.isna(row["Course URL"])
                        else str(row["Course URL"])
                    ),
                    "category": None,
                    "subject": None,
                    "source": "coursera",
                })

        else:
            with open(
                DATASET_PATH,
                mode="r",
                encoding="utf-8",
            ) as file:
                reader = csv.DictReader(file)

                for row in reader:
                    self.courses.append({
                        "id": None,
                        "course_name": row.get("Course Name", ""),
                        "description": row.get(
                            "Course Description", ""
                        ),
                        "skills": row.get("Skills", ""),
                        "university": row.get("University"),
                        "difficulty_level": row.get(
                            "Difficulty Level"
                        ),
                        "course_rating": self._parse_rating(
                            row.get("Course Rating")
                        ),
                        "course_url": row.get("Course URL"),
                        "category": None,
                        "subject": None,
                        "source": "coursera",
                    })

        logger.info(
            "Loaded %d Coursera resources",
            len(self.courses),
        )

    @staticmethod
    def _parse_rating(value):
        try:
            if value is None or str(value).strip() == "":
                return None

            return float(value)

        except (ValueError, TypeError):
            return None

    def _fetch_admin_resources(self):
        """Fetch active Admin resources from Supabase."""

        try:
            db = get_db()

            if db is None:
                logger.warning(
                    "Supabase is unavailable. Using Coursera resources only."
                )
                return []

            response = (
                db.table("learning_resources")
                .select(ADMIN_RESOURCE_COLUMNS)
                .eq("is_active", True)
                .execute()
            )

            resources = []

            for item in response.data or []:
                resources.append({
                    "id": str(item.get("id", "")),
                    "course_name": str(item.get("title") or ""),
                    "description": str(
                        item.get("description") or ""
                    ),
                    "skills": " ".join(
                        item.get("tags") or []
                    ),
                    "university": None,
                    "difficulty_level": None,
                    "course_rating": None,
                    "course_url": item.get("url"),
                    "category": item.get("category"),
                    "subject": item.get("subject"),
                    "source": "admin",
                })

            logger.info(
                "Fetched %d active Admin resources",
                len(resources),
            )

            return resources

        except Exception:
            logger.warning(
                "Unable to fetch Admin resources. "
                "Continuing with Coursera dataset.",
                exc_info=True,
            )
            return []

    @staticmethod
    def _build_features(resource):
        return " ".join([
            str(resource.get("course_name") or ""),
            str(resource.get("description") or ""),
            str(resource.get("skills") or ""),
            str(resource.get("category") or ""),
            str(resource.get("subject") or ""),
        ]).strip()

    def _refresh_index(self, admin_resources):
        """Rebuild the unified TF-IDF index when catalog changes."""

        resources = self.courses + admin_resources

        signature = tuple(
            (
                item.get("id"),
                item.get("course_name"),
                item.get("description"),
                item.get("skills"),
                item.get("course_url"),
                item.get("category"),
                item.get("subject"),
                item.get("source"),
            )
            for item in resources
        )

        if signature == self._resource_signature:
            return

        self.admin_resources = admin_resources

        if not SKLEARN_AVAILABLE:
            self._resource_signature = signature
            return

        self.df = pd.DataFrame(resources)

        self.df["combined_features"] = self.df.apply(
            self._build_features,
            axis=1,
        )

        self.tfidf = TfidfVectorizer(
            stop_words="english",
            max_features=5000,
        )

        try:
            self.tfidf_matrix = self.tfidf.fit_transform(
                self.df["combined_features"]
            )

        except ValueError:
            logger.warning(
                "No valid vocabulary found in resource catalog."
            )
            self.tfidf_matrix = None

        self._resource_signature = signature

        logger.info(
            "Unified TF-IDF index refreshed: %d resources",
            len(resources),
        )

    def recommend_courses(
        self,
        query: str,
        top_n: int = 5,
    ) -> list:
        """Recommend relevant Coursera and active Admin resources."""

        if not isinstance(query, str) or not query.strip():
            return []

        if (
            not isinstance(top_n, int)
            or isinstance(top_n, bool)
            or top_n < 1
        ):
            return []

        # Fetch current Admin resources before searching.
        admin_resources = self._fetch_admin_resources()

        # Rebuild index only when resource data changes.
        self._refresh_index(admin_resources)

        if not SKLEARN_AVAILABLE:
            return self._keyword_recommendations(
                query,
                top_n,
            )

        if self.tfidf_matrix is None or self.df.empty:
            return []

        try:
            query_vector = self.tfidf.transform([
                query.strip()
            ])

            scores = cosine_similarity(
                query_vector,
                self.tfidf_matrix,
            ).flatten()

            if (
                len(scores) == 0
                or scores.max() < SIMILARITY_THRESHOLD
            ):
                return []

            ranked_indices = scores.argsort()[::-1]
            recommendations = []

            for index in ranked_indices:
                score = float(scores[index])

                if score < SIMILARITY_THRESHOLD:
                    break

                resource = self.df.iloc[index]

                recommendations.append({
                    "course_name": resource["course_name"],
                    "university": resource["university"],
                    "difficulty_level": resource[
                        "difficulty_level"
                    ],
                    "course_rating": resource["course_rating"],
                    "course_url": resource["course_url"],
                    "similarity_score": round(score, 4),
                    "source": resource["source"],
                    "resource_id": resource["id"],
                    "category": resource["category"],
                    "subject": resource["subject"],
                })

                if len(recommendations) >= top_n:
                    break

            return recommendations

        except Exception:
            logger.exception("Recommendation engine failed")
            raise

    def _keyword_recommendations(
        self,
        query: str,
        top_n: int,
    ) -> list:
        """Fallback keyword-based search without scikit-learn."""

        query_words = [
            word
            for word in query.lower().split()
            if len(word) > 2
        ]

        matches = []

        resources = self.courses + self.admin_resources

        for resource in resources:
            text = self._build_features(resource).lower()

            matched_count = sum(
                1 for word in query_words
                if word in text
            )

            if matched_count == 0:
                continue

            score = min(
                1.0,
                0.25 + matched_count * 0.12,
            )

            matches.append({
                "course_name": resource["course_name"],
                "university": resource["university"],
                "difficulty_level": resource[
                    "difficulty_level"
                ],
                "course_rating": resource["course_rating"],
                "course_url": resource["course_url"],
                "similarity_score": round(score, 4),
                "source": resource["source"],
                "resource_id": resource["id"],
                "category": resource["category"],
                "subject": resource["subject"],
            })

        matches.sort(
            key=lambda item: item["similarity_score"],
            reverse=True,
        )

        return matches[:top_n]


# Reuse one initialized service throughout this process.
recommendation_service = RecommendationService()
