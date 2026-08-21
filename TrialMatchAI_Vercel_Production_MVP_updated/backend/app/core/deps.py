from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models import User
from backend.app.core.security import decode_token

bearer = HTTPBearer(auto_error=False)

def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    # Bypass authentication for hackathon demo
    user = db.query(User).first()
    if not user:
        # Create a mock user if none exists
        user = User(id=1, email="researcher@trialmatch.ai", is_active=True)
    return user
