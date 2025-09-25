# app/routers/usuarios.py
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db import get_db
from app.models import User
from app.auth import get_current_user, is_admin, hash_password, verify_password

router = APIRouter(tags=["usuarios"])
templates = Jinja2Templates(directory="templates")

# --------- Helpers ---------
def require_admin_or_redirect(user: User | None) -> RedirectResponse | None:
    if not is_admin(user):
        return RedirectResponse(url="/?error=Solo%20Admin", status_code=303)
    return None

# --------- Admin: listado ---------
@router.get("/usuarios", response_class=HTMLResponse)
def usuarios_index(request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    redir = require_admin_or_redirect(user)
    if redir: return redir

    users = db.query(User).order_by(User.username).all()
    return templates.TemplateResponse("usuarios_index.html", {"request": request, "users": users})

# --------- Admin: crear ---------
@router.get("/usuarios/nuevo", response_class=HTMLResponse)
def usuarios_nuevo(request: Request, user: User = Depends(get_current_user)):
    redir = require_admin_or_redirect(user)
    if redir: return redir
    return templates.TemplateResponse("usuarios_form.html", {
        "request": request, "modo": "crear", "u": None
    })

@router.post("/usuarios")
def usuarios_crear(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    username: str = Form(...),
    role: str = Form("User"),
    active: str | None = Form(None),
    password: str = Form(...),
    password2: str = Form(...),
):
    redir = require_admin_or_redirect(user)
    if redir: return redir

    if password != password2:
        return RedirectResponse(url="/usuarios/nuevo?error=Las%20claves%20no%20coinciden", status_code=303)

    nuevo = User(
        username=username.strip(),
        password_hash=hash_password(password),
        role=("Admin" if role == "Admin" else "User"),
        active=True if active == "1" else False
    )
    db.add(nuevo)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return RedirectResponse(url="/usuarios/nuevo?error=Usuario%20ya%20existe", status_code=303)

    return RedirectResponse(url="/usuarios?ok=1", status_code=303)

# --------- Admin: editar ---------
@router.get("/usuarios/{uid}/editar", response_class=HTMLResponse)
def usuarios_editar_form(uid: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    redir = require_admin_or_redirect(user)
    if redir: return redir

    u = db.get(User, uid)
    if not u:
        return RedirectResponse(url="/usuarios?error=No%20encontrado", status_code=303)
    return templates.TemplateResponse("usuarios_form.html", {
        "request": request, "modo": "editar", "u": u
    })

@router.post("/usuarios/{uid}")
def usuarios_actualizar(
    uid: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    username: str = Form(...),
    role: str = Form("User"),
    active: str | None = Form(None),
):
    redir = require_admin_or_redirect(user)
    if redir: return redir

    u = db.get(User, uid)
    if not u:
        return RedirectResponse(url="/usuarios?error=No%20encontrado", status_code=303)

    u.username = username.strip()
    u.role = "Admin" if role == "Admin" else "User"
    u.active = True if active == "1" else False
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return RedirectResponse(url=f"/usuarios/{uid}/editar?error=Usuario%20ya%20existe", status_code=303)

    return RedirectResponse(url="/usuarios?ok=1", status_code=303)

# --------- Admin: resetear contraseña de un usuario ---------
@router.get("/usuarios/{uid}/password", response_class=HTMLResponse)
def usuarios_password_form(uid: int, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    redir = require_admin_or_redirect(user)
    if redir: return redir
    u = db.get(User, uid)
    if not u:
        return RedirectResponse(url="/usuarios?error=No%20encontrado", status_code=303)
    return templates.TemplateResponse("usuarios_password.html", {"request": request, "u": u})

@router.post("/usuarios/{uid}/password")
def usuarios_password(
    uid: int,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    password: str = Form(...),
    password2: str = Form(...),
):
    redir = require_admin_or_redirect(user)
    if redir: return redir

    if password != password2:
        return RedirectResponse(url=f"/usuarios/{uid}/password?error=Claves%20no%20coinciden", status_code=303)
    u = db.get(User, uid)
    if not u:
        return RedirectResponse(url="/usuarios?error=No%20encontrado", status_code=303)
    u.password_hash = hash_password(password)
    db.commit()
    return RedirectResponse(url="/usuarios?ok=1", status_code=303)

# --------- Cambiar mi contraseña (cualquier usuario logueado) ---------
@router.get("/mi-password", response_class=HTMLResponse)
def mi_password_form(request: Request, user: User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("mi_password.html", {"request": request})

@router.post("/mi-password")
def mi_password(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    actual: str = Form(...),
    nueva: str = Form(...),
    nueva2: str = Form(...),
):
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    if nueva != nueva2:
        return RedirectResponse(url="/mi-password?error=Claves%20no%20coinciden", status_code=303)
    if not verify_password(actual, user.password_hash):
        return RedirectResponse(url="/mi-password?error=Contraseña%20actual%20incorrecta", status_code=303)

    u = db.get(User, user.id)
    u.password_hash = hash_password(nueva)
    db.commit()
    return RedirectResponse(url="/?ok=1", status_code=303)