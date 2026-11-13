import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

import models
from database import get_db
from .crypto import decode_text_string, encrypt_text_string
from .passwords import hash_password, verify_password


logger = logging.getLogger("share_text.audit")
CHUNK_SIZE = 100


def parse_uuid(value: str, field_name: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}.")


class TextService:
    def _get_secret_for_text(self, db, text_id: uuid.UUID):
        association = db.query(models.AssocTextDataKey).filter(
            models.AssocTextDataKey.text_data_id == text_id
        ).first()
        if not association:
            raise HTTPException(status_code=404, detail="Text ID not found.")

        secret = db.query(models.TextSecretKey).filter(
            models.TextSecretKey.id == association.text_secret_key
        ).first()
        if not secret or secret.is_deleted:
            raise HTTPException(status_code=404, detail="Text ID not found.")
        return secret

    def _get_active_secret(self, db, secret_key: str, lock: bool = False):
        secret_id = parse_uuid(secret_key, "secret key")
        query = db.query(models.TextSecretKey).filter(models.TextSecretKey.id == secret_id)
        if lock:
            query = query.with_for_update()

        secret = query.first()
        if not secret:
            raise HTTPException(status_code=403, detail="Invalid secret key.")
        if secret.is_deleted:
            raise HTTPException(status_code=404, detail="Text not found.")
        self._check_expiry(secret)
        return secret

    @staticmethod
    def _check_expiry(secret):
        if secret.expires_at <= datetime.now(timezone.utc):
            raise HTTPException(status_code=404, detail="This text has expired.")

    @staticmethod
    def _get_text_rows(db, text_id: uuid.UUID):
        rows = db.query(models.TextData).filter(
            models.TextData.text_id == text_id
        ).order_by(models.TextData.text_order).all()
        if not rows:
            raise HTTPException(status_code=404, detail="No data found.")
        return rows

    @staticmethod
    def _decode_rows(rows) -> str:
        return "".join(decode_text_string(row.hashed_text) for row in rows)

    @staticmethod
    def _store_chunks(db, text_id: uuid.UUID, text: str):
        for order, start in enumerate(range(0, len(text), CHUNK_SIZE), start=1):
            chunk = text[start : start + CHUNK_SIZE]
            db.add(models.TextData(
                text_id=text_id,
                text_order=order,
                hashed_text=encrypt_text_string(chunk),
            ))

    @staticmethod
    def _delete_share_content(db, secret):
        text_id = db.query(models.AssocTextDataKey.text_data_id).filter(
            models.AssocTextDataKey.text_secret_key == secret.id
        ).scalar()

        if text_id:
            db.query(models.TextData).filter(
                models.TextData.text_id == text_id
            ).delete(synchronize_session=False)
            db.query(models.AssocTextDataKey).filter(
                models.AssocTextDataKey.text_secret_key == secret.id
            ).delete(synchronize_session=False)

        secret.is_deleted = True
        secret.updated_at = datetime.now(timezone.utc)

    def get_text(self, text_id: str, password: str | None = None):
        if not text_id:
            raise HTTPException(status_code=400, detail="Please enter a valid text ID.")

        text_uuid = parse_uuid(text_id, "text ID")
        with get_db() as db:
            secret = self._get_secret_for_text(db, text_uuid)
            self._check_expiry(secret)

            if secret.password_hash:
                if password is None:
                    raise HTTPException(status_code=401, detail="This text requires a password.")
                if not verify_password(password, secret.password_hash):
                    raise HTTPException(status_code=403, detail="Incorrect password.")

            remaining_views = None
            if secret.max_views is not None:
                # Lock capped shares so simultaneous reads cannot exceed the limit.
                secret = db.query(models.TextSecretKey).filter(
                    models.TextSecretKey.id == secret.id
                ).with_for_update().first()
                if not secret or secret.is_deleted:
                    raise HTTPException(status_code=404, detail="This text is no longer available.")
                self._check_expiry(secret)
                if secret.view_count >= secret.max_views:
                    raise HTTPException(status_code=404, detail="This text has reached its view limit.")

                secret.view_count += 1
                remaining_views = secret.max_views - secret.view_count

            text = self._decode_rows(self._get_text_rows(db, text_uuid))
            message = "Text fetched successfully."

            if remaining_views == 0:
                self._delete_share_content(db, secret)
                message = "Text fetched. This was the final view and the text has been deleted."

            return {
                "message": message,
                "result": text,
                "remaining_views": remaining_views,
            }

    def store_text(
        self,
        text: str,
        ttl_hours: int = 24,
        max_views: int | None = None,
        password: str | None = None,
    ):
        if not text or not text.strip():
            raise HTTPException(status_code=400, detail="Please enter a valid text.")

        text_id = uuid.uuid4()
        secret_id = uuid.uuid4()
        expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)

        with get_db() as db:
            self._store_chunks(db, text_id, text)
            db.add(models.TextSecretKey(
                id=secret_id,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                is_deleted=False,
                expires_at=expires_at,
                max_views=max_views,
                view_count=0,
                password_hash=hash_password(password) if password else None,
            ))
            db.add(models.AssocTextDataKey(
                text_data_id=text_id,
                text_secret_key=secret_id,
            ))

            logger.info("text_stored text_id=%s", text_id)
            return {
                "text_id": str(text_id),
                "secret_key": str(secret_id),
                "expires_at": expires_at.isoformat(),
                "max_views": max_views,
                "password_protected": bool(password),
            }

    def get_text_by_secret(self, secret_key: str):
        if not secret_key:
            raise HTTPException(status_code=400, detail="Please provide a valid secret key.")

        with get_db() as db:
            secret = self._get_active_secret(db, secret_key)
            association = db.query(models.AssocTextDataKey).filter(
                models.AssocTextDataKey.text_secret_key == secret.id
            ).first()
            if not association:
                raise HTTPException(status_code=404, detail="Text not found.")

            rows = self._get_text_rows(db, association.text_data_id)
            return {
                "message": "Text fetched successfully.",
                "text_id": str(association.text_data_id),
                "result": self._decode_rows(rows),
                "max_views": secret.max_views,
                "view_count": secret.view_count,
                "expires_at": secret.expires_at.isoformat(),
            }

    def edit_text(self, text: str, secret_key: str):
        if not text or not text.strip():
            raise HTTPException(status_code=400, detail="Please enter valid text.")
        if not secret_key:
            raise HTTPException(status_code=400, detail="Please provide a valid secret key.")

        with get_db() as db:
            secret = self._get_active_secret(db, secret_key, lock=True)
            association = db.query(models.AssocTextDataKey).filter(
                models.AssocTextDataKey.text_secret_key == secret.id
            ).first()
            if not association:
                raise HTTPException(status_code=404, detail="Text not found.")

            db.query(models.TextData).filter(
                models.TextData.text_id == association.text_data_id
            ).delete(synchronize_session=False)
            self._store_chunks(db, association.text_data_id, text)
            secret.updated_at = datetime.now(timezone.utc)
            logger.info("text_updated text_id=%s", association.text_data_id)
            return {"message": "Text updated successfully."}

    def delete_text(self, secret_key: str):
        if not secret_key:
            raise HTTPException(status_code=400, detail="Please provide a valid secret key.")

        with get_db() as db:
            secret = self._get_active_secret(db, secret_key, lock=True)
            self._delete_share_content(db, secret)
            logger.info("text_deleted secret_id=%s", secret.id)
            return {"message": "Text deleted successfully."}

    def purge_expired(self, batch_size: int = 200):
        """Delete one small batch of expired shares; multiple workers can run safely."""
        now = datetime.now(timezone.utc)
        with get_db() as db:
            expired = db.query(models.TextSecretKey).filter(
                models.TextSecretKey.is_deleted.is_(False),
                models.TextSecretKey.expires_at <= now,
            ).order_by(models.TextSecretKey.expires_at).limit(batch_size).with_for_update(skip_locked=True).all()

            for secret in expired:
                self._delete_share_content(db, secret)

            if expired:
                logger.info("expired_texts_purged count=%d", len(expired))
            return len(expired)
