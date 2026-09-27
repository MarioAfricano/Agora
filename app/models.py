from datetime import datetime

from sqlalchemy import BigInteger, DateTime, func
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

