from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Email(Base):
    __tablename__ = "emails"
    __table_args__ = (
        UniqueConstraint("imap_uid", name="uq_emails_imap_uid"),
        UniqueConstraint("message_id", name="uq_emails_message_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    imap_uid: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    message_id: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    subject: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    from_email: Mapped[str | None] = mapped_column(String(512), nullable=True, index=True)
    from_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    text_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    html_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_headers: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow)

    links: Mapped[list["EmailLink"]] = relationship(back_populates="email", cascade="all, delete-orphan")
    attachments: Mapped[list["EmailAttachment"]] = relationship(back_populates="email", cascade="all, delete-orphan")
    incidents: Mapped[list["Incident"]] = relationship(back_populates="email", cascade="all, delete-orphan")


class EmailLink(Base):
    __tablename__ = "email_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email_id: Mapped[int] = mapped_column(ForeignKey("emails.id", ondelete="CASCADE"))
    url: Mapped[str] = mapped_column(Text)
    domain: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_shortened: Mapped[bool] = mapped_column(Boolean, default=False)
    is_suspicious: Mapped[bool] = mapped_column(Boolean, default=False)

    email: Mapped["Email"] = relationship(back_populates="links")


class EmailAttachment(Base):
    __tablename__ = "email_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email_id: Mapped[int] = mapped_column(ForeignKey("emails.id", ondelete="CASCADE"))
    filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extension: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_suspicious: Mapped[bool] = mapped_column(Boolean, default=False)

    email: Mapped["Email"] = relationship(back_populates="attachments")


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email_id: Mapped[int] = mapped_column(ForeignKey("emails.id", ondelete="CASCADE"))
    risk_level: Mapped[str] = mapped_column(String(32), index=True)
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    rule_score: Mapped[float] = mapped_column(Float, default=0.0)
    ml_score: Mapped[float] = mapped_column(Float, default=0.0)
    model_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(64), default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow)

    email: Mapped["Email"] = relationship(back_populates="incidents")
    reasons: Mapped[list["IncidentReason"]] = relationship(back_populates="incident", cascade="all, delete-orphan")
    notifications: Mapped[list["TelegramNotification"]] = relationship(back_populates="incident", cascade="all, delete-orphan")
    feedback: Mapped[list["IncidentFeedback"]] = relationship(back_populates="incident", cascade="all, delete-orphan")


class IncidentReason(Base):
    __tablename__ = "incident_reasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"))
    reason_code: Mapped[str] = mapped_column(String(128), index=True)
    reason_text: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(32), default="medium")

    incident: Mapped["Incident"] = relationship(back_populates="reasons")


class TelegramNotification(Base):
    __tablename__ = "telegram_notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"))
    chat_id: Mapped[str] = mapped_column(String(128))
    telegram_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    delivery_status: Mapped[str] = mapped_column(String(64), default="pending")
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow)

    incident: Mapped["Incident"] = relationship(back_populates="notifications")


class IncidentFeedback(Base):
    __tablename__ = "incident_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id", ondelete="CASCADE"))
    feedback_type: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow)

    incident: Mapped["Incident"] = relationship(back_populates="feedback")


class AppState(Base):
    __tablename__ = "app_state"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), default=datetime.utcnow, onupdate=datetime.utcnow)
