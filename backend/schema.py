from pydantic import BaseModel, Field

class StoreTextReq(BaseModel):
    text: str = Field(min_length=1, max_length=40000)


class EditTextReq(BaseModel):
    text: str = Field(min_length=1, max_length=40000)
    secret_key: str = Field(min_length=1, max_length=64)


class SecretKeyReq(BaseModel):
    secret_key: str = Field(min_length=1, max_length=64)
