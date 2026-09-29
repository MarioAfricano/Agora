from typing import Annotated

from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.db import engine, get_db
from app.security import hash_password
from app.models import User

app = FastAPI(title="Agora")
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
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    db: Session = Depends(get_db),
):
    email = email.strip().lower()
    user = User(email=email, password_hash=hash_password(password))

    db.add(user)
    db.commit()
    return RedirectResponse(url="/", status_code=303)