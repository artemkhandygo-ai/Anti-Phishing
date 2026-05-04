from pydantic import BaseModel


class StatsSummary(BaseModel):
    total_incidents: int
    safe: int
    suspicious: int
    phishing: int
