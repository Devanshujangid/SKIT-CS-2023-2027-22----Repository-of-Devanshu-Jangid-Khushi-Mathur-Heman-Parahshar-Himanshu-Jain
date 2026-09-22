# backend/routes/ai.py

import json
import logging
import os
import time
from typing import Any, Dict

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from google import genai
from google.genai import types

from prompts.study_plan import (
    OnboardingDataInput,
    STUDY_PLAN_SYSTEM_INSTRUCTION,
    build_study_plan_prompt,
    validate_study_plan_output,
)
from auth import verify_clerk_token
from database import save_study_plan


load_dotenv()

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])

logger = logging.getLogger(__name__)


# -----------------------------
# Request Models
# -----------------------------

class TestPromptRequest(BaseModel):
    prompt: str


class GeneratePlanRequest(BaseModel):
    onboarding_data: OnboardingDataInput


# -----------------------------
# Gemini Configuration
# -----------------------------

def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing in .env")

    return genai.Client(api_key=api_key)


def get_target_model() -> str:
    return os.getenv(
        "GEMINI_MODEL",
        "gemini-2.5-flash"
    )


# -----------------------------
# Helper: Generate Gemini Text
# -----------------------------

def generate_gemini_response(prompt: str) -> str:
    client = get_gemini_client()
    model = get_target_model()

    last_error = None

    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                response_mime_type="application/json"
              )
            )

            if not response.text:
                raise RuntimeError("Gemini returned an empty response")

            return response.text

        except Exception as exc:
            last_error = exc
            logger.exception(
                "Gemini request failed on attempt %s/3",
                attempt + 1
            )

            if attempt < 2:
                time.sleep(2)

    raise RuntimeError(f"Gemini API error: {last_error}")


# -----------------------------
# Helper: Extract JSON
# -----------------------------

def extract_json(text: str) -> Dict[str, Any]:
    cleaned = text.strip()

    # Remove Markdown code fences if Gemini returns them
    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "", 1)
        cleaned = cleaned.replace("```", "", 1)
        cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)

        if not isinstance(parsed, dict):
            raise ValueError("Expected a JSON object")

        return parsed

    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")

        if start == -1 or end == -1:
            raise ValueError("Gemini response did not contain valid JSON")

        try:
            parsed = json.loads(cleaned[start:end + 1])

            if not isinstance(parsed, dict):
                raise ValueError("Expected a JSON object")

            return parsed

        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Could not parse Gemini JSON response: {exc}"
            ) from exc


# -----------------------------
# Test Endpoint
# -----------------------------

@router.post("/test")
async def test_ai(request: TestPromptRequest):
    try:
        response_text = generate_gemini_response(request.prompt)

        return {
            "success": True,
            "model": get_target_model(),
            "response": response_text,
        }

    except Exception as exc:
        logger.exception("AI test endpoint failed")

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )


# -----------------------------
# Generate Study Plan Endpoint
# -----------------------------

@router.post("/generate-plan")
async def generate_study_plan(
    request: GeneratePlanRequest,
    user_data: dict = Depends(verify_clerk_token)
):
    try:
        onboarding_data = request.onboarding_data

        user_prompt = build_study_plan_prompt(onboarding_data)

        client = get_gemini_client()
        model = get_target_model()

        response = client.models.generate_content(
            model=model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=STUDY_PLAN_SYSTEM_INSTRUCTION,
                response_mime_type="application/json"
            )
        )

        if not response.text:
            raise RuntimeError("Gemini returned an empty study plan")

        raw_plan = extract_json(response.text)
        validated_plan = validate_study_plan_output(raw_plan)

        clerk_id = user_data.get("sub")

        if not clerk_id:
            raise RuntimeError("Authenticated user Clerk ID is missing")

        # Save generated study plan for the authenticated user 
        saved_plan = save_study_plan( 
            clerk_id=clerk_id, 
            plan_data=validated_plan.model_dump() 
        )

        return {
            "success": True,
            "model": model,
            "plan": validated_plan.model_dump(),
            "saved_plan": saved_plan,
        }

    except Exception as exc:
        logger.exception("Study plan generation failed")

        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )