from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.templates import templates
from app.db import get_db
from app.models.inventario import Bodega

router = APIRouter(tags=["inventario:bodegas"])

@router.get("/inventario/bodegas", response_class=HTMLResponse)
def bodegas_list(request: Request, q: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Bodega).order_by(Bodega.nombre)
    if q:
        stmt = stmt.filter(Bodega.nombre.ilike(f"%{q}%"))
    bodegas = db.execute(stmt).scalars().all()
    return templates.TemplateResponse("inventario/bodegas_list.html", {"request": request, "bodegas": bodegas, "q": q or ""})

@router.get("/inventario/bodegas/nueva", response_class=HTMLResponse)
def bodegas_new_form(request: Request):
    return templates.TemplateResponse("inventario/bodegas_form.html", {"request": request, "bodega": None})

@router.post("/inventario/bodegas/nueva")
def bodegas_create(
    request: Request,
    nombre: str = Form(...),
    codigo: str | None = Form(None),
    ubicacion: str | None = Form(None),
    activa: int = Form(1),
    db: Session = Depends(get_db),
):
    b = Bodega(nombre=nombre.strip(), codigo=codigo or None, ubicacion=ubicacion or None, activa=1 if activa else 0)
    db.add(b)
    db.commit()
    return RedirectResponse(url="/inventario/bodegas?ok=1", status_code=303)

@router.get("/inventario/bodegas/{bodega_id}/editar", response_class=HTMLResponse)
def bodegas_edit_form(bodega_id: int, request: Request, db: Session = Depends(get_db)):
    b = db.get(Bodega, bodega_id)
    if not b:
        raise HTTPException(404)
    return templates.TemplateResponse("inventario/bodegas_form.html", {"request": request, "bodega": b})

@router.post("/inventario/bodegas/{bodega_id}/editar")
def bodegas_update(
    bodega_id: int,
    nombre: str = Form(...),
    codigo: str | None = Form(None),
    ubicacion: str | None = Form(None),
    activa: int = Form(1),
    db: Session = Depends(get_db),
):
    b = db.get(Bodega, bodega_id)
    if not b:
        raise HTTPException(404)
    b.nombre = nombre.strip()
    b.codigo = codigo or None
    b.ubicacion = ubicacion or None
    b.activa = 1 if activa else 0
    db.commit()
    return RedirectResponse(url="/inventario/bodegas?ok=1", status_code=303)

@router.post("/inventario/bodegas/{bodega_id}/eliminar")
def bodegas_delete(bodega_id: int, db: Session = Depends(get_db)):
    b = db.get(Bodega, bodega_id)
    if not b:
        raise HTTPException(404)
    try:
        db.delete(b)
        db.commit()
        return RedirectResponse(url="/inventario/bodegas?ok=1", status_code=303)
    except Exception:
        db.rollback()
        return RedirectResponse(url="/inventario/bodegas?error=No%20se%20puede%20eliminar%20(bodega%20en%20uso)", status_code=303)
