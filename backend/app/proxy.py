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

@app.post("/analyse")
async def public_analyse(
    request: SubmissionAuto,
    api_key: str = Depends(get_api_key_from_header)
):
    # Validate API key
    if not await authenticate_api_key(api_key):
        raise HTTPException(401, "Invalid API key")
    
    # Call your main backend internally (server-to-server)
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "http://127.0.0.1:8000/api/v1/submissions/create-submission",  # Internal call
            json=request.model_dump(),
            headers={
                "Internal-Auth": os.getenv("INTERNAL_SECRET"),
                "Authorization": f"Bearer {api_key}"
            }
        )
    return response.json()

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(app, host="0.0.0.0", port=8001)