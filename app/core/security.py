"""Utilitas keamanan untuk autentikasi.

Modul ini menyediakan dua hal utama:

1. **Hashing password** menggunakan PBKDF2-HMAC-SHA256 (modul bawaan Python,
   tanpa dependency eksternal). Format hash yang disimpan:
   ``pbkdf2_sha256$<iterasi>$<salt_base64>$<digest_base64>``.

2. **Token akses (JWT)** ber-algoritma HS256 yang ditandatangani dengan
   ``settings.secret_key``. Payload token berisi ``sub`` (username), ``role``,
   ``iat`` (waktu dibuat) dan ``exp`` (waktu kedaluwarsa).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app.core.config import settings

ALGORITHM = "HS256"

# Daftar role yang dikenali aplikasi.
ROLE_SUPERADMIN = "superadmin"
ROLE_MANAGER = "manager"
ROLE_MARKETING = "marketing"

VALID_ROLES: tuple[str, ...] = (ROLE_SUPERADMIN, ROLE_MANAGER, ROLE_MARKETING)

# Parameter PBKDF2. Iterasi tinggi = brute-force makin mahal.
_PBKDF2_ITERATIONS = 240_000
_SALT_BYTES = 16


def hash_password(password: str) -> str:
    """Ubah password plaintext menjadi hash PBKDF2 yang aman disimpan di DB.

    Salt dibuat acak setiap kali dipanggil sehingga dua password identik akan
    menghasilkan hash berbeda.
    """
    salt = os.urandom(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS
    )
    return "pbkdf2_sha256${}${}${}".format(
        _PBKDF2_ITERATIONS,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, hashed: str) -> bool:
    """Cek apakah ``password`` cocok dengan ``hashed`` yang tersimpan.

    Mengembalikan ``False`` untuk hash yang rusak/format tidak dikenal
    (tidak melempar exception) dan memakai perbandingan konstan-waktu
    (``hmac.compare_digest``) untuk mencegah timing attack.
    """
    try:
        algorithm, iterations, salt_b64, digest_b64 = hashed.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, int(iterations)
        )
        return hmac.compare_digest(expected, actual)
    except (ValueError, TypeError):
        return False


def create_access_token(
    subject: str, role: str, expires_delta: timedelta | None = None
) -> str:
    """Buat JWT untuk user yang berhasil login.

    ``subject`` diisi username dan ``role`` diisi role user, sehingga endpoint
    lain bisa menentukan hak akses tanpa query DB lagi. Bila ``expires_delta``
    tidak diisi, masa berlaku diambil dari ``settings.access_token_expire_minutes``.
    """
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Verifikasi tanda tangan + masa berlaku token dan kembalikan payload-nya.

    Melempar ``jwt.PyJWTError`` (mis. ``ExpiredSignatureError``,
    ``InvalidSignatureError``) bila token tidak valid. Exception ini ditangkap
    oleh dependency ``get_current_user`` dan diubah menjadi HTTP 401.
    """
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
