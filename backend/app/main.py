from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
import asyncio
from enum import Enum

from .db.database import get_db
from .models.submission import Submission
from .schemas.submission import SubmissionCreate, SubmissionResponse, ProcessingStatus

# Create FastAPI application
app = FastAPI(
    title="Heimdall-hook API",
    description="API for Heimdall",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basic route for testing
@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Hook API is running"}

async def process_text(text):
    """
    Process the submitted text and determine if it meets requirements.
    
    Args:
        text: The text to process
        
    Returns:
        Dict with processed results and validation status
    """
    await asyncio.sleep(1)
    
    word_count = len(text.split())
    
    meets_requirements = word_count >= 5
    
    score = word_count
    
    result = {
        "word_count": word_count,
        "processed_successfully": True,
        "meets_requirements": meets_requirements,
        "score": score,
        "analysis": {
            "sentiment": "positive" if "good" in text.lower() else "neutral",
        }
    }
    
    return result

# Submission endpoint
@app.post("/api/submissions", response_model=SubmissionResponse)
async def create_submission(
    submission_data: SubmissionCreate = Body(...),
    db: Session = Depends(get_db)
):
    """
    Create a new submission with the provided text.
    Process the text and return the status.
    """
    # Create submission record with initial status
    submission = Submission(
        text=submission_data.text,
        api_key=submission_data.api_key,
        status=ProcessingStatus.PROCESSING,
        source_url=submission_data.source_url,
    )
    
    db.add(submission)
    db.commit()
    db.refresh(submission)
    
    try:
        # Process the text
        processing_result = await process_text(submission_data.text)
        
        # Update submission based on processing result
        if processing_result["processed_successfully"]:
            if processing_result["score"]:
                submission.score = processing_result["score"]
            
            if processing_result["meets_requirements"]:
                submission.status = ProcessingStatus.SUCCESS
                submission.processing_result = processing_result
            else:
                submission.status = ProcessingStatus.FAILED_REQUIREMENTS
                submission.processing_result = processing_result
                submission.failure_reason = "Text does not meet requirements"
        else:
            submission.status = ProcessingStatus.FAILED_PROCESSING
            submission.processing_result = processing_result
            submission.failure_reason = "Processing error"
        
        # Send to main website system (as a future step)
        # This would be implemented to forward successful submissions
        if submission.status == ProcessingStatus.SUCCESS:
            # TODO: Implement forwarding to main system
            # E.g. await forward_to_main_system(submission)
            pass
        
    except Exception as e:
        # Handle any unexpected errors
        submission.status = ProcessingStatus.FAILED_PROCESSING
        submission.failure_reason = str(e)
    
    # Save the updated submission
    db.commit()
    db.refresh(submission)
    
    # Return response
    return SubmissionResponse(
        id=submission.id,
        status=submission.status,
        created_at=submission.created_at,
        processed_at=submission.processed_at,
        meets_requirements=submission.status == ProcessingStatus.SUCCESS,
        failure_reason=submission.failure_reason
    )
    
# Get submission status endpoint
@app.get("/api/submissions/{submission_id}", response_model=SubmissionResponse)
async def get_submission(submission_id: int, db: Session = Depends(get_db)):
    """Get the status of a submission by ID."""
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    return SubmissionResponse(
        id=submission.id,
        status=submission.status,
        created_at=submission.created_at,
        processed_at=submission.processed_at,
        meets_requirements=submission.status == ProcessingStatus.SUCCESS,
        failure_reason=submission.failure_reason
    )
    
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)