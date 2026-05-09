import uuid
from datetime import datetime, timezone
from fastapi import HTTPException

import models
from .crypto import encrypt_text_string, decode_text_string
from database import get_db


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

    def _get_active_secret(self, db, secret_key: str):
        secret_key_id = parse_uuid(secret_key, "secret key")
        secret = db.query(models.TextSecretKey).filter(
            models.TextSecretKey.id == secret_key_id
        ).first()

        if not secret:
            raise HTTPException(status_code=403, detail="Invalid secret key.")

        if secret.is_deleted:
            raise HTTPException(status_code=404, detail="Text ID not found. Please enter a valid ID.")

        return secret

    def _get_assoc_by_secret(self, db, secret_key: str):
        secret_key_id = parse_uuid(secret_key, "secret key")
        assoc_text_data = db.query(models.AssocTextDataKey).filter(
            models.AssocTextDataKey.text_secret_key == secret_key_id
        ).first()

        if not assoc_text_data:
            raise HTTPException(status_code=404, detail="Text ID not found. Please enter a valid ID.")

        return assoc_text_data

    def get_text(self, text_id: str):
        if not text_id:
            raise HTTPException(status_code=400, detail="Please enter a valid text ID.")
        text_uuid = parse_uuid(text_id, "text ID")

        with get_db() as db:
            assoc_data = db.query(models.AssocTextDataKey).filter(models.AssocTextDataKey.text_data_id==text_uuid).first()
            if not assoc_data:
                raise HTTPException(status_code=404, detail="Text ID not found. Please enter a valid ID.")
            
            text_secret_key = assoc_data.text_secret_key
            secret_key = db.query(models.TextSecretKey).filter(models.TextSecretKey.id==text_secret_key).first()

            if secret_key.is_deleted:
                raise HTTPException(status_code=404, detail="Text ID not found. Please enter a valid ID.")
            
            rows = db.query(models.TextData).filter(
                        models.TextData.text_id == text_id
                    ).order_by(models.TextData.text_order).all()
            
            if not rows:
                raise HTTPException(status_code=404, detail="No data found.")
            
            return {
                "message": "Text fetched successfully.",
                "result": self._decode_rows(rows)
            }
            

    def store_text(self, text: str):
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
                is_deleted=False
            )
            db.add(text_secret)

            assoc_data = models.AssocTextDataKey(
                text_data_id=text_id,
                text_secret_key=text_secret_key
            )
            db.add(assoc_data)
            db.commit()
            return {
                "text_id": str(text_id),
                "secret_key": str(text_secret_key)
            }

    def get_text_by_secret(self, secret_key: str):
        if not secret_key:
            raise HTTPException(status_code=400, detail="Please provide a valid secret key.")

        with get_db() as db:
            self._get_active_secret(db, secret_key)
            assoc_text_data = self._get_assoc_by_secret(db, secret_key)
            rows = db.query(models.TextData).filter(
                models.TextData.text_id == assoc_text_data.text_data_id
            ).order_by(models.TextData.text_order).all()

            if not rows:
                raise HTTPException(status_code=404, detail="No data found.")

            return {
                "message": "Text fetched successfully.",
                "text_id": str(assoc_text_data.text_data_id),
                "result": self._decode_rows(rows)
            }
    
    def edit_text(self, text: str, secret_key: str):
        if not text or not text.strip():
            raise HTTPException(status_code=400, detail="Please enter valid text.")

        if not secret_key:
            raise HTTPException(status_code=400, detail="Please provide a valid secret key.")

        with get_db() as db:
            secret = self._get_active_secret(db, secret_key)
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
            db.commit()

            return {
                "message": "Text updated successfully."
            }
    
    def delete_text(self, secret_key: str):
        if not secret_key:
            raise HTTPException(status_code=400, detail="Please provide a valid secret key.")

        with get_db() as db:
            secret = self._get_active_secret(db, secret_key)

            secret.is_deleted = True
            secret.updated_at = datetime.now(timezone.utc)
            db.commit()

            return {"message": "Text deleted successfully."}
