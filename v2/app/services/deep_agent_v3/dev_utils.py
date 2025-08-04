
from sqlmodel import Session, select
from app.db.models_postgres import User

DEV_USER_EMAIL = "dev@example.com"

def get_or_create_dev_user(db_session: Session) -> User:
    """Get or create a dummy user for development purposes."""
    user = db_session.exec(select(User).where(User.email == DEV_USER_EMAIL)).first()
    if not user:
        user = User(email=DEV_USER_EMAIL, full_name="Development User", is_active=True)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user
