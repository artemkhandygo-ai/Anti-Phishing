from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.stats import StatsSummary
from app.services.stats_service import get_summary

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/summary", response_model=StatsSummary, include_in_schema=False)
def stats_summary(db: Session = Depends(get_db)):
    return get_summary(db)
