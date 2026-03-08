from sqlalchemy import Column, UUID, Integer, Text, Boolean, DateTime
from datetime import datetime, timezone
from uuid import uuid4

from database import base



class TextData(base):
    __tablename__ = "text_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    text_id = Column(UUID, unique=False, nullable=False)
    text_order = Column(Integer, unique=False, nullable=False)
    hashed_text = Column(Text, unique=False, nullable=True)


class TextSecretKey(base):
    __tablename__ = "text_secret_key"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at = Column(DateTime, nullable=False, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=datetime.now(timezone.utc))
    is_deleted = Column(Boolean, default=True, nullable=False)


class AssocTextDataKey(base):
    __tablename__ = "assoc_text_data_key"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    text_data_id = Column(UUID, nullable=False, unique=True)
    text_secret_key = Column(UUID, nullable=False, unique=True)