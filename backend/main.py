
import logging
import os
from pathlib import Path
from typing import List, Optional, Union

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.is_file():
    load_dotenv(dotenv_path=_env_path)
load_dotenv()

from auth import verify_clerk_token
from database import get_db
from routes.ai import router as ai_router
from routes.plans import router as plans_router
from routes import export
from routes.tasks import router as tasks_router
from routes.recommendations import router as recommendations_router
from routes.resources import router as resources_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Smart Learning Planner API")


# ============================================================
# CORS CONFIGURATION
# ============================================================

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# REGISTER ROUTERS
# ============================================================

app.include_router(ai_router)
app.include_router(plans_router)
app.include_router(export.router)
app.include_router(tasks_router)
app.include_router(recommendations_router)
app.include_router(resources_router)


# ============================================================
# PROFILE REQUEST MODEL
# ============================================================

class ProfileCreateRequest(BaseModel):
    email: Optional[EmailStr] = None
    semester: int
    study_hours_per_day: float
    goals: Union[str, List[str]]
    subjects: List[str] = Field(default_factory=list)


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "service": "Smart Learning Planner Backend"
    }


# ============================================================
# PROTECTED ROUTE
# ============================================================

@app.get("/api/v1/protected-route")
def protected_route(
    user: dict = Depends(verify_clerk_token)
):
    return {
        "message": "Access granted",
        "clerk_id": user["sub"]
    }


# ============================================================
# CREATE OR UPDATE STUDENT PROFILE
# ============================================================

@app.post(
    "/api/v1/profile",
    status_code=status.HTTP_201_CREATED
)
async def create_or_update_profile(
    payload: ProfileCreateRequest,
    user_data: dict = Depends(verify_clerk_token)
):
    clerk_id = user_data.get("sub")

    if not clerk_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user ID is missing"
        )

    email = payload.email or user_data.get("email")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required to create a profile"
        )

    goals_list = (
        payload.goals
        if isinstance(payload.goals, list)
        else [payload.goals]
    )
    subjects_list = payload.subjects

    try:
        db = get_db()

        # Create or retrieve the internal user record.
        user_res = (
            db.table("users")
            .upsert(
                {
                    "clerk_id": clerk_id,
                    "email": str(email),
                    "role": "student"
                },
                on_conflict="clerk_id"
            )
            .execute()
        )

        if not user_res.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create or retrieve user"
            )

        internal_user_id = user_res.data[0]["id"]

        # Create or update the student's profile.
        profile_res = (
            db.table("student_profiles")
            .upsert(
                {
                    "user_id": internal_user_id,
                    "semester": payload.semester,
                    "study_hours_per_day": payload.study_hours_per_day,
                    "goals": goals_list,
                    "subjects": subjects_list,
                    "onboarding_completed": True
                },
                on_conflict="user_id"
            )
            .execute()
        )

        if not profile_res.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save student profile"
            )

        return {
            "success": True,
            "message": "Profile saved successfully",
            "data": profile_res.data[0]
        }

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("Failed to save student profile")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save student profile",
        ) from exc


# ============================================================
# APPLICATION ENTRY POINT
# ============================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
