from fastapi import FastAPI, Depends, HTTPException, Request, BackgroundTasks, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import asyncio
import time
import logging
from datetime import datetime
from urllib.parse import urlparse
from passlib.context import CryptContext
from urllib.parse import urlparse

from .db.database import get_db
from .models.owner import Owner
from .models.api_key import ApiKey
from .models.submission import Submission, ProcessingStatus
from .schemas.owner import OwnerCreate, OwnerResponse
from .schemas.api_key import ApiKeyCreate, ApiKeyResponse
from .schemas.submission import SubmissionCreate, SubmissionResponse, SubmissionDetailResponse


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

# Health check endpoint
@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Widget Hook API is running"}

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
	exc_str = f'{exc}'.replace('\n', ' ').replace('   ', ' ')
	logging.error(f"{request}: {exc_str}")
	content = {'status_code': 10422, 'message': exc_str, 'data': None}
	return JSONResponse(content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


# ---------- AUTHORISATION ----------

def get_api_key_from_header(authorization: str = Header(None)) -> str:
    """Extract API key from Authorization header"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header"
        )
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must start with 'Bearer '"
        )
    
    api_key = authorization.split(" ")[1]
    if not api_key or len(api_key) < 8:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format"
        )
    
    return api_key


# ---------- PASSWORD HASHING ----------

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password"""
    return pwd_context.verify(plain_password, hashed_password)


# ---------- PROCESSING/HELPER FUNCTIONS ----------

# Text processing function
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
        
        # Update status to processing
        submission.update_status(ProcessingStatus.PROCESSING)
        db.commit()
        
        # Process without time pressure
        try:
            processing_result = await process_text(submission.text)
            
            # Update submission with results
            submission.processing_result = processing_result
            submission.meets_requirements = processing_result.get("meets_requirements", False)
            
            if submission.meets_requirements:
                submission.update_status(ProcessingStatus.SUCCESS)
            else:
                submission.update_status(ProcessingStatus.FAILED, "Text does not meet requirements")
            
        except Exception as e:
            submission.update_status(ProcessingStatus.FAILED, f"Background processing error: {str(e)}")
        
        db.commit()
        
    except Exception as e:
        print(f"Background processing error for submission {submission_id}: {e}")
    finally:
        db.close()


# ---------- OWNER ENDPOINTS ----------

@app.post("/api/owners", response_model=OwnerResponse)
async def create_owner(owner_data: OwnerCreate, db: Session = Depends(get_db)):
    """
    Create a new owner account.
    """
    # Check if owner already exists
    existing_owner = db.query(Owner).filter(Owner.email == owner_data.email).first()
    if existing_owner:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new owner
    owner = Owner(
        email=owner_data.email,
        name=owner_data.name,
        domain=owner_data.domain,
        password_hash=hash_password(owner_data.password)
    )
    
    db.add(owner)
    db.commit()
    db.refresh(owner)
    
    return OwnerResponse(
        id=owner.id,
        email=owner.email,
        name=owner.name,
        domain=owner.domain,
        is_active=owner.is_active,
        is_verified=owner.is_verified,
        monthly_submission_limit=owner.monthly_submission_limit,
        monthly_submissions_used=owner.monthly_submissions_used,
        created_at=owner.created_at
    )

@app.get("/api/owners/{owner_id}", response_model=OwnerResponse)
async def get_owner(owner_id: int, db: Session = Depends(get_db)):
    """
    Get owner by ID.
    """
    owner = db.query(Owner).filter(Owner.id == owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    
    return OwnerResponse(
        id=owner.id,
        email=owner.email,
        name=owner.name,
        domain=owner.domain,
        is_active=owner.is_active,
        is_verified=owner.is_verified,
        monthly_submission_limit=owner.monthly_submission_limit,
        monthly_submissions_used=owner.monthly_submissions_used,
        created_at=owner.created_at
    )


# ---------- API KEY ENDPOINTS ----------

@app.post("/api/owners/{owner_id}/api-keys", response_model=ApiKeyResponse)
async def create_api_key(
    owner_id: int, 
    api_key_data: ApiKeyCreate, 
    db: Session = Depends(get_db)
):
    """
    Generate a new API key for an owner.
    """
    # Check if owner exists
    owner = db.query(Owner).filter(Owner.id == owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    
    # Check if API key name already exists for this owner
    existing_key = db.query(ApiKey).filter(
        ApiKey.owner_id == owner_id,
        ApiKey.name == api_key_data.name
    ).first()
    if existing_key:
        raise HTTPException(status_code=400, detail="API key name already exists for this owner")
    
    # Generate new API key
    api_key = ApiKey(
        owner_id=owner_id,
        name=api_key_data.name,
        key=ApiKey.generate_key()
    )
    
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    return ApiKeyResponse(
        id=api_key.id,
        owner_id=api_key.owner_id,
        name=api_key.name,
        key=api_key.key,  # Full key returned only on creation
        is_active=api_key.is_active,
        total_requests=api_key.total_requests,
        last_used_at=api_key.last_used_at,
        created_at=api_key.created_at
    )

@app.get("/api/owners/{owner_id}/api-keys")
async def list_api_keys(owner_id: int, db: Session = Depends(get_db)):
    """
    List all API keys for a owner (with masked keys).
    """
    # Check if owner exists
    owner = db.query(Owner).filter(Owner.id == owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    
    api_keys = db.query(ApiKey).filter(ApiKey.owner_id == owner_id).all()
    
    # Return masked keys for security
    return [
        {
            "id": key.id,
            "name": key.name,
            "masked_key": key.masked_key,
            "is_active": key.is_active,
            "total_requests": key.total_requests,
            "last_used_at": key.last_used_at,
            "created_at": key.created_at
        }
        for key in api_keys
    ]

@app.delete("/api/api-keys/{api_key_id}")
async def delete_api_key(api_key_id: int, db: Session = Depends(get_db)):
    """
    Delete (deactivate) an API key.
    """
    api_key = db.query(ApiKey).filter(ApiKey.id == api_key_id).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    # Instead of deleting, deactivate for audit trail
    api_key.is_active = False
    db.commit()
    
    return {"message": "API key deactivated successfully"}


# ---------- SUBMISSION ENDPOINTS ----------

@app.post("/api/submissions", response_model=SubmissionResponse)
async def create_submission(
    submission_data: SubmissionCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(get_api_key_from_header),
    db: Session = Depends(get_db)
):
    """
    Create a new submission and process it.
    If processing takes longer than 3 seconds, continue in background.
    """
    # Authenticate API key
    api_key_obj = await authenticate_api_key(api_key, db)
    
    # Create submission record
    submission = Submission(
        owner_id=api_key_obj.owner_id,
        api_key_id=api_key_obj.id,
        text=submission_data.text,
        text_length=len(submission_data.text),
        custom_id=submission_data.custom_id,
        questionResult=submission_data.questionResult,
        domain=submission_data.domain,
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
        processing_result = await asyncio.wait_for(
            process_text(submission_data.text),
            timeout=3.0
        )
        
        # Processing completed within 3 seconds!
        submission.processing_result = processing_result
        submission.meets_requirements = processing_result.get("meets_requirements", False)
        
        if submission.meets_requirements:
            submission.update_status(ProcessingStatus.SUCCESS)
            message = "Success! Your submission has been processed."
        else:
            submission.update_status(ProcessingStatus.FAILED, "Text does not meet requirements")
            message = "Your submission was processed but doesn't meet our requirements."
        
        db.commit()
        db.refresh(submission)
        
        return SubmissionResponse(
            id=submission.id,
            status=submission.status,
            text_length=submission.text_length,
            meets_requirements=submission.meets_requirements,
            failure_reason=submission.failure_reason,
            created_at=submission.created_at,
            completed_processing_at=submission.completed_processing_at,
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
            status=submission.status,
            text_length=submission.text_length,
            meets_requirements=None,
            failure_reason=None,
            created_at=submission.created_at,
            completed_processing_at=None,
            message="Thank you for your submission! We're processing it now and will notify the website owner when complete."
        )
        
    except Exception as e:
        # Error occurred within 3 seconds - user is still there
        submission.update_status(ProcessingStatus.FAILED, f"Processing error: {str(e)}")
        db.commit()
        
        return SubmissionResponse(
            id=submission.id,
            status=submission.status,
            text_length=submission.text_length,
            meets_requirements=False,
            failure_reason=submission.failure_reason,
            created_at=submission.created_at,
            completed_processing_at=submission.completed_processing_at,
            message="Sorry, there was an error processing your submission. Please try again."
        )

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
    
    # Determine appropriate message based on status
    message_map = {
        ProcessingStatus.PENDING: "Submission is queued for processing",
        ProcessingStatus.PROCESSING: "Submission is currently being processed",
        ProcessingStatus.SUCCESS: "Submission processed successfully",
        ProcessingStatus.FAILED: f"Submission failed: {submission.failure_reason}",
        ProcessingStatus.TIMEOUT: "Submission is being processed in background"
    }
    
    return SubmissionResponse(
        id=submission.id,
        status=submission.status,
        text_length=submission.text_length,
        meets_requirements=submission.meets_requirements,
        failure_reason=submission.failure_reason,
        created_at=submission.created_at,
        completed_processing_at=submission.completed_processing_at,
        message=message_map.get(submission.status, "Status unknown")
    )

@app.get("/api/owners/{owner_id}/submissions")
async def list_owner_submissions(
    owner_id: int,
    skip: int = 0,
    limit: int = 50,
    status: str = None,
    db: Session = Depends(get_db)
):
    """List submissions for an owner (for admin/dashboard use)."""
    # Verify owner exists
    owner = db.query(Owner).filter(Owner.id == owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    
    # Build query
    query = db.query(Submission).filter(Submission.owner_id == owner_id)
    
    # Add status filter if provided
    if status:
        query = query.filter(Submission.status == status)
    
    # Get submissions with pagination
    submissions = query.order_by(Submission.created_at.desc()).offset(skip).limit(limit).all()
    
    # Return simplified list response
    return [
        {
            "id": sub.id,
            "status": sub.status,
            "text_preview": sub.text[:100] + "..." if len(sub.text) > 100 else sub.text,
            "text_length": sub.text_length,
            "meets_requirements": sub.meets_requirements,
            "domain": sub.domain,
            "created_at": sub.created_at
        }
        for sub in submissions
    ]

@app.get("/api/owners/{owner_id}/submissions/{submission_id}", response_model=SubmissionDetailResponse)
async def get_submission_detail(
    owner_id: int,
    submission_id: int, 
    db: Session = Depends(get_db)
):
    """Get detailed submission info for admin/dashboard use."""
    # Get submission and verify ownership
    submission = db.query(Submission).filter(
        Submission.id == submission_id,
        Submission.owner_id == owner_id
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    return SubmissionDetailResponse(
        id=submission.id,
        status=submission.status,
        text=submission.text,
        text_length=submission.text_length,
        meets_requirements=submission.meets_requirements,
        failure_reason=submission.failure_reason,
        processing_result=submission.processing_result,
        domain=submission.domain,
        created_at=submission.created_at,
        completed_processing_at=submission.completed_processing_at,
        message="Submission details retrieved successfully"
    )

@app.get("/api/owners/{owner_id}/submissions/stats")
async def get_submission_stats(owner_id: int, db: Session = Depends(get_db)):

    """Get submission statistics for a owner."""
    # Verify owner exists
    owner = db.query(Owner).filter(Owner.id == owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    
    # Get basic stats
    total = db.query(Submission).filter(Submission.owner_id == owner_id).count()
    successful = db.query(Submission).filter(
        Submission.owner_id == owner_id,
        Submission.status == ProcessingStatus.SUCCESS
    ).count()
    failed = db.query(Submission).filter(
        Submission.owner_id == owner_id,
        Submission.status == ProcessingStatus.FAILED
    ).count()
    pending = db.query(Submission).filter(
        Submission.owner_id == owner_id,
        Submission.status.in_([ProcessingStatus.PENDING, ProcessingStatus.PROCESSING, ProcessingStatus.TIMEOUT])
    ).count()
    
    return {
        "total_submissions": total,
        "successful_submissions": successful,
        "failed_submissions": failed,
        "pending_submissions": pending,
        "success_rate": round((successful / total * 100) if total > 0 else 0, 2)
    }
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)