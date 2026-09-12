import os
import json
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
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Missing GEMINI_API_KEY in environment configuration."
        )

    genai.configure(api_key=gemini_api_key)

    # Allow configuration via env, default to gemini-1.5-flash
    target_model = model_name or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    return genai.GenerativeModel(
        model_name=target_model,
        system_instruction=STUDY_PLAN_SYSTEM_INSTRUCTION
    )


class AITestRequest(BaseModel):
    prompt: str = "Hello, respond with a short connectivity test message."


@router.post("/test")
async def test_gemini(request: AITestRequest):
    """
    Endpoint to verify Google Generative AI connection and API key setup.
    """
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Missing GEMINI_API_KEY in .env configuration."
        )

    try:
        genai.configure(api_key=gemini_api_key)
        target_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        model = genai.GenerativeModel(target_model)
        response = model.generate_content(request.prompt)

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
    Endpoint to generate a structured 7-day study plan from student onboarding data.
    Uses a deterministic prompt template and enforces raw JSON output.
    """
    try:
        model = get_gemini_model()
        user_prompt = build_study_plan_prompt(payload)

        # Enforce JSON mime type where supported by generative AI SDK
        response = model.generate_content(
            user_prompt,
            generation_config={"response_mime_type": "application/json"}
        )

        # Parse JSON response to verify valid structure
        raw_text = response.text.strip()
        
        # Clean any accidental markdown code blocks if returned
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.startswith("```"):
            raw_text = raw_text[3:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]

        parsed_json = json.loads(raw_text.strip())

        return {
            "success": True,
            "plan": parsed_json
        }

    except json.JSONDecodeError as json_err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse LLM response as JSON: {str(json_err)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Study plan generation error: {str(e)}"
        )