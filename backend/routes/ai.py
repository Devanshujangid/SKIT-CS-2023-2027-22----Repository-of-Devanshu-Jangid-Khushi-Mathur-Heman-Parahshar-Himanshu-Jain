# backend/routes/ai.py

import json
import logging
import os
import time
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from google import genai
from google.genai import types

from database import (
    get_db,
    get_or_create_user,
    save_study_plan,
    save_plan_tasks,
)
from rate_limit import check_gemini_rate_limit
from services.learning_loop import get_learning_loop_payload

from prompts.study_plan import (
    OnboardingDataInput,
    STUDY_PLAN_SYSTEM_INSTRUCTION,
    REGENERATION_SYSTEM_INSTRUCTION,
    RegenerationInput,
    build_study_plan_prompt,
    build_regeneration_prompt,
    validate_study_plan_output,
    StudyPlanOutputSchema,
)
from auth import verify_clerk_token


load_dotenv()

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])
logger = logging.getLogger(__name__)

# In-memory status is suitable for local development.
# It resets on restart and is not shared between multiple workers.
generation_status: Dict[str, Dict[str, str]] = {}


# ------------------------------------------------------------------
# Request models
# ------------------------------------------------------------------

class TestPromptRequest(BaseModel):
    prompt: str


class GeneratePlanRequest(BaseModel):
    onboarding_data: OnboardingDataInput


class RegeneratePlanRequest(BaseModel):
    current_plan: StudyPlanOutputSchema = Field(
        ...,
        description="The previous study plan JSON used as context.",
    )
    user_feedback: str = Field(
        ...,
        description="Instructions for refining the study plan.",
    )
    onboarding_data: Optional[OnboardingDataInput] = Field(
        None,
        description="Optional student onboarding profile context.",
    )


class AdaptPlanRequest(BaseModel):
    execution_history: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional task/session execution history.",
    )
    onboarding_data: Optional[OnboardingDataInput] = Field(
        None,
        description="Optional updated onboarding data.",
    )


# ------------------------------------------------------------------
# Gemini configuration
# ------------------------------------------------------------------

def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing from the environment.")

    return genai.Client(api_key=api_key)


def get_target_model() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


# ------------------------------------------------------------------
# Gemini generation helper
# ------------------------------------------------------------------

def generate_gemini_response(
    prompt: str,
    system_instruction: Optional[str] = None,
) -> str:
    client = get_gemini_client()
    model = get_target_model()

    max_attempts = 3
    base_delay = 2
    last_error = None

    for attempt in range(max_attempts):
        try:
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                system_instruction=system_instruction or None,
            )

            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config,
            )

            if not response.text:
                raise RuntimeError("Gemini returned an empty response.")

            return response.text

        except Exception as exc:
            last_error = exc
            error_text = str(exc).lower()

            retryable = any(
                keyword in error_text
                for keyword in (
                    "429",
                    "rate limit",
                    "resource exhausted",
                    "503",
                    "service unavailable",
                    "timeout",
                    "timed out",
                    "temporarily unavailable",
                )
            )

            logger.warning(
                "Gemini request failed on attempt %s/%s: %s",
                attempt + 1,
                max_attempts,
                exc,
            )

            if not retryable:
                raise RuntimeError(
                    f"Gemini API request failed: {exc}"
                ) from exc

            if attempt < max_attempts - 1:
                delay = base_delay * (2 ** attempt

                )
                logger.warning(
                    "Retrying Gemini request in %s seconds.",
                    delay,
                )
                time.sleep(delay)

    raise RuntimeError(
        f"Gemini API failed after {max_attempts} attempts: {last_error}"
    )


# ------------------------------------------------------------------
# JSON parsing helper
# ------------------------------------------------------------------

def extract_json(text: str) -> Dict[str, Any]:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Gemini response is empty.")

    cleaned = text.strip()

    # Remove Markdown code fences.
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        cleaned = "\n".join(lines).strip()

    try:
        parsed = json.loads(cleaned)

    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")

        if start < 0 or end < start:
            raise ValueError(
                "Gemini response did not contain valid JSON."
            )

        try:
            parsed = json.loads(cleaned[start:end + 1])

        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Could not parse Gemini JSON response: {exc}"
            ) from exc

    if not isinstance(parsed, dict):
        raise ValueError(
            "Expected the Gemini response to be a JSON object."
        )

    return parsed


def _model_to_dict(model: Any) -> Dict[str, Any]:
    """Convert a Pydantic model or dictionary to a plain dictionary."""

    if isinstance(model, dict):
        return model

    if hasattr(model, "model_dump"):
        return model.model_dump(mode="json")

    if hasattr(model, "dict"):
        return model.dict()

    raise TypeError(
        "Validated study plan has an unsupported format."
    )


def _get_clerk_id(user_data: dict) -> str:
    """Extract the Clerk subject ID from verified auth data."""

    clerk_id = user_data.get("sub") or user_data.get("clerk_id")

    if not clerk_id:
        raise HTTPException(
            status_code=401,
            detail="Authenticated user Clerk ID is missing.",
        )

    return str(clerk_id)


# ------------------------------------------------------------------
# Background generation helper
# ------------------------------------------------------------------

def generate_and_save_plan(
    user_prompt: Optional[str],
    clerk_id: str,
    system_instruction: str = STUDY_PLAN_SYSTEM_INSTRUCTION,
    onboarding_data: Optional[OnboardingDataInput] = None,
    email: Optional[str] = None,
):
    try:
        logger.info("Background study plan generation started.")

        generation_status[clerk_id] = {
            "status": "generating",
            "message": "Your study plan is being generated.",
        }

        # Build the prompt using fresh learning history.
        if onboarding_data is not None:
            learning_history = (
                get_learning_loop_payload(clerk_id) or {}
            )

            user_prompt = build_study_plan_prompt(
                onboarding_data,
                learning_history=learning_history,
            )

        if not user_prompt:
            raise ValueError("Study plan prompt is missing.")

        response_text = generate_gemini_response(
            prompt=user_prompt,
            system_instruction=system_instruction,
        )

        raw_plan = extract_json(response_text)
        validated_plan = validate_study_plan_output(raw_plan)
        plan_data = _model_to_dict(validated_plan)

        # Requires the versioning database migration.
        save_study_plan(
            clerk_id=clerk_id,
            plan_data=plan_data,
            email=email,
        )

        try:
            save_plan_tasks(
                clerk_id=clerk_id,
                plan_data=plan_data,
            )
        except Exception:
            logger.exception(
                "Could not synchronize individual plan tasks."
            )

        generation_status[clerk_id] = {
            "status": "completed",
            "message": "Study plan generated successfully.",
        }

        logger.info(
            "Background study plan generation completed."
        )

    except Exception:
        logger.exception(
            "Background study plan generation failed."
        )

        generation_status[clerk_id] = {
            "status": "failed",
            "message": "Study plan generation failed. Please try again.",
        }


# ------------------------------------------------------------------
# Generation status endpoint
# ------------------------------------------------------------------

@router.get("/generation-status")
async def get_generation_status(
    user_data: dict = Depends(verify_clerk_token),
):
    clerk_id = _get_clerk_id(user_data)

    generation = generation_status.get(
        clerk_id,
        {
            "status": "not_started",
            "message": "No study plan generation has been started.",
        },
    )

    return {
        "success": True,
        **generation,
    }


# ------------------------------------------------------------------
# Test endpoint
# ------------------------------------------------------------------

@router.post("/test")
async def test_ai(
    request: TestPromptRequest,
    user_data: dict = Depends(verify_clerk_token),
):
    clerk_id = _get_clerk_id(user_data)
    check_gemini_rate_limit(clerk_id)

    try:
        response_text = generate_gemini_response(
            request.prompt
        )

        return {
            "success": True,
            "model": get_target_model(),
            "response": response_text,
        }

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("AI test endpoint failed.")

        raise HTTPException(
            status_code=500,
            detail="AI test request failed. Check backend logs.",
        ) from exc


# ------------------------------------------------------------------
# Generate study plan endpoint
# ------------------------------------------------------------------

@router.post("/generate-plan")
async def generate_study_plan(
    request: GeneratePlanRequest,
    background_tasks: BackgroundTasks,
    user_data: dict = Depends(verify_clerk_token),
):
    clerk_id = _get_clerk_id(user_data)

    try:
        check_gemini_rate_limit(clerk_id)

        learning_history = (
            get_learning_loop_payload(clerk_id) or {}
        )

        user_prompt = build_study_plan_prompt(
            request.onboarding_data,
            learning_history=learning_history,
        )

        generation_status[clerk_id] = {
            "status": "generating",
            "message": "Your study plan is being generated.",
        }

        background_tasks.add_task(
            generate_and_save_plan,
            user_prompt=user_prompt,
            clerk_id=clerk_id,
            onboarding_data=request.onboarding_data,
            email=user_data.get("email"),
        )

        return {
            "success": True,
            "message": "Study plan generation started.",
            "model": get_target_model(),
        }

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Could not start study plan generation."
        )

        raise HTTPException(
            status_code=500,
            detail="Could not start study plan generation. Check backend logs.",
        ) from exc


# ------------------------------------------------------------------
# Regenerate / tweak study plan endpoint
# ------------------------------------------------------------------

@router.post("/regenerate-plan")
@router.post("/tweak-plan")
async def regenerate_study_plan(
    request: RegeneratePlanRequest,
    background_tasks: BackgroundTasks,
    user_data: dict = Depends(verify_clerk_token),
):
    """Refine a supplied plan using the user's feedback."""

    clerk_id = _get_clerk_id(user_data)

    try:
        check_gemini_rate_limit(clerk_id)

        generation_status[clerk_id] = {
            "status": "generating",
            "message": "Your study plan is being regenerated.",
        }

        regeneration_input = RegenerationInput(
            current_plan=request.current_plan,
            user_feedback=request.user_feedback,
            onboarding_data=request.onboarding_data,
        )

        user_prompt = build_regeneration_prompt(
            regeneration_input
        )

        background_tasks.add_task(
            generate_and_save_plan,
            user_prompt=user_prompt,
            clerk_id=clerk_id,
            system_instruction=REGENERATION_SYSTEM_INSTRUCTION,
            email=user_data.get("email"),
        )

        return {
            "success": True,
            "message": "Study plan regeneration started.",
            "model": get_target_model(),
        }

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Could not start study plan regeneration."
        )

        raise HTTPException(
            status_code=500,
            detail="Could not start study plan regeneration. Check backend logs.",
        ) from exc


# ------------------------------------------------------------------
# AI adaptive study-plan endpoint
# ------------------------------------------------------------------

@router.post("/adapt-plan")
async def adapt_study_plan(
    request: AdaptPlanRequest,
    user_data: dict = Depends(verify_clerk_token),
):
    """
    Generate a new plan version using the current plan and
    learning history.

    The database RPC must atomically save the new version
    and deactivate the previous active plan.
    """

    clerk_id = _get_clerk_id(user_data)

    try:
        check_gemini_rate_limit(clerk_id)

        db = get_db()

        user_id = get_or_create_user(
            db,
            clerk_id=clerk_id,
            email=user_data.get("email"),
        )

        # 1. Fetch the current active plan.
        active_result = (
            db.table("study_plans")
            .select(
                "id, plan_data, created_at, updated_at"
            )
            .eq("user_id", user_id)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )

        if not active_result.data:
            raise HTTPException(
                status_code=404,
                detail="No active study plan found. Generate a plan first.",
            )

        active_plan = active_result.data[0]
        current_plan_data = active_plan.get("plan_data")

        if not isinstance(current_plan_data, dict):
            raise HTTPException(
                status_code=500,
                detail="The current study plan contains invalid data.",
            )

        # 2. Use supplied onboarding data or load saved profile.
        onboarding_data = request.onboarding_data

        if onboarding_data is None:
            profile_result = (
                db.table("student_profiles")
                .select(
                    "semester, study_hours_per_day, goals, subjects"
                )
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )

            if not profile_result.data:
                raise HTTPException(
                    status_code=404,
                    detail="Student onboarding profile was not found.",
                )

            profile = profile_result.data[0]
            raw_subjects = profile.get("subjects") or []

            # Database subjects are TEXT[].
            # Convert strings into the SubjectInput format.
            normalized_subjects = [
                {"name": subject}
                if isinstance(subject, str)
                else subject
                for subject in raw_subjects
            ]

            onboarding_data = OnboardingDataInput.model_validate(
                {
                    "semester": profile["semester"],
                    "study_hours_per_day": profile["study_hours_per_day"],
                    "goals": profile.get("goals") or [],
                    "subjects": normalized_subjects,
                }
            )

        # 3. Fetch learning history.
        learning_history = (
            get_learning_loop_payload(clerk_id) or {}
        )

        if not isinstance(learning_history, dict):
            learning_history = {
                "learning_history": learning_history
            }

        # Include the old plan and extra frontend history.
        learning_history["previous_plan"] = current_plan_data

        if request.execution_history is not None:
            learning_history["provided_execution_history"] = (
                request.execution_history
            )

        # 4. Generate and validate before saving anything.
        prompt = build_study_plan_prompt(
            onboarding_data,
            learning_history=learning_history,
        )

        response_text = generate_gemini_response(
            prompt=prompt,
            system_instruction=STUDY_PLAN_SYSTEM_INSTRUCTION,
        )

        raw_plan = extract_json(response_text)

        validated_plan = validate_study_plan_output(
            raw_plan
        )

        plan_data = _model_to_dict(validated_plan)

        # 5. Create and activate the new plan version.
        # Requires create_study_plan_version() in PostgreSQL.
        saved_rows = save_study_plan(
            clerk_id=clerk_id,
            plan_data=plan_data,
            email=user_data.get("email"),
        )

        saved_plan = (
            saved_rows[0]
            if isinstance(saved_rows, list) and saved_rows
            else saved_rows
        )

        if (
            not isinstance(saved_plan, dict)
            or not saved_plan.get("id")
        ):
            raise RuntimeError(
                "Database did not confirm the new study-plan version."
            )

        # 6. Synchronize task rows separately.
        # Task-sync failure must not undo a successfully saved plan.
        try:
            save_plan_tasks(
                clerk_id=clerk_id,
                plan_data=plan_data,
            )
        except Exception:
            logger.exception(
                "New plan saved, but task synchronization failed."
            )

        generation_status[clerk_id] = {
            "status": "completed",
            "message": "Adaptive study plan generated successfully.",
        }

        return {
            "success": True,
            "message": "Adaptive study plan generated and activated.",
            "previous_plan_id": active_plan["id"],
            "plan_id": saved_plan["id"],
            "plan": plan_data,
        }

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Adaptive study-plan generation failed."
        )

        generation_status[clerk_id] = {
            "status": "failed",
            "message": "Adaptive plan generation failed. Please try again.",
        }

        raise HTTPException(
            status_code=500,
            detail="Adaptive plan generation failed. Check backend logs.",
        ) from exc