
import uuid
from sqlalchemy import Column, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from app.db.postgres import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String)
    picture = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
