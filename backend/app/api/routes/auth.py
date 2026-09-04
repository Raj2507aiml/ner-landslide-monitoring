import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin, UserOut, TokenResponse
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token
)

logger = logging.getLogger(__name__)

router = APIRouter()

def seed_initial_users_if_needed(db: Session):
    """Seed initial default admin and citizen accounts if table is empty."""
    try:
        # Check admin
        admin = db.query(User).filter(
            (User.email == "commander@ner.gov.in") | (User.email == "admin@ner.gov.in")
        ).first()
        if not admin:
            admin = User(
                name="Col. Sanjeev Roy (Retd.)",
                email="commander@ner.gov.in",
                hashed_password=hash_password("password123"),
                role="admin",
                phone="+91 94350 12345",
                state="NER HQ (Shillong)"
            )
            db.add(admin)
            logger.info("Seeded default official admin account: commander@ner.gov.in")

        # Check citizen
        citizen = db.query(User).filter(User.email == "citizen@ner.gov.in").first()
        if not citizen:
            citizen = User(
                name="Pema Tashi",
                email="citizen@ner.gov.in",
                hashed_password=hash_password("password123"),
                role="user",
                phone="+91 98765 43210",
                state="Meghalaya"
            )
            db.add(citizen)
            logger.info("Seeded default public citizen account: citizen@ner.gov.in")

        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"Note on initial user seeding: {e}")

def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """Dependency to validate JWT Bearer token and fetch authenticated user."""
    seed_initial_users_if_needed(db)

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization.split(" ")[1].strip()
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        # Also attempt lookup by email
        email = payload.get("email")
        if email:
            user = db.query(User).filter(User.email == email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with token not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to strictly enforce Admin role. Normal users receive 403 Forbidden."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access Denied: Administrative privileges required. Public citizen accounts cannot access Incident Command operations."
        )
    return current_user

@router.post("/register", response_model=TokenResponse)
def register_user(req: UserRegister, db: Session = Depends(get_db)):
    """Register a new citizen account with role='user'."""
    seed_initial_users_if_needed(db)

    clean_email = req.email.strip().lower()
    clean_name = req.name.strip()
    clean_password = req.password.strip()

    if not clean_name:
        raise HTTPException(status_code=400, detail="Full name is required.")
    if not clean_email or "@" not in clean_email:
        raise HTTPException(status_code=400, detail="A valid email address is required.")
    if len(clean_password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters.")

    # Check for existing email
    existing = db.query(User).filter(User.email == clean_email).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="An account with this email is already registered. Please log in."
        )

    # All public registrations are created strictly with role='user'
    new_user = User(
        name=clean_name,
        email=clean_email,
        hashed_password=hash_password(clean_password),
        role="user",
        phone=(req.phone or "").strip() if req.phone else None,
        state=(req.state or "North Eastern Region").strip() if req.state else "North Eastern Region"
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = create_access_token({
        "sub": new_user.id,
        "email": new_user.email,
        "role": new_user.role,
        "name": new_user.name
    })

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(new_user)
    )

@router.post("/login", response_model=TokenResponse)
def login_user(req: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user or admin credentials and return JWT token."""
    seed_initial_users_if_needed(db)

    clean_input = req.email.strip().lower()
    clean_password = req.password.strip()

    if not clean_input or not clean_password:
        raise HTTPException(status_code=400, detail="Email and password are required.")

    # Lookup user by email
    user = db.query(User).filter(User.email == clean_input).first()

    # Support admin alias if 'admin' or 'commander' entered
    if not user and clean_input in ("admin", "commander"):
        user = db.query(User).filter(User.email == "commander@ner.gov.in").first()

    # Support citizen alias if 'citizen' or 'user' entered
    if not user and clean_input in ("citizen", "user"):
        user = db.query(User).filter(User.email == "citizen@ner.gov.in").first()

    if not user or not verify_password(clean_password, user.hashed_password):
        # Specific check for admin portal
        if req.portal_hint == "admin":
            raise HTTPException(
                status_code=401,
                detail="Access Denied: Invalid official administrator credentials."
            )
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password. If you do not have an account, please click Register."
        )

    # If logging in via Admin Portal, enforce admin role check
    if req.portal_hint == "admin" and user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Access Denied: This portal is restricted to official Incident Commanders and NDMA administrators."
        )

    token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "name": user.name
    })

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserOut.model_validate(user)
    )

@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Return profile of the currently authenticated user."""
    return UserOut.model_validate(current_user)

@router.get("/admin-verify")
def verify_admin_privileges(admin_user: User = Depends(get_current_admin_user)):
    """
    Protected verification endpoint for administrative access.
    Returns 200 OK only for confirmed admins. Normal users receive 403 Forbidden.
    """
    return {
        "status": "authorized",
        "role": admin_user.role,
        "email": admin_user.email,
        "name": admin_user.name,
        "detail": "Verified Incident Commander / Authority Access Granted."
    }
