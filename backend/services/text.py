import uuid
import logging
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException

import models
from .crypto import encrypt_text_string, decode_text_string
from .passwords import hash_password, verify_password
from database import get_db

logger = logging.getLogger("share_text.audit")


def parse_uuid(value: str, field_name: str):
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}.")


class TextService():
    def _decode_rows(self, rows):
        final_text = ""
        for row in rows:
            final_text += decode_text_string(row.hashed_text)
        return final_text

    def _purge_expired_secret(self, db, secret):
        text_id = db.query(models.AssocTextDataKey.text_data_id).filter(
            models.AssocTextDataKey.text_secret_key == secret.id
        ).scalar()
        if text_id:
            db.query(models.TextData).filter(models.TextData.text_id == text_id).delete(synchronize_session=False)
            db.query(models.AssocTextDataKey).filter(
                models.AssocTextDataKey.text_secret_key == secret.id
            ).delete(synchronize_session=False)
        secret.is_deleted = True
        secret.updated_at = datetime.now(timezone.utc)

    def _get_active_secret(self, db, secret_key: str, lock: bool = False):
        secret_key_id = parse_uuid(secret_key, "secret key")
        query = db.query(models.TextSecretKey).filter(models.TextSecretKey.id == secret_key_id)
        if lock:
            query = query.with_for_update()
        secret = query.first()

        if not secret:
            raise HTTPException(status_code=403, detail="Invalid secret key.")

        if secret.is_deleted:
            raise HTTPException(status_code=404, detail="Text ID not found. Please enter a valid ID.")

        if secret.expires_at <= datetime.now(timezone.utc):
            raise HTTPException(status_code=404, detail="This text has expired.")

        return secret

    def _get_assoc_by_secret(self, db, secret_key: str):
        secret_key_id = parse_uuid(secret_key, "secret key")
        assoc_text_data = db.query(models.AssocTextDataKey).filter(
            models.AssocTextDataKey.text_secret_key == secret_key_id
        ).first()

        if not assoc_text_data:
            raise HTTPException(status_code=404, detail="Text ID not found. Please enter a valid ID.")

        return assoc_text_data

    def get_text(self, text_id: str, password: str | None = None):
        if not text_id:
            raise HTTPException(status_code=400, detail="Please enter a valid text ID.")
        text_uuid = parse_uuid(text_id, "text ID")

        with get_db() as db:
            assoc_data = db.query(models.AssocTextDataKey).filter(models.AssocTextDataKey.text_data_id==text_uuid).first()
            if not assoc_data:
                raise HTTPException(status_code=404, detail="Text ID not found. Please enter a valid ID.")
            
            text_secret_key = assoc_data.text_secret_key
            secret_key = db.query(models.TextSecretKey).filter(models.TextSecretKey.id==text_secret_key).first()

            if not secret_key or secret_key.is_deleted:
                raise HTTPException(status_code=404, detail="Text ID not found. Please enter a valid ID.")
            if secret_key.expires_at <= datetime.now(timezone.utc):
                raise HTTPException(status_code=404, detail="This text has expired.")

            if secret_key.password_hash:
                if password is None:
                    raise HTTPException(status_code=401, detail="This text requires a password.")
                if not verify_password(password, secret_key.password_hash):
                    raise HTTPException(status_code=403, detail="Incorrect password.")

            # Lock only view-limited shares. This makes the read counter atomic
            # without serializing traffic to ordinary, unlimited shares.
            remaining_views = None
            if secret_key.max_views is not None:
                secret_key = db.query(models.TextSecretKey).filter(
                    models.TextSecretKey.id == secret_key.id
                ).with_for_update().first()
                if (
                    not secret_key
                    or secret_key.is_deleted
                    or secret_key.expires_at <= datetime.now(timezone.utc)
                ):
                    raise HTTPException(status_code=404, detail="This text is no longer available.")
                if secret_key.password_hash and (
                    password is None or not verify_password(password, secret_key.password_hash)
                ):
                    raise HTTPException(status_code=403, detail="Incorrect password.")
                if secret_key.view_count >= secret_key.max_views:
                    raise HTTPException(status_code=404, detail="This text has reached its view limit.")
                secret_key.view_count += 1
                remaining_views = secret_key.max_views - secret_key.view_count
            
            rows = db.query(models.TextData).filter(
                        models.TextData.text_id == text_uuid
                    ).order_by(models.TextData.text_order).all()
            
            if not rows:
                raise HTTPException(status_code=404, detail="No data found.")
            
            result = {
                "message": "Text fetched successfully.",
                "result": self._decode_rows(rows),
                "remaining_views": remaining_views,
            }
            if secret_key.max_views is not None and remaining_views == 0:
                self._purge_expired_secret(db, secret_key)
                result["message"] = "Text fetched. This was the final view and the text has been deleted."
            return result
            

    def store_text(
        self,
        text: str,
        ttl_hours: int = 24,
        max_views: int | None = None,
        password: str | None = None,
    ):
        if not text or not text.strip():
            raise HTTPException(status_code=400, detail="Please enter a valid text.")

        with get_db() as db:
            text_id = uuid.uuid4()
            text_secret_key = uuid.uuid4()
            text_order = 1

            for i in range(0, len(text), 100):
                text_chunk = text[i:i+100]
                encrypted_text_chunk = encrypt_text_string(text=text_chunk)
                text_data = models.TextData(
                    text_id=text_id,
                    text_order=text_order,
                    hashed_text=encrypted_text_chunk
                )
                db.add(text_data)
                text_order += 1
            
            text_secret = models.TextSecretKey(
                id=text_secret_key,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                is_deleted=False,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=ttl_hours),
                max_views=max_views,
                view_count=0,
                password_hash=hash_password(password) if password else None,
            )
            db.add(text_secret)

            assoc_data = models.AssocTextDataKey(
                text_data_id=text_id,
                text_secret_key=text_secret_key
            )
            db.add(assoc_data)
            logger.info("text_stored text_id=%s", text_id)
            return {
                "text_id": str(text_id),
                "secret_key": str(text_secret_key),
                "expires_at": text_secret.expires_at.isoformat(),
                "max_views": max_views,
                "password_protected": bool(password),
            }

    def get_text_by_secret(self, secret_key: str):
        if not secret_key:
            raise HTTPException(status_code=400, detail="Please provide a valid secret key.")

        with get_db() as db:
            secret = self._get_active_secret(db, secret_key)
            assoc_text_data = self._get_assoc_by_secret(db, secret_key)
            rows = db.query(models.TextData).filter(
                models.TextData.text_id == assoc_text_data.text_data_id
            ).order_by(models.TextData.text_order).all()

            if not rows:
                raise HTTPException(status_code=404, detail="No data found.")

            return {
                "message": "Text fetched successfully.",
                "text_id": str(assoc_text_data.text_data_id),
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
            assoc_text_data = self._get_assoc_by_secret(db, secret_key)
            text_id = assoc_text_data.text_data_id

            db.query(models.TextData).filter(
                models.TextData.text_id == text_id
            ).delete()

            text_order = 1

            for i in range(0, len(text), 100):
                text_chunk = text[i:i+100]
                encrypted_chunk = encrypt_text_string(text=text_chunk)
                text_data = models.TextData(
                    text_id=text_id,
                    text_order=text_order,
                    hashed_text=encrypted_chunk
                )
                db.add(text_data)
                text_order += 1

            secret.updated_at = datetime.now(timezone.utc)
            logger.info("text_updated text_id=%s", text_id)

            return {
                "message": "Text updated successfully."
            }
    
    def delete_text(self, secret_key: str):
        if not secret_key:
            raise HTTPException(status_code=400, detail="Please provide a valid secret key.")

        with get_db() as db:
            secret = self._get_active_secret(db, secret_key, lock=True)
            assoc_text_data = self._get_assoc_by_secret(db, secret_key)
            text_id = assoc_text_data.text_data_id

            db.query(models.TextData).filter(
                models.TextData.text_id == text_id
            ).delete()
            db.query(models.AssocTextDataKey).filter(
                models.AssocTextDataKey.id == assoc_text_data.id
            ).delete()
            secret.is_deleted = True
            secret.updated_at = datetime.now(timezone.utc)
            logger.info("text_deleted text_id=%s", text_id)

            return {"message": "Text deleted successfully."}

    def purge_expired(self, batch_size: int = 200):
        """Claim expired rows in small, skip-locked batches so workers can clean in parallel."""
        now = datetime.now(timezone.utc)
        with get_db() as db:
            expired = db.query(models.TextSecretKey).filter(
                models.TextSecretKey.is_deleted.is_(False),
                models.TextSecretKey.expires_at <= now,
            ).order_by(models.TextSecretKey.expires_at).limit(batch_size).with_for_update(skip_locked=True).all()
            for secret in expired:
                self._purge_expired_secret(db, secret)
            if expired:
                logger.info("expired_texts_purged count=%d", len(expired))
            return len(expired)
