from pydantic import BaseModel

class StoreTextReq(BaseModel):
    text: str