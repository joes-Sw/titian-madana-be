from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  (register models on Base)
from app.core.seed import DEFAULT_USERS, seed_default_users
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import User

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)
TestingSessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, future=True
)


def _override_get_db() -> Generator:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    Base.metadata.create_all(bind=engine)
    with TestingSessionLocal() as db:
        seed_default_users(db)

    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def _login(client: TestClient, username: str, password: str):
    return client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )


def _register(client: TestClient, **overrides):
    body = {
        "username": "budi",
        "full_name": "Budi Santoso",
        "password": "Budi12345",
        "confirm_password": "Budi12345",
    }
    body.update(overrides)
    return client.post("/api/auth/register", json=body)


# --- Login ---------------------------------------------------------------


@pytest.mark.parametrize("account", DEFAULT_USERS, ids=lambda a: a["role"])
def test_login_success_for_each_role(client: TestClient, account: dict) -> None:
    response = _login(client, account["username"], account["password"])
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["role"] == account["role"]
    assert body["username"] == account["username"]
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_only_requires_username_and_password(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "manager", "password": "Manager#123"},
    )
    assert response.status_code == 200, response.text


def test_login_wrong_password(client: TestClient) -> None:
    response = _login(client, "superadmin", "WrongPass#123")
    assert response.status_code == 401
    assert "salah" in response.json()["detail"].lower()


def test_login_unknown_user(client: TestClient) -> None:
    response = _login(client, "ghost", "Whatever#123")
    assert response.status_code == 401


def test_login_short_password_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "manager", "password": "123"},
    )
    assert response.status_code == 422


def test_login_username_with_space_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "super admin", "password": "Superadmin#123"},
    )
    assert response.status_code == 422


# --- Register ------------------------------------------------------------


def test_register_default_role_is_marketing(client: TestClient) -> None:
    response = _register(client)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["username"] == "budi"
    assert body["role"] == "marketing"
    assert body["is_active"] is True
    assert "hashed_password" not in body


def test_register_with_manager_role(client: TestClient) -> None:
    response = _register(client, username="rina", role="manager")
    assert response.status_code == 201, response.text
    assert response.json()["role"] == "manager"


def test_register_superadmin_is_forbidden(client: TestClient) -> None:
    response = _register(client, username="hacker", role="superadmin")
    assert response.status_code == 422


def test_register_duplicate_username_conflict(client: TestClient) -> None:
    assert _register(client, username="superadmin").status_code == 409


def test_register_confirm_password_mismatch(client: TestClient) -> None:
    response = _register(client, confirm_password="Budi99999")
    assert response.status_code == 422


def test_register_weak_password_rejected(client: TestClient) -> None:
    no_digit = _register(client, username="a1", password="abcdefgh", confirm_password="abcdefgh")
    assert no_digit.status_code == 422
    no_letter = _register(client, username="a2", password="12345678", confirm_password="12345678")
    assert no_letter.status_code == 422
    too_short = _register(client, username="a3", password="Ab1", confirm_password="Ab1")
    assert too_short.status_code == 422


def test_register_username_with_space_rejected(client: TestClient) -> None:
    response = _register(client, username="bu di")
    assert response.status_code == 422


def test_registered_user_can_login(client: TestClient) -> None:
    assert _register(client, username="sinta").status_code == 201
    response = _login(client, "sinta", "Budi12345")
    assert response.status_code == 200, response.text
    assert response.json()["role"] == "marketing"


def test_register_stores_hashed_password(client: TestClient) -> None:
    assert _register(client, username="tono").status_code == 201
    with TestingSessionLocal() as db:
        user = db.scalar(select(User).where(User.username == "tono"))
    assert user is not None
    assert user.hashed_password != "Budi12345"
    assert user.hashed_password.startswith("pbkdf2_sha256$")


# --- Profil & RBAC -------------------------------------------------------


def test_me_returns_current_user(client: TestClient) -> None:
    token = _login(client, "marketing", "Marketing#123").json()["access_token"]
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["role"] == "marketing"


def test_me_without_token_is_unauthorized(client: TestClient) -> None:
    assert client.get("/api/auth/me").status_code == 401


def test_me_with_invalid_token_is_unauthorized(client: TestClient) -> None:
    response = client.get(
        "/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


def test_admin_scrape_requires_authentication(client: TestClient) -> None:
    assert client.post("/api/admin/scrape").status_code == 401


def test_admin_scrape_forbidden_for_marketing(client: TestClient) -> None:
    token = _login(client, "marketing", "Marketing#123").json()["access_token"]
    response = client.post(
        "/api/admin/scrape", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


def test_admin_runs_forbidden_for_anonymous(client: TestClient) -> None:
    assert client.get("/api/admin/scrape/runs").status_code == 401
