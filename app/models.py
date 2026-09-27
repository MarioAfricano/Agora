from datetime import datetime, date

from sqlalchemy import BigInteger, DateTime, func, ForeignKey, CheckConstraint
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

