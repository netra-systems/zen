import uuid
from sqlalchemy import Column, String, DateTime, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.sql import func
from app.db.postgres import Base
from app.schemas.Message import MessageType

class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    content = Column(String, nullable=False)
    type = Column(ENUM(MessageType, name="message_type"), nullable=False)
    sub_agent_name = Column(String)
    tool_info = Column(JSON)
    raw_data = Column(JSON)
    displayed_to_user = Column(Boolean, default=True)
