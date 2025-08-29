import math
import secrets
from typing import List, Optional, Union
import uuid
from fastapi import FastAPI, Depends, HTTPException, Request, BackgroundTasks, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import func
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
import stripe

from .db.database import get_db
from .models.owner import Owner
from .models.verified_site import VerifiedSite
from .models.api_key import ApiKey
from .models.submission import Submission, ProcessingStatus
from .models.watermark import Watermark
from .models.payment import Payment
from .models.event import Event
from .schemas.owner import LoginRequest, OwnerJwt, PlanCancel, Token, PasswordReset, PasswordUpdate, OwnerCreate, OwnerUpdate, SettingsUpdate, PlanUpdate, TokenPurchase, OwnerResponse, OwnerDetailResponse
from .schemas.verified_site import SiteSimpleResponse, SiteDetailResponse
from .schemas.api_key import ApiKeyCreate, ApiKeyListResponse, ApiKeyReveal
from .schemas.submission import SubmissionAuto, SubmissionEdit, SubmissionHookResponse, SubmissionManual, SubmissionResponse, SubmissionDetailResponse
from .schemas.watermark import WatermarkCreate
from .schemas.payment import PaymentCreate, PaymentListResponse, PaymentMethodDelete, PaymentMethodListResponse, PaymentResponse, SubscriptionCancel, SubscriptionUpdate

# !!!! DO NOT TOUCH
MARKUP_FACTOR = 15
# !!!!

stripe.api_key = os.getenv("STRIPE_KEY")

# Create FastAPI application
app = FastAPI(
    title="Heimdall-hook API",
    description="API for Heimdall",
    version="0.1.0"
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://heimdallqc.com",
        "https://checkout.stripe.com"
    ],
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

@app.get("/api/v1/site-status")
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

async def get_current_owner(
    db: Session,
    owner_id: int = None,
    customer_id: str = None
):
    """Returns owner based on either owner_id or owner's customer_id. One must be provided."""
    if not owner_id and not customer_id:
        raise HTTPException(status_code=400, detail="Either owner_id or customer_id must be provided")
    if owner_id:
        owner = db.query(Owner).filter(Owner.id == owner_id).first()
        if not owner:
            raise HTTPException(status_code=404, detail="Owner not found")
    else:
        owner = db.query(Owner).filter(Owner.customer_id == customer_id).first()
        if not owner:
            raise HTTPException(status_code=404, detail="Owner not found")
    return owner

async def get_payment(
    db: Session,
    unique_id: str,
    owner_id: int = None,
    subscription_id: str = None
):
    """Returns payment item identified using subscription_id"""
    if not owner_id and not subscription_id:
        raise HTTPException(status_code=400, detail="Either owner_id or subscription_id must be provided")
    if owner_id:
        payment = db.query(Payment).filter(
            Payment.owner_id == owner_id,
            Payment.unique_id == unique_id
        ).first()
        if not payment:
            raise HTTPException(status_code=400, detail="Payment item not found")
    else:
        payment = db.query(Payment).filter(Payment.subscription_id == subscription_id).first()
        if not payment:
            raise HTTPException(status_code=400, detail="Payment item not found")
    return payment


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
    
# -- ANALYTICS


# ---------- OWNER ENDPOINTS ----------

# PUBLIC: ANYONE CAN ACCESS
# PRIVATE - KEY: NEEDS VALID API KEY TO ACCESS
# PRIVATE - LOGIN: OWNER NEEDS TO BE LOGGED IN TO ACCESS
# PRIVATE - JWT: ACCESSED VIA JWT

@app.post("/api/v1/owners") # PUBLIC
async def create_owner(
    owner_data: OwnerCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new owner account.
    """
    existing_owner = db.query(Owner).filter(Owner.email == owner_data.email).first()
    if existing_owner:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    verified_site = await create_verif_site(owner_data.domain, db)
    if not verified_site:
        raise HTTPException(status_code=404, detail="Cannot verify site")
    
    # Create new owner
    owner = Owner(
        email=owner_data.email,
        domain=owner_data.domain,
        password_hash=hash_password(owner_data.password),
        name=owner_data.name,
        company=owner_data.company,
        domain_id=verified_site.id
    )
    
    db.add(owner)
    db.commit()
    db.refresh(owner)
    
    return

@app.post("/api/v1/owners/is-valid") # PRIVATE - JWT
async def confirm_jwt(
    token: OwnerJwt,
    db: Session = Depends(get_db)
):
    """
    Confirm JWT validity
    """
    owner = db.query(Owner).filter(
        Owner.id == token.id,
        Owner.email == token.email
    ).first()
    if not owner:
        raise HTTPException(status_code=404, detail="JWT invalid")
    
    return True

@app.post("/api/v1/owners/{owner_id}", response_model=OwnerResponse) # PRIVATE - LOGIN
async def get_owner(
    owner_id: int,
    db: Session = Depends(get_db)
):
    """
    Get owner by ID.
    """
    owner = await get_current_owner(db, owner_id=owner_id)
    
    return OwnerResponse(
        id=owner.id,
        email=owner.email,
        name=owner.name,
        domain=owner.domain,
        company=owner.company,
        is_active=owner.is_active,
        is_verified=owner.is_verified,
        current_tokens=owner.current_tokens,
        tokens_used=owner.tokens_used,
        watermarks_made=owner.watermarks_made,
        plagiarisms_prevented=owner.plagiarisms_prevented,
        entries_needing_action=owner.entries_needing_action
    )
    
@app.post("/api/v1/owners/{owner_id}/detailed", response_model=OwnerDetailResponse) # PRIVATE - LOGIN
async def get_owner_details(
    owner_id: int,
    db: Session = Depends(get_db)
):
    """
    Get owner by ID.
    """
    owner = await get_current_owner(db, owner_id=owner_id)
    
    return OwnerDetailResponse(
        id=owner.id,
        email=owner.email,
        name=owner.name,
        domain=owner.domain,
        company=owner.company,
        is_active=owner.is_active,
        is_verified=owner.is_verified,
        current_tokens=owner.current_tokens,
        tokens_used=owner.tokens_used,
        watermarks_made=owner.watermarks_made,
        plagiarisms_prevented=owner.plagiarisms_prevented,
        entries_needing_action=owner.entries_needing_action,
        domain_id=owner.domain_id,
        verified_month_end=owner.verified_month_end,
        plan=owner.plan,
        function_pref=owner.function_pref,
        ui_pref=owner.ui_pref,
        ai_threshold_option=owner.ai_threshold_option,
        created_at=owner.created_at,
        updated_at=owner.updated_at,
        verified_at=owner.verified_at,
        customer_id=owner.customer_id,
        subscription_id=owner.subscription_id,
        session_ids=owner.session_ids
    )

# -- DEACTIVATE/DELETE OWNER

# -- GET PLAN USAGE

@app.post("/api/v1/owners/{owner_id}/invoices", response_model=Union[List[PaymentListResponse], None])
async def get_owner_invoices(
    owner_id: int,
    db: Session = Depends(get_db)
):
    """Return list of owner's invoices for display"""
    try:
        owner = await get_current_owner(db, owner_id=owner_id)
        if not owner.customer_id:
            return None

        # Subscriptions
        invoices = stripe.Invoice.list(
            customer=owner.customer_id
        )
        
        invoice_list = [
            PaymentListResponse(
                amount=invoice.total,
                status=invoice.status,
                created_at=invoice.created,
                pdf_link=invoice.invoice_pdf
            )
            for invoice in invoices.data if invoice.status == "paid"
        ]
        
        return invoice_list
    
    except stripe.error.StripeError:
        raise HTTPException(
            status_code=400,
            detail="Failed to retrieve invoices"
        )
    
@app.patch("/api/v1/owners/update-plan")
async def change_plan(
    request: SubscriptionUpdate,
    db: Session = Depends(get_db),
):
    """Upgrade/Downgrade owner's plan, calculate proration accordingly"""
    try:
        owner = await get_current_owner(db, owner_id=request.owner_id)
        
        subscription = stripe.Subscription.retrieve(owner.subscription_id)
        
        if subscription.customer != owner.customer_id:
            raise HTTPException(
                status_code=403,
                detail="Unauthorised attempt"
            )
        
        # Update subscription item first
        updated_subscription = stripe.Subscription.modify(
            owner.subscription_id,
            items=[{
                'id': subscription['items']['data'][0]['id'],
                'price': request.new_plan_id
            }],
            proration_behavior='create_prorations' if request.prorate else 'none'
        )
        if not updated_subscription:
            raise HTTPException(
                status_code=400,
                detail="Failed to update subscription"
            )
    except stripe.error.StripeError:
        raise HTTPException(
            status_code=400,
            detail="Failed to change subscription"
        )
    else:
        # Then update in database if no errors
        owner.change_plan(request.new_plan_id)
        owner.verify_owner(cancelled=False)
        db.commit()
        return
        
@app.put("/api/v1/owners/cancel-plan")
async def cancel_plan(
    request: SubscriptionCancel,
    db: Session = Depends(get_db)
):  
    """Cancel owners subscription, providing a refund of the unused amount. Must have an active subscription."""
    try:
        owner = await get_current_owner(db, owner_id=request.owner_id)
        
        subscription = stripe.Subscription.retrieve(owner.subscription_id)
        
        if subscription.customer != owner.customer_id:
            raise HTTPException(
                status_code=403,
                detail="Unauthorised attempt"
            )
        
        # -- PRORATE REFUND - FOR FUTURE USE
        
        """
        if request.is_immediate_cancel:
            # Create refund for prorated amount
            cancelled_sub = stripe.Subscription.cancel(
                owner.subscription_id
            )
            
            latest_invoice = stripe.Invoice.list(
                customer=owner.customer_id,
                subscription=owner.subscription_id,
                limit=1
            ).data[0]
            
            if latest_invoice.status == "paid":
                # Calculate prorated amount
                now = datetime.now().timestamp()
                period_start = subscription["items"].data[0].current_period_start
                period_end = subscription["items"].data[0].current_period_end
                
                if now < period_end:
                    processing_fee = 0.95
                    unused_time = period_end - now
                    total_time = period_end - period_start
                    refund_ratio = unused_time / total_time
                    refund_amount = int(latest_invoice.amount_paid * refund_ratio * processing_fee)
                    
                    payment = await get_payment(db=db, owner_id=owner.id, subscription_id=owner.subscription_id)
                    
                    # Create refund
                    stripe.Refund.create(
                        payment_intent=payment.payment_intent_id,
                        amount=refund_amount,
                        reason="requested_by_customer"
                    )
            
            message = "Subscription cancelled immediately"
        """
        
        # --
        
        # Cancel at period end
        stripe.Subscription.modify(
            owner.subscription_id,
            cancel_at_period_end=True
        )
        message = "Subscription will cancel at the end of the current plan"
        
        return {
            "message": message
        }
    
    except stripe.error.StripeError as e:
        print(e)
        raise HTTPException(
            status_code=400,
            detail="Failed to cancel subscription"
        )
    
@app.patch("/api/v1/owners/update-settings")
async def update_settings(
    request: SettingsUpdate,
    db: Session = Depends(get_db)
):

    owner = db.query(Owner).filter(Owner.id == request.owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    
    owner.function_pref = request.function_pref
    owner.ui_pref = request.ui_pref
    owner.ai_threshold_option = request.ai_threshold_option
    
    db.commit()
    
    return {
        "status": "Updated preferences successfully"
    }

@app.patch("/api/v1/forgot-password") # PUBLIC
async def forgot_password(
    request: PasswordReset,
    db: Session = Depends(get_db)
):
    """
    Initiate password reset process by sending reset token to owner's email
    """
    message = "If an account with that email exists, a reset link has been sent."
    
    owner = db.query(Owner).filter(Owner.email == request.email).first()
    if not owner:
        return {
            "message": message
        }
    
    reset_token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(hours=1)
    
    owner.reset_token = reset_token
    owner.token_expiration = expires_at
    db.commit()
    
    print(send_reset_email(request.email, reset_token))
    
    return {
        "message": message
    }

@app.patch("/api/v1/reset-password") # PRIVATE - TOKEN
async def reset_password(
    request: PasswordUpdate,
    db: Session = Depends(get_db)
):
    """
    Reset password using the provided token
    """
    owner = db.query(Owner).filter(Owner.email == request.email).first()
    valid_reset_token = owner.reset_token == request.token
    
    if not valid_reset_token or datetime.now(timezone.utc) > owner.token_expiration:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    new_pword_hash = hash_password(request.new_password)
    owner.password_hash = new_pword_hash
    
    owner.reset_token = None
    owner.token_expiration = None
    db.commit()
    
    return

@app.post("/api/v1/owners/{owner_id}/payment-methods", response_model=Union[List[PaymentMethodListResponse], None])
async def get_payment_methods(
    owner_id: int,
    db: Session = Depends(get_db)
):
    """Returns list of owner's payment methods"""
    try:
        owner = await get_current_owner(db, owner_id=owner_id)
        if not owner.customer_id:
            return None
        
        # Retrieve owner's payment methods from Stripe
        payment_methods = stripe.PaymentMethod.list(
            customer=owner.customer_id,
            type='card'
        )

        return [
            PaymentMethodListResponse(
                payment_method_id=pm.id,
                payment_method_type=pm.type,
                card=pm.card if pm.type == "card" else None,
                created_at=pm.created
            )
            for pm in payment_methods.data
        ]
    except stripe.error.StripeError:
        raise HTTPException(
            status_code=400,
            detail="Failed to retrieve payment methods"
        )
        
@app.delete("/api/v1/owners/{owner_id}/delete-payment-method", response_model=dict)
async def delete_payment_method(
    request: PaymentMethodDelete,
    db: Session = Depends(get_db)
):
    """Delete a saved payment method"""
    try:
        owner = await get_current_owner(db, request.owner_id)
        
        payment_method = stripe.PaymentMethod.retrieve(
            request.payment_method_id
        )
        
        if payment_method.customer != owner.customer_id:
            raise HTTPException(
                status_code=403,
                detail="Unauthorised attempt"
            )
            
        # Delete payment method
        stripe.PaymentMethod.detach(
            request.payment_method_id
        )
        
        return {
            "success": True,
            "message": "Payment method deleted successfully"
        }
    except stripe.error.StripeError:
        raise HTTPException(
            status_code=400,
            detail="Failed to delete payment method"
        )
        

# ---------- SITE ENDPOINTS ----------

@app.get("/api/v1/verif-sites/{site_link}", response_model=SiteSimpleResponse) # PUBLIC
async def check_verified_site(
    site_link: str,
    db: Session = Depends(get_db)
):
    """
    Check if site is verified
    """
    verif_site = db.query(VerifiedSite).filter(VerifiedSite.domain == site_link).first()
    if not verif_site:
        raise HTTPException(status_code=404, detail="Site not found")
    
    return SiteSimpleResponse(
        domain=verif_site.domain,
        id=verif_site.id,
        is_active=verif_site.is_active
    )

async def create_verif_site(domain, db):
    """
    Create a verified site
    """
    
    # ----- CHECK SITE VALIDITY -----
    
    verif_site = VerifiedSite(
        domain=domain
    )
    
    db.add(verif_site)
    db.commit()
    db.refresh(verif_site)
    
    return verif_site

# ---------- API KEY ENDPOINTS ----------

@app.post("/api/v1/owners/api-keys", response_model=ApiKeyReveal) # PRIVATE - LOGIN
async def create_api_key(
    api_key_data: ApiKeyCreate, 
    db: Session = Depends(get_db)
):
    """
    Generate a new API key for an owner.
    """
    # Check if owner exists
    owner = db.query(Owner).filter(Owner.id == api_key_data.owner_id).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    
    # Generate new API key
    api_key = ApiKey(
        owner_id=api_key_data.owner_id,
        name=api_key_data.name,
        key=ApiKey.generate_key()
    )
    
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    return ApiKeyReveal(
        id=api_key.id,
        owner_id=api_key.owner_id,
        name=api_key.name,
        is_active=True,
        key=api_key.key
    )

@app.get("/api/v1/owners/{owner_id}/api-keys", response_model=List[ApiKeyListResponse]) # PRIVATE - LOGIN
async def get_api_keys(
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
    
    api_keys = db.query(ApiKey).filter(
        ApiKey.owner_id == owner_id,
        ApiKey.is_active == True
    ).all()
    
    # Return masked keys for security
    return [
        ApiKeyListResponse(
            id=api_key.id,
            name=api_key.name,
            masked_key=api_key.masked_key,
            is_active=api_key.is_active,
        )
        for api_key in api_keys if api_keys
    ]

@app.patch("/api/v1/owners/{owner_id}/api-keys/{api_key_id}/deactivate-key") # PRIVATE - LOGIN
async def deactivate_api_key(
    owner_id: int,
    api_key_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete (deactivate) an API key.
    """
    api_key = db.query(ApiKey).filter(
        ApiKey.id == api_key_id,
        ApiKey.owner_id == owner_id,
        ApiKey.is_active == True
    ).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    # Instead of deleting, deactivate for audit trail
    api_key.is_active = False
    db.commit()
    
    return


# ---------- SUBMISSION ENDPOINTS ----------

@app.post("/api/v1/submissions", response_model=Union[SubmissionResponse, SubmissionHookResponse]) # PRIVATE - KEY
async def create_submission(
    submission_data: SubmissionAuto,
    api_key: str = Depends(get_api_key_from_header),
    db: Session = Depends(get_db)
):
    """
    Create a new submission and process it.
    """
    # Authenticate API key
    api_key_obj = await authenticate_api_key(api_key, db)
    
    owner = db.query(Owner).filter( Owner.id == api_key_obj.owner_id ).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    for i in owner.function_pref.keys():
        if owner.function_pref[i] == True:
            checked_pref = i
            break
    
    # Create submission record
    submission = Submission(
        owner_id=owner.id,
        api_key_id=api_key_obj.id,
        orig_text=submission_data.orig_text,
        orig_text_length=len(submission_data.orig_text),
        question_result=submission_data.question_result,
        manual_upload=submission_data.manual_upload,
        status=ProcessingStatus.PENDING,
        meets_requirements=submission_data.meets_requirements,
        action_needed=submission_data.action_needed,
        function_pref=checked_pref,
        domain=submission_data.domain,
        page_link=submission_data.page_link
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
            message = "Submission processed."
        else:
            submission.update_status(ProcessingStatus.FAILED, "Text failed to process")
            message = "Submission failed to process"
            
        if plag_res["score"] != "N/A" and plag_res["score"] >= 60:
            submission.update_action(True)
            submission.meets_requirements = True
            owner.plagiarisms_prevented = owner.plagiarisms_prevented + 1
            data = {
                "owner_id": owner.id,
                "submission_id": submission.id,
                "ai_score": ai_res["score"],
                "plag_score": plag_res["score"],
                "citations": plag_res["result"]["citations"] if "citations" in plag_res["result"].keys() else None
            }
            
            watermark = _create_watermark(db, data)
            
            return SubmissionHookResponse(
                watermark_id=watermark.id,
                temp_text=submission.temp_text
            )
        else:    
            if ai_res["score"] != "N/A" and ai_res["score"] < owner.ai_threshold_option:
                submission.update_status(ProcessingStatus.FAILED, "AI score below threshold")
                message = "AI score below threshold"
                submission.meets_requirements = False
            else:
                submission.meets_requirements = True
        
        db.commit()
        db.refresh(submission)
        
        return SubmissionResponse(
            id=submission.id,
            owner_id=submission.owner_id,
            status=submission.status,
            orig_text_prev=submission.orig_text[:30],
            action_needed=submission.action_needed,
            manual_upload=submission.manual_upload,
            tokens_used=submission.tokens_used,
            created_at=submission.created_at,
            meets_requirements=submission.meets_requirements,
            failure_reason=submission.failure_reason,
            completed_processing_at=submission.completed_processing_at,
            message=message
        )
    except Exception as e:
        submission.update_status(ProcessingStatus.FAILED, f"Processing error: {str(e)}")
        db.commit()
        
        return SubmissionResponse(
            id=submission.id,
            owner_id=submission.owner_id,
            status=submission.status,
            orig_text_prev=submission.orig_text[:30],
            action_needed=submission.action_needed,
            manual_upload=submission.manual_upload,
            tokens_used=submission.tokens_used,
            created_at=submission.created_at,
            meets_requirements=submission.meets_requirements,
            failure_reason=submission.failure_reason,
            completed_processing_at=submission.completed_processing_at,
            message="Error processing your submission"
        )

@app.post("/api/v1/upload-submission", response_model=SubmissionResponse) # PRIVATE - LOGIN
async def upload_submission(
    submission_data: SubmissionManual,
    db: Session = Depends(get_db)
):
    """
    Create a new submission and process it.
    """
    key = db.query(ApiKey).filter(
        ApiKey.owner_id == submission_data.owner_id,
        ApiKey.id == submission_data.api_key_id,
        ApiKey.is_active == True
    ).first()
    if not key:
        raise HTTPException(status_code=404, detail="No key available")
    
    owner = db.query(Owner).filter( Owner.id == submission_data.owner_id ).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    for i in owner.function_pref.keys():
        if owner.function_pref[i] == True:
            checked_pref = i
            break
    
    # Create submission record
    submission = Submission(
        owner_id=owner.id,
        api_key_id=submission_data.api_key_id,
        orig_text=submission_data.orig_text,
        orig_text_length=len(submission_data.orig_text),
        manual_upload=submission_data.manual_upload,
        status=ProcessingStatus.PENDING,
        meets_requirements=submission_data.meets_requirements,
        action_needed=submission_data.action_needed,
        function_pref=checked_pref
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
            message = "Submission processed."
        else:
            submission.update_status(ProcessingStatus.FAILED, "Text failed to process")
            message = "Submission failed to process"
            
        if plag_res["score"] != "N/A" and plag_res["score"] >= 60:
            submission.update_action(True)
            submission.meets_requirements = True
            data = {
                "owner_id": owner.id,
                "submission_id": submission.id,
                "ai_res": ai_res["score"],
                "plag_res": plag_res["score"],
                "citations": plag_res["result"]["citations"] if "citations" in plag_res["result"].keys() else None
            }
            
            watermark = await _create_watermark(db, data)
            
            return SubmissionHookResponse(
                watermark_id=watermark.id,
                temp_text=submission.temp_text
            )
        else:    
            if ai_res["score"] != "N/A" and ai_res["score"] < owner.ai_threshold_option:
                submission.update_status(ProcessingStatus.FAILED, "AI score below threshold")
                db.commit()
                db.refresh(submission)
                message = "AI score below threshold"
                submission.meets_requirements = False
            else:
                submission.meets_requirements = True
        
        db.commit()
        db.refresh(submission)
        
        return SubmissionResponse(
            id=submission.id,
            owner_id=submission.owner_id,
            status=submission.status,
            orig_text_prev=submission.orig_text[:30],
            action_needed=submission.action_needed,
            manual_upload=submission.manual_upload,
            tokens_used=submission.tokens_used,
            created_at=submission.created_at,
            meets_requirements=submission.meets_requirements,
            failure_reason=submission.failure_reason,
            completed_processing_at=submission.completed_processing_at,
            message=message
        )   
    except Exception as e:
        submission.update_status(ProcessingStatus.FAILED, f"Processing error: {str(e)}")
        db.commit()
        
        return SubmissionResponse(
            id=submission.id,
            owner_id=submission.owner_id,
            status=submission.status,
            orig_text_prev=submission.orig_text[:30],
            action_needed=submission.action_needed,
            manual_upload=submission.manual_upload,
            tokens_used=submission.tokens_used,
            created_at=submission.created_at,
            meets_requirements=submission.meets_requirements,
            failure_reason=submission.failure_reason,
            completed_processing_at=submission.completed_processing_at,
            message="Error processing your submission"
        )

@app.get("/api/v1/owners/{owner_id}/submissions", response_model=List[SubmissionDetailResponse]) # PRIVATE - LOGIN
async def get_owner_submissions(
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
        SubmissionDetailResponse(
            id=sub.id,
            owner_id=sub.owner_id,
            api_key_id=sub.api_key_id,
            status=sub.status,
            action_needed=sub.action_needed,
            manual_upload=sub.manual_upload,
            tokens_used=sub.tokens_used,
            created_at=sub.created_at,
            meets_requirements=sub.meets_requirements,
            failure_reason=sub.failure_reason,
            completed_processing_at=sub.completed_processing_at,
            orig_text=sub.orig_text,
            edit_text=sub.edit_text,
            ai_result=sub.ai_result,
            plag_result=sub.plag_result,
            domain=sub.domain,
            page_link=sub.page_link,
            function_pref=sub.function_pref,
            edited=sub.edited,
            edited_at=sub.edited_at,
            temp_text=sub.temp_text,
        )
        for sub in submissions if submissions
    ]

@app.get("/api/v1/owners/{owner_id}/submissions/{submission_id}", response_model=SubmissionDetailResponse) # PRIVATE - LOGIN
async def get_submission_detailed(
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
    
    return submission
    
@app.delete("/api/v1/owners/{owner_id}/submissions/{submission_id}/delete-submission") # PRIVATE - LOGIN
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

@app.patch("/api/v1/owners/{owner_id}/submissions/{submission_id}/edit-submission") # PRIVATE - LOGIN
async def edit_submission(
    submission_data: SubmissionEdit,
    db: Session = Depends(get_db)
):
    submission = db.query(Submission).filter(
        Submission.id == submission_data.entry_id,
        Submission.owner_id == submission_data.owner_id
    ).first()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    submission.edit_text = submission_data.edit_text
    submission.edited = True
    submission.edited_at = datetime.now()
    
    # Handles sub if ACTION_NEEDED is True
    if submission.action_needed:
        # RESCAN FOR PLAGIARISM
        pass
    
    db.commit()
    
    return

def _create_watermark(db, req=WatermarkCreate):
    
    watermark = Watermark(
        owner_id=req["owner_id"],
        submission_id=req["submission_id"],
        ai_score=req["ai_score"],
        plag_score=req["plag_score"],
        citations=req["citations"]
    )
    
    db.add(watermark)
    db.commit()
    db.refresh(watermark)
    
    return watermark

# -- GET WATERMARKS

# -- DELETE WATERMARK


# ---------- LOG IN ENDPOINTS ----------

@app.post("/api/v1/auth/login")
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """Email and password (2FA??)"""
    owner = db.query(Owner).filter(Owner.email == login_data.email).first()
    if not owner or not verify_password(login_data.password, owner.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    return {
        "email": owner.email,
        "name": owner.name,
        "id": owner.id
    }
    

# ---------- STRIPE ENDPOINTS/WEBHOOKS/HELPERS ----------

# -- WEBHOOK HELPERS

async def _handle_session_completed(db, data):
    """Handles the checkout.session.completed webhook"""
    main_data = data.get("data")
    data_obj = main_data.get("object")
    owner_id = data_obj.get("metadata").get("owner_id")
    unique_id = data_obj.get("metadata").get("unique_id")

    # Idempotency check
    is_already_processed = await _handle_idempotency_check(db, data.get("id"), data.get("type"))
    
    if is_already_processed:
        return {
            "status": "duplicate"
        }
    
    # Fetch database entries
    try:
        owner = await get_current_owner(db, owner_id=owner_id)
        payment = await get_payment(db, owner_id=owner.id, unique_id=unique_id)
    except Exception as e:
        print("Failed to fetch owner or payment: ", e)
    
    # Check "customer_id" exists, create if not
    try:
        owner.customer_id = await _ensure_stripe_customer(db, owner)
        
        db.commit()
    except Exception as e:
        print("Failed to save customer_id: ", e)
    
    # Create event - save only when all datapoints are available, no duplicate due to earlier check
    await _create_event(db, data.get("id"), data.get("type"), owner.customer_id)
    
    return {
        "status": "success"
    }
  
async def _handle_session_expired(db, data):
    """Handles the checkout.session.expired webhook"""
    main_data = data.get("data")
    data_obj = main_data.get("object")
    owner_id = data_obj.get("metadata").get("owner_id")
    unique_id = data_obj.get("metadata").get("unique_id")
    
    # Fetch database entries
    try:
        owner = await get_current_owner(db, owner_id=owner_id)
        payment = await get_payment(db, owner_id=owner.id, unique_id=unique_id)
    except Exception as e:
        print("Failed to fetch owner or payment: ", e)
        
    # Delete payment record
    try:
        db.delete(payment)
        db.commit()
    except Exception as e:
        print("Payment failed to delete: ", e)
        
    # Remove "session_id"
    try:
        # Remove the session_id from owner's session_ids list if present
        session_id = data_obj.get("id")
        if session_id and owner.session_ids and session_id in owner.session_ids:
            owner.session_ids.remove(session_id)
            db.commit()
    except Exception as e:
        print("Failed to remove session_id from owner: ", e)
    
    # Create event - save only when all datapoints are available, no duplicate due to earlier check
    await _create_event(db, data.get("id"), data.get("type"), owner.customer_id)
    
    return {
        "status": "success"
    }
        
async def _handle_subscription_created(db, data):
    """Handles the customer.subscription.created webhook"""
    main_data = data.get("data")
    data_obj = main_data.get("object")
    customer_id = data_obj.get("customer")
    owner_id = data_obj.get("metadata").get("owner_id")
    unique_id = data_obj.get("metadata").get("unique_id")

    # Idempotency check
    is_already_processed = await _handle_idempotency_check(db, data.get("id"), data.get("type"), customer_id)
    
    if is_already_processed:
        return {
            "status": "duplicate"
        }
    
    # Fetch database entries
    try:
        owner = await get_current_owner(db, owner_id=owner_id)
        payment = await get_payment(db, owner_id=owner.id, unique_id=unique_id)
    except Exception as e:
        print("Failed to fetch owner or payment: ", e)
        return {
            "status": "failed"
        }
        
    # Save "customer_id"
    try:
        payment.customer_id = customer_id
        
        db.commit()
    except Exception as e:
        print("Failed to save customer_id: ", e)

    # Save "subscription_id"
    try:
        subscription_id = data_obj.get("id")

        if subscription_id:
            owner.subscription_id = subscription_id
            payment.subscription_id = subscription_id
        else:
            raise Exception
    except Exception as e:
        print("Failed to save subscription_id: ", e)
        
    # Create event, no duplicate due to earlier check
    await _create_event(db, data.get("id"), data.get("type"), owner.customer_id)    
    
    db.commit()
    
    return {
        "status": "success"
    }
    
async def _handle_invoice_created(db, data):
    """Handles the invoice.payment_succeeded webhook"""
    main_data = data.get("data")
    data_obj = main_data.get("object")
    customer_id = data_obj.get("customer")
    owner_id = data_obj.get("lines").get("data")[0].get("metadata").get("owner_id") or data_obj.get("metadata").get("owner_id")
    unique_id = data_obj.get("lines").get("data")[0].get("metadata").get("unique_id") or data_obj.get("metadata").get("unique_id")

    print(data_obj)
    # Idempotency check
    is_already_processed = await _handle_idempotency_check(db, data.get("id"), data.get("type"), customer_id)
    
    if is_already_processed:
        return {
            "status": "duplicate"
        }
    
    # Fetch database entries
    try:
        owner = await get_current_owner(db, owner_id=owner_id)
        payment = await get_payment(db, owner_id=owner.id, unique_id=unique_id)
    except Exception as e:
        print("Failed to fetch owner or payment: ", e)
        
    # Save "invoice_id"
    try:
        invoice_id = data_obj.get("id") if data_obj else None
        
        if invoice_id:
            payment.invoice_id = invoice_id
            db.commit()
        else:
            raise Exception
    except Exception as e:
        print("Failed to save invoice_id: ", e)
    
    # Save "invoice_pdf"
    try:
        invoice_pdf = data_obj.get("invoice_pdf") if data_obj else None
        
        if invoice_pdf:
            payment.invoice_pdf = invoice_pdf
            db.commit()
        else:
            raise Exception
    except Exception as e:
        print("Failed to save invoice_pdf: ", e)
        
    payment.status = "complete"
    if not owner.is_verified:
        owner.change_plan(payment.price_id)
        owner.verify_owner(cancelled=False)
    else:
        if not data_obj.get("billing_reason") == "manual":
            owner.reset_monthly_tokens()

    db.commit()
    
    # Create event, no duplicate due to earlier check
    await _create_event(db, data.get("id"), data.get("type"), owner.customer_id)
        
    return {
        "status": "success"
    }
    
async def _handle_payment_succeeded(db, data):
    """Handles the invoice.payment_succeeded webhook"""
    main_data = data.get("data")
    data_obj = main_data.get("object")
    customer_id = data_obj.get("customer")
    owner_id = data_obj.get("metadata").get("owner_id")
    unique_id = data_obj.get("metadata").get("unique_id")
    pack_name = data_obj.get("metadata").get("pack_name")
    
    # Idempotency check
    is_already_processed = await _handle_idempotency_check(db, data.get("id"), data.get("type"), customer_id)
    
    if is_already_processed:
        return {
            "status": "duplicate"
        }
    
    # Fetch database entries
    try:
        owner = await get_current_owner(db, owner_id=owner_id)
        payment = await get_payment(db, owner_id=owner.id, unique_id=unique_id)
    except Exception as e:
        print("Failed to fetch owner or payment: ", e)
        return {
            "status": "failed"
        }
        
    payment.status = "complete"
    owner.add_tokens(pack_name)
    
    db.commit()
    
    # Create event, no duplicate due to earlier check
    await _create_event(db, data.get("id"), data.get("type"), owner.customer_id)
    
    return {
        "status": "success"
    }
    
async def _handle_idempotency_check(db, event_id, event_type, customer_id = None):
    """Check if event has already been processed, save otherwise"""
    is_duplicate = False
    
    if customer_id:
        event = db.query(Event).filter(
            Event.event_id == event_id,
            Event.event_type == event_type,
            Event.customer_id == customer_id
        ).first()
    else:
        event = db.query(Event).filter(
            Event.event_id == event_id,
            Event.event_type == event_type
        ).first()
    
    if event:
        # DUPLICATE - ALREADY PROCESSED
        is_duplicate = True

    return is_duplicate
    
# -- HELPERS
    
async def _create_event(db, event_id, event_type, customer_id):
    
    new_event = Event(
        event_id=event_id,
        event_type=event_type,
        customer_id=customer_id
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    
    return {
        "status": "success"
    }
    
async def _ensure_stripe_customer(db, owner):
    """Ensure owner is a Stripe customer, create if not"""
    if owner.customer_id:
        confirmed = stripe.Customer.retrieve(
            owner.customer_id
        )
        if confirmed:
            return owner.customer_id
    
    try:
        # Create Stripe customer
        customer = stripe.Customer.create(
            email=owner.email,
            name=owner.name
        )
        
        # Save to db
        await _update_owner_stripe_customer_id(db, owner.id, customer.id)
        
        return customer.id
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to create customer"
        )
        
async def _update_owner_stripe_customer_id(
    db: Session,
    owner_id: int,
    customer_id: str
):
    """Updates owner's Stripe customer ID in database"""
    owner = await get_current_owner(db, owner_id=owner_id)
    owner.customer_id = customer_id
    
    db.commit()
    return

# -- ENDPOINTS

@app.post("/api/v1/payments/create-payment-session", response_model=dict)
async def create_payment_session(
    request: PaymentCreate,
    db: Session = Depends(get_db)
):
    """Create a payment (subscription or one_off), creates Stripe customer if needed"""
    try:
        owner = await get_current_owner(db, owner_id=request.owner_id)
        customer_id = await _ensure_stripe_customer(db, owner)
        unique_id = str(uuid.uuid4())
        
        success_url = request.success_url or "http://localhost:3000/account/api-management"
        
        checkout_params = {
            "customer": customer_id,
            "payment_method_types": ["card"],
            "success_url": success_url,
            "metadata": {"owner_id": str(owner.id), "unique_id": unique_id},
            "customer_update": {
                "address": "auto",
                "name": "auto"
            }
        }
        
        if request.payment_type == "subscription":
            try:
                price = stripe.Price.retrieve(request.price_id)
                if price.type != "recurring":
                    raise HTTPException(
                        status_code=400,
                        detail="Price ID must be for recurring payments"
                    )
            except stripe.error.InvalidRequestError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid price ID"
                )
            
            checkout_params.update({
                "mode": "subscription",
                "line_items": [
                    {
                        "price": request.price_id,
                        "quantity": 1
                    }
                ],
                "subscription_data": {
                    "metadata": {"owner_id": str(owner.id), "unique_id": unique_id},
                },
                "saved_payment_method_options": {
                    "payment_method_save": "enabled"
                },
                "payment_method_collection": "if_required"
            })
        else:
            if not request.price_id:
                raise HTTPException(
                    status_code=400,
                    detail="No price_id provided"
                )
                
            try:
                price = stripe.Price.retrieve(request.price_id)
                if price.type != "one_time":
                    raise HTTPException(
                        status_code=400,
                        detail="Price ID must be for one-time payments"
                    )
            except stripe.error.InvalidRequestError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid price ID"
                )
                
            checkout_params.update({
                "mode": "payment",
                "invoice_creation": {
                    "enabled": "true",
                    "invoice_data": {
                        "metadata": {"owner_id": str(owner.id), "unique_id": unique_id}
                    }
                },
                "line_items": [
                    {
                        "price": request.price_id,
                        "quantity": 1,
                    }
                ],
                "payment_intent_data": {
                    "metadata": {"owner_id": str(owner.id), "unique_id": unique_id, "pack_name": request.name},
                }
            })
            
        session = stripe.checkout.Session.create(**checkout_params)
        
        payment = Payment(
            owner_id=owner.id,
            customer_id=owner.customer_id or None,
            session_id=session.get("id"),
            unique_id=unique_id,
            status=session.status,
            currency="gbp",
            price_id=request.price_id,
            amount=session.amount_total,
            payment_type=request.payment_type,
            name=request.name
        )
        
        db.add(payment)
        db.commit()
        
        return {
            "session_url": session.url
        }
    
    except stripe.error.StripeError as e:
        print(e)
        raise HTTPException(
            status_code=400,
            detail="Failed to create checkout session"
        )
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred"
        )
        
# -- WEBHOOK LISTENER

@app.post("/api/v1/webhooks/stripe-webhooks")
async def stripe_listener(
    request: Request,
    db: Session = Depends(get_db)
):
    # Generic data
    data = await request.json()
    event_type = data.get("type")
    
    # -- CHECKOUT-COMPLETED WEBHOOK
    if event_type == "checkout.session.completed":
        
        if data:
            handler = await _handle_session_completed(db, data)
            
            if handler["status"] == "success":
                db.commit()
        else:
            raise HTTPException(
                status_code=400,
                detail="No data provided"
            )
            
        return

    if event_type == "checkout.session.expired":
        
        if data:
            handler = await _handle_session_expired(db, data)
            
            if handler["status"] == "success":
                db.commit()
        else:
            raise HTTPException(
                status_code=400,
                detail="No data provided"
            )
            
        return
       
    # -- SUBSCRIPTION-CREATED WEBHOOK
    if event_type == "customer.subscription.created":
        
        if data:
            handler = await _handle_subscription_created(db, data)
            
            if handler["status"] == "success":
                db.commit()
        else:
            raise HTTPException(
                status_code=400,
                detail="No data provided"
            )
            
        return

    # -- INVOICE-GENERATED WEBHOOK
    if event_type == "invoice.payment_succeeded":
        # Store invoice when payment succeeded
        
        if data:
            handler = await _handle_invoice_created(db, data)
            
            if handler["status"] == "success":
                db.commit()
        else:
            raise HTTPException(
                status_code=400,
                detail="No data provided"
            )
            
        return
    
    # -- INVOICE-FAILED WEBHOOK
    if event_type == "invoice.payment_failed":
        print(data)
        
    if event_type == "payment_intent.succeeded":

        if data:
            handler = await _handle_payment_succeeded(db, data)
            
            if handler["status"] == "success":
                db.commit()
        else:
            raise HTTPException(
                status_code=400,
                detail="No data provided"
            )
            
        return
    
    # -- SUBSCRIPTION-CANCELLED WEBHOOK
    if event_type == "customer.subscription.deleted":
        owner = await get_current_owner(db, customer_id=data.get("data").get("object").get("customer"))
        
        owner.change_plan("none")
        owner.verify_owner(cancelled=True)
        owner.subscription_id = ""
        
        db.commit()
    
    return

    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)