from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Tipe role yang diizinkan aplikasi.
Role = Literal["superadmin", "manager", "marketing"]


class LoginRequest(BaseModel):
    """Body request untuk ``POST /api/auth/login``.

    ``confirm_password`` wajib dikirim dan harus sama dengan ``password``
    (dipakai untuk mencegah typo saat login). Username otomatis di-*trim*
    dan diubah ke huruf kecil oleh validator.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "superadmin",
                "password": "Superadmin#123",
                "confirm_password": "Superadmin#123",
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
    confirm_password: str = Field(
        min_length=6,
        max_length=128,
        description="Ulangi password. Harus sama persis dengan `password`.",
        examples=["Superadmin#123"],
    )

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        """Rapikan username: hilangkan spasi tepi dan jadikan lowercase."""
        username = value.strip().lower()
        if not username:
            raise ValueError("Username tidak boleh kosong")
        if " " in username:
            raise ValueError("Username tidak boleh mengandung spasi")
        return username

    @model_validator(mode="after")
    def passwords_must_match(self) -> "LoginRequest":
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
    """Profil user yang sedang login (dipakai ``GET /api/auth/me``)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: Role
    full_name: str | None = None
    is_active: bool
    created_at: datetime | None = None
