import os
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

load_dotenv()

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])


class AITestRequest(BaseModel):
    prompt: str


@router.post("/test")
async def test_gemini(request: AITestRequest):
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise HTTPException(
            status_code=500,
            detail="Missing GEMINI_API_KEY in .env configuration."
        )

    try:
        genai.configure(api_key=gemini_api_key)
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