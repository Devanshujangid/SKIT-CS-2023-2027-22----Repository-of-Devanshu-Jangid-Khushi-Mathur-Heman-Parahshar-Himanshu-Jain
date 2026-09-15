from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List

from auth import verify_clerk_token
from database import get_db
from routes.ai import router as ai_router

app = FastAPI(title="Smart Learning Planner API")

# Configure CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include AI Router
app.include_router(ai_router)


# Request Payload Schema
from typing import List, Union, Optional

class ProfileCreateRequest(BaseModel):
    email: Optional[EmailStr] = None
    semester: int
    study_hours_per_day: float
    goals: Union[str, List[str]]
    subjects: Optional[List[str]] = []


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Smart Learning Planner Backend"}


@app.get("/api/v1/protected-route")
def protected_route(user: dict = Depends(verify_clerk_token)):
    return {"message": "Access granted", "clerk_id": user.get("sub")}


@app.post("/api/v1/profile", status_code=status.HTTP_201_CREATED)
async def create_or_update_profile(
    payload: ProfileCreateRequest,
    user_data: dict = Depends(verify_clerk_token)
):
    clerk_id = user_data.get("sub", "dev_user_default") if user_data else "dev_user_default"
    email = payload.email or (user_data.get("email") if user_data else None) or "student@example.com"

    goals_list = payload.goals if isinstance(payload.goals, list) else [payload.goals]
    subjects_list = payload.subjects or []

    # Optional DB connection attempt
    try:
        from database import get_db
        db = get_db()
        if db:
            user_res = db.table("users").upsert({
                "clerk_id": clerk_id,
                "email": email,
                "role": "student"
            }, on_conflict="clerk_id").execute()

            internal_user_id = user_res.data[0]["id"] if user_res.data else None

            profile_res = db.table("student_profiles").upsert({
                "user_id": internal_user_id,
                "semester": payload.semester,
                "study_hours_per_day": payload.study_hours_per_day,
                "goals": goals_list,
                "subjects": subjects_list,
                "onboarding_completed": True
            }, on_conflict="user_id").execute()

            return {
                "message": "Profile created successfully",
                "data": profile_res.data[0] if profile_res.data else {}
            }
    except Exception as db_err:
        print(f"Database notice (running in mock mode): {db_err}")

    return {
        "message": "Profile created successfully",
        "data": {
            "clerk_id": clerk_id,
            "email": email,
            "semester": payload.semester,
            "study_hours_per_day": payload.study_hours_per_day,
            "goals": goals_list,
            "subjects": subjects_list,
            "onboarding_completed": True
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)