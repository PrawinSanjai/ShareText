from pydantic import BaseModel

class StoreTextReq(BaseModel):
    text: str


class EditTextReq(BaseModel):
    text: str
    secret_key: str


class SecretKeyReq(BaseModel):
    secret_key: str
