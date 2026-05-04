"""initial schema

Revision ID: 0001_initial
Revises: None
Create Date: 2026-04-29 00:00:00
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "emails",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("imap_uid", sa.String(length=255), nullable=True),
        sa.Column("message_id", sa.String(length=512), nullable=True),
        sa.Column("subject", sa.String(length=1000), nullable=True),
        sa.Column("from_email", sa.String(length=512), nullable=True),
        sa.Column("from_name", sa.String(length=512), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("text_body", sa.Text(), nullable=True),
        sa.Column("html_body", sa.Text(), nullable=True),
        sa.Column("raw_headers", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.UniqueConstraint("imap_uid", name="uq_emails_imap_uid"),
        sa.UniqueConstraint("message_id", name="uq_emails_message_id"),
    )
    op.create_index("ix_emails_id", "emails", ["id"])
    op.create_index("ix_emails_imap_uid", "emails", ["imap_uid"])
    op.create_index("ix_emails_message_id", "emails", ["message_id"])
    op.create_index("ix_emails_from_email", "emails", ["from_email"])

    op.create_table(
        "app_state",
        sa.Column("key", sa.String(length=128), primary_key=True),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=False), nullable=False),
    )

    op.create_table(
        "email_links",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email_id", sa.Integer(), sa.ForeignKey("emails.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("domain", sa.String(length=512), nullable=True),
        sa.Column("is_shortened", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_suspicious", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_table(
        "email_attachments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email_id", sa.Integer(), sa.ForeignKey("emails.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=True),
        sa.Column("content_type", sa.String(length=255), nullable=True),
        sa.Column("size", sa.Integer(), nullable=True),
        sa.Column("extension", sa.String(length=32), nullable=True),
        sa.Column("is_suspicious", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email_id", sa.Integer(), sa.ForeignKey("emails.id", ondelete="CASCADE"), nullable=False),
        sa.Column("risk_level", sa.String(length=32), nullable=False),
        sa.Column("risk_score", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("rule_score", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("ml_score", sa.Float(), nullable=False, server_default=sa.text("0.0")),
        sa.Column("model_version", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=False, server_default=sa.text("'new'")),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
    )
    op.create_index("ix_incidents_id", "incidents", ["id"])
    op.create_index("ix_incidents_risk_level", "incidents", ["risk_level"])
    op.create_table(
        "incident_reasons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("incident_id", sa.Integer(), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reason_code", sa.String(length=128), nullable=False),
        sa.Column("reason_text", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default=sa.text("'medium'")),
    )
    op.create_index("ix_incident_reasons_reason_code", "incident_reasons", ["reason_code"])
    op.create_table(
        "telegram_notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("incident_id", sa.Integer(), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chat_id", sa.String(length=128), nullable=False),
        sa.Column("telegram_message_id", sa.String(length=128), nullable=True),
        sa.Column("delivery_status", sa.String(length=64), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("sent_at", sa.DateTime(timezone=False), nullable=False),
    )
    op.create_table(
        "incident_feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("incident_id", sa.Integer(), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("feedback_type", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("incident_feedback")
    op.drop_table("telegram_notifications")
    op.drop_index("ix_incident_reasons_reason_code", table_name="incident_reasons")
    op.drop_table("incident_reasons")
    op.drop_index("ix_incidents_risk_level", table_name="incidents")
    op.drop_index("ix_incidents_id", table_name="incidents")
    op.drop_table("incidents")
    op.drop_table("email_attachments")
    op.drop_table("email_links")
    op.drop_table("app_state")
    op.drop_index("ix_emails_from_email", table_name="emails")
    op.drop_index("ix_emails_message_id", table_name="emails")
    op.drop_index("ix_emails_imap_uid", table_name="emails")
    op.drop_index("ix_emails_id", table_name="emails")
    op.drop_table("emails")
