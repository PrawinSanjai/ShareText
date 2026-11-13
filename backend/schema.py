from pydantic import BaseModel, Field

MAX_TEXT_LENGTH = 40000

class StoreTextReq(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    ttl_hours: int = Field(default=24, ge=1, le=168)
    max_views: int | None = Field(default=None, ge=1, le=1000)
    password: str | None = Field(default=None, min_length=8, max_length=128)


class ReadTextReq(BaseModel):
    password: str | None = Field(default=None, max_length=128)


class EditTextReq(BaseModel):
    text: str = Field(min_length=1, max_length=MAX_TEXT_LENGTH)
    secret_key: str = Field(min_length=1, max_length=64)


class SecretKeyReq(BaseModel):
    secret_key: str = Field(min_length=1, max_length=64)
