from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.db import engine


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