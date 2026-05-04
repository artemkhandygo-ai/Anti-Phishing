from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.repositories import EmailRepository
from app.db.session import get_db
from app.schemas.email import EmailOut
from app.tasks.email_tasks import fetch_and_analyze_emails

router = APIRouter(prefix="/emails", tags=["emails"])


@router.get("", response_model=list[EmailOut], include_in_schema=False)
def list_emails(limit: int = 50, db: Session = Depends(get_db)):
    return EmailRepository(db).list(limit=limit)


@router.get("/{email_id}", response_model=EmailOut, include_in_schema=False)
def get_email(email_id: int, db: Session = Depends(get_db)):
    email = EmailRepository(db).get(email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    return email


@router.post("/fetch", include_in_schema=False)
def fetch_emails(limit: int = 10):
    task = fetch_and_analyze_emails.delay(limit=limit)
    return {"task_id": task.id, "status": "queued"}
