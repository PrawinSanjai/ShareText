import uuid
from datetime import datetime, timezone
from fastapi import HTTPException

import models
from .crypto import encrypt_text_string, decode_text_string
from database import get_db

class TextService():
    def get_text(self, text_id: str):
        if not text_id:
            return {
                "message": "Please enter a valid text ID."
            }
        with get_db() as db:
            assoc_data = db.query(models.AssocTextDataKey).filter(models.AssocTextDataKey.text_data_id==text_id).first()
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
            
            final_text = ""
            for row in rows:
                decrypted_text = decode_text_string(row.hashed_text)
                final_text += decrypted_text
            
            return {
                "message": "Text fetched successfully.",
                "result": final_text
            }
            

    def store_text(self, text: str):
        if not text:
            return {
                "message": "Please enter a valid text."
            }
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
    
    def edit_text(self, text: str, secret_key: str):
        if not text:
            return {
                "message": "Please enter valid text."
            }

        if not secret_key:
            return {
                "message": "Please provide a valid secret key."
            }

        with get_db() as db:

            secret = db.query(models.TextSecretKey).filter(
                models.TextSecretKey.id == secret_key
            ).first()

            if not secret:
                raise HTTPException(status_code=403, detail="Invalid secret key.")

            if secret.is_deleted:
                raise HTTPException(status_code=404, detail="Text ID not found. Please enter a valid ID.")

            assoc_text_data = db.query(models.AssocTextDataKey).filter(
                models.AssocTextDataKey.text_secret_key == secret_key
            ).first()

            text_id = assoc_text_data.text_data_id

            db.query(models.TextData).filter(
                models.TextData.text_id == text_id
            ).delete()

            text_order = 1

            for i in range(0, len(text), 100):
                text_chunk = text[i:i+100]
                encrypted_chunk = encrypt_text_string(text=text_chunk)
                text_data = models.TextData(
                    id=text_id,
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
        with get_db() as db:
            secret = db.query(models.TextSecretKey).filter(models.TextSecretKey.id == secret_key).first()

            if not secret or secret.is_deleted:
                raise HTTPException(status_code=404, detail="Secret Key not found. Please enter a valid key.")
            
            # text_id = secret.text_data_id
            # db.query(models.TextData).filter(models.TextData.text_id == text_id).delete()

            secret.is_deleted = True
            secret.updated_at = datetime.now(timezone.utc)
            db.commit()

            return {"message": "Text deleted successfully."}