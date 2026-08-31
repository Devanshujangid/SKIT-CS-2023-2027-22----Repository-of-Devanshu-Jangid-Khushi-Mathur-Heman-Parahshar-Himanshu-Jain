from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List

from auth import verify_clerk_token
from database import get_db

app = FastAPI(title="Smart Learning Planner API")

# Configure CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Payload Schema
class ProfileCreateRequest(BaseModel):
    email: EmailStr
    semester: int
    study_hours_per_day: float
    goals: List[str]

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Smart Learning Planner Backend"}

@app.post("/api/v1/profile", status_code=status.HTTP_201_CREATED)
async def create_or_update_profile(
    payload: ProfileCreateRequest,
    user_data: dict = Depends(verify_clerk_token),
    db = Depends(get_db)
):
    clerk_id = user_data.get("sub")
    if not clerk_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clerk ID missing from session token."
        )

    try:
        # 1. Upsert into 'users' table
        user_res = db.table("users").upsert({
            "clerk_id": clerk_id,
            "email": payload.email,
            "role": "student"
        }, on_conflict="clerk_id").execute()

        if not user_res.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to record user."
            )

        internal_user_id = user_res.data[0]["id"]

        # 2. Upsert into 'student_profiles' table
        profile_res = db.table("student_profiles").upsert({
            "user_id": internal_user_id,
            "semester": payload.semester,
            "study_hours_per_day": payload.study_hours_per_day,
            "goals": payload.goals,
            "onboarding_completed": True
        }, on_conflict="user_id").execute()

        return {
            "message": "Profile created successfully",
            "data": profile_res.data[0]
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database error: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)