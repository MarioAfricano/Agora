from datetime import date

from sqlalchemy import func, select

from app.igdb import igdb
from app.importer import import_game
from app.models import GameCompany, GameGenre, GamePlatform

FAKE_GAME = {
    "id": 113112,
    "name": "Hades",
    "summary": "A rogue-lite dungeon crawler.",
    "first_release_date": 1600300800,
    "cover": {"id": 1, "image_id": "cob9kr"},
    "genres": [
        {"id": 12, "name": "Role-playing (RPG)"},
        {"id": 32, "name": "Indie"},
    ],
    "platforms": [
        {"id": 6, "name": "PC (Microsoft Windows)"},
    ],
    "involved_companies": [
        {
            "company": {"id": 928, "name": "Supergiant Games"},
            "developer": True,
            "publisher": True,
        },
        {
            "company": {"id": 9691, "name": "Secret 6"},
            "developer": False,
            "publisher": False,
        },
    ],
}


def test_import_game_creates_the_game(db, monkeypatch):
    monkeypatch.setattr(igdb, "get_game", lambda igdb_id: FAKE_GAME)

    game = import_game(db, 113112)

    assert game.name == "Hades"
    assert game.release_date == date(2020, 9, 17)
    assert game.cover_image_id == "cob9kr"


def test_import_game_links_genres_and_platforms(db, monkeypatch):
    monkeypatch.setattr(igdb, "get_game", lambda igdb_id: FAKE_GAME)
    game = import_game(db, 113112)

    genre_count = db.scalar(
        select(func.count()).select_from(GameGenre).where(GameGenre.game_id == game.id)
    )
    platform_count = db.scalar(
        select(func.count())
        .select_from(GamePlatform)
        .where(GamePlatform.game_id == game.id)
    )
    assert genre_count == 2
    assert platform_count == 1


def test_import_game_skips_companies_without_role(db, monkeypatch):
    monkeypatch.setattr(igdb, "get_game", lambda igdb_id: FAKE_GAME)
    game = import_game(db, 113112)

    companies_count = db.scalar(
        select(func.count())
        .select_from(GameCompany)
        .where(GameCompany.game_id == game.id)
    )
    assert companies_count == 1


def test_import_game_twice_reuses_the_game(db, monkeypatch):
    calls = []

    def fake_get_game(igdb_id):
        calls.append(igdb_id)
        return FAKE_GAME

    monkeypatch.setattr(igdb, "get_game", fake_get_game)

    first = import_game(db, 113112)
    second = import_game(db, 113112)

    assert first.id == second.id
    assert len(calls) == 1


def test_import_game_returns_none_when_not_found(db, monkeypatch):
    monkeypatch.setattr(igdb, "get_game", lambda igdb_id: None)
    game = import_game(db, 1)

    assert game is None
