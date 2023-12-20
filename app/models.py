from pydantic import BaseModel

class BillRequest(BaseModel):
    url: str
