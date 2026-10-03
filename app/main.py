from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app.auth import get_current_user
from app.config import settings
from app.db import engine, get_db
from app.igdb import cover_url, igdb
from app.importer import import_game
from app.models import LIBRARY_STATUSES, Game, LibraryEntry, User
from app.security import hash_password, verify_password

app = FastAPI(title="Agora")
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["cover_url"] = cover_url


@app.get("/")
def home(
    request: Request,
    current_user: Annotated[User | None, Depends(get_current_user)],
):
    return templates.TemplateResponse(
        request, "home.html", {"current_user": current_user}
    )


@app.get("/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": "unreachable"},
        )

    return {"status": "ok", "database": "ok"}


@app.get("/register")
def register(
    request: Request,
    current_user: Annotated[User | None, Depends(get_current_user)],
):
    if current_user is not None:
        return RedirectResponse(url="/library", status_code=303)

    return templates.TemplateResponse(
        request, "register.html", {"current_user": current_user}
    )


@app.post("/register")
def register_submit(
    request: Request,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    db: Annotated[Session, Depends(get_db)],
):
    email = email.strip().lower()

    if len(password) < 8:
        return templates.TemplateResponse(
            request,
            "register.html",
            {"error": "Password must be at least 8 characters.", "email": email},
            status_code=400,
        )

    if "@" not in email:
        return templates.TemplateResponse(
            request,
            "register.html",
            {"error": "Email address must contain '@'.", "email": email},
            status_code=400,
        )

    user = User(email=email, password_hash=hash_password(password))
    try:
        db.add(user)
        db.commit()
    except IntegrityError:
        db.rollback()
        return templates.TemplateResponse(
            request,
            "register.html",
            {
                "error": "An account with this email address already exists.",
                "email": email,
            },
            status_code=409,
        )

    request.session.clear()
    request.session["user_id"] = user.id

    return RedirectResponse(url="/library", status_code=303)


@app.get("/login")
def login(
    request: Request,
    current_user: Annotated[User | None, Depends(get_current_user)],
):
    if current_user is not None:
        return RedirectResponse(url="/library", status_code=303)

    return templates.TemplateResponse(
        request, "login.html", {"current_user": current_user}
    )


@app.post("/login")
def login_submit(
    request: Request,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    db: Annotated[Session, Depends(get_db)],
):
    email = email.strip().lower()

    user = db.scalar(select(User).where(User.email == email))

    if user is None or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Invalid email or password.", "email": email},
            status_code=400,
        )

    request.session.clear()
    request.session["user_id"] = user.id
    return RedirectResponse(url="/library", status_code=303)


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


@app.get("/library")
def library(
    request: Request,
    current_user: Annotated[User | None, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    status: str = "",
):
    if current_user is None:
        return RedirectResponse(url="/login", status_code=303)

    if status not in LIBRARY_STATUSES:
        status = ""

    query = (
        select(LibraryEntry, Game)
        .join(Game, LibraryEntry.game_id == Game.id)
        .where(LibraryEntry.user_id == current_user.id)
    )

    if status:
        query = query.where(LibraryEntry.status == status)

    query = query.order_by(LibraryEntry.created_at.desc())
    entries = db.execute(query).all()

    return templates.TemplateResponse(
        request,
        "library.html",
        {
            "current_user": current_user,
            "entries": entries,
            "statuses": LIBRARY_STATUSES,
            "current_status": status,
        },
    )


@app.get("/search")
def search(
    request: Request,
    current_user: Annotated[User | None, Depends(get_current_user)],
    q: str = "",
):
    if current_user is None:
        return RedirectResponse(url="/login", status_code=303)

    q = q.strip()
    results = []
    error = None

    if q:
        try:
            games = igdb.search_games(q)
        except httpx.HTTPError:
            error = "Search is temporarily unavailable. Please try again later."
        else:
            for game in games:
                timestamp = game.get("first_release_date")
                cover = game.get("cover")
                results.append(
                    {
                        "name": game["name"],
                        "year": datetime.fromtimestamp(timestamp, tz=UTC).year
                        if timestamp
                        else None,
                        "cover_url": cover_url(cover["image_id"]) if cover else None,
                        "igdb_id": game["id"],
                    }
                )
    return templates.TemplateResponse(
        request,
        "search.html",
        {"current_user": current_user, "query": q, "results": results, "error": error},
    )


@app.post("/library/add")
def library_add(
    request: Request,
    current_user: Annotated[User | None, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    igdb_id: Annotated[int, Form()],
):
    if current_user is None:
        return RedirectResponse(url="/login", status_code=303)
    try:
        game = import_game(db, igdb_id)
        if not game:
            return RedirectResponse(url="/search", status_code=303)
        library_entry = LibraryEntry(user_id=current_user.id, game_id=game.id)

        db.add(library_entry)
        db.commit()
    except httpx.HTTPError:
        return RedirectResponse(url="/search", status_code=303)
    except IntegrityError:
        db.rollback()
        return RedirectResponse(url="/library", status_code=303)
    return RedirectResponse(url="/library", status_code=303)


def _get_owned_entry(db: Session, entry_id: int, user: User) -> LibraryEntry:
    entry = db.get(LibraryEntry, entry_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(status_code=404)
    return entry


def _render_entry(request, db, user, entry, error=None, status_code=200):
    game = db.get(Game, entry.game_id)
    return templates.TemplateResponse(
        request,
        "entry.html",
        {
            "current_user": user,
            "entry": entry,
            "game": game,
            "statuses": LIBRARY_STATUSES,
            "error": error,
        },
        status_code=status_code,
    )


@app.get("/library/{entry_id}")
def library_entry(
    request: Request,
    entry_id: int,
    current_user: Annotated[User | None, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    if current_user is None:
        return RedirectResponse(url="/login", status_code=303)
    entry = _get_owned_entry(db, entry_id, current_user)
    return _render_entry(request, db, current_user, entry)


@app.post("/library/{entry_id}")
def library_entry_update(
    request: Request,
    entry_id: int,
    current_user: Annotated[User | None, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    status: Annotated[str, Form()],
    hours_played: Annotated[str, Form()] = "",
    rating: Annotated[str, Form()] = "",
    started_at: Annotated[str, Form()] = "",
    finished_at: Annotated[str, Form()] = "",
    notes: Annotated[str, Form()] = "",
):
    if current_user is None:
        return RedirectResponse(url="/login", status_code=303)
    entry = _get_owned_entry(db, entry_id, current_user)
    try:
        rating_value = int(rating) if rating else None
        hours_played_value = Decimal(hours_played) if hours_played else None
        started_at_value = date.fromisoformat(started_at) if started_at else None
        finished_at_value = date.fromisoformat(finished_at) if finished_at else None
        entry_notes_value = notes.strip() or None
    except (ValueError, InvalidOperation):
        return _render_entry(
            request, db, current_user, entry, "Please check the values you entered", 400
        )

    if status not in LIBRARY_STATUSES:
        return _render_entry(
            request,
            db,
            current_user,
            entry,
            error="Invalid status.",
            status_code=400,
        )
    if rating_value is not None and not 1 <= rating_value <= 10:
        return _render_entry(
            request,
            db,
            current_user,
            entry,
            error="Rating must be between 1 and 10.",
            status_code=400,
        )
    if hours_played_value is not None and not 0 <= hours_played_value <= Decimal(
        "99999.9"
    ):
        return _render_entry(
            request,
            db,
            current_user,
            entry,
            error="Hours played is not valid",
            status_code=400,
        )
    if started_at_value and finished_at_value and finished_at_value < started_at_value:
        return _render_entry(
            request,
            db,
            current_user,
            entry,
            error='"Started at" must be before "Finished at"',
            status_code=400,
        )

    entry.status = status
    entry.rating = rating_value
    entry.hours_played = hours_played_value
    entry.started_at = started_at_value
    entry.finished_at = finished_at_value
    entry.notes = entry_notes_value

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return _render_entry(
            request,
            db,
            current_user,
            entry,
            error="Could not save your changes",
            status_code=400,
        )

    return RedirectResponse(url=f"/library/{entry.id}", status_code=303)


@app.post("/library/{entry_id}/status")
def library_entry_status(
    request: Request,
    entry_id: int,
    current_user: Annotated[User | None, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    status: Annotated[str, Form()],
):
    if current_user is None:
        raise HTTPException(status_code=401)
    entry = _get_owned_entry(db, entry_id, current_user)

    if status not in LIBRARY_STATUSES:
        raise HTTPException(status_code=400)
    entry.status = status
    db.commit()

    return templates.TemplateResponse(
        request,
        "partials/entry_status.html",
        {"entry": entry, "statuses": LIBRARY_STATUSES},
    )


@app.post("/library/{entry_id}/delete")
def library_delete(
    entry_id: int,
    current_user: Annotated[User | None, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    if current_user is None:
        raise HTTPException(status_code=401)
    entry = _get_owned_entry(db, entry_id, current_user)

    db.delete(entry)
    db.commit()

    return HTMLResponse("<li>Game removed.</li>")
    