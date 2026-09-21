import os
import json
import asyncio
import google.generativeai as genai

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from prompts.study_plan import (
    OnboardingDataInput,
    STUDY_PLAN_SYSTEM_INSTRUCTION,
    build_study_plan_prompt,
)

load_dotenv()

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])


def get_gemini_model(model_name: str = None) -> genai.GenerativeModel:
    """
    Initializes and returns the configured Gemini model.
    """

    gemini_api_key = os.getenv("GEMINI_API_KEY")

    if not gemini_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Missing GEMINI_API_KEY in environment configuration."
        )

    genai.configure(api_key=gemini_api_key)

    target_model = model_name or os.getenv(
        "GEMINI_MODEL",
        "gemini-2.5-flash"
    )

    return genai.GenerativeModel(
        model_name=target_model,
        system_instruction=STUDY_PLAN_SYSTEM_INSTRUCTION
    )


class AITestRequest(BaseModel):
    prompt: str = "Hello, respond with a short connectivity test message."


@router.post("/test")
async def test_gemini(request: AITestRequest):
    """
    Endpoint to verify Gemini API connectivity.
    """

    try:
        gemini_api_key = os.getenv("GEMINI_API_KEY")

        if not gemini_api_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Missing GEMINI_API_KEY in environment configuration."
            )

        genai.configure(api_key=gemini_api_key)

        target_model = os.getenv(
            "GEMINI_MODEL",
            "gemini-3.6-flash"
        )

        model = genai.GenerativeModel(target_model)

        response = await asyncio.to_thread(
            model.generate_content,
            request.prompt
        )

        return {
            "success": True,
            "model_used": target_model,
            "response": response.text
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gemini API error: {str(e)}"
        )


@router.post("/generate-plan")
async def generate_study_plan(payload: OnboardingDataInput):
    """
    Generates a structured 7-day personalized study plan.

    Includes:
    - Gemini AI integration
    - Retry mechanism
    - JSON MIME type enforcement
    - JSON parsing and validation
    """

    max_retries = 3
    retry_delay = 2

    model = get_gemini_model()
    user_prompt = build_study_plan_prompt(payload)

    last_error = None

    for attempt in range(max_retries):
        try:

            response = await asyncio.to_thread(
                model.generate_content,
                user_prompt,
                generation_config={
                    "response_mime_type": "application/json"
                }
            )

            raw_text = response.text.strip()

            if not raw_text:
                raise ValueError("Gemini returned an empty response.")

            # Remove accidental markdown wrappers
            if raw_text.startswith("```json"):
                raw_text = raw_text[7:]

            elif raw_text.startswith("```"):
                raw_text = raw_text[3:]

            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]

            parsed_json = json.loads(raw_text.strip())

            return {
                "success": True,
                "plan": parsed_json,
                "model_used": os.getenv(
                    "GEMINI_MODEL",
                    "gemini-3.6-flash"
                )
            }

        except json.JSONDecodeError as e:
            last_error = f"Invalid JSON response from Gemini: {str(e)}"

        except Exception as e:
            last_error = str(e)

        # Retry only if attempts remain
        if attempt < max_retries - 1:
            await asyncio.sleep(retry_delay * (attempt + 1))

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail=f"Study plan generation failed after {max_retries} attempts: {last_error}"
    )
