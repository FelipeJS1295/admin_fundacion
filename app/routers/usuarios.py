# app/routers/usuarios.py
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db import get_db
from app.models import User
from app.auth import get_current_user, hash_password, verify_password
from app.auth.roles import require_admin
from app.core.templates import templates

# ---------- RUTAS SOLO ADMIN ----------
router_admin = APIRouter(
    prefix="/usuarios",
    tags=["usuarios"],
    dependencies=[Depends(require_admin)]  # <- bloquea todo este grupo
)

@router_admin.get("", response_class=HTMLResponse)
def usuarios_index(request: Request, db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.username).all()
    return templates.TemplateResponse("usuarios/index.html", {"request": request, "users": users})

@router_admin.get("/nuevo", response_class=HTMLResponse)
def usuarios_nuevo(request: Request):
    return templates.TemplateResponse("usuarios/form.html", {"request": request, "modo": "crear", "u": None})

@router_admin.post("")
def usuarios_crear(
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(...),
    role: str = Form("User"),
    active: str | None = Form(None),
    password: str = Form(...),
    password2: str = Form(...),
):
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

@router_admin.get("/{uid}/editar", response_class=HTMLResponse)
def usuarios_editar_form(uid: int, request: Request, db: Session = Depends(get_db)):
    u = db.get(User, uid)
    if not u:
        return RedirectResponse(url="/usuarios?error=No%20encontrado", status_code=303)
    return templates.TemplateResponse("usuarios/form.html", {"request": request, "modo": "editar", "u": u})

@router_admin.post("/{uid}")
def usuarios_actualizar(
    uid: int,
    request: Request,
    db: Session = Depends(get_db),
    username: str = Form(...),
    role: str = Form("User"),
    active: str | None = Form(None),
):
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

@router_admin.get("/{uid}/password", response_class=HTMLResponse)
def usuarios_password_form(uid: int, request: Request, db: Session = Depends(get_db)):
    u = db.get(User, uid)
    if not u:
        return RedirectResponse(url="/usuarios?error=No%20encontrado", status_code=303)
    return templates.TemplateResponse("usuarios/password.html", {"request": request, "u": u})

@router_admin.post("/{uid}/password")
def usuarios_password(uid: int, request: Request, db: Session = Depends(get_db), password: str = Form(...), password2: str = Form(...)):
    if password != password2:
        return RedirectResponse(url=f"/usuarios/{uid}/password?error=Claves%20no%20coinciden", status_code=303)
    u = db.get(User, uid)
    if not u:
        return RedirectResponse(url="/usuarios?error=No%20encontrado", status_code=303)
    u.password_hash = hash_password(password)
    db.commit()
    return RedirectResponse(url="/usuarios?ok=1", status_code=303)

# ---------- RUTAS DE CUENTA (cualquier usuario logueado) ----------
router_account = APIRouter(tags=["cuenta"])

@router_account.get("/mi-password", response_class=HTMLResponse)
def mi_password_form(request: Request, user: User = Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("cuenta/mi_password.html", {"request": request})

@router_account.post("/mi-password")
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
