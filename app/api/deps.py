"""Dependencias de FastAPI: sesión, usuario autenticado y RBAC (RF-102)."""
from __future__ import annotations

import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.models import AuditLog, Role, User

bearer = HTTPBearer(auto_error=False, description="JWT emitido por /api/auth/login")

DB = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(db: DB, creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> User:
    unauthorized = HTTPException(status.HTTP_401_UNAUTHORIZED, "No autenticado o token inválido.", headers={"WWW-Authenticate": "Bearer"})
    if creds is None:
        raise unauthorized
    try:
        payload = decode_access_token(creds.credentials)
        user_id = uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise unauthorized
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: Role):
    async def checker(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Acción restringida a: {', '.join(r.value for r in roles)}.")
        return user

    return checker


StaffUser = Annotated[User, Depends(require_roles(Role.DOCENTE, Role.ADMINISTRADOR))]
AdminUser = Annotated[User, Depends(require_roles(Role.ADMINISTRADOR))]


def is_staff(user: User) -> bool:
    return user.role in (Role.DOCENTE, Role.ADMINISTRADOR)


def audit(db: AsyncSession, user: User | None, action: str, entity: str, entity_id, detail: dict | None = None) -> None:
    db.add(AuditLog(user_id=user.id if user else None, action=action, entity=entity, entity_id=str(entity_id), detail=detail or {}))
