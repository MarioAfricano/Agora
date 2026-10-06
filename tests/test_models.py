import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.models import User


def test_user_email_must_be_unique(db):
    email = "testing@email.com"
    password = "testingPassword"
    db.add(User(email=email, password_hash=password))
    db.commit()

    db.add(User(email=email, password_hash=password))
    with pytest.raises(IntegrityError):
        db.commit()


def test_database_starts_empty(db):
    count = db.scalar(select(func.count()).select_from(User))
    assert count == 0
