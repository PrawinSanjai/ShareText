from fastapi import APIRouter

from services.text import TextService
from schema import EditTextReq, SecretKeyReq, StoreTextReq

router = APIRouter()
text_service = TextService()

@router.get("/{text_id}")
def get_text(text_id: str):
    return text_service.get_text(text_id=text_id)

@router.post("/store")
def store_text(data: StoreTextReq):
    return text_service.store_text(data.text)

@router.post("/manage")
def get_text_by_secret(data: SecretKeyReq):
    return text_service.get_text_by_secret(data.secret_key)

@router.put("/edit")
def edit_text(data: EditTextReq):
    return text_service.edit_text(data.text, data.secret_key)

@router.delete("/delete")
def delete_text(data: SecretKeyReq):
    return text_service.delete_text(data.secret_key)
