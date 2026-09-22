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


def save_study_plan(clerk_id: str, plan_data: dict) -> dict:
    """
    Save a generated study plan for the authenticated Clerk user.
    """
    db = get_db()

    # Find the internal Supabase user ID using Clerk ID
    user_res = (
        db.table("users")
        .select("id")
        .eq("clerk_id", clerk_id)
        .execute()
    )

    if not user_res.data:
        raise RuntimeError("User not found for the provided Clerk ID")

    user_id = user_res.data[0]["id"]

    # Save the generated study plan against that user
    plan_res = (
        db.table("study_plans")
        .insert({
            "user_id": user_id,
            "plan_data": plan_data
        })
        .execute()
    )

    if not plan_res.data:
        raise RuntimeError("Study plan could not be saved")

    return plan_res.data[0]