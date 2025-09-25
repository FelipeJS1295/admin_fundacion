# app/routers/categorias.py
from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.db import get_db
from app.models import Categoria

router = APIRouter(tags=["categorias"])
templates = Jinja2Templates(directory="templates")

@router.get("/categorias", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    cats = db.query(Categoria).order_by(Categoria.nombre).all()
    return templates.TemplateResponse("categorias_index.html", {
        "request": request, "categorias": cats
    })

@router.get("/categorias/nueva", response_class=HTMLResponse)
def nueva(request: Request):
    return templates.TemplateResponse("categorias_form.html", {
        "request": request, "modo": "crear", "categoria": None
    })

@router.post("/categorias")
def crear(
    request: Request,
    nombre: str = Form(...),
    tipo: str = Form(...),
    db: Session = Depends(get_db),
):
    c = Categoria(nombre=nombre.strip(), tipo=tipo)
    db.add(c)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return RedirectResponse(url="/categorias/nueva?error=Nombre%20ya%20existe", status_code=303)
    return RedirectResponse(url="/categorias?ok=1", status_code=303)

@router.get("/categorias/{cat_id}/editar", response_class=HTMLResponse)
def editar_form(cat_id: int, request: Request, db: Session = Depends(get_db)):
    c = db.get(Categoria, cat_id)
    if not c:
        return RedirectResponse(url="/categorias?error=No%20encontrada", status_code=303)
    return templates.TemplateResponse("categorias_form.html", {
        "request": request, "modo": "editar", "categoria": c
    })

@router.post("/categorias/{cat_id}")
def actualizar(
    cat_id: int,
    request: Request,
    nombre: str = Form(...),
    tipo: str = Form(...),
    db: Session = Depends(get_db),
):
    c = db.get(Categoria, cat_id)
    if not c:
        return RedirectResponse(url="/categorias?error=No%20encontrada", status_code=303)
    c.nombre = nombre.strip()
    c.tipo = tipo
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return RedirectResponse(url=f"/categorias/{cat_id}/editar?error=Nombre%20ya%20existe", status_code=303)
    return RedirectResponse(url="/categorias?ok=1", status_code=303)

@router.post("/categorias/{cat_id}/eliminar")
def eliminar(cat_id: int, db: Session = Depends(get_db)):
    c = db.get(Categoria, cat_id)
    if c:
        db.delete(c)
        db.commit()
    return RedirectResponse(url="/categorias?ok=1", status_code=303)
