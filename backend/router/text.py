from fastapi import APIRouter

from services.text import TextService
from schema import StoreTextReq

router = APIRouter()
text_service = TextService()

@router.post("/get")
def get_text(text_id: str):
    return text_service.get_text(text_id)

@router.post("/store")
def store_text(data: StoreTextReq):
    return text_service.store_text(data.text)

@router.put("/edit")
def edit_text(text: str, secret_key: str):
    return text_service.edit_text(text, secret_key)

@router.delete("/delete")
def delete_text(secret_key: str):
    return text_service.delete_text(secret_key)