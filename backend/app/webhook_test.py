from fastapi import FastAPI, Depends, HTTPException, Query, Request, status, Header
from fastapi.middleware.cors import CORSMiddleware

# Create FastAPI application
app = FastAPI(
    title="Heimdall-hook API",
    description="API for Heimdall",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/yello")
async def yelo(request: Request):
    
    print("yello: ")
    data = await request.json()
    print(data)
    
    return

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(app, host="0.0.0.0", port=8001)