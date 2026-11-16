"""DTOs de entrada/salida de la API (capa de interfaz)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models.models import Role, SubmissionStatus


# ---------------------------------------------------------------- Auth / Usuarios
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=3, max_length=160)
    password: str = Field(min_length=8, max_length=128)
    student_code: str | None = Field(default=None, max_length=40)


class UserCreate(RegisterRequest):
    role: Role = Role.ESTUDIANTE


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: EmailStr
    full_name: str
    student_code: str | None
    role: Role
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------------------------------------------------------------- Cohortes / Labs
class LaboratoryCreate(BaseModel):
    cohort_id: int
    title: str = Field(min_length=3, max_length=200)
    objectives: str = ""
    competencies: list[str] = Field(default_factory=list)
    order: int = 1


class LaboratoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    cohort_id: int
    title: str
    objectives: str
    competencies: list[str]
    order: int
    has_active_rubric: bool = False


class CohortCreate(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str = ""
    order: int = 1


class CohortOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str
    order: int
    laboratories: list[LaboratoryOut] = Field(default_factory=list)


# ---------------------------------------------------------------- Rúbricas
class PerformanceLevel(BaseModel):
    label: str = Field(min_length=1, max_length=60)
    min_score: float = Field(ge=0.0, le=5.0)
    max_score: float = Field(ge=0.0, le=5.0)
    descriptor: str = ""

    @model_validator(mode="after")
    def _range(self):
        if self.min_score > self.max_score:
            raise ValueError(f"Nivel '{self.label}': min_score no puede ser mayor que max_score")
        return self


class RubricCriterion(BaseModel):
    id: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_\-]+$")
    name: str = Field(min_length=2, max_length=200)
    competency: str = Field(min_length=2, max_length=120)
    description: str = ""
    weight: float = Field(gt=0, le=100, description="Ponderación porcentual del criterio")
    levels: list[PerformanceLevel] = Field(default_factory=list)


class RubricBase(BaseModel):
    laboratory_id: int
    name: str = Field(min_length=3, max_length=200)
    criteria: list[RubricCriterion] = Field(min_length=1)


class RubricCreate(RubricBase):
    activate: bool = True


class RubricValidationOut(BaseModel):
    valid: bool
    total_weight: float
    difference: float
    errors: list[str]


class RubricOut(BaseModel):
    id: int
    laboratory_id: int
    laboratory_title: str | None = None
    name: str
    total_weight: float
    criteria: list[RubricCriterion]
    is_active: bool
    created_at: datetime


# ---------------------------------------------------------------- Entregas
class SubmissionOut(BaseModel):
    id: int
    student_id: uuid.UUID
    student_name: str
    laboratory_id: int
    laboratory_title: str
    cohort_id: int
    cohort_name: str
    pdf_original_name: str | None
    has_pdf: bool
    pdf_text_chars: int
    repo_url: str | None
    has_code_zip: bool
    code_manifest: dict[str, Any]
    notes: str
    status: SubmissionStatus
    submitted_at: datetime
    latest_evaluation_id: int | None = None
    latest_score: float | None = None


# ---------------------------------------------------------------- Evaluaciones
class CriterionScoreLine(BaseModel):
    criterion_id: str
    name: str
    competency: str
    weight: float
    partial_score: float
    contribution: float
    ai_partial_score: float
    evidence_quote: str = ""
    reasoning: str = ""
    adjusted: bool = False
    adjust_reason: str = ""


class EvaluationOut(BaseModel):
    id: int
    submission_id: int
    rubric_id: int
    student_name: str
    laboratory_title: str
    cohort_name: str
    general_summary: str
    strengths: list[str]
    weaknesses: list[str]
    recommendations: list[str]
    criteria_scores: list[CriterionScoreLine]
    raw_score: float
    calculated_score: float
    formula: str
    ai_provider: str
    teacher_approved: bool
    teacher_comment: str
    adjusted: bool
    approved_at: datetime | None
    created_at: datetime


class CriterionAdjustment(BaseModel):
    criterion_id: str
    partial_score: float = Field(ge=0.0, le=5.0)
    reason: str = Field(min_length=3, max_length=500)


class EvaluationAdjustRequest(BaseModel):
    adjustments: list[CriterionAdjustment] = Field(min_length=1)


class EvaluationApproveRequest(BaseModel):
    teacher_comment: str = Field(default="", max_length=2000)


class AIStatusOut(BaseModel):
    provider: str
    model: str | None
    configured: bool
    fallback_to_mock: bool
