"""add agentic knowledge models

Revision ID: 25c8947d715a
Revises: 507061b0f5f0
Create Date: 2026-09-21 16:48:30.625773

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.mssql import NVARCHAR

revision: str = "25c8947d715a"
down_revision: Union[str, None] = "507061b0f5f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _identity() -> sa.Identity:
    return sa.Identity(start=1, increment=1)


def _created_at() -> sa.Column:
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        server_default=sa.func.sysutcdatetime(),
        nullable=False,
    )


def _updated_at() -> sa.Column:
    return sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        server_default=sa.func.sysutcdatetime(),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), _identity(), nullable=False),
        sa.Column("name", sa.Unicode(length=255), nullable=False),
        sa.Column("document_type", sa.Unicode(length=50), nullable=False),
        sa.Column("description", NVARCHAR(length=None), nullable=True),
        sa.Column("category", sa.Unicode(length=100), nullable=True),
        sa.Column("source_system", sa.Unicode(length=100), nullable=True),
        sa.Column("current_version_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"), nullable=False),
        _created_at(),
        _updated_at(),
        sa.PrimaryKeyConstraint("id", name="pk_documents"),
    )
    op.create_table(
        "document_versions",
        sa.Column("id", sa.Integer(), _identity(), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("file_name", sa.Unicode(length=255), nullable=False),
        sa.Column("file_type", sa.Unicode(length=20), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("blob_container", sa.Unicode(length=255), nullable=False),
        sa.Column("blob_path", sa.Unicode(length=1000), nullable=False),
        sa.Column("blob_url", sa.Unicode(length=2000), nullable=True),
        sa.Column("checksum", sa.Unicode(length=128), nullable=False),
        sa.Column("status", sa.Unicode(length=50), server_default=sa.text("'UPLOADED'"), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("overall_confidence", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.sysutcdatetime(),
            nullable=False,
        ),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=True),
        sa.Column("approved_by_user_id", sa.Integer(), nullable=True),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_document_versions"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            name="fk_document_versions_document_id_documents",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"],
            ["users.id"],
            name="fk_document_versions_uploaded_by_user_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_user_id"],
            ["users.id"],
            name="fk_document_versions_approved_by_user_id_users",
        ),
        sa.UniqueConstraint(
            "document_id",
            "version_number",
            name="uq_document_versions_document_id_version_number",
        ),
    )
    op.create_foreign_key(
        "fk_documents_current_version_id_document_versions",
        "documents",
        "document_versions",
        ["current_version_id"],
        ["id"],
    )
    op.create_table(
        "chunks",
        sa.Column("id", sa.Integer(), _identity(), nullable=False),
        sa.Column("document_version_id", sa.Integer(), nullable=False),
        sa.Column("chunk_number", sa.Integer(), nullable=False),
        sa.Column("content", NVARCHAR(length=None), nullable=False),
        sa.Column("section_title", sa.Unicode(length=500), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("content_type", sa.Unicode(length=50), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("current_interpretation_id", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 2), nullable=True),
        sa.Column("status", sa.Unicode(length=50), server_default=sa.text("'CREATED'"), nullable=False),
        sa.Column("ai_search_document_id", sa.Unicode(length=255), nullable=True),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=True),
        _created_at(),
        _updated_at(),
        sa.PrimaryKeyConstraint("id", name="pk_chunks"),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.id"],
            name="fk_chunks_document_version_id_document_versions",
        ),
        sa.UniqueConstraint(
            "document_version_id",
            "chunk_number",
            name="uq_chunks_document_version_id_chunk_number",
        ),
    )
    op.create_table(
        "chunk_interpretations",
        sa.Column("id", sa.Integer(), _identity(), nullable=False),
        sa.Column("chunk_id", sa.Integer(), nullable=False),
        sa.Column("interpretation_version", sa.Integer(), nullable=False),
        sa.Column("interpretation", NVARCHAR(length=None), nullable=False),
        sa.Column("structured_content", sa.JSON(), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 2), nullable=False),
        sa.Column("model_name", sa.Unicode(length=100), nullable=False),
        sa.Column("prompt_version", sa.Unicode(length=50), nullable=True),
        sa.Column("based_on_interpretation_id", sa.Integer(), nullable=True),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_chunk_interpretations"),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["chunks.id"],
            name="fk_chunk_interpretations_chunk_id_chunks",
        ),
        sa.ForeignKeyConstraint(
            ["based_on_interpretation_id"],
            ["chunk_interpretations.id"],
            name="fk_chunk_interpretations_based_on_interpretation_id_chunk_interpretations",
        ),
        sa.UniqueConstraint(
            "chunk_id",
            "interpretation_version",
            name="uq_chunk_interpretations_chunk_id_interpretation_version",
        ),
    )
    op.create_foreign_key(
        "fk_chunks_current_interpretation_id_chunk_interpretations",
        "chunks",
        "chunk_interpretations",
        ["current_interpretation_id"],
        ["id"],
    )
    op.create_table(
        "human_feedbacks",
        sa.Column("id", sa.Integer(), _identity(), nullable=False),
        sa.Column("document_version_id", sa.Integer(), nullable=False),
        sa.Column("chunk_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.Unicode(length=50), nullable=False),
        sa.Column("feedback_text", NVARCHAR(length=None), nullable=True),
        sa.Column("previous_interpretation_id", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_human_feedbacks"),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.id"],
            name="fk_human_feedbacks_document_version_id_document_versions",
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["chunks.id"],
            name="fk_human_feedbacks_chunk_id_chunks",
        ),
        sa.ForeignKeyConstraint(
            ["previous_interpretation_id"],
            ["chunk_interpretations.id"],
            name="fk_human_feedbacks_previous_interpretation_id_chunk_interpretations",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_human_feedbacks_created_by_user_id_users",
        ),
    )
    op.create_table(
        "processing_executions",
        sa.Column("id", sa.Integer(), _identity(), nullable=False),
        sa.Column("document_version_id", sa.Integer(), nullable=False),
        sa.Column("execution_type", sa.Unicode(length=50), nullable=False),
        sa.Column("status", sa.Unicode(length=50), server_default=sa.text("'RUNNING'"), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.sysutcdatetime(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("chunks_processed", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("chunks_requiring_review", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("chunks_approved", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("error_message", NVARCHAR(length=None), nullable=True),
        sa.Column("execution_metadata", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_processing_executions"),
        sa.ForeignKeyConstraint(
            ["document_version_id"],
            ["document_versions.id"],
            name="fk_processing_executions_document_version_id_document_versions",
        ),
    )
    op.create_table(
        "query_sessions",
        sa.Column("id", sa.Integer(), _identity(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.sysutcdatetime(),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Unicode(length=50), server_default=sa.text("'ACTIVE'"), nullable=False),
        sa.Column(
            "controller_type",
            sa.Unicode(length=50),
            server_default=sa.text("'AI_AGENT'"),
            nullable=False,
        ),
        sa.Column("controller_user_id", sa.Integer(), nullable=True),
        sa.Column("session_metadata", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_query_sessions"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_query_sessions_user_id_users"),
        sa.ForeignKeyConstraint(
            ["controller_user_id"],
            ["users.id"],
            name="fk_query_sessions_controller_user_id_users",
        ),
    )
    op.create_table(
        "query_messages",
        sa.Column("id", sa.Integer(), _identity(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.Unicode(length=50), nullable=False),
        sa.Column("content", NVARCHAR(length=None), nullable=False),
        sa.Column("sender_user_id", sa.Integer(), nullable=True),
        sa.Column("search_query", NVARCHAR(length=None), nullable=True),
        sa.Column("retrieval_attempt", sa.Integer(), nullable=True),
        sa.Column("context_sufficient", sa.Boolean(), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 2), nullable=True),
        sa.Column("answer_status", sa.Unicode(length=50), nullable=True),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_query_messages"),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["query_sessions.id"],
            name="fk_query_messages_session_id_query_sessions",
        ),
        sa.ForeignKeyConstraint(
            ["sender_user_id"],
            ["users.id"],
            name="fk_query_messages_sender_user_id_users",
        ),
    )
    op.create_table(
        "query_citations",
        sa.Column("id", sa.Integer(), _identity(), nullable=False),
        sa.Column("query_message_id", sa.Integer(), nullable=False),
        sa.Column("chunk_id", sa.Integer(), nullable=False),
        sa.Column("relevance_score", sa.Numeric(5, 2), nullable=True),
        sa.Column("citation_order", sa.Integer(), nullable=False),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_query_citations"),
        sa.ForeignKeyConstraint(
            ["query_message_id"],
            ["query_messages.id"],
            name="fk_query_citations_query_message_id_query_messages",
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"],
            ["chunks.id"],
            name="fk_query_citations_chunk_id_chunks",
        ),
        sa.UniqueConstraint(
            "query_message_id",
            "citation_order",
            name="uq_query_citations_query_message_id_citation_order",
        ),
    )
    op.create_table(
        "query_handoffs",
        sa.Column("id", sa.Integer(), _identity(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("from_controller_type", sa.Unicode(length=50), nullable=False),
        sa.Column("to_controller_type", sa.Unicode(length=50), nullable=False),
        sa.Column("from_user_id", sa.Integer(), nullable=True),
        sa.Column("to_user_id", sa.Integer(), nullable=True),
        sa.Column("initiated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Unicode(length=1000), nullable=True),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_query_handoffs"),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["query_sessions.id"],
            name="fk_query_handoffs_session_id_query_sessions",
        ),
        sa.ForeignKeyConstraint(
            ["from_user_id"],
            ["users.id"],
            name="fk_query_handoffs_from_user_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["to_user_id"],
            ["users.id"],
            name="fk_query_handoffs_to_user_id_users",
        ),
        sa.ForeignKeyConstraint(
            ["initiated_by_user_id"],
            ["users.id"],
            name="fk_query_handoffs_initiated_by_user_id_users",
        ),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Integer(), _identity(), nullable=False),
        sa.Column("entity_type", sa.Unicode(length=50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.Unicode(length=50), nullable=False),
        sa.Column("actor_type", sa.Unicode(length=50), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("event_data", sa.JSON(), nullable=True),
        _created_at(),
        sa.PrimaryKeyConstraint("id", name="pk_audit_events"),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            name="fk_audit_events_actor_user_id_users",
        ),
    )
    op.create_index(
        "ix_audit_events_entity_type_entity_id",
        "audit_events",
        ["entity_type", "entity_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_audit_events_entity_type_entity_id", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_table("query_handoffs")
    op.drop_table("query_citations")
    op.drop_table("query_messages")
    op.drop_table("query_sessions")
    op.drop_table("processing_executions")
    op.drop_table("human_feedbacks")
    op.drop_constraint(
        "fk_chunks_current_interpretation_id_chunk_interpretations",
        "chunks",
        type_="foreignkey",
    )
    op.drop_table("chunk_interpretations")
    op.drop_table("chunks")
    op.drop_constraint(
        "fk_documents_current_version_id_document_versions",
        "documents",
        type_="foreignkey",
    )
    op.drop_table("document_versions")
    op.drop_table("documents")
