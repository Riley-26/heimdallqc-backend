import math
import secrets
from typing import List, Union
import uuid
from fastapi import FastAPI, Depends, HTTPException, Query, Request, status, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import logging
from datetime import datetime, timedelta, timezone
import requests
import os
import json
import stripe
from jose import jwe
import resend
from jinja2 import Template

from .db.database import SessionLocal, get_db
from .models.owner import Owner
from .models.api_key import ApiKey
from .models.submission import Submission, ProcessingStatus
from .models.payment import Payment
from .models.event import Event
from .schemas.owner import EmailPrefsUpdate, LoginRequest, OwnerDelete, PasswordReset, PasswordUpdate, OwnerCreate, SettingsUpdate, OwnerResponse, OwnerDetailResponse
from .schemas.api_key import ApiKeyCreate, ApiKeyDeactivate, ApiKeyListResponse, ApiKeyReveal
from .schemas.submission import SubmissionAuto, SubmissionCreated, SubmissionDelete, SubmissionEdit, SubmissionManual, SubmissionResponse, SubmissionDetailResponse
from .schemas.payment import PaymentCreate, PaymentListResponse, PaymentMethodDelete, PaymentMethodListResponse, SubscriptionUpdate

# !!!! DO NOT TOUCH
MARKUP_FACTOR = 15
PAGE_LIMIT = 10
TRIAL_LENGTH = 7
PLAG_THRESHOLD = 60
# !!!!

stripe.api_key = os.getenv("STRIPE_KEY")
resend.api_key = os.getenv("RESEND_KEY")

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
        "i_package": status_types["error"],
        "emailing": status_types["functioning"],
        "analysis": status_types["functioning"],
        "webhook": status_types["functioning"],
        "contact": status_types["functioning"]
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
import jwt
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
security = HTTPBearer()

def hash_password(password: str) -> str:
    """Hash a password"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


# ---------- PROCESSING/HELPER FUNCTIONS ----------

# Helper function to authenticate API key
async def authenticate_api_key(api_key: str) -> ApiKey:
    """Authenticate and return the API key object"""
    db = SessionLocal()
    try:
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
    finally:
        db.close()

# Text processing function
def process_text(text: str, owner_pref: str = "", checked_state: bool = False):
    """
    Process the submitted text and determine if it meets requirements.
    
    Args:
        text: The text to process
        
    Returns:
        Dict with processed results and validation status
    """
    # ANALYSIS
    plag_result = plag_analysis(text, owner_pref)
    ai_result = {
        "status": 200,
        "score": 100,
        "tokens": 0
    }
    if not checked_state:
        ai_result = ai_analysis(text)
    
    return {
        "ai_result": ai_result,
        "plag_result": plag_result,
        "text": text
    }

async def get_current_owner(
    db: Session,
    owner_unique_id: str = None,
    customer_id: str = None
):
    """Returns owner based on either owner_unique_id or owner's customer_id. One must be provided."""
    
    if not owner_unique_id and not customer_id:
        raise HTTPException(status_code=400, detail="Either owner_unique_id or customer_id must be provided")
    if owner_unique_id:
        owner = db.query(Owner).filter(Owner.unique_id == owner_unique_id).first()
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
    owner_unique_id: str = None,
    subscription_id: str = None
):
    """Returns payment item identified using subscription_id"""
    if not owner_unique_id and not subscription_id:
        raise HTTPException(status_code=400, detail="Either owner_unique_id or subscription_id must be provided")
    if owner_unique_id:
        payment = db.query(Payment).filter(
            Payment.owner_unique_id == owner_unique_id,
            Payment.unique_id == unique_id
        ).first()
        if not payment:
            raise HTTPException(status_code=400, detail="Payment item not found")
    else:
        payment = db.query(Payment).filter(Payment.subscription_id == subscription_id).first()
        if not payment:
            raise HTTPException(status_code=400, detail="Payment item not found")
    return payment

def convert_unique_id(unique_id: str):
    """Converts owner unique_id from string to UUID4 type"""
    try:
        owner_uuid = uuid.UUID(unique_id)
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid JWT id format")
    
    return owner_uuid

def validate_jwt(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Extract payload from JWT, fetches owner from it"""
    token = credentials.credentials
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,  # 256 bits for A256GCM
        salt=b'',   # NextAuth uses empty salt
        info=b'NextAuth.js Generated Encryption Key',  # This is the key info NextAuth uses
    )
    derived_key = hkdf.derive(os.getenv("NEXTAUTH_SECRET").encode())
    try:
        # Decrypt the JWE token
        payload = jwe.decrypt(token, derived_key)
        # payload is now a JSON string, parse it
        user_data = json.loads(payload)
        
        # Get the user ID from the JWT payload
        unique_id = user_data.get("sub")
        if not unique_id:
            raise HTTPException(status_code=401, detail="Invalid token")
            
        # Look up user in database
        owner = db.query(Owner).filter(Owner.unique_id == unique_id).first()
        if not owner:
            raise HTTPException(status_code=401, detail="Owner not found")
            
        return owner
    except Exception as e:
        print(f"JWE Decryption Error: {e}")

def render_action_needed_email(base_url: str, work_id: str):
    html_template = """
    <html>
      <body>
        <div style="width: 100%; background-color: #111; height: 120px; display: flex; justify-content: center; align-items: center;">
            <img src="https://heimdallqc.com/images/SVG/logo-colour.svg" alt="Heimdall QC Logo" style="width: 80px;" />
        </div>
        <div style="padding: 20px; background-color: #222; font-family: Arial;">
          <h1 style="color: #fff; font-size: 28px; margin-bottom: 16px;">Action needed</h1>
          <p style="color: #ccc; fontSize: 16px; marginBottom: 24px;">A submitted text in your website has been flagged as containing plagiarism. Please go to your account and make necessary modifications.</p>
          <br/>
          <p style="color: #ccc; fontSize: 16px; marginBottom: 24px;">Submission's Work ID: {{ work_id }}</p>
          <a href="{{ base_url }}/account"
             style="background-color: #222; color: #fff; font-size: 16px; padding: 12px 24px; border-radius: 6px; text-decoration: none; margin-bottom: 24px; border: none; display: inline-block;">
            My Account
          </a>
        </div>
      </body>
    </html>
    """
    template = Template(html_template)
    return template.render(base_url=base_url,work_id=work_id)

def render_payment_conf_email(invoice_pdf: str, base_url: str):
    html_template = """
    <html>
      <body>
        <div style="width: 100%; background-color: #111; height: 120px; display: flex; justify-content: center; align-items: center;">
            <img src="https://heimdallqc.com/images/SVG/logo-colour.svg" alt="Heimdall QC Logo" style="width: 80px;" />
        </div>
        <div style="padding: 20px; background-color: #222; font-family: Arial;">
          <h1 style="color: #fff; font-size: 28px; margin-bottom: 16px;">Thank you for your payment!</h1>
          <p style="color: #ccc; font-size: 16px; margin-bottom: 24px;">To view your invoice, please click the link below or go to the "billing" section of your account.</p>
          <a href="{{ invoice_pdf }}"
             style="background-color: #222; color: #fff; font-size: 16px; margin-bottom: 12px; padding: 12px 24px; border-radius: 6px; text-decoration: none; margin-bottom: 24px; border: none; display: inline-block;">
            Invoice PDF
          </a>
          <a href="{{ base_url }}/account/billing"
             style="background-color: #222; color: #fff; font-size: 16px; padding: 12px 24px; border-radius: 6px; text-decoration: none; margin-bottom: 24px; border: none; display: inline-block;">
            My Account
          </a>
          <p style="color: #888; font-size: 14px;">If you have any questions, please email us at support@heimdallqc.com</p>
        </div>
      </body>
    </html>
    """
    template = Template(html_template)
    return template.render(invoice_pdf=invoice_pdf, base_url=base_url)

def render_low_tokens_email(current: int, bill_cycle: str, base_url: str):
    html_template = """
    <html>
      <body>
        <div style="width: 100%; background-color: #111; height: 120px; display: flex; justify-content: center; align-items: center;">
            <img src="https://heimdallqc.com/images/SVG/logo-colour.svg" alt="Heimdall QC Logo" style="width: 80px;" />
        </div>
        <div style="padding: 20px; background-color: #222; font-family: Arial;">
          <h1 style="color: #fff; font-size: 28px; margin-bottom: 16px;">Low Tokens: {{ current }}</h1>
          <p style="color: #ccc; font-size: 16px; margin-bottom: 16px;">Tokens are below the threshold. Buy some extra tokens, or hold out until your next billing cycle there is enough time. Submissions will not be saved if tokens run out.</p>
          <p style="color: #ccc; font-size: 16px; margin-bottom: 24px;">Next bill: {{ bill_cycle }}</p>
          <a href="{{ base_url }}/account/billing"
             style="background-color: #222; color: #fff; font-size: 16px; padding: 12px 24px; border-radius: 6px; text-decoration: none; margin-bottom: 24px; border: none; display: inline-block;">
            My Account
          </a>
          <p style="color: #888; font-size: 14px;">If you have any questions, please email us at support@heimdallqc.com</p>
        </div>
      </body>
    </html>
    """
    template = Template(html_template)
    return template.render(current=current, bill_cycle=bill_cycle, base_url=base_url)

def render_no_tokens_email(bill_cycle: str, base_url: str):
    html_template = """
    <html>
      <body>
        <div style="width: 100%; background-color: #111; height: 120px; display: flex; justify-content: center; align-items: center;">
            <img src="https://heimdallqc.com/images/SVG/logo-colour.svg" alt="Heimdall QC Logo" style="width: 80px;" />
        </div>
        <div style="padding: 20px; background-color: #222; font-family: Arial;">
          <h1 style="color: #fff; font-size: 28px; margin-bottom: 16px;">No Tokens Remaining</h1>
          <p style="color: #ccc; font-size: 16px; margin-bottom: 16px;">A submission has failed due to insufficient tokens. You should purchase more, or wait until the next billing cycle.</p>
          <p style="color: #ccc; font-size: 16px; margin-bottom: 24px;">Next bill: {{ bill_cycle }}</p>
          <a href="{{ base_url }}/account/billing"
             style="background-color: #222; color: #fff; font-size: 16px; padding: 12px 24px; border-radius: 6px; text-decoration: none; margin-bottom: 24px; border: none; display: inline-block;">
            My Account
          </a>
          <p style="color: #888; font-size: 14px;">If you have any questions, please email us at support@heimdallqc.com</p>
        </div>
      </body>
    </html>
    """
    template = Template(html_template)
    return template.render(bill_cycle=bill_cycle, base_url=base_url)

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
def plag_analysis(text: str, owner_pref: str):
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

    if "status" not in response.keys() or "result" not in response.keys():
        return {
            "status": 400,
            "score": "N/A",
            "result": {},
            "tokens": 0
        }

    if response["status"] == 200 and response["result"]["score"] >= 80:
        if response["result"]["sourceCounts"] > 0:
            if owner_pref == "ai_rewrite":
                result = ai_rewrite(text)
            elif owner_pref == "redact":
                result = redact_text(text, response["sources"])
                
            if "sources" in response.keys():
                result["sources"] = response["sources"]
    
    return {
        "status": response["status"],
        "score": response["result"]["score"],
        "result": result if result else {},
        "tokens": response["credits_used"]
    }

# -- AUTO-CITATION -- FOR FUTURE
'''
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
'''

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

@app.post("/api/v1/owners")
async def create_owner(
    request: OwnerCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new owner account.
    """
    existing_owner = db.query(Owner).filter(Owner.email == request.email).first()
    if existing_owner:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new owner
    owner = Owner(
        email=request.email,
        domain=request.domain,
        password_hash=hash_password(request.password),
        name=request.name,
        company=request.company
    )
    
    db.add(owner)
    db.commit()
    db.refresh(owner)
    
    return LoginRequest(
        email=owner.email,
        password=request.password
    )

@app.get("/api/v1/owners/self", response_model=OwnerResponse)
async def get_owner(
    owner: Owner = Depends(validate_jwt)
):
    """
    Get owner by ID.
    """
    
    return OwnerResponse(
        id=owner.id,
        unique_id=owner.unique_id,
        email=owner.email,
        name=owner.name,
        domain=owner.domain,
        company=owner.company,
        is_active=owner.is_active,
        is_verified=owner.is_verified,
        cancelled_plan=owner.cancelled_plan,
        current_tokens=owner.current_tokens,
        tokens_used=owner.tokens_used,
        plan=owner.plan,
        plagiarisms_prevented=owner.plagiarisms_prevented,
        entries_needing_action=owner.entries_needing_action,
        texts_analysed=owner.texts_analysed
    )
    
@app.get("/api/v1/owners/self/detailed", response_model=OwnerDetailResponse)
async def get_owner_details(
    owner: Owner = Depends(validate_jwt)
):
    """
    Get details of owner by ID.
    """
    
    return OwnerDetailResponse(
        id=owner.id,
        unique_id=owner.unique_id,
        email=owner.email,
        name=owner.name,
        domain=owner.domain,
        company=owner.company,
        is_active=owner.is_active,
        is_verified=owner.is_verified,
        cancelled_plan=owner.cancelled_plan,
        current_tokens=owner.current_tokens,
        tokens_used=owner.tokens_used,
        plagiarisms_prevented=owner.plagiarisms_prevented,
        entries_needing_action=owner.entries_needing_action,
        texts_analysed=owner.texts_analysed,
        verified_month_end=owner.verified_month_end,
        plan=owner.plan,
        function_pref=owner.function_pref,
        ai_threshold_option=owner.ai_threshold_option,
        tokens_threshold=owner.tokens_threshold,
        low_tokens_option=owner.low_tokens_option,
        created_at=owner.created_at,
        updated_at=owner.updated_at,
        verified_at=owner.verified_at,
        customer_id=owner.customer_id,
        subscription_id=owner.subscription_id,
        session_ids=owner.session_ids,
        claimed_trial=owner.claimed_trial,
        trial_used=owner.trial_used
    )

# -- DEACTIVATE/DELETE OWNER
@app.delete("/api/v1/owners/delete-account")
async def delete_owner(
    request: OwnerDelete,
    owner: Owner = Depends(validate_jwt),
    db: Session = Depends(get_db)
):
    """Delete owner's data"""
    try:
        if verify_password(request.password, owner.password_hash):
            if owner.customer_id:
                # Delete Stripe customer
                customer = stripe.Customer.retrieve(owner.customer_id)
                
                if customer:
                    stripe.Customer.delete(owner.customer_id)
            
            # Delete all data
            payments = db.query(Payment).filter(Payment.customer_id == owner.customer_id).all()
            submissions = db.query(Submission).filter(Submission.owner_id == owner.id).all()
            api_keys = db.query(ApiKey).filter(ApiKey.owner_id == owner.id).all()
            all_data = payments + submissions + api_keys
            
            for i in all_data:
                db.delete(i)
                
            db.delete(owner)
            db.commit()
        else:
            raise HTTPException(
                status_code=400,
                detail="Incorrect password"
            )
    except Exception as e:
        print(e)
        raise HTTPException(
            status_code=400,
            detail="Failed to delete data"
        )
    
    return {
        "status": 200,
        "message": "Successfully deleted user"
    }

# -- GET PLAN USAGE

@app.get("/api/v1/owners/invoices/self", response_model=Union[List[PaymentListResponse], None])
async def get_owner_invoices(
    owner: Owner = Depends(validate_jwt)
):
    """Return list of owner's invoices for display"""
    if not owner.customer_id:
        return None
    try:
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
    owner: Owner = Depends(validate_jwt),
    db: Session = Depends(get_db),
):
    """Upgrade/Downgrade owner's plan, calculate proration accordingly"""
    try:
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
            proration_behavior='create_prorations'
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
        
@app.patch("/api/v1/owners/cancel-plan")
async def cancel_plan(
    owner: Owner = Depends(validate_jwt),
    db: Session = Depends(get_db)
):  
    """Cancel owners subscription. Must have an active subscription."""
    try:
        subscription = stripe.Subscription.retrieve(owner.subscription_id)
        
        if subscription.customer != owner.customer_id:
            raise HTTPException(
                status_code=403,
                detail="Unauthorised attempt"
            )
        
        # Cancel at period end
        stripe.Subscription.modify(
            owner.subscription_id,
            cancel_at_period_end=True
        )
        message = "Subscription will cancel at the end of the current plan"
        
        owner.cancelled_plan = True
        db.commit()
        
        return {
            "message": message
        }
    
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=400,
            detail="Failed to cancel subscription"
        )
    
@app.patch("/api/v1/owners/update-settings")
async def update_settings(
    request: SettingsUpdate,
    owner: Owner = Depends(validate_jwt),
    db: Session = Depends(get_db)
):
    """Updates all of the owner's settings"""
    owner.function_pref = request.function_pref
    owner.ai_threshold_option = request.ai_threshold_option
    
    db.commit()
    
    return {
        "status": "Updated preferences successfully"
    }

@app.patch("/api/v1/owners/save-email-prefs")
async def save_email_prefs(
    request: EmailPrefsUpdate,
    owner: Owner = Depends(validate_jwt),
    db: Session = Depends(get_db)
):
    """Save owner's email preferences"""
    owner.low_tokens_option = request.low_tokens_option["low_tokens_option"]
    owner.tokens_threshold = request.tokens_threshold["tokens_threshold"]
    
    db.commit()
    
    return {
        "status": "Updated preferences successfully"
    }

@app.patch("/api/v1/forgot-password")
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
    
    return {
        "message": message,
        "email": request.email,
        "token": reset_token
    }

@app.patch("/api/v1/reset-password")
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

@app.get("/api/v1/owners/payment-methods/self", response_model=Union[List[PaymentMethodListResponse], None])
async def get_payment_methods(
    owner: Owner = Depends(validate_jwt)
):
    """Returns list of owner's payment methods"""
    if not owner.customer_id:
        return None
    try:
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
        
@app.delete("/api/v1/owners/payment-methods/delete-payment-method", response_model=dict)
async def delete_payment_method(
    request: PaymentMethodDelete,
    owner: Owner = Depends(validate_jwt)
):
    """Delete a saved payment method"""
    try: 
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
        
@app.put("/api/v1/owners/claim-trial")
async def claim_trial(
    owner: Owner = Depends(validate_jwt),
    db: Session = Depends(get_db)
):
    """Claim free trial"""
    owner.claimed_trial = True
    db.commit()
    
    return

# ---------- API KEY ENDPOINTS ----------

@app.post("/api/v1/api-keys/create-key", response_model=ApiKeyReveal)
async def create_api_key(
    api_key_data: ApiKeyCreate,
    owner: Owner = Depends(validate_jwt),
    db: Session = Depends(get_db)
):
    """
    Generate a new API key for an owner.
    """
    # Generate new API key
    api_key = ApiKey(
        owner_id=owner.id,
        name=api_key_data.name,
        key=ApiKey.generate_key()
    )
    
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    return ApiKeyReveal(
        name=api_key.name,
        is_active=True,
        key=api_key.key
    )

@app.get("/api/v1/api-keys/self", response_model=List[ApiKeyListResponse])
async def get_api_keys(
    owner: Owner = Depends(validate_jwt),
    db: Session = Depends(get_db)
):
    """
    List all API keys for an owner (with masked keys).
    """
    
    api_keys = db.query(ApiKey).filter(
        ApiKey.owner_id == owner.id,
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

@app.patch("/api/v1/api-keys/deactivate-key")
async def deactivate_api_key(
    request: ApiKeyDeactivate,
    owner: Owner = Depends(validate_jwt),
    db: Session = Depends(get_db)
):
    """
    Delete (deactivate) an API key.
    """
    api_key = db.query(ApiKey).filter(
        ApiKey.id == request.api_key_id,
        ApiKey.owner_id == owner.id,
        ApiKey.is_active == True
    ).first()
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    # Instead of deleting, deactivate for audit trail
    api_key.is_active = False
    db.commit()
    
    return


# ---------- SUBMISSION ENDPOINTS ----------

from fastapi import BackgroundTasks

def process_submission(owner_id, submission_id, text, work_id, webhook_url="", function_pref="", question_result=False):
    """Background function for processing submission"""
    db = SessionLocal()
    try:
        owner = db.query(Owner).filter(Owner.id == owner_id).first()
        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        
        if not owner or not submission:
            print("Owner or submission not found")
            return
        
        processing_result = process_text(text, function_pref, question_result)
        
        # Update owner stats
        owner.texts_analysed = owner.texts_analysed + 1
        db.commit()
        
        # Set results
        ai_res = processing_result["ai_result"]
        plag_res = processing_result["plag_result"]
        res_tokens = 0
        
        # Set tokens, scaled using markup factor
        if "tokens" in ai_res.keys():
            res_tokens += math.ceil(ai_res["tokens"] / MARKUP_FACTOR)
        if "tokens" in plag_res.keys():
            res_tokens += math.ceil(plag_res["tokens"] / MARKUP_FACTOR)
            
        # Delete if insufficient tokens, send email
        if res_tokens > owner.current_tokens:
            email_params: resend.Emails.sendParams = {
                "from": "no-reply@heimdallqc.com",
                "to": [owner.email],
                "subject": "No Tokens Remaining",
                "html": render_no_tokens_email(bill_cycle=owner.verified_month_end, base_url=os.getenv("BASE_URL"))
            }
            resend.Emails.send(email_params)
            
            owner.current_tokens = 0
            
            db.delete(submission)
            db.commit()
            
            return SubmissionCreated(
                status=500,
                message="Insufficient tokens"
            )
            
        # Start updating submission entry
        submission.ai_result = ai_res
        submission.plag_result = plag_res
        submission.meets_requirements = ai_res["status"] == 200 or plag_res["status"] == 200
        submission.tokens_used = submission.tokens_used + res_tokens
        
        # Update owner stats
        owner.current_tokens = owner.current_tokens - res_tokens
        owner.tokens_used = owner.tokens_used + res_tokens
        
        # Check if submission should be saved
        modified_text = None
        
        if submission.meets_requirements:
            # Save modified text, plag score is high
            if "result" in plag_res.keys():
                if "modif_text" in plag_res["result"].keys():
                    modified_text = plag_res["result"]["modif_text"]
                    submission.temp_text = modified_text
                
            submission.update_status(ProcessingStatus.SUCCESS)
        else:
            submission.update_status(ProcessingStatus.FAILED, "Text failed to process")
            
        db.commit()
            
        # Plagiarism detected, send email
        if plag_res["score"] != "N/A" and plag_res["score"] >= PLAG_THRESHOLD:
            """
            
            email_params: resend.Emails.sendParams = {
                "from": "no-reply@heimdallqc.com",
                "to": [owner.email],
                "subject": "Plagiarism Detected - Action Needed",
                "html": render_action_needed_email(base_url=os.getenv("BASE_URL"),work_id=work_id)
            }
            resend.Emails.send(email_params)
            """
            
            submission.update_action(True)
            submission.meets_requirements = True
            owner.plagiarisms_prevented = owner.plagiarisms_prevented + 1
            
            db.commit()
        else:    
            if ai_res["score"] != "N/A" and ai_res["score"] < owner.ai_threshold_option:
                db.delete(submission)
            else:
                submission.meets_requirements = True
                
                if submission.action_needed:
                    submission.action_needed = False
        
        db.commit()
        
        # Send email if low tokens - tokens fallen below owner's set threshold
        if owner.low_tokens_option and owner.current_tokens <= owner.tokens_threshold:
            email_params: resend.Emails.sendParams = {
                "from": "no-reply@heimdallqc.com",
                "to": [owner.email],
                "subject": "Low Tokens",
                "html": render_low_tokens_email(current=owner.current_tokens, bill_cycle=owner.verified_month_end, base_url=os.getenv("BASE_URL"))
            }
            resend.Emails.send(email_params)
        
        # Call webhook, everything is good
        try:
            if webhook_url:
                response = requests.post(
                    webhook_url,
                    json={
                        "status": 200,
                        "message": "Results successfully received" if modified_text else "No results received",
                        "work_id": work_id,
                        "text": text,
                        "modified_text": modified_text
                    },
                    timeout=10
                )
                response.raise_for_status()
        except Exception as e:
            raise HTTPException(status_code=400, detail="Cannot send data to webhook")
        
        return {
            "status": 200
        }
        
    except Exception as e:
        submission.update_status(ProcessingStatus.FAILED, f"Processing error: {str(e)}")
        db.commit()
        
        # Call webhook, error processing text
        try:
            if webhook_url:
                response = requests.post(
                    webhook_url,
                    json={
                        "status": 500,
                        "message": "Failed to process text",
                        "work_id": work_id,
                        "text": text,
                        "modified_text": None
                    },
                    timeout=10
                )
                response.raise_for_status()
        except Exception as e:
            raise HTTPException(status_code=400, detail="Cannot send data to webhook")

        return {
            "status": 500
        }

@app.post("/api/v1/submissions/create-submission")
async def create_submission(
    submission_data: SubmissionAuto,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(get_api_key_from_header),
    internal_auth: str = Header(None, alias="Internal-Auth"),
    db: Session = Depends(get_db)
):
    """
    Create a new submission and process it.
    """
    # Check for internal authentication (bypass API key check if internal)
    if internal_auth and internal_auth == os.getenv("INTERNAL_SECRET"):
        api_key_obj = db.query(ApiKey).filter(
            ApiKey.key == api_key,
            ApiKey.is_active == True
        ).first()
        if not api_key_obj:
            raise HTTPException(status_code=401, detail="Invalid API key")
    else:
        # External request - authenticate API key normally
        api_key_obj = await authenticate_api_key(api_key)
    
    # Get owner's preferred modif function
    owner = db.query(Owner).filter( Owner.id == api_key_obj.owner_id ).first()
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    for i in owner.function_pref.keys():
        if owner.function_pref[i] == True:
            checked_pref = i
            break
        
    # Cannot process if no tokens
    if owner.current_tokens <= 0:
        # Just in case
        if not owner.current_tokens == 0:
            owner.current_tokens = 0
            db.commit()
        
        return SubmissionCreated(
            status=500,
            message="Insufficient tokens"
        )
    
    # Create submission record
    submission = Submission(
        owner_id=owner.id,
        api_key_id=api_key_obj.id,
        orig_text=submission_data.orig_text,
        orig_text_length=len(submission_data.orig_text),
        question_result=submission_data.question_result,
        manual_upload=False,
        status=ProcessingStatus.PROCESSING,
        meets_requirements=False,
        action_needed=False,
        function_pref=checked_pref,
        work_id=submission_data.work_id,
        domain=submission_data.domain,
        page_link=submission_data.page_link
    )
    
    db.add(submission)
    db.commit()
    db.refresh(submission)
    
    background_tasks.add_task(process_submission, owner.id, submission.id, submission_data.orig_text, submission_data.work_id, submission_data.webhook_url, checked_pref, submission_data.question_result)
    
    return

@app.post("/api/v1/submissions/upload-submission")
async def upload_submission(
    submission_data: SubmissionManual,
    owner: Owner = Depends(validate_jwt),
    db: Session = Depends(get_db)
):
    """
    Create a new submission and process it.
    """
    key = db.query(ApiKey).filter(
        ApiKey.owner_id == owner.id,
        ApiKey.id == submission_data.api_key_id,
        ApiKey.is_active == True
    ).first()
    if not key:
        raise HTTPException(status_code=404, detail="No key available")
    
    for i in owner.function_pref.keys():
        if owner.function_pref[i] == True:
            checked_pref = i
            break
    if owner.current_tokens <= 0:
        raise HTTPException(status_code=400, detail="No tokens remaining")
    
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
        function_pref=checked_pref,
        work_id=f"hmdl-wk-{uuid.uuid4()}"
    )
    
    db.add(submission)
    db.commit()
    db.refresh(submission)
    
    try:
        # Update status to processing
        submission.update_status(ProcessingStatus.PROCESSING)
        owner.texts_analysed = owner.texts_analysed + 1
        db.commit()
        
        processing_result = await process_text(submission_data.orig_text, checked_pref)
        
        ai_res = processing_result["ai_result"]
        plag_res = processing_result["plag_result"]
        res_tokens = 0
        
        # Set tokens, scaled by markup factor
        if "tokens" in ai_res.keys():
            res_tokens += math.ceil(ai_res["tokens"] / MARKUP_FACTOR)
        if "tokens" in plag_res.keys():
            res_tokens += math.ceil(plag_res["tokens"] / MARKUP_FACTOR)
            
        # Delete if insufficient tokens
        if res_tokens > owner.current_tokens:
            email_params: resend.Emails.sendParams = {
                "from": "no-reply@heimdallqc.com",
                "to": [owner.email],
                "subject": "Insufficient Tokens",
                "html": render_no_tokens_email(bill_cycle=owner.verified_month_end, base_url=os.getenv("BASE_URL"))
            }
            resend.Emails.send(email_params)
            
            owner.current_tokens = 0
            
            db.delete(submission)
            db.commit()
            return None
        
        # Start updating submission entry
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
        else:
            submission.update_status(ProcessingStatus.FAILED, "Text failed to process")
            
        db.commit()
        
        # -- EMAIL - LOW TOKENS
        if owner.low_tokens_option and owner.current_tokens <= owner.tokens_threshold:
            email_params: resend.Emails.sendParams = {
                "from": "no-reply@heimdallqc.com",
                "to": [owner.email],
                "subject": "Low Tokens",
                "html": render_low_tokens_email(current=owner.current_tokens, bill_cycle=owner.verified_month_end, base_url=os.getenv("BASE_URL"))
            }
            
            resend.Emails.send(email_params)
            
        # Plag score must meet criteria
        if plag_res["score"] != "N/A" and plag_res["score"] >= 60:
            
            # -- PLAGIARISM DETECTED
            
            email_params: resend.Emails.sendParams = {
                "from": "no-reply@heimdallqc.com",
                "to": [owner.email],
                "subject": "Plagiarism Detected - Action Needed",
                "html": render_action_needed_email(base_url=os.getenv("BASE_URL"))
            }
            
            resend.Emails.send(email_params)
            
            submission.update_action(True)
            submission.meets_requirements = True
            owner.plagiarisms_prevented = owner.plagiarisms_prevented + 1
            
            data = {
                "owner_id": owner.id,
                "submission_id": submission.id,
                "ai_score": ai_res["score"],
                "plag_score": plag_res["score"]
            }
            db.commit()
        else:    
            if ai_res["score"] != "N/A" and ai_res["score"] < owner.ai_threshold_option:
                db.delete(submission)
            else:
                submission.meets_requirements = True
        
        db.commit()
        db.refresh(submission)
        
    except Exception as e:
        submission.update_status(ProcessingStatus.FAILED, f"Processing error: {str(e)}")
        db.commit()
        
        return {
            "status": "failed"
        }
    
    except Exception as e:
        return {
            "status": "completed"
        }

@app.get("/api/v1/submissions/self", response_model=List[SubmissionResponse])
async def get_owner_submissions(
    page: int = Query(1, ge=1),
    status: str = "success",
    owner: Owner = Depends(validate_jwt),
    db: Session = Depends(get_db)
):
    """List submissions for an owner (for admin/dashboard use)."""
    
    # Build query
    query = db.query(Submission).filter(Submission.owner_id == owner.id)
    
    # Add status filter if provided
    if status:
        query = query.filter(Submission.status == status)
    
    # Get submissions with pagination
    submissions = query.order_by(Submission.created_at.desc()).offset((page-1)*PAGE_LIMIT).limit(PAGE_LIMIT).all()

    # Return list response
    return [
        SubmissionResponse(
            id=sub.id,
            status=sub.status,
            action_needed=sub.action_needed,
            manual_upload=sub.manual_upload,
            tokens_used=sub.tokens_used,
            created_at=sub.created_at,
            unique_id=sub.unique_id,
            work_id=sub.work_id,
            meets_requirements=sub.meets_requirements,
            orig_text=sub.orig_text,
            edit_text=sub.edit_text,
            temp_text=sub.temp_text,
            ai_result=sub.ai_result,
            plag_result=sub.plag_result,
            edited=sub.edited,
            page_link=sub.page_link,
            domain=sub.domain,
            function_pref=sub.function_pref,
        )
        for sub in submissions if submissions
    ]

@app.get("/api/v1/submissions/{submission_id}", response_model=SubmissionDetailResponse)
async def get_submission_detailed(
    submission_id: str,
    owner: Owner = Depends(validate_jwt),
    db: Session = Depends(get_db)
):
    """Get detailed submission info for admin/dashboard use."""
    # Get submission and verify ownership
    submission = db.query(Submission).filter(
        Submission.unique_id == submission_id,
        Submission.owner_id == owner.id
    ).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    return SubmissionDetailResponse(
        id=submission.id,
        status=submission.status,
        action_needed=submission.action_needed,
        manual_upload=submission.manual_upload,
        tokens_used=submission.tokens_used,
        created_at=submission.created_at,
        unique_id=submission.unique_id,
        work_id=submission.work_id,
        meets_requirements=submission.meets_requirements,
        orig_text=submission.orig_text,
        edit_text=submission.edit_text,
        temp_text=submission.temp_text,
        ai_result=submission.ai_result,
        plag_result=submission.plag_result,
        edited=submission.edited,
        page_link=submission.page_link,
        domain=submission.domain,
        function_pref=submission.function_pref,
        api_key_id=submission.api_key_id,
        owner_id=submission.owner_id,
        failure_reason=submission.failure_reason,
        completed_processing_at=submission.completed_processing_at,
        edited_at=submission.edited_at
    )
   
@app.get("/api/v1/submissions/work_id/{work_id}")
async def get_submission_by_workid(
    work_id: str,
    db: Session = Depends(get_db)
):
    """Get detailed submission info using API key and work ID."""
    # Get submission and verify ownership
    submission = db.query(Submission).filter(
        Submission.work_id == work_id
    ).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    return {
        "id": submission.id,
        "owner_id": submission.owner_id,
        "status": submission.status,
        "action_needed": submission.action_needed,
        "manual_upload": submission.manual_upload,
        "tokens_used": submission.tokens_used,
        "created_at": submission.created_at,
        "work_id": submission.work_id,
        "meets_requirements": submission.meets_requirements,
        "orig_text": submission.orig_text,
        "edit_text": submission.edit_text,
        "temp_text": submission.temp_text,
        "ai_result": submission.ai_result,
        "plag_result": submission.plag_result,
        "edited": submission.edited,
        "page_link": submission.page_link,
        "domain": submission.domain,
        "function_pref": submission.function_pref,
        "failure_reason": submission.failure_reason,
        "completed_processing_at": submission.completed_processing_at,
        "edited_at": submission.edited_at
    }
   
@app.get("/api/v1/submissions/self/action-needed", response_model=List[SubmissionResponse])
async def get_submissions_action(
    page: int = Query(1, ge=1),
    status: str = "success",
    owner: Owner = Depends(validate_jwt),
    db: Session = Depends(get_db)
):
    """List submissions for an owner (for admin/dashboard use)."""

    # Build query
    query = db.query(Submission).filter(Submission.owner_id == owner.id)
    
    # Add status filter if provided
    if status:
        query = query.filter(
            Submission.status == status,
            Submission.action_needed == True
        )
    
    # Get submissions with pagination
    submissions = query.order_by(Submission.created_at.desc()).offset((page-1)*PAGE_LIMIT).limit(PAGE_LIMIT).all()
    
    # Return list response
    return [
        SubmissionResponse(
            id=sub.id,
            status=sub.status,
            action_needed=sub.action_needed,
            manual_upload=sub.manual_upload,
            tokens_used=sub.tokens_used,
            created_at=sub.created_at,
            unique_id=sub.unique_id,
            work_id=sub.work_id,
            meets_requirements=sub.meets_requirements,
            orig_text=sub.orig_text,
            edit_text=sub.edit_text,
            temp_text=sub.temp_text,
            ai_result=sub.ai_result,
            plag_result=sub.plag_result,
            edited=sub.edited,
            page_link=sub.page_link,
            domain=sub.domain,
            function_pref=sub.function_pref,
        )
        for sub in submissions if submissions
    ]
    
@app.get("/api/v1/submissions/self/entry-count")
async def get_submission_count(
    owner: Owner = Depends(validate_jwt),
    db: Session = Depends(get_db)
):
    """Get a count of all submissions, split into action-needed and not"""
    
    entry_count = len(db.query(Submission).filter(Submission.owner_id == owner.id).all())
    action_entry_count = len(db.query(Submission).filter(Submission.owner_id == owner.id, Submission.action_needed == True).all())
    success_entry_count = len(db.query(Submission).filter(Submission.owner_id == owner.id, Submission.status == "success").all())
    success_action_entry_count = len(db.query(Submission).filter(Submission.owner_id == owner.id, Submission.action_needed == True, Submission.status == "success").all())
    
    return {
        "ententry_countries": entry_count,
        "action_entry_count": action_entry_count,
        "success_entry_count": success_entry_count,
        "success_action_entry_count": success_action_entry_count,
    }
    
@app.delete("/api/v1/submissions/delete-submission")
async def delete_submission(
    request: SubmissionDelete,
    owner: Owner = Depends(validate_jwt),
    db: Session = Depends(get_db)
):
    submission = db.query(Submission).filter(
        Submission.unique_id == request.submission_unique_id,
        Submission.owner_id == owner.id
    ).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    db.delete(submission)
    db.commit()
    
    return

@app.patch("/api/v1/submissions/edit-submission")
async def edit_submission(
    request: SubmissionEdit,
    background_tasks: BackgroundTasks,
    owner: Owner = Depends(validate_jwt),
    db: Session = Depends(get_db)
):
    submission = db.query(Submission).filter(
        Submission.unique_id == request.submission_unique_id,
        Submission.owner_id == owner.id
    ).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # Rescan for plagiarism
    if request.rescan:
        background_tasks.add_task(process_submission, owner.id, submission.id, request.edit_text, submission.work_id)
        
    submission.edit_text = request.edit_text
    submission.edited = True
    submission.edited_at = datetime.now()
    
    db.commit()
    
    return


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
        "id": owner.unique_id
    }
    

# ---------- STRIPE ENDPOINTS/WEBHOOKS/HELPERS ----------

# -- WEBHOOK HELPERS

async def _handle_session_completed(db, data):
    """Handles the checkout.session.completed webhook"""
    main_data = data.get("data")
    data_obj = main_data.get("object")
    owner_unique_id = data_obj.get("metadata").get("owner_unique_id")
    unique_id = data_obj.get("metadata").get("unique_id")

    # Idempotency check
    is_already_processed = await _handle_idempotency_check(db, data.get("id"), data.get("type"))
    
    if is_already_processed:
        return {
            "status": "duplicate"
        }
    
    # Fetch database entries
    try:
        owner = await get_current_owner(db, owner_unique_id=owner_unique_id)
        payment = await get_payment(db, owner_unique_id=owner.unique_id, unique_id=unique_id)
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
    owner_unique_id = data_obj.get("metadata").get("owner_unique_id")
    unique_id = data_obj.get("metadata").get("unique_id")
    
    # Fetch database entries
    try:
        owner = await get_current_owner(db, owner_unique_id=owner_unique_id)
        payment = await get_payment(db, owner_unique_id=owner.unique_id, unique_id=unique_id)
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
    owner_unique_id = data_obj.get("metadata").get("owner_unique_id")
    unique_id = data_obj.get("metadata").get("unique_id")

    # Idempotency check
    is_already_processed = await _handle_idempotency_check(db, data.get("id"), data.get("type"), customer_id)
    
    if is_already_processed:
        return {
            "status": "duplicate"
        }
    
    # Fetch database entries
    try:
        owner = await get_current_owner(db, owner_unique_id=owner_unique_id)
        payment = await get_payment(db, owner_unique_id=owner.unique_id, unique_id=unique_id)
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
    lines_data = data_obj.get("lines").get("data")[0]
    owner_unique_id = lines_data.get("metadata").get("owner_unique_id") or data_obj.get("metadata").get("owner_unique_id")
    unique_id = lines_data.get("metadata").get("unique_id") or data_obj.get("metadata").get("unique_id")

    # Idempotency check
    is_already_processed = await _handle_idempotency_check(db, data.get("id"), data.get("type"), customer_id)
    
    if is_already_processed:
        return {
            "status": "duplicate"
        }
    
    # Fetch database entries
    try:
        owner = await get_current_owner(db, owner_unique_id=owner_unique_id)
        payment = await get_payment(db, owner_unique_id=owner.unique_id, unique_id=unique_id)
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
            
            email_params: resend.Emails.sendParams = {
                "from": "no-reply@heimdallqc.com",
                "to": [owner.email],
                "subject": "Payment Confirmation",
                "html": render_payment_conf_email(invoice_pdf=invoice_pdf, base_url=os.getenv("BASE_URL"))
            }
            
            resend.Emails.send(email_params)
        else:
            raise Exception
    except Exception as e:
        print("Failed to save invoice_pdf: ", e)
        
    payment.status = "complete"
    if owner.claimed_trial:
        owner.trial_used = True
        
    period_end_seconds = lines_data.get("period").get("end")
    if period_end_seconds:
        owner.verified_month_end = datetime.fromtimestamp(period_end_seconds, tz=timezone.utc)
        
    if not owner.is_verified:
        # New subscription
        owner.change_plan(payment.price_id)
        owner.verify_owner(cancelled=False)
    else:
        # Recurring payment
        if not data_obj.get("billing_reason") == "manual":
            owner.add_monthly_tokens()

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
    owner_unique_id = data_obj.get("metadata").get("owner_unique_id")
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
        owner = await get_current_owner(db, owner_unique_id=owner_unique_id)
        payment = await get_payment(db, owner_unique_id=owner.unique_id, unique_id=unique_id)
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
        await _update_owner_stripe_customer_id(db, owner.unique_id, customer.id)
        
        return customer.id
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to create customer"
        )
        
async def _update_owner_stripe_customer_id(
    db: Session,
    owner_unique_id: str,
    customer_id: str
):
    """Updates owner's Stripe customer ID in database"""
    owner = await get_current_owner(db, owner_unique_id=owner_unique_id)
    owner.customer_id = customer_id
    
    db.commit()
    return

# -- ENDPOINTS

@app.post("/api/v1/payments/create-payment-session", response_model=dict)
async def create_payment_session(
    request: PaymentCreate,
    owner: Owner = Depends(validate_jwt),
    db: Session = Depends(get_db)
):
    """Create a payment (subscription or one_off), creates Stripe customer if needed"""
    
    # CANNOT PURCHASE IF NOT SUBSCRIBED
    if request.payment_type == "one_off" and not owner.is_verified:
        raise HTTPException(status_code=400, detail="You must have a subscription before buying tokens")
        
    try:
        customer_id = await _ensure_stripe_customer(db, owner)
        unique_id = str(uuid.uuid4())
        
        success_url = request.success_url or None
        
        checkout_params = {
            "customer": customer_id,
            "payment_method_types": ["card"],
            "success_url": success_url,
            "metadata": {"owner_unique_id": str(owner.unique_id), "unique_id": unique_id},
            "customer_update": {
                "address": "auto",
                "name": "auto"
            },
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
                    "trial_period_days": 7 if owner.claimed_trial and not owner.trial_used else None,
                    "metadata": {"owner_unique_id": str(owner.unique_id), "unique_id": unique_id},
                },
                "saved_payment_method_options": {
                    "payment_method_save": "enabled"
                },
                "payment_method_collection": "always"
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
                        "metadata": {"owner_unique_id": str(owner.unique_id), "unique_id": unique_id}
                    }
                },
                "line_items": [
                    {
                        "price": request.price_id,
                        "quantity": 1,
                    }
                ],
                "payment_intent_data": {
                    "metadata": {"owner_unique_id": str(owner.unique_id), "unique_id": unique_id, "pack_name": request.name},
                },
                "saved_payment_method_options": {
                    "payment_method_save": "enabled"
                }
            })
            
        session = stripe.checkout.Session.create(**checkout_params)
        
        payment = Payment(
            owner_unique_id=owner.unique_id,
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
        raise HTTPException(
            status_code=400,
            detail="Failed to create invoice"
        )
        
    # -- PAYMENT-SUCCEEDED WEBHOOK
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
        owner.verified_month_end = None
        owner.cancelled_plan = False
        
        db.commit()
    
    return


@app.post("/yello")
async def yelo(request: Request):
    
    print("yello: ")
    data = await request.json()
    print(data)
    
    return
    
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(app, host="0.0.0.0", port=8000)