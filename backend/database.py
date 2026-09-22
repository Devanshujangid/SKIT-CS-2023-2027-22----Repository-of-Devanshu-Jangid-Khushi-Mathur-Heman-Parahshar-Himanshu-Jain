import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

# Check if a valid URL is provided; otherwise create a dummy/mock placeholder
supabase: Client = None

if SUPABASE_URL.startswith("http://") or SUPABASE_URL.startswith("https://"):
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    except Exception as e:
        print(f"Warning: Could not initialize Supabase client: {e}")
else:
    print("Warning: SUPABASE_URL is not configured with a valid HTTP/HTTPS URL. Running without active DB connection.")

def get_db() -> Client:
    if not supabase:
        raise RuntimeError("Database connection not initialized. Please configure SUPABASE_URL in .env")
    return supabase

def upsert_study_plan(clerk_id: str, plan_data: dict):
    db = get_db()

    # Find internal user UUID using Clerk ID
    user_response = (
        db.table("users")
        .select("id")
        .eq("clerk_id", clerk_id)
        .limit(1)
        .execute()
    )

    if not user_response.data:
        raise ValueError("User not found")

    user_id = user_response.data[0]["id"]

    # Insert or update the user's study plan
    response = (
        db.table("study_plans")
        .upsert(
            {
                "user_id": user_id,
                "plan_data": plan_data,
            },
            on_conflict="user_id"
        )
        .execute()
    )

    return response.data