from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.app.schemas.models import LoginIn, MeOut, TokenOut
from backend.api.app.dependencies import get_current_user
from backend.db.models.orm import User
from backend.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).one_or_none()
    if user is None or body.password != "demo":
        raise HTTPException(status_code=401, detail="Invalid credentials (demo password is 'demo')")
    return TokenOut(access_token=f"demo:{user.email}")


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user)):
    return MeOut(id=str(user.id), name=user.name, email=user.email, role=user.role)
