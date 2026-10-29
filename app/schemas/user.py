from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Tipe role yang dikenal aplikasi.
Role = Literal["superadmin", "manager", "marketing"]

# Role yang boleh dipilih saat registrasi mandiri. Superadmin sengaja
# dikecualikan agar tidak ada pendaftaran yang menaikkan hak akses sendiri.
SelfRegisterRole = Literal["manager", "marketing"]


def _normalize_username(value: str) -> str:
    """Rapikan username: hilangkan spasi tepi, lowercase, tolak spasi di tengah."""
    username = value.strip().lower()
    if not username:
        raise ValueError("Username tidak boleh kosong")
    if " " in username:
        raise ValueError("Username tidak boleh mengandung spasi")
    return username


class LoginRequest(BaseModel):
    """Body request untuk ``POST /api/auth/login``.

    Hanya butuh ``username`` dan ``password``. ``confirm_password`` tidak
    dipakai di login karena tidak menambah keamanan.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "superadmin",
                "password": "Superadmin#123",
            }
        }
    )

    username: str = Field(
        min_length=3,
        max_length=64,
        description="Username akun, minimal 3 karakter tanpa spasi.",
        examples=["superadmin"],
    )
    password: str = Field(
        min_length=6,
        max_length=128,
        description="Password akun, minimal 6 karakter.",
        examples=["Superadmin#123"],
    )

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return _normalize_username(value)


class RegisterRequest(BaseModel):
    """Body request untuk ``POST /api/auth/register``.

    Field yang direkomendasikan:

    - ``username``: wajib, unik, minimal 3 karakter tanpa spasi.
    - ``full_name``: opsional, nama tampilan.
    - ``password``: wajib, minimal 8 karakter serta mengandung huruf dan angka.
    - ``confirm_password``: wajib, harus sama dengan ``password`` (di sini
      konfirmasi memang relevan karena user membuat password baru).
    - ``role``: opsional, default ``marketing``. Hanya ``manager``/``marketing``
      yang boleh dipilih; ``superadmin`` hanya dibuat lewat seeding.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "budi",
                "full_name": "Budi Santoso",
                "password": "Budi12345",
                "confirm_password": "Budi12345",
                "role": "marketing",
            }
        }
    )

    username: str = Field(
        min_length=3,
        max_length=64,
        description="Username unik, minimal 3 karakter tanpa spasi.",
        examples=["budi"],
    )
    full_name: str | None = Field(
        default=None,
        max_length=128,
        description="Nama lengkap / nama tampilan (opsional).",
        examples=["Budi Santoso"],
    )
    password: str = Field(
        min_length=8,
        max_length=128,
        description="Minimal 8 karakter, harus mengandung huruf dan angka.",
        examples=["Budi12345"],
    )
    confirm_password: str = Field(
        min_length=8,
        max_length=128,
        description="Ulangi password. Harus sama persis dengan `password`.",
        examples=["Budi12345"],
    )
    role: SelfRegisterRole = Field(
        default="marketing",
        description="Role akun baru: `manager` atau `marketing` (default marketing).",
        examples=["marketing"],
    )

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return _normalize_username(value)

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        name = value.strip()
        return name or None

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if not any(char.isalpha() for char in value):
            raise ValueError("Password harus mengandung minimal satu huruf")
        if not any(char.isdigit() for char in value):
            raise ValueError("Password harus mengandung minimal satu angka")
        return value

    @model_validator(mode="after")
    def passwords_must_match(self) -> "RegisterRequest":
        """Pastikan ``password`` dan ``confirm_password`` identik."""
        if self.password != self.confirm_password:
            raise ValueError("Password dan konfirmasi password tidak sama")
        return self


class TokenOut(BaseModel):
    """Respons sukses login: token JWT + info user untuk dipakai FE."""

    access_token: str = Field(description="JWT untuk dikirim di header Authorization.")
    token_type: str = Field(default="bearer", description="Tipe token, selalu `bearer`.")
    expires_in: int = Field(description="Masa berlaku token dalam detik.")
    role: Role = Field(description="Role user: superadmin, manager, atau marketing.")
    username: str = Field(description="Username yang login.")
    full_name: str | None = Field(default=None, description="Nama lengkap user.")


class UserOut(BaseModel):
    """Profil user (dipakai ``GET /api/auth/me`` dan respons registrasi)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: Role
    full_name: str | None = None
    is_active: bool
    created_at: datetime | None = None
