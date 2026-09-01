from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from auth import verify_clerk_token
from routes.ai import router as ai_router

app = FastAPI(title="Smart Learning Planner API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai_router)

@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Smart Learning Planner Backend"}

@app.get("/api/v1/protected-route")
def protected_route(user: dict = Depends(verify_clerk_token)):
    return {"message": "Access granted", "clerk_id": user.get("sub")}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)