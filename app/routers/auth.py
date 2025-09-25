from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db import get_db, SessionLocal
from app.models import User
from app.auth import verify_password, hash_password, get_current_user

router = APIRouter(tags=["auth"])
from app.core.templates import templates

@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("auth/login.html", {"request": request, "next": request.query_params.get("next", "/")})

@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == username, User.active == True).first()
    if not user or not verify_password(password, user.password_hash):
        return RedirectResponse(url="/login?error=Credenciales%20inv%C3%A1lidas", status_code=303)
    request.session["user_id"] = user.id
    return RedirectResponse(url=next or "/", status_code=303)

@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login?ok=1", status_code=303)

def seed_admin_user():
    """Crea un admin por defecto si no hay ninguno."""
    db = SessionLocal()
    try:
        existe = db.query(User).first()
        if not existe:
            admin = User(
                username="admin",
                password_hash=hash_password("admin123"),  # cámbialo luego
                role="Admin",
                active=True
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()
