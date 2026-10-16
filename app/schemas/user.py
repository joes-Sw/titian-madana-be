from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.security import VALID_ROLES


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    confirm_password: str = Field(min_length=6, max_length=128)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        username = value.strip().lower()
        if not username:
            raise ValueError("Username tidak boleh kosong")
        if " " in username:
            raise ValueError("Username tidak boleh mengandung spasi")
        return username

    @model_validator(mode="after")
    def passwords_must_match(self) -> "LoginRequest":
        if self.password != self.confirm_password:
            raise ValueError("Password dan konfirmasi password tidak sama")
        return self


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str
    username: str
    full_name: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str
    full_name: str | None = None
    is_active: bool
    created_at: datetime | None = None


class RoleInfoOut(BaseModel):
    username: str
    role: str
    allowed_roles: list[str] = list(VALID_ROLES)
