from fastapi import FastAPI, Depends, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import asyncio
import time
from datetime import datetime
from urllib.parse import urlparse

from .db.database import get_db
from .models.owner import Owner
from .models.api_key import ApiKey
from .models.submission import Submission, ProcessingStatus
from .schemas.submission import SubmissionCreate, SubmissionResponse


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


async def process_text(text: str) -> dict:
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


# Helper function to extract domain from URL
def extract_domain(url: str) -> str:
    """Extract domain from URL for analytics"""
    try:
        if url and url.startswith(('http://', 'https://')):
            return urlparse(url).netloc.lower()
        return None
    except:
        return None


# Helper function to authenticate API key
async def authenticate_api_key(api_key: str, db: Session) -> ApiKey:
    """Authenticate and return the API key object"""
    api_key_obj = db.query(ApiKey).filter(
        ApiKey.key == api_key,
        ApiKey.is_active == True
    ).first()
    
    if not api_key_obj:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    
    if api_key_obj.is_expired:
        raise HTTPException(status_code=401, detail="API key has expired")
    
    # Update last used timestamp
    api_key_obj.last_used_at = datetime.now()
    api_key_obj.total_requests += 1
    db.commit()
    
    return api_key_obj


# Background processing function
async def process_submission_background(submission_id: int):
    """Process submission in background after timeout"""
    from .db.database import SessionLocal
    
    db = SessionLocal()
    try:
        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        if not submission or submission.is_completed:
            return
        
        # Update status to background processing
        submission.update_status(ProcessingStatus.BACKGROUND_PROCESSING)
        db.commit()
        
        # Process without time pressure
        try:
            processing_result = await process_text(submission.text)
            
            # Update submission with results
            submission.processing_result = processing_result
            submission.meets_requirements = processing_result.get("meets_requirements", False)
            submission.score = processing_result.get("score")
            
            if submission.meets_requirements:
                submission.update_status(ProcessingStatus.SUCCESS)
            else:
                submission.update_status(ProcessingStatus.FAILED_REQUIREMENTS, "Text does not meet requirements")
            
        except Exception as e:
            submission.update_status(ProcessingStatus.FAILED_PROCESSING, f"Background processing error: {str(e)}")
            submission.error_details = {"error": str(e), "type": "background_processing"}
        
        db.commit()
        
    except Exception as e:
        print(f"Background processing error for submission {submission_id}: {e}")
    finally:
        db.close()


# Main submission endpoint
@app.post("/api/submissions", response_model=SubmissionResponse)
async def create_submission(
    submission_data: SubmissionCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create a new submission and process it.
    If processing takes longer than 3 seconds, continue in background.
    """
    # Authenticate API key
    api_key_obj = await authenticate_api_key(submission_data.api_key, db)
    
    # Extract request information
    source_domain = extract_domain(submission_data.source_url)
    
    # Create submission record
    submission = Submission(
        user_id=api_key_obj.user_id,
        api_key_id=api_key_obj.id,
        text=submission_data.text,
        text_length=len(submission_data.text),
        text_word_count=len(submission_data.text.split()),
        source_url=submission_data.source_url,
        source_domain=source_domain,
        metadata=submission_data.metadata,
        context=submission_data.context,
        status=ProcessingStatus.PENDING
    )
    
    db.add(submission)
    db.commit()
    db.refresh(submission)
    
    try:
        # Update status to processing
        submission.update_status(ProcessingStatus.PROCESSING)
        db.commit()
        
        # Try processing with 3-second timeout
        start_time = time.time()
        processing_result = await asyncio.wait_for(
            process_text(submission_data.text),
            timeout=3.0
        )
        
        # Calculate processing time
        processing_duration = int((time.time() - start_time) * 1000)
        submission.processing_duration_ms = processing_duration
        
        # Processing completed within 3 seconds!
        submission.processing_result = processing_result
        submission.meets_requirements = processing_result.get("meets_requirements", False)
        submission.score = processing_result.get("score")
        
        if submission.meets_requirements:
            submission.update_status(ProcessingStatus.SUCCESS)
            message = "Success! Your submission has been processed."
        else:
            submission.update_status(ProcessingStatus.FAILED_REQUIREMENTS, "Text does not meet requirements")
            message = "Your submission was processed but doesn't meet our requirements."
        
        db.commit()
        db.refresh(submission)
        
        return SubmissionResponse(
            id=submission.id,
            status=submission.status,
            text_length=submission.text_length,
            meets_requirements=submission.meets_requirements,
            score=submission.score,
            failure_reason=submission.failure_reason,
            created_at=submission.created_at,
            completed_processing_at=submission.completed_processing_at,
            processing_duration_ms=submission.processing_duration_ms,
            message=message
        )
        
    except asyncio.TimeoutError:
        # Processing is taking longer than 3 seconds
        submission.update_status(ProcessingStatus.TIMEOUT)
        db.commit()
        
        # Continue processing in background
        background_tasks.add_task(process_submission_background, submission.id)
        
        return SubmissionResponse(
            id=submission.id,
            status=ProcessingStatus.TIMEOUT,
            text_length=submission.text_length,
            meets_requirements=None,
            score=None,
            failure_reason=None,
            created_at=submission.created_at,
            completed_processing_at=None,
            processing_duration_ms=None,
            message="Thank you for your submission! We're processing it now and will notify the website owner when complete."
        )
        
    except Exception as e:
        # Error occurred within 3 seconds - user is still there
        submission.update_status(ProcessingStatus.FAILED_PROCESSING, f"Processing error: {str(e)}")
        submission.error_details = {"error": str(e), "type": "processing_error"}
        db.commit()
        
        return SubmissionResponse(
            id=submission.id,
            status=ProcessingStatus.FAILED_PROCESSING,
            text_length=submission.text_length,
            meets_requirements=False,
            score=None,
            failure_reason=submission.failure_reason,
            created_at=submission.created_at,
            completed_processing_at=submission.completed_processing_at,
            processing_duration_ms=None,
            message="Sorry, there was an error processing your submission. Please try again."
        )
    
    
# Health check endpoint
@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Widget Hook API is running"}


# Get submission status endpoint
@app.get("/api/submissions/{submission_id}", response_model=SubmissionResponse)
async def get_submission_status(
    submission_id: int, 
    api_key: str,
    db: Session = Depends(get_db)
):
    """Get the status of a submission by ID."""
    # Authenticate API key
    api_key_obj = await authenticate_api_key(api_key, db)
    
    # Get submission and verify ownership
    submission = db.query(Submission).filter(
        Submission.id == submission_id,
        Submission.user_id == api_key_obj.user_id
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    return SubmissionResponse(
        id=submission.id,
        status=submission.status,
        text_length=submission.text_length,
        meets_requirements=submission.meets_requirements,
        score=submission.score,
        failure_reason=submission.failure_reason,
        created_at=submission.created_at,
        completed_processing_at=submission.completed_processing_at,
        processing_duration_ms=submission.processing_duration_ms,
        message="Submission status retrieved successfully"
    )