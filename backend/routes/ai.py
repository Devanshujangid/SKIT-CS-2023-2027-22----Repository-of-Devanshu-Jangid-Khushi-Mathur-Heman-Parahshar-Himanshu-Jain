import os

import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("Missing GEMINI_API_KEY in .env")

genai.configure(api_key=GEMINI_API_KEY)

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])


class AITestRequest(BaseModel):
    prompt: str


@router.post("/test")
async def test_gemini(request: AITestRequest):
    try:
        model = genai.GenerativeModel("gemini-3.6-flash")

        response = model.generate_content(request.prompt)

        return {
            "success": True,
            "response": response.text
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Gemini API error: {str(e)}"
        )