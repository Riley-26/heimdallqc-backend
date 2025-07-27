import math
import secrets
from fastapi import FastAPI, Depends, HTTPException, Request, BackgroundTasks, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import asyncio
import time
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from passlib.context import CryptContext
from urllib.parse import urlparse
import requests
import os
import json

from .db.database import get_db
from .models.owner import Owner, Verified_site
from .models.api_key import ApiKey
from .models.submission import Submission, ProcessingStatus
from .schemas.owner import CancelPlan, ForgotPasswordRequest, OwnerCreate, OwnerLogin, OwnerResponse, ResetPasswordRequest, SiteResponse, UpdatePlan, UpdateSettings, UpdateTokens
from .schemas.api_key import ApiKeyCreate, ApiKeyResponse
from .schemas.submission import SubmissionCreate, SubmissionEdit, SubmissionResponse, SubmissionDetailResponse, SubmissionUpload

MARKUP_FACTOR = 15

# Create FastAPI application
app = FastAPI(
    title="Heimdall-hook API",
    description="API for Heimdall",
    version="0.1.0"
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health endpoints
@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Heimdall is running"}

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
	exc_str = f'{exc}'.replace('\n', ' ').replace('   ', ' ')
	logging.error(f"{request}: {exc_str}")
	content = {'status_code': 10422, 'message': exc_str, 'data': None}
	return JSONResponse(content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

@app.get("/site-status")
async def site_status():
    status_types = {
        "functioning": "green",
        "partial": "amber",
        "error": "red"
    }
    
    # DIAGNOSTICS CHECK
    
    status = {
        "e_package": status_types["functioning"],
        "i_package": status_types["functioning"],
        "verif_checker": status_types["functioning"],
        "watermarking": status_types["functioning"],
        "contact": status_types["functioning"],
    }
    
    return status

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

def send_reset_email(email: str, reset_token: str):
    return {
        "email": email,
        "reset_token": reset_token,
        "reset_link": f"http://localhost:3000/signin/reset-password?token={reset_token}"
    }

# ---------- PASSWORD HASHING ----------

import bcrypt

def hash_password(password: str) -> str:
    """Hash a password"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


# ---------- PROCESSING/HELPER FUNCTIONS ----------

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

# Text processing function
async def process_text(text: str, owner_pref: str) -> dict:
    """
    Process the submitted text and determine if it meets requirements.
    
    Args:
        text: The text to process
        
    Returns:
        Dict with processed results and validation status
    """
    
    # ANALYSIS
    ai_result = ai_analysis(text)
    plag_result = plag_analysis(text, owner_pref)
    
    return {
        "ai_result": ai_result,
        "plag_result": plag_result,
        "text": text
    }

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
            processing_result = await process_text(submission.orig_text, )
            
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


# ---------- ANALYSIS FUNCTIONS ----------

# -- AI ANALYSIS
def ai_analysis(text: str):
    winston_url = "https://api.gowinston.ai/v2/ai-content-detection"
    key = os.getenv("WINST_KEY")
    
    payload = {
        "text": text,
        "version": "latest",
        "sentences": True,
        "language": "auto"
    }
    
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    
    response = json.loads(requests.request("POST", winston_url, json=payload, headers=headers).text)

    if "status" not in response.keys():
        return {
            "status": 400,
            "score": "N/A",
            "tokens": 0
        }

    return {
        "status": response["status"],
        "score": round(100 - response["score"]),
        "tokens": response["credits_used"]
    }

# -- PLAGIARISM ANALYSIS
def plag_analysis(text: str, owner_pref: str = "auto_cite"):
    winston_url = "https://api.gowinston.ai/v2/plagiarism"
    key = os.getenv("WINST_KEY")
    
    payload = {
        "text": text
    }
    
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    
    response = json.loads(requests.request("POST", winston_url, json=payload, headers=headers).text)
    result = {}
    tokens = 0

    if "status" not in response.keys():
        return {
            "status": 400,
            "score": "N/A",
            "result": {},
            "tokens": 0
        }
        
    if response["status"] == 200 and response["result"]["score"] >= 80:
        if response["result"]["sourceCounts"] > 0:
            if owner_pref == "auto_cite":
                result = auto_cite(text, response["sources"])
            elif owner_pref == "ai_rewrite":
                result = ai_rewrite(text)
            elif owner_pref == "redact":
                result = redact_text(text, response["sources"])
                
            if "tokens" in result.keys():
                tokens += result["tokens"]
    
    return {
        "status": response["status"],
        "score": response["result"]["score"],
        "result": result if result else {},
        "tokens": response["credits_used"]
    }

# -- AUTO-CITATION
def auto_cite(text: str, sources: list):
    """
    Auto-cite multiple sources in the text, avoiding overlapping citations.
    Args:
        text: The original text.
        sources: List of source dicts, each with 'plagiarismFound', 'url', 'title'.
    Returns:
        Dict with 'cited_text' and a list of 'citations' used.
    """
    # Collect all citation ranges with source info
    ranges = []
    for source in sources:
        for found in source.get("plagiarismFound", []):
            ranges.append({
                "start": found["startIndex"],
                "end": found["endIndex"],
                "source": {"url": source["url"], "title": source["title"]}
            })

    # Sort by start index, then by longest match first
    ranges.sort(key=lambda x: (x["start"], -(x["end"] - x["start"])))

    # Merge overlapping/duplicate ranges, keeping the first source for each range
    merged = []
    last_end = -1
    for r in ranges:
        if r["start"] >= last_end:
            merged.append(r)
            last_end = r["end"]
        else:
            # Overlap: skip or adjust as needed (here, we skip)
            continue

    # Build the new text with citations
    cited_text = ""
    last_idx = 0
    citations = []
    for r in merged:
        cited_text += text[last_idx:r["start"]]
        cited_text += f'"{text[r["start"]:r["end"]]}"'
        citations.append(r["source"])
        last_idx = r["end"]
    cited_text += text[last_idx:]

    return {
        "modif_text": cited_text,
        "citations": citations
    }

# -- AI REWRITE
def ai_rewrite(text: str):
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("GPT_KEY"))

    response = client.responses.create(
        model="gpt-4.1-mini",
        instructions="",
        input=f"""
            Rewrite my original text:
            
            "{text}"
            
            Output only the text.
        """
    )

    print(response)

    return { 
        "modif_text": response.output_text,
        "tokens": 0
    }

# -- REDACTED
def redact_text(text: str, sources: list):
    """
    Redact multiple sources in the text, avoiding overlapping redactions.
    Args:
        text: The original text.
        sources: List of source dicts, each with 'plagiarismFound'.
    Returns:
        The redacted text.
    """
    # Collect all ranges to redact
    ranges = []
    for source in sources:
        for found in source.get("plagiarismFound", []):
            ranges.append({
                "start": found["startIndex"],
                "end": found["endIndex"]
            })

    # Sort by start index, then by longest match first
    ranges.sort(key=lambda x: (x["start"], -(x["end"] - x["start"])))

    # Merge overlapping/duplicate ranges
    merged = []
    last_end = -1
    for r in ranges:
        if r["start"] >= last_end:
            merged.append(r)
            last_end = r["end"]
        else:
            # Overlap: skip or adjust as needed (here, we skip)
            continue

    # Build the new text with redactions
    redacted_text = ""
    last_idx = 0
    for r in merged:
        redacted_text += text[last_idx:r["start"]]
        redacted_text += " [REDACTED] "
        last_idx = r["end"]
    redacted_text += text[last_idx:]

    return { "modif_text": redacted_text }

@app.get("/api/v1/verif-sites/{site_link}", response_model=SiteResponse) # PUBLIC
async def check_verified_site(
    site_link: str,
    db: Session = Depends(get_db)
):
    """
    Check if site is verified
    """
    verif_site = db.query(Verified_site).filter(Verified_site.domain == site_link).first()
    if not verif_site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    return SiteResponse(
        domain=verif_site.domain,
        id=verif_site.id,
        is_active=verif_site.is_active,
        total_requests=verif_site.total_requests,
        last_used_at=verif_site.last_used_at,
        created_at=verif_site.created_at
    )
    
# -- ANALYTICS


# ---------- OWNER ENDPOINTS ----------

# PUBLIC: ANYONE CAN ACCESS
# PRIVATE - KEY: NEEDS VALID API KEY TO ACCESS
# PRIVATE - LOGIN: OWNER NEEDS TO BE LOGGED IN TO ACCESS

@app.post("/api/v1/owners") # PUBLIC
async def create_owner(
    owner_data: OwnerCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new owner account.
    """
    # Check if owner already exists
    existing_owner = db.query(Owner).filter(Owner.email == owner_data.email).first()
    if existing_owner:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    verified_site = await create_verif_site(owner_data.domain, db)
    
    if verified_site:
        # Create new owner
        owner = Owner(
            domain_id=verified_site.id,
            email=owner_data.email,
            name=owner_data.name,
            domain=owner_data.domain,
            company=owner_data.company,
            password_hash=hash_password(owner_data.password)
        )
        
        db.add(owner)
        db.commit()
        db.refresh(owner)
    
    return {
        "owner_data": owner_data,
        "domain": owner_data.domain
    }

async def create_verif_site(domain, db):
    """
    Create a verified site
    """
    verif_site = Verified_site(
        domain=domain
    )
    
    db.add(verif_site)
    db.commit()
    db.refresh(verif_site)
    
    return verif_site

@app.get("/api/v1/owners/{owner_id}", response_model=OwnerResponse) # PRIVATE - LOGIN
async def get_owner(
    owner_id: int,
    db: Session = Depends(get_db)
):
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
        created_at=owner.created_at,
        watermarks_made=owner.watermarks_made,
        plagiarisms_prevented=owner.plagiarisms_prevented,
        current_tokens=owner.current_tokens,
        plan=owner.plan,
        function_pref=owner.function_pref,
        ui_pref=owner.ui_pref,
        ai_threshold_option=owner.ai_threshold_option,
        tokens_used=owner.tokens_used,
        verified_at=owner.verified_at,
        verified_month_end=owner.verified_month_end
    )

# -- DEACTIVATE/DELETE OWNER

# -- GET PLAN USAGE

# -- UPGRADE/CHANGE PLAN
@app.post("/api/v1/owners/update-plan")
async def update_plan(
    request: UpdatePlan,
    db: Session = Depends(get_db)
):
    owner = db.query(Owner).filter(Owner.id == request.id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    
    new_plan = owner.change_plan(request.plan_name)
    owner.plan = new_plan["plan"]
    owner.current_tokens = new_plan["tokens"]
    
    owner.is_verified = True
    owner.verify_owner()
    
    db.commit()
    
    return {
        "status": "Updated plan successfully"
    }
    
# -- CANCEL PLAN
@app.post("/api/v1/owners/cancel-plan")
async def cancel_plan(
    request: CancelPlan,
    db: Session = Depends(get_db)
):
    from .models.owner import plans_dict
    
    owner = db.query(Owner).filter(Owner.id == request.id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    
    owner.plan = plans_dict["None"]
    owner.is_verified = False
    
    db.commit()
    
    return {
        "status": "Cancelled plan successfully"
    }

@app.post("/api/v1/owners/buy-tokens")
async def buy_tokens(
    request: UpdateTokens,
    db: Session = Depends(get_db)
):
    owner = db.query(Owner).filter(Owner.id == request.id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    
    added_tokens = owner.add_tokens(request.pack_name)
    if added_tokens != None:
        owner.current_tokens = added_tokens["tokens"]
    else:
        raise HTTPException(status_code=404, detail="Failed to add tokens")
    
    db.commit()
    
    return {
        "status": "Tokens successfully bought"
    }

@app.post("/api/v1/owners/update-settings")
async def update_settings(
    request: UpdateSettings,
    db: Session = Depends(get_db)
):

    owner = db.query(Owner).filter(Owner.id == request.id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    
    owner.function_pref = request.function_pref
    owner.ui_pref = request.ui_pref
    owner.ai_threshold_option = request.ai_threshold_option
    
    db.commit()
    
    return {
        "status": "Updated preferences successfully"
    }

@app.post("/api/v1/forgot-password") # PUBLIC
async def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Initiate password reset process by sending reset token to owner's email
    """
    owner = db.query(Owner).filter(Owner.email == request.email).first()

    if not owner:
        return {"message": "If an account with that email exists, a reset link has been sent."}
    
    reset_token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(hours=1)
    
    owner.reset_token = reset_token
    owner.token_expiration = expires_at
    db.commit()
    
    print(send_reset_email(request.email, reset_token))
    
    return {"message": "If an account with that email exists, a reset link has been sent."}

@app.post("/api/v1/reset-password") # PRIVATE - TOKEN
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Reset password using the provided token
    """
    owner = db.query(Owner).filter(Owner.email == request.email).first()
    reset_token = owner.reset_token == request.token
    
    if not reset_token or datetime.now(timezone.utc) > owner.token_expiration:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    new_pword_hash = hash_password(request.new_password)
    owner.password_hash = new_pword_hash
    
    owner.reset_token = None
    owner.token_expiration = None
    db.commit()
    
    return {
        "detail": "Successfully reset password"
    }


# ---------- API KEY ENDPOINTS ----------

@app.post("/api/v1/owners/{owner_id}/api-keys", response_model=ApiKeyResponse) # PRIVATE - LOGIN
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

@app.get("/api/v1/owners/{owner_id}/api-key") # PRIVATE - LOGIN
async def list_api_key(
    owner_id: int,
    db: Session = Depends(get_db)
):
    """
    List all API keys for an owner (with masked keys).
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

@app.delete("/api/v1/api-keys/{api_key_id}/delete-key") # PRIVATE - LOGIN
async def deactivate_api_key(
    api_key_id: int,
    db: Session = Depends(get_db)
):
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

@app.post("/api/v1/submissions", response_model=SubmissionResponse) # PRIVATE - KEY
async def create_submission(
    submission_data: SubmissionCreate,
    request: Request,
    api_key: str = Depends(get_api_key_from_header),
    db: Session = Depends(get_db)
):
    """
    Create a new submission and process it.
    """
    # Authenticate API key
    api_key_obj = await authenticate_api_key(api_key, db)
    
    owner = db.query(Owner).filter( Owner.id == api_key_obj.owner_id ).first()
    for i in owner.function_pref.keys():
        if owner.function_pref[i] == True:
            checked_pref = i
    
    # Create submission record
    submission = Submission(
        owner_id=api_key_obj.owner_id,
        api_key_id=api_key_obj.id,
        orig_text=submission_data.orig_text,
        orig_text_length=len(submission_data.orig_text),
        edit_text=submission_data.edit_text,
        edit_text_length=len(submission_data.edit_text) if submission_data.edit_text else 0,
        custom_id=submission_data.custom_id,
        question_result=submission_data.question_result,
        domain=submission_data.domain,
        page_link=submission_data.page_link,
        status=ProcessingStatus.PENDING,
        manual_upload=False,
        action_needed=submission_data.action_needed,
        edited=submission_data.edited,
        function_pref=checked_pref,
        temp_text=submission_data.temp_text
    )
    
    db.add(submission)
    db.commit()
    db.refresh(submission)
    
    try:
        # Update status to processing
        submission.update_status(ProcessingStatus.PROCESSING)
        db.commit()
        
        processing_result = await process_text(submission_data.orig_text, checked_pref)
        ai_res = processing_result["ai_result"]
        plag_res = processing_result["plag_result"]
        res_tokens = 0
        
        if "tokens" in ai_res.keys():
            res_tokens += math.ceil(ai_res["tokens"] / MARKUP_FACTOR)
        if "tokens" in plag_res.keys():
            res_tokens += math.ceil(plag_res["tokens"] / MARKUP_FACTOR)
        
        submission.ai_result = ai_res
        submission.plag_result = plag_res
        submission.meets_requirements = ai_res["status"] == 200 or plag_res["status"] == 200
        
        submission.tokens_used = submission.tokens_used + res_tokens
        owner.current_tokens = owner.current_tokens - res_tokens
        owner.tokens_used = owner.tokens_used + res_tokens
        
        if submission.meets_requirements:
            if "modif_text" in plag_res["result"].keys():
                submission.temp_text = plag_res["result"]["modif_text"]
                
            submission.update_status(ProcessingStatus.SUCCESS)
            message = "Success! Your submission has been processed."
        else:
            submission.update_status(ProcessingStatus.FAILED, "Text failed to process")
            message = "Your submission has failed to process."
            
        if plag_res["score"] != "N/A" and plag_res["score"] >= 60:
            submission.update_action(True)
        else:    
            if ai_res["score"] != "N/A" and ai_res["score"] < owner.ai_threshold_option:
                submission.update_status(ProcessingStatus.FAILED, "AI score below threshold")
                db.commit()
                db.refresh(submission)
                return SubmissionResponse(
                    owner_id=submission.owner_id,
                    id=submission.id,
                    status=submission.status,
                    orig_text_length=submission.orig_text_length,
                    meets_requirements=False,
                    action_needed=submission.action_needed,
                    failure_reason=submission.failure_reason,
                    created_at=submission.created_at,
                    completed_processing_at=submission.completed_processing_at,
                    message="AI score below threshold",
                    manual_upload=submission.manual_upload,
                    tokens_used=submission.tokens_used
                )
        
        db.commit()
        db.refresh(submission)
        
        return SubmissionResponse(
            owner_id=submission.owner_id,
            id=submission.id,
            status=submission.status,
            orig_text_length=submission.orig_text_length,
            meets_requirements=submission.meets_requirements,
            action_needed=submission.action_needed,
            failure_reason=submission.failure_reason,
            created_at=submission.created_at,
            completed_processing_at=submission.completed_processing_at,
            message=message,
            manual_upload=submission.manual_upload,
            tokens_used=submission.tokens_used
        )
    except Exception as e:
        submission.update_status(ProcessingStatus.FAILED, f"Processing error: {str(e)}")
        db.commit()
        
        return SubmissionResponse(
            owner_id=submission.owner_id,
            id=submission.id,
            status=submission.status,
            orig_text_length=submission.orig_text_length,
            meets_requirements=False,
            action_needed=submission.action_needed,
            failure_reason=submission.failure_reason,
            created_at=submission.created_at,
            completed_processing_at=submission.completed_processing_at,
            message="Sorry, there was an error processing your submission. Please try again.",
            manual_upload=submission.manual_upload,
            tokens_used=submission.tokens_used
        )

@app.post("/api/v1/upload-submission", response_model=SubmissionResponse) # PRIVATE - LOGIN
async def upload_submission(
    submission_data: SubmissionUpload,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Create submission via upload
    """
    key = db.query(ApiKey).filter(
        ApiKey.owner_id == submission_data.owner_id,
        ApiKey.id == submission_data.key_id,
        ApiKey.is_active == True
    ).first()
    if not key:
        raise HTTPException(status_code=404, detail="No key available")
    
    owner = db.query(Owner).filter( Owner.id == submission_data.owner_id ).first()
    for i in owner.function_pref.keys():
        if owner.function_pref[i] == True:
            checked_pref = i

    # Create submission record
    submission = Submission(
        owner_id=submission_data.owner_id,
        api_key_id=key.id,
        orig_text=submission_data.orig_text,
        orig_text_length=len(submission_data.orig_text),
        edit_text=submission_data.edit_text,
        edit_text_length=len(submission_data.edit_text) if submission_data.edit_text else 0,
        custom_id=submission_data.custom_id,
        question_result=submission_data.question_result,
        domain=submission_data.domain,
        status=ProcessingStatus.PENDING,
        manual_upload=True,
        action_needed=submission_data.action_needed,
        edited=submission_data.edited,
        function_pref=checked_pref,
        temp_text=submission_data.temp_text
    )
    
    db.add(submission)
    db.commit()
    db.refresh(submission)
    
    try:
        # Update status to processing
        submission.update_status(ProcessingStatus.PROCESSING)
        db.commit()
        
        processing_result = await process_text(submission_data.orig_text, checked_pref)
        ai_res = processing_result["ai_result"]
        plag_res = processing_result["plag_result"]
        res_tokens = 0
        
        if "tokens" in ai_res.keys():
            res_tokens += math.ceil(ai_res["tokens"] / MARKUP_FACTOR)
        if "tokens" in plag_res.keys():
            res_tokens += math.ceil(plag_res["tokens"] / MARKUP_FACTOR)
        
        submission.ai_result = ai_res
        submission.plag_result = plag_res
        submission.meets_requirements = ai_res["status"] == 200 and plag_res["status"] == 200
        
        submission.tokens_used = submission.tokens_used + res_tokens
        owner.current_tokens = owner.current_tokens - res_tokens
        owner.tokens_used = owner.tokens_used + res_tokens
        
        if submission.meets_requirements:
            submission.temp_text = plag_res["result"]["modif_text"]
                
            submission.update_status(ProcessingStatus.SUCCESS)
            message = "Success! Your submission has been processed."
            
        else:
            submission.update_status(ProcessingStatus.FAILED, "Text failed to process")
            message = "Your submission has failed to process."
            
        if plag_res["score"] != "N/A" and plag_res["score"] >= 60:
            submission.update_action(True)
        else:    
            if ai_res["score"] != "N/A" and ai_res["score"] < owner.ai_threshold_option:
                submission.update_status(ProcessingStatus.FAILED, "AI score below threshold")
                db.commit()
                return SubmissionResponse(
                    owner_id=submission.owner_id,
                    id=submission.id,
                    status=submission.status,
                    orig_text_length=submission.orig_text_length,
                    meets_requirements=False,
                    action_needed=submission.action_needed,
                    failure_reason=submission.failure_reason,
                    created_at=submission.created_at,
                    completed_processing_at=submission.completed_processing_at,
                    message="AI score below threshold",
                    manual_upload=submission.manual_upload,
                    tokens_used=submission.tokens_used
                )
        
        db.commit()
        db.refresh(submission)
        
        return SubmissionResponse(
            owner_id=submission_data.owner_id,
            id=submission.id,
            status=submission.status,
            orig_text_length=submission.orig_text_length,
            meets_requirements=submission.meets_requirements,
            action_needed=submission.action_needed,
            failure_reason=submission.failure_reason,
            created_at=submission.created_at,
            completed_processing_at=submission.completed_processing_at,
            message=message,
            manual_upload=submission.manual_upload,
            tokens_used=submission.tokens_used
        )
    except Exception as e:
        submission.update_status(ProcessingStatus.FAILED, f"Processing error: {str(e)}")
        db.commit()
        
        return SubmissionResponse(
            owner_id=submission_data.owner_id,
            id=submission.id,
            status=submission.status,
            orig_text_length=submission.orig_text_length,
            meets_requirements=False,
            action_needed=submission.action_needed,
            failure_reason=submission.failure_reason,
            created_at=submission.created_at,
            completed_processing_at=submission.completed_processing_at,
            message="Sorry, there was an error processing your submission. Please try again.",
            manual_upload=submission.manual_upload,
            tokens_used=submission.tokens_used
        )

@app.get("/api/v1/owners/{owner_id}/submissions") # PRIVATE - LOGIN
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
    
    # Return list response
    return [
        {
            "id": sub.id,
            "status": sub.status,
            "ai_result": sub.ai_result,
            "plag_result": sub.plag_result,
            "orig_text_preview": sub.orig_text[:80] + "..." if len(sub.orig_text) > 80 else sub.orig_text,
            "orig_text": sub.orig_text,
            "orig_text_length": sub.orig_text_length,
            "edit_text_preview": sub.edit_text[:80] + "..." if sub.edit_text and len(sub.edit_text) > 80 else sub.edit_text,
            "edit_text": sub.edit_text,
            "edit_text_length": sub.edit_text_length,
            "meets_requirements": sub.meets_requirements,
            "manual_upload": sub.manual_upload,
            "action_needed": sub.action_needed,
            "domain": sub.domain,
            "page_link": sub.page_link,
            "created_at": sub.created_at,
            "edited": sub.edited,
            "edited_at": sub.edited_at,
            "function_pref": sub.function_pref,
            "temp_text": sub.temp_text
        }
        for sub in submissions
    ]

@app.get("/api/v1/owners/{owner_id}/submissions/{submission_id}", response_model=SubmissionDetailResponse) # PRIVATE - LOGIN
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
        owner_id=submission.owner_id,
        id=submission.id,
        status=submission.status,
        orig_text=submission.orig_text,
        orig_text_length=submission.orig_text_length,
        edit_text=submission.edit_text,
        edit_text_length=submission.edit_text_length,
        meets_requirements=submission.meets_requirements,
        action_needed=submission.action_needed,
        failure_reason=submission.failure_reason,
        domain=submission.domain,
        created_at=submission.created_at,
        completed_processing_at=submission.completed_processing_at,
        manual_upload=submission.manual_upload,
        edited=submission.edited,
        ai_result=submission.ai_result,
        plag_result=submission.plag_result,
        function_pref=submission.function_pref,
        temp_text=submission.temp_text,
        message="Submission details retrieved successfully"
    )

@app.get("/api/v1/owners/{owner_id}/submissions/stats") # PRIVATE - LOGIN
async def get_submission_stats(
    owner_id: int,
    db: Session = Depends(get_db)
):

    """Get submission statistics for an owner."""
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
    
@app.get("/api/v1/submissions/{submission_id}", response_model=SubmissionResponse) # PRIVATE - LOGIN
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
        orig_text_length=submission.orig_text_length,
        edit_text_length=submission.edit_text_length,
        meets_requirements=submission.meets_requirements,
        failure_reason=submission.failure_reason,
        created_at=submission.created_at,
        completed_processing_at=submission.completed_processing_at,
        message=message_map.get(submission.status, "Status unknown")
    )
    
@app.delete("/api/v1/owners/{owner_id}/submissions/{submission_id}/delete-submission")
async def delete_submission(
    submission_id: int,
    owner_id: int,
    db: Session = Depends(get_db)
):
    submission = db.query(Submission).filter(
        Submission.id == submission_id,
        Submission.owner_id == owner_id
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    db.delete(submission)
    db.commit()
    
    return {
        "message": "Successfully deleted submission"
    }

@app.post("/api/v1/owners/{owner_id}/submissions/{submission_id}/edit-submission")
async def edit_submission(
    submission_data: SubmissionEdit,
    db: Session = Depends(get_db)
):
    submission = db.query(Submission).filter(
        Submission.id == submission_data.id,
        Submission.owner_id == submission_data.owner_id
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    submission.edit_text = submission_data.new_text
    submission.edit_text_length = len(submission_data.new_text)
    submission.edited = True
    submission.edited_at = datetime.now()
    
    db.commit()
    
    return {
        "message": "Submission edited successfully"
    }

# -- CREATE WATERMARK
@app.post("/api/v1/watermarks")
async def create_watermark(
    submission_data: SubmissionCreate,
    request: Request,
    api_key: str = Depends(get_api_key_from_header),
    db: Session = Depends(get_db)
):
    pass

# -- GET WATERMARKS

# -- DELETE WATERMARK


# ---------- LOG IN ENDPOINTS ----------

# LOG IN
@app.post("/api/v1/auth/login")
async def login(
    login_data: OwnerLogin,
    db: Session = Depends(get_db)
):
    """Email and password (2FA??)"""
    owner = db.query(Owner).filter(Owner.email == login_data.email).first()
    if not owner or not verify_password(login_data.password, owner.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    return {
        "email": login_data.email,
        "name": owner.name,
        "id": owner.id
    }
    
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)