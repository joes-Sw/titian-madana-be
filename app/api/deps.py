"""Dependency FastAPI untuk autentikasi dan otorisasi berbasis role.

Cara pakai di sebuah endpoint:

    # Wajib login (semua role)
    def endpoint(user: User = Depends(get_current_user)): ...

    # Wajib login DAN role tertentu
    def endpoint(user: User = Depends(require_roles("superadmin", "manager"))): ...
"""

from __future__ import annotations

from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User

# auto_error=False agar kita bisa mengembalikan pesan 401 sendiri (bukan default).
bearer_scheme = HTTPBearer(auto_error=False)

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Token autentikasi tidak valid",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Ambil user dari header ``Authorization: Bearer <token>``.

    Alur: cek header ada -> decode & verifikasi JWT -> cari user di DB ->
    pastikan akun masih aktif. Melempar HTTP 401 bila token tidak ada/valid/
    kedaluwarsa, dan HTTP 403 bila akun dinonaktifkan.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token autentikasi tidak ditemukan",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sudah kadaluarsa, silakan login kembali",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise _CREDENTIALS_EXC

    username = payload.get("sub")
    if not username:
        raise _CREDENTIALS_EXC

    user = db.scalar(select(User).where(User.username == username))
    if user is None:
        raise _CREDENTIALS_EXC
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun tidak aktif",
        )
    return user


def require_roles(*roles: str) -> Callable[..., User]:
    """Factory dependency: izinkan akses hanya untuk role yang disebutkan.

    Contoh: ``Depends(require_roles("superadmin", "manager"))``. Bila user
    login tetapi role-nya tidak termasuk, dikembalikan HTTP 403.
    """

    def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Akses ditolak. Role '{user.role}' tidak diizinkan untuk "
                    f"aksi ini (butuh: {', '.join(roles)})"
                ),
            )
        return user

    return _checker
