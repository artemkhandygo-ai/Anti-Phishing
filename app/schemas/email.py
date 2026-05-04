from datetime import datetime
from pydantic import BaseModel


class EmailOut(BaseModel):
    id: int
    subject: str | None = None
    from_email: str | None = None
    from_name: str | None = None
    received_at: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True
