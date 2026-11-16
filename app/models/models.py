"""Modelo de datos relacional (SRS §6.1). Portable SQLite ⇄ PostgreSQL."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, JSONType


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Role(str, enum.Enum):
    ESTUDIANTE = "ESTUDIANTE"
    DOCENTE = "DOCENTE"
    ADMINISTRADOR = "ADMINISTRADOR"


class SubmissionStatus(str, enum.Enum):
    ENTREGADO = "ENTREGADO"        # cargado, sin evaluar
    EVALUADO_IA = "EVALUADO_IA"    # evaluado por IA, pendiente de revisión docente
    PUBLICADO = "PUBLICADO"        # aprobado y visible para el estudiante


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    student_code: Mapped[str | None] = mapped_column(String(40), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role, name="user_role"), default=Role.ESTUDIANTE, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    submissions: Mapped[list["Submission"]] = relationship(back_populates="student", cascade="all, delete-orphan")


class Cohort(Base):
    __tablename__ = "cohorts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    order: Mapped[int] = mapped_column(Integer, default=1)

    laboratories: Mapped[list["Laboratory"]] = relationship(
        back_populates="cohort", cascade="all, delete-orphan", order_by="Laboratory.order"
    )


class Laboratory(Base):
    __tablename__ = "laboratories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cohort_id: Mapped[int] = mapped_column(ForeignKey("cohorts.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    objectives: Mapped[str] = mapped_column(Text, default="")
    competencies: Mapped[list] = mapped_column(JSONType, default=list)  # temáticas IA abordadas
    order: Mapped[int] = mapped_column(Integer, default=1)

    cohort: Mapped[Cohort] = relationship(back_populates="laboratories")
    rubrics: Mapped[list["Rubric"]] = relationship(back_populates="laboratory", cascade="all, delete-orphan")


class Rubric(Base):
    __tablename__ = "rubrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    laboratory_id: Mapped[int] = mapped_column(ForeignKey("laboratories.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    total_weight: Mapped[float] = mapped_column(Float, default=100.0)
    criteria_json: Mapped[list] = mapped_column(JSONType, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    laboratory: Mapped[Laboratory] = relationship(back_populates="rubrics")


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    laboratory_id: Mapped[int] = mapped_column(ForeignKey("laboratories.id", ondelete="CASCADE"), index=True)
    pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pdf_original_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pdf_text: Mapped[str] = mapped_column(Text, default="")
    repo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    code_zip_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    code_manifest: Mapped[dict] = mapped_column(JSONType, default=dict)
    code_excerpt: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus, name="submission_status"), default=SubmissionStatus.ENTREGADO
    )
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    student: Mapped[User] = relationship(back_populates="submissions")
    laboratory: Mapped[Laboratory] = relationship()
    evaluations: Mapped[list["Evaluation"]] = relationship(
        back_populates="submission", cascade="all, delete-orphan", order_by="Evaluation.created_at"
    )


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"), index=True)
    rubric_id: Mapped[int] = mapped_column(ForeignKey("rubrics.id", ondelete="CASCADE"))
    raw_llm_json: Mapped[dict] = mapped_column(JSONType, default=dict)       # salida IA validada (inmutable)
    criteria_scores: Mapped[list] = mapped_column(JSONType, default=list)    # desglose vigente (tras ajustes)
    raw_score: Mapped[float] = mapped_column(Float, default=0.0)            # suma exacta (4 decimales)
    calculated_score: Mapped[float] = mapped_column(Float, default=0.0)     # nota oficial 0,0–5,0 (1 decimal)
    ai_provider: Mapped[str] = mapped_column(String(60), default="mock")
    teacher_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    teacher_comment: Mapped[str] = mapped_column(Text, default="")
    adjusted: Mapped[bool] = mapped_column(Boolean, default=False)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    submission: Mapped[Submission] = relationship(back_populates="evaluations")
    rubric: Mapped[Rubric] = relationship()


class AuditLog(Base):
    """Trazabilidad y supervisión docente (SRS §8.3)."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(80))
    entity: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[str] = mapped_column(String(60))
    detail: Mapped[dict] = mapped_column(JSONType, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
