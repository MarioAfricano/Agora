from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.igdb import igdb
from app.models import (
    Company,
    Game,
    GameCompany,
    GameGenre,
    GamePlatform,
    Genre,
    Platform,
)


def _get_or_create(db: Session, model, igdb_id: int, name: str):
    instance = db.scalar(select(model).where(model.igdb_id == igdb_id))
    if instance is None:
        instance = model(igdb_id=igdb_id, name=name)
        db.add(instance)
        db.flush()
    return instance


def import_game(db: Session, igdb_id: int) -> Game | None:
    game = db.scalar(select(Game).where(Game.igdb_id == igdb_id))
    if game is not None:
        return game

    data = igdb.get_game(igdb_id)
    if data is None:
        return None

    timestamp = data.get("first_release_date")
    release = datetime.fromtimestamp(timestamp, tz=UTC).date() if timestamp else None

    cover = data.get("cover")
    cover_id = cover["image_id"] if cover else None

    game = Game(
        igdb_id=igdb_id,
        name=data["name"],
        summary=data.get("summary"),
        release_date=release,
        cover_image_id=cover_id,
    )

    db.add(game)
    db.flush()

    genres = data.get("genres", [])
    for genre_data in genres:
        genre = _get_or_create(db, Genre, genre_data["id"], genre_data["name"])
        db.add(GameGenre(game_id=game.id, genre_id=genre.id))

    platforms = data.get("platforms", [])
    for platform_data in platforms:
        platform = _get_or_create(
            db, Platform, platform_data["id"], platform_data["name"]
        )
        db.add(GamePlatform(game_id=game.id, platform_id=platform.id))

    companies = data.get("involved_companies", [])
    for company_data in companies:
        if not company_data["developer"] and not company_data["publisher"]:
            continue
        company = _get_or_create(
            db, Company, company_data["company"]["id"], company_data["company"]["name"]
        )
        db.add(
            GameCompany(
                game_id=game.id,
                company_id=company.id,
                is_developer=company_data["developer"],
                is_publisher=company_data["publisher"],
            )
        )

    return game
