from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    func,
    Numeric,
    SmallInteger,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    igdb_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    name: Mapped[str]


class Platform(Base):
    __tablename__ = "platforms"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    igdb_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    name: Mapped[str]


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    igdb_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    name: Mapped[str]


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    igdb_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    name: Mapped[str]
    summary: Mapped[str | None]
    release_date: Mapped[date | None]
    cover_image_id: Mapped[str | None]
    cover_s3_key: Mapped[str | None]
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class GameGenre(Base):
    __tablename__ = "game_genres"

    game_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("games.id", ondelete="CASCADE"), primary_key=True
    )
    genre_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True
    )


class GamePlatform(Base):
    __tablename__ = "game_platforms"

    game_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("games.id", ondelete="CASCADE"), primary_key=True
    )
    platform_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("platforms.id", ondelete="CASCADE"), primary_key=True
    )


class GameCompany(Base):
    __tablename__ = "game_companies"
    __table_args__ = (
        CheckConstraint("is_developer OR is_publisher", name="has_role"),
    )

    game_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("games.id", ondelete="CASCADE"), primary_key=True
    )
    company_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("companies.id", ondelete="CASCADE"), primary_key=True
    )
    is_developer: Mapped[bool]
    is_publisher: Mapped[bool]


class LibraryEntry(Base):
    __tablename__ = "library_entries"
    __table_args__ = (
        UniqueConstraint("user_id", "game_id", name="one_entry_per_user_game"),
        CheckConstraint(
            "status IN ('playing', 'finished', 'dropped', 'backlog')", name="valid_status"
        ),
        CheckConstraint("rating BETWEEN 1 AND 10", name="rating_range"),
        CheckConstraint("finished_at >= started_at", name="finished_after_started"),
        CheckConstraint("hours_played >= 0", name="non_negative_hours"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE")
    )
    game_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("games.id", ondelete="RESTRICT")
    )
    platform_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("platforms.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(server_default="backlog")
    hours_played: Mapped[Decimal | None] = mapped_column(Numeric(6, 1))
    rating: Mapped[int | None] = mapped_column(SmallInteger)
    notes: Mapped[str | None]
    started_at: Mapped[date | None]
    finished_at: Mapped[date | None]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
