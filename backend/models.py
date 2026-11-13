from sqlalchemy import Column, UUID, Integer, Text, Boolean, DateTime, Index, CheckConstraint
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
    __table_args__ = (
        CheckConstraint("max_views IS NULL OR max_views > 0", name="positive_max_views"),
        CheckConstraint("view_count >= 0", name="nonnegative_view_count"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    is_deleted = Column(Boolean, default=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    max_views = Column(Integer, nullable=True)
    view_count = Column(Integer, nullable=False, default=0, server_default="0")
    password_hash = Column(Text, nullable=True)


class AssocTextDataKey(base):
    __tablename__ = "assoc_text_data_key"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    text_data_id = Column(UUID, nullable=False, unique=True, index=True)
    text_secret_key = Column(UUID, nullable=False, unique=True, index=True)


Index("ix_text_data_text_id_order", TextData.text_id, TextData.text_order, unique=True)
