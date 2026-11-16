"""Módulo 1 – Autenticación y gestión de usuarios (RF-101, RF-102)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import DB, AdminUser, CurrentUser, StaffUser, audit
from app.core.security import create_access_token, hash_password, verify_password
from app.models.models import Role, User
from app.schemas.schemas import LoginRequest, RegisterRequest, TokenResponse, UserCreate, UserOut

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])
users_router = APIRouter(prefix="/api/users", tags=["Usuarios"])


async def _email_taken(db, email: str) -> bool:
    return (await db.execute(select(User.id).where(func.lower(User.email) == email.lower()))).first() is not None


def _token(user: User) -> TokenResponse:
    return TokenResponse(access_token=create_access_token(str(user.id), user.role.value), user=UserOut.model_validate(user))


@router.post("/register", response_model=TokenResponse, status_code=201, summary="Autorregistro (sólo rol ESTUDIANTE)")
async def register(body: RegisterRequest, db: DB):
    if await _email_taken(db, body.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "El correo ya está registrado.")
    user = User(email=body.email.lower(), full_name=body.full_name.strip(), student_code=body.student_code,
                password_hash=hash_password(body.password), role=Role.ESTUDIANTE)
    db.add(user)
    await db.flush()
    audit(db, user, "REGISTER", "user", user.id)
    await db.commit()
    return _token(user)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: DB):
    user = (await db.execute(select(User).where(func.lower(User.email) == body.email.lower()))).scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas.")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Usuario inactivo.")
    return _token(user)


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user


@users_router.get("", response_model=list[UserOut], summary="Listar usuarios (docente/admin)")
async def list_users(db: DB, _: StaffUser, role: Role | None = None):
    stmt = select(User).order_by(User.role, User.full_name)
    if role:
        stmt = stmt.where(User.role == role)
    return (await db.execute(stmt)).scalars().all()


@users_router.post("", response_model=UserOut, status_code=201, summary="Registrar usuario (docente→estudiantes, admin→cualquier rol)")
async def create_user(body: UserCreate, db: DB, actor: StaffUser):
    if actor.role == Role.DOCENTE and body.role != Role.ESTUDIANTE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Un docente sólo puede registrar estudiantes.")
    if await _email_taken(db, body.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "El correo ya está registrado.")
    user = User(email=body.email.lower(), full_name=body.full_name.strip(), student_code=body.student_code,
                password_hash=hash_password(body.password), role=body.role)
    db.add(user)
    await db.flush()
    audit(db, actor, "CREATE_USER", "user", user.id, {"role": body.role.value})
    await db.commit()
    return user


@users_router.patch("/{user_id}/active", response_model=UserOut, summary="Activar/desactivar usuario (admin)")
async def toggle_active(user_id: uuid.UUID, active: bool, db: DB, actor: AdminUser):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Usuario no encontrado.")
    if user.id == actor.id:
        raise HTTPException(400, "No puede desactivarse a sí mismo.")
    user.is_active = active
    audit(db, actor, "TOGGLE_USER", "user", user.id, {"active": active})
    await db.commit()
    return user
