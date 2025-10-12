import os
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
from .main import authenticate_api_key, get_api_key_from_header
from .schemas.submission import SubmissionAuto

app = FastAPI()

# Safe to allow all origins here
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def health():
    return {"status": "ok"}

@app.post("/analyse")
async def analyse(
    request: SubmissionAuto,
    api_key: str = Depends(get_api_key_from_header)
):
    if not await authenticate_api_key(api_key):
        raise HTTPException(401, "Invalid API key")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{os.getenv('BASE_API_URL')}/api/v1/submissions/create-submission",  # Internal call
                json=request.model_dump(),
                headers={
                    "Internal-Auth": os.getenv("INTERNAL_SECRET"),
                    "Authorization": f"Bearer {api_key}"
                }
            )
            response.raise_for_status()
        except Exception as e:
            raise HTTPException(status_code=400, detail="An error occurred")
        
    return

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(app, host="0.0.0.0", port=8001)