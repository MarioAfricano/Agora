from typing import Annotated

from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import text, select
from sqlalchemy.exc import OperationalError, IntegrityError
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.db import engine, get_db
from app.models import User
from app.security import hash_password, verify_password


app = FastAPI(title="Agora")
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
templates = Jinja2Templates(directory="app/templates")


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request, "home.html", {})


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
def register(request: Request):
    return templates.TemplateResponse(request, "register.html", {})

@app.post("/register")
def register_submit(
    request: Request,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    db: Session = Depends(get_db),
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
                "email": email
            },
            status_code=409,
        )

    return RedirectResponse(url="/", status_code=303)


@app.get("/login")
def login(request: Request):
    return templates.TemplateResponse(request, "login.html", {})


@app.post("/login")
def login_submit(
    request: Request,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    db: Session = Depends(get_db),
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
    return RedirectResponse(url="/", status_code=303)


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)