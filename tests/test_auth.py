from sqlalchemy import select

from app.models import User


def test_register_creates_user_and_redirects_to_library(client, db):
    response = client.post(
        "/register",
        data={"email": "new@example.com", "password": "password123"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/library"
    assert db.scalar(select(User).where(User.email == "new@example.com")) is not None


def test_register_rejects_short_password(client, db):
    response = client.post(
        "/register",
        data={"email": "new@example.com", "password": "123"},
    )

    assert response.status_code == 400
    assert "Password must be at least 8 characters." in response.text
    assert db.scalar(select(User).where(User.email == "new@example.com")) is None


def test_library_redirects_to_login_without_session(client, db):
    response = client.get(
        "/library",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_login_with_wrong_password_returns_400(client, db):
    client.post(
        "/register",
        data={"email": "new@example.com", "password": "password123"},
        follow_redirects=False,
    )

    client.post(
        "/logout",
    )
    response = client.post(
        "/login", data={"email": "new@example.com", "password": "password111"}
    )

    assert response.status_code == 400
    assert "Invalid email or password." in response.text


def test_register_logs_the_user_in(client, db):
    client.post(
        "/register", data={"email": "new@example.com", "password": "password123"}
    )

    response = client.get("/library", follow_redirects=False)

    assert response.status_code == 200
