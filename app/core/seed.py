from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    ROLE_MANAGER,
    ROLE_MARKETING,
    ROLE_SUPERADMIN,
    hash_password,
)
from app.models import User

DEFAULT_USERS: tuple[dict[str, str], ...] = (
    {
        "username": "superadmin",
        "password": "Superadmin#123",
        "role": ROLE_SUPERADMIN,
        "full_name": "Super Admin",
    },
    {
        "username": "manager",
        "password": "Manager#123",
        "role": ROLE_MANAGER,
        "full_name": "Manager Operasional",
    },
    {
        "username": "marketing",
        "password": "Marketing#123",
        "role": ROLE_MARKETING,
        "full_name": "Marketing",
    },
)


def seed_default_users(db: Session) -> list[str]:
    """Buat akun dummy bila belum ada. Idempotent, mengembalikan username baru."""
    created: list[str] = []
    for item in DEFAULT_USERS:
        exists = db.scalar(select(User).where(User.username == item["username"]))
        if exists is not None:
            continue
        db.add(
            User(
                username=item["username"],
                hashed_password=hash_password(item["password"]),
                role=item["role"],
                full_name=item["full_name"],
                is_active=True,
            )
        )
        created.append(item["username"])
    if created:
        db.commit()
    return created
