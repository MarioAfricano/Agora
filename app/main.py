from datetime import UTC, datetime
from typing import Annotated

import httpx
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
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
from app.models import Game, LIBRARY_STATUSES, LibraryEntry, User
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
):
    if current_user is None:
        return RedirectResponse(url="/login", status_code=303)

    entries = db.execute(
        select(LibraryEntry, Game)
        .join(Game, LibraryEntry.game_id == Game.id)
        .where(LibraryEntry.user_id == current_user.id)
        .order_by(LibraryEntry.created_at.desc())
    ).all()

    return templates.TemplateResponse(
        request, "library.html", {"current_user": current_user, "entries": entries}
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


@app.get("/library/{entry_id}")
def library_entry(
    request: Request,
    entry_id: int,
    current_user: Annotated[User | None, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    if current_user is None:
        return RedirectResponse(url="/login", status_code=303)
    entry = db.get(LibraryEntry, entry_id)
    if not entry or entry.user_id != current_user.id:
        raise HTTPException(status_code=404)
    game = db.get(Game, entry.game_id)

    return templates.TemplateResponse(
        request,
        "entry.html",
        {"current_user": current_user, "entry": entry, "game": game, "statuses": LIBRARY_STATUSES},
    )
