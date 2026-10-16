"""Endpoint autentikasi.

Berisi login berbasis role dan endpoint untuk mengambil profil user yang
sedang login. Tidak ada endpoint registrasi; akun dibuat via seeding
(lihat ``app/core/seed.py`` dan ``scripts/seed_users.py``).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.security import VALID_ROLES, create_access_token, verify_password
from app.db.session import get_db
from app.models import User
from app.schemas import LoginRequest, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=TokenOut,
    summary="Login dan dapatkan token",
    response_description="Token JWT beserta role user",
    responses={
        401: {"description": "Username atau password salah"},
        403: {"description": "Akun tidak aktif atau role tidak dikenali"},
        422: {"description": "Validasi body gagal (mis. password != confirm_password)"},
    },
)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenOut:
    """Login dengan ``username``, ``password``, dan ``confirm_password``.

    ``confirm_password`` harus sama dengan ``password``. Bila kredensial benar,
    mengembalikan JWT (``access_token``) dan ``role`` yang dapat dipakai FE untuk
    menampilkan menu/halaman sesuai hak akses.
    """
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None or not verify_password(payload.password, user.hashed_password):
        # Pesan disengaja sama untuk user tidak ada & password salah
        # agar tidak membocorkan username mana yang terdaftar.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username atau password salah",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akun tidak aktif, hubungi superadmin",
        )
    if user.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{user.role}' tidak dikenali",
        )

    token = create_access_token(subject=user.username, role=user.role)
    return TokenOut(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
        role=user.role,
        username=user.username,
        full_name=user.full_name,
    )


@router.get(
    "/me",
    response_model=UserOut,
    summary="Profil user yang sedang login",
    responses={401: {"description": "Token tidak ada / tidak valid / kedaluwarsa"}},
)
def me(user: User = Depends(get_current_user)) -> User:
    """Kembalikan data user berdasarkan token pada header Authorization.

    Berguna untuk memverifikasi token saat FE melakukan refresh halaman.
    """
    return user
