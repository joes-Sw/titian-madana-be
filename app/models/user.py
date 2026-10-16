from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    """Akun pengguna aplikasi.

    Akun dibuat lewat seeding (``app/core/seed.py``) atau script
    ``scripts/seed_users.py``; tidak ada endpoint registrasi publik.
    Kolom ``role`` menentukan hak akses dan harus salah satu dari
    ``superadmin`` / ``manager`` / ``marketing`` (lihat
    ``app/core/security.py``).
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Username unik yang dipakai untuk login (disimpan lowercase).
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # Password TIDAK pernah disimpan plaintext, melainkan hash PBKDF2.
    hashed_password: Mapped[str] = mapped_column(String(255))
    # Role user: superadmin, manager, atau marketing.
    role: Mapped[str] = mapped_column(String(32), index=True)
    full_name: Mapped[str | None] = mapped_column(String(128))
    # Bila False, login ditolak walau kredensial benar.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
