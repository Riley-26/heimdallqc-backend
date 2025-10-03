from sqlalchemy import Column, Integer, String, DateTime, Boolean, Table, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..db.database import Base
from datetime import datetime, timedelta
from sqlalchemy.dialects.postgresql import UUID
import uuid

plans_dict = {
    "None": {
        "id": "none",
        "name": "none",
        "tokens": 0,
        "price": 0
    },
    "Extrinsic": {
        "id": "price_1RvgtBR9LI2BudDrjnZpax1X",
        "name": "extrinsic",
        "tokens": 8000,
        "price": 34
    },
    "Intrinsic": {
        "id": "price_1Rvh1DR9LI2BudDrp05uZgkV",
        "name": "intrinsic",
        "tokens": 6000,
        "price": 26
    },
    "Combo": {
        "id": "price_1Rvh1SR9LI2BudDrHW0tFWz9",
        "name": "combo",
        "tokens": 16500,
        "price": 55
    }
}

class Tokens:
    sm = {
        "tokens": 1000,
        "price": 5
    }
    md = {
        "tokens": 4000,
        "price": 18
    }
    lg = {
        "tokens": 10000,
        "price": 40
    }
    xl = {
        "tokens": 50000,
        "price": 175
    }
    
class Owner(Base):
    __tablename__ = "owners"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Unique key - for referencing
    unique_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    
    # Authentication
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    reset_token = Column(String(255), nullable=True)
    token_expiration = Column(DateTime(timezone=True), nullable=True)
    
    # Basic profile
    name = Column(String(200), nullable=False)
    domain = Column(String(100), nullable=True)
    company = Column(String(200), nullable=True)
    
    # Account status
    cancelled_plan = Column(Boolean, default=False)
    claimed_trial = Column(Boolean, default=False)
    trial_used = Column(Boolean, default=False)
    customer_id = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verified_month_end = Column(DateTime(timezone=True), nullable=True)
    plan = Column(JSON, nullable=False, default=plans_dict["None"])
    subscription_id = Column(String(255), nullable=True)
    session_ids = Column(JSON, nullable=False, default=list)
    
    # Settings
    function_pref = Column(JSON, nullable=False, default=lambda: {
        "ai_rewrite": True,
        "redact": False
    })
    ai_threshold_option = Column(Integer, nullable=False, default=60)
    low_tokens_option = Column(Boolean, nullable=False, default=True)
    tokens_threshold = Column(Integer, nullable=False, default=500)
    
    # Usage tracking
    current_tokens = Column(Integer, default=plans_dict["None"]["tokens"], nullable=False)
    tokens_used = Column(Integer, default=0, nullable=False)
    plagiarisms_prevented = Column(Integer, default=0, nullable=False)
    entries_needing_action = Column(Integer, default=0, nullable=False)
    texts_analysed = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    api_keys = relationship("ApiKey", back_populates="owner", cascade="all, delete-orphan")
    submissions = relationship("Submission", back_populates="owner")
    payments = relationship("Payment", back_populates="owner")

    def __repr__(self):
        return f"<Owner(id={self.id}, email={self.email})>"
    
    def change_plan(self, new_plan_id):
        # Find the plan where the "id" matches new_plan_id
        matched_plan = None
        for plan_name, plan_info in plans_dict.items():
            if plan_info["id"] == new_plan_id:
                matched_plan = plan_name
                break

        if matched_plan:
            # Only increase tokens if tokens are short
            if self.current_tokens < plans_dict[matched_plan]["tokens"]:
                self.current_tokens = plans_dict[matched_plan]["tokens"]
                
            self.plan = plans_dict[matched_plan]

            return {
                "status": "success"
            }
        else:
            return None
        
    def add_tokens(self, pack):
        pack_dict = {
            "sm": Tokens.sm,
            "md": Tokens.md,
            "lg": Tokens.lg,
            "xl": Tokens.xl
        }
        if pack in pack_dict.keys():
            self.current_tokens += pack_dict[pack]["tokens"]
            
            return
        
        return None
    
    def update_prefs(self, new_prefs):
        if not isinstance(new_prefs, dict):
            raise ValueError("new_prefs must be a dictionary")
        if self.preferences is None:
            self.preferences = {}
        for key, value in new_prefs.items():
            if key in self.preferences:
                self.preferences[key] = value
    
    def verify_owner(self, cancelled):
        """Call this when owner upgrades to a paid plan."""
        if not cancelled:
            now = datetime.now()
            self.is_verified = True
            self.verified_at = now
        else:
            self.is_verified = False
            
    def add_monthly_tokens(self):
        """Call this to reset tokens"""
        now = datetime.now()
        if self.verified_month_end and now >= self.verified_month_end:
            self.current_tokens = self.plan.get("tokens", 0)
            # Set next month end
            self.verified_month_end = self.verified_month_end + timedelta(days=30)
        