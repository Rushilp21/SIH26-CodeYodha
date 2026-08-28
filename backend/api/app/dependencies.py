from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from backend.db.models.orm import User
from backend.db.session import get_db


def get_current_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    email = token
    if token.startswith("demo:"):
        email = token.split(":", 1)[1]
    user = db.query(User).filter(User.email == email).one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return user
