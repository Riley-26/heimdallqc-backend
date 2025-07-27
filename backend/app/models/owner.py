from sqlalchemy import Column, Integer, String, DateTime, Boolean, Table, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..db.database import Base
from datetime import datetime, timedelta

plans_dict = {
    "None": {
        "name": "none",
        "tokens": 0,
        "price": 0
    },
    "Extrinsic": {
        "name": "extrinsic",
        "tokens": 8000,
        "price": 34
    },
    "Intrinsic": {
        "name": "intrinsic",
        "tokens": 6000,
        "price": 27
    },
    "Combo": {
        "name": "combo",
        "tokens": 16500,
        "price": 59
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
    
    # Foreign key
    domain_id = Column(Integer, ForeignKey("verified_sites.id"), nullable=False, index=True)
    
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
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verified_month_end = Column(DateTime(timezone=True), nullable=True)
    plan = Column(JSON, nullable=False, default=plans_dict["None"])
    
    # Settings
    function_pref = Column(JSON, nullable=False, default=lambda: {
        "auto_cite": True,
        "ai_rewrite": False,
        "redact": False
    })
    ui_pref = Column(JSON, nullable=False, default=lambda : {
        "widget": True,
        "watermarks": True
    })
    ai_threshold_option = Column(Integer, nullable=False, default=0)
    
    # Usage tracking
    current_tokens = Column(Integer, default=plans_dict["None"]["tokens"], nullable=False)
    tokens_used = Column(Integer, default=0, nullable=False)
    watermarks_made = Column(Integer, default=0, nullable=False)
    plagiarisms_prevented = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    api_keys = relationship("ApiKey", back_populates="owner", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Owner(id={self.id}, email={self.email})>"
    
    def change_plan(self, new_plan):
        tokens = self.current_tokens

        if new_plan in plans_dict.keys():
            # Only increase tokens if tokens are short
            if self.current_tokens < plans_dict[new_plan]["tokens"]:
                tokens = plans_dict[new_plan]["tokens"]
            
            return {
                "plan": plans_dict[new_plan],
                "tokens": tokens
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
            tokens = self.current_tokens + pack_dict[pack]["tokens"]
            return {
                "tokens": tokens,
                "price": pack_dict[pack]["price"]
            }
        return None
    
    def update_prefs(self, new_prefs):
        if not isinstance(new_prefs, dict):
            raise ValueError("new_prefs must be a dictionary")
        if self.preferences is None:
            self.preferences = {}
        for key, value in new_prefs.items():
            if key in self.preferences:
                self.preferences[key] = value
    
    def verify_owner(self):
        """Call this when owner is verified."""
        self.is_verified = True
        now = datetime.now()
        self.verified_at = now
        # Set month end to 30 days from now
        self.verified_month_end = now + timedelta(days=30)
        
    def reset_monthly_tokens(self):
        """Call this to reset tokens if month has passed."""
        now = datetime.now()
        if self.verified_month_end and now >= self.verified_month_end:
            self.current_tokens = self.plan.get("tokens", 0)
            # Set next month end
            self.verified_month_end = self.verified_month_end + timedelta(days=30)
    
    
class Verified_site(Base):
    __tablename__ = "verified_sites"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    domain = Column(String(100), nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Usage tracking
    total_requests = Column(Integer, default=0)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    owner = relationship("Owner", backref="verified_site")
    
    def __repr__(self):
        return f"<Verified_site(id={self.id}, domain={self.domain})>"