from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator

from .config import get_settings
from .database import Base

try:  # pgvector is only required on PostgreSQL
    from pgvector.sqlalchemy import Vector
except Exception:  # pragma: no cover
    Vector = None


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class EmbeddingType(TypeDecorator):
    """pgvector `vector(N)` on PostgreSQL, JSON list elsewhere (SQLite dev/test)."""
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql" and Vector is not None:
            return dialect.type_descriptor(Vector(get_settings().embedding_dim))
        return dialect.type_descriptor(JSON(none_as_null=True))  # real SQL NULL, not JSON 'null'

    def process_bind_param(self, value, dialect):
        return None if value is None else [float(x) for x in value]

    def process_result_value(self, value, dialect):
        return None if value is None else [float(x) for x in value]


def _ts():
    return mapped_column(DateTime(timezone=True), default=utcnow)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    full_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(20), index=True)  # creator | entrepreneur | admin
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)  # entrepreneurs verified by an admin
    created_at: Mapped[datetime] = _ts()
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    creator_profile: Mapped[Optional["CreatorProfile"]] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    entrepreneur_profile: Mapped[Optional["EntrepreneurProfile"]] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    ideas: Mapped[List["Idea"]] = relationship(back_populates="creator", cascade="all, delete-orphan")


class CreatorProfile(Base):
    __tablename__ = "creator_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    headline: Mapped[str] = mapped_column(String(160), default="")
    bio: Mapped[str] = mapped_column(Text, default="")
    organization: Mapped[str] = mapped_column(String(160), default="")
    location: Mapped[str] = mapped_column(String(120), default="")
    website: Mapped[str] = mapped_column(String(255), default="")
    skills: Mapped[list] = mapped_column(JSON, default=list)
    user: Mapped[User] = relationship(back_populates="creator_profile")


class EntrepreneurProfile(Base):
    __tablename__ = "entrepreneur_profiles"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    company_name: Mapped[str] = mapped_column(String(160), default="")
    company_type: Mapped[str] = mapped_column(String(40), default="startup")  # startup|investor|corporate|other
    bio: Mapped[str] = mapped_column(Text, default="")
    website: Mapped[str] = mapped_column(String(255), default="")
    location: Mapped[str] = mapped_column(String(120), default="")
    industries: Mapped[list] = mapped_column(JSON, default=list)
    technologies: Mapped[list] = mapped_column(JSON, default=list)
    interests: Mapped[str] = mapped_column(Text, default="")
    preferred_stages: Mapped[list] = mapped_column(JSON, default=list)
    target_markets: Mapped[list] = mapped_column(JSON, default=list)
    investment_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    investment_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    embedding = mapped_column(EmbeddingType, nullable=True)
    embedding_model: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    user: Mapped[User] = relationship(back_populates="entrepreneur_profile")


class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(20))  # industry | technology
    description: Mapped[str] = mapped_column(String(255), default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (UniqueConstraint("name", "kind", name="uq_category_name_kind"),)


class Idea(Base):
    __tablename__ = "ideas"
    id: Mapped[int] = mapped_column(primary_key=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(160))
    short_description: Mapped[str] = mapped_column(String(500))
    problem: Mapped[str] = mapped_column(Text)
    solution: Mapped[str] = mapped_column(Text)
    industry: Mapped[str] = mapped_column(String(80), index=True)
    target_audience: Mapped[str] = mapped_column(String(500))
    technologies: Mapped[list] = mapped_column(JSON, default=list)
    stage: Mapped[str] = mapped_column(String(20), default="concept")  # concept|research|prototype|mvp|launched
    expected_impact: Mapped[str] = mapped_column(Text, default="")
    business_potential: Mapped[str] = mapped_column(Text, default="")
    funding_needed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    visibility: Mapped[str] = mapped_column(String(20), default="public", index=True)  # public|restricted|private
    moderation_status: Mapped[str] = mapped_column(String(20), default="active", index=True)  # active|hidden|removed
    embedding = mapped_column(EmbeddingType, nullable=True)
    embedding_model: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = _ts()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    creator: Mapped[User] = relationship(back_populates="ideas")
    documents: Mapped[List["IdeaDocument"]] = relationship(back_populates="idea", cascade="all, delete-orphan")
    evaluations: Mapped[List["Evaluation"]] = relationship(back_populates="idea", cascade="all, delete-orphan",
                                                          order_by="Evaluation.version.desc()")


class IdeaDocument(Base):
    __tablename__ = "idea_documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    idea_id: Mapped[int] = mapped_column(ForeignKey("ideas.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(80), unique=True)
    content_type: Mapped[str] = mapped_column(String(120))
    size: Mapped[int] = mapped_column(Integer)
    uploaded_at: Mapped[datetime] = _ts()
    idea: Mapped[Idea] = relationship(back_populates="documents")


class Evaluation(Base):
    """AI evaluation report (one row per run; `report` holds the full JSON)."""
    __tablename__ = "evaluations"
    id: Mapped[int] = mapped_column(primary_key=True)
    idea_id: Mapped[int] = mapped_column(ForeignKey("ideas.id", ondelete="CASCADE"), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="queued")  # queued|running|completed|failed
    stage: Mapped[str] = mapped_column(String(40), default="queued")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    mode: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # live_llm | demo
    provider: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    report: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    technical_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    market_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    innovation_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    overall_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = _ts()
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    idea: Mapped[Idea] = relationship(back_populates="evaluations")
    similar: Mapped[List["SimilarityResult"]] = relationship(back_populates="evaluation", cascade="all, delete-orphan",
                                                            order_by="SimilarityResult.similarity.desc()")


class SimilarityResult(Base):
    __tablename__ = "similarity_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    evaluation_id: Mapped[int] = mapped_column(ForeignKey("evaluations.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[str] = mapped_column(String(20))  # reference | platform | research_paper
    source_ref: Mapped[str] = mapped_column(String(300))  # reference slug | idea id | paper URL
    title: Mapped[str] = mapped_column(String(300))
    url: Mapped[Optional[str]] = mapped_column(String(400), nullable=True)
    similarity: Mapped[float] = mapped_column(Float)      # percent, computed from vectors
    differences: Mapped[str] = mapped_column(Text, default="")
    is_competitor: Mapped[bool] = mapped_column(Boolean, default=False)
    evaluation: Mapped[Evaluation] = relationship(back_populates="similar")


class ReferenceProject(Base):
    """Curated dataset of REAL existing projects/products used as the comparison corpus."""
    __tablename__ = "reference_projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text)
    url: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    embedding = mapped_column(EmbeddingType, nullable=True)
    embedding_model: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)


class SavedIdea(Base):
    __tablename__ = "saved_ideas"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    idea_id: Mapped[int] = mapped_column(ForeignKey("ideas.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = _ts()
    __table_args__ = (UniqueConstraint("user_id", "idea_id", name="uq_saved_user_idea"),)


class CollaborationRequest(Base):
    __tablename__ = "collaboration_requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    idea_id: Mapped[int] = mapped_column(ForeignKey("ideas.id", ondelete="CASCADE"), index=True)
    entrepreneur_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20), default="collaborate")  # collaborate|fund|develop
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|accepted|declined|withdrawn
    response_message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = _ts()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    idea: Mapped[Idea] = relationship()
    entrepreneur: Mapped[User] = relationship(foreign_keys=[entrepreneur_id])
    creator: Mapped[User] = relationship(foreign_keys=[creator_id])


class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    recipient_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    idea_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ideas.id", ondelete="SET NULL"), nullable=True)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = _ts()
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (Index("ix_msg_pair", "sender_id", "recipient_id"),)


class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(String(500), default="")
    link: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = _ts()


class AdminActivityLog(Base):
    __tablename__ = "admin_activity_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    admin_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(60))
    target_type: Mapped[str] = mapped_column(String(40))
    target_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    detail: Mapped[str] = mapped_column(String(400), default="")
    created_at: Mapped[datetime] = _ts()


class ContentReport(Base):
    __tablename__ = "content_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    idea_id: Mapped[int] = mapped_column(ForeignKey("ideas.id", ondelete="CASCADE"), index=True)
    reason: Mapped[str] = mapped_column(String(40))  # spam|plagiarism|inappropriate|confidential|other
    details: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="open")  # open|dismissed|actioned
    resolution_note: Mapped[str] = mapped_column(String(400), default="")
    resolved_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = _ts()
    reporter: Mapped[User] = relationship(foreign_keys=[reporter_id])
    idea: Mapped[Idea] = relationship()
