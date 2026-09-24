from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_id(self, user_id: int) -> User | None:
        return self._db.get(User, user_id)

    def find_by_email(self, email: str) -> User | None:
        normalized_email = self._normalize_email(email)
        statement = select(User).where(func.lower(User.email) == normalized_email)
        return self._db.scalar(statement)

    def mark_last_login(self, user: User) -> User:
        user.last_login_at = datetime.now(timezone.utc)
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user

    def _normalize_email(self, email: str) -> str:
        return email.strip().lower()
