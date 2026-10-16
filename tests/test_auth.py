from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models  # noqa: F401  (register models on Base)
from app.core.seed import DEFAULT_USERS, seed_default_users
from app.db.base import Base
from app.db.session import get_db
from app.main import app

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
        json={
            "username": username,
            "password": password,
            "confirm_password": password,
        },
    )


@pytest.mark.parametrize("account", DEFAULT_USERS, ids=lambda a: a["role"])
def test_login_success_for_each_role(client: TestClient, account: dict) -> None:
    response = _login(client, account["username"], account["password"])
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["role"] == account["role"]
    assert body["username"] == account["username"]
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password(client: TestClient) -> None:
    response = _login(client, "superadmin", "WrongPass#123")
    assert response.status_code == 401
    assert "salah" in response.json()["detail"].lower()


def test_login_unknown_user(client: TestClient) -> None:
    response = _login(client, "ghost", "Whatever#123")
    assert response.status_code == 401


def test_login_confirm_password_mismatch(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={
            "username": "manager",
            "password": "Manager#123",
            "confirm_password": "Manager#999",
        },
    )
    assert response.status_code == 422


def test_login_short_password_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "manager", "password": "123", "confirm_password": "123"},
    )
    assert response.status_code == 422


def test_login_username_with_space_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={
            "username": "super admin",
            "password": "Superadmin#123",
            "confirm_password": "Superadmin#123",
        },
    )
    assert response.status_code == 422


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
