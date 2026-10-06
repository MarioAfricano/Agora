import pytest
from sqlalchemy import select

from app.models import Game, LibraryEntry, User


@pytest.fixture
def other_users_entry(db):
    owner = User(email="owner@example.com", password_hash="x")
    game = Game(igdb_id=1, name="Hades")
    db.add_all([owner, game])
    db.flush()

    entry = LibraryEntry(user_id=owner.id, game_id=game.id)
    db.add(entry)
    db.flush()
    return entry


def log_in_as(client, email):
    client.post("/register", data={"email": email, "password": "passwordTest123"})


def test_owner_can_see_own_entry(client, db):
    log_in_as(client, "owner@example.com")
    owner = db.scalar(select(User).where(User.email == "owner@example.com"))

    game = Game(igdb_id=1, name="Hades")
    db.add(game)
    db.flush()

    entry = LibraryEntry(user_id=owner.id, game_id=game.id)
    db.add(entry)
    db.flush()

    response = client.get(f"/library/{entry.id}")
    assert response.status_code == 200


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/library/{id}"),
        ("post", "/library/{id}"),
        ("post", "/library/{id}/status"),
        ("post", "/library/{id}/delete"),
    ],
)
def test_cannot_access_other_users_entry(client, db, other_users_entry, method, path):
    log_in_as(client, "intruder@example.com")

    response = client.request(
        method,
        path.format(id=other_users_entry.id),
        data={"status": "playing"},
    )

    assert response.status_code == 404
    assert db.get(LibraryEntry, other_users_entry.id) is not None
