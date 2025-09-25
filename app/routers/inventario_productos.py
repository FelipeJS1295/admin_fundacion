from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.templates import templates
from app.db import get_db
from app.models.inventario import Producto, Unidad, CategoriaInv

router = APIRouter(tags=["inventario:productos"])

def _get_opts(db: Session):
    unidades = db.execute(select(Unidad).where(Unidad.activo == 1).order_by(Unidad.nombre)).scalars().all()
    categorias = db.execute(select(CategoriaInv).where(CategoriaInv.activo == 1).order_by(CategoriaInv.nombre)).scalars().all()
    return {"unidades": unidades, "categorias": categorias}

@router.get("/inventario/productos", response_class=HTMLResponse)
def productos_list(request: Request, q: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Producto).order_by(Producto.nombre)
    if q:
        like = f"%{q}%"
        stmt = stmt.filter((Producto.nombre.ilike(like)) | (Producto.sku.ilike(like)))
    productos = db.execute(stmt).scalars().all()
    return templates.TemplateResponse("inventario/productos_list.html", {"request": request, "productos": productos, "q": q or ""})

@router.get("/inventario/productos/nuevo", response_class=HTMLResponse)
def productos_new_form(request: Request, db: Session = Depends(get_db)):
    ctx = {"request": request, "prod": None, **_get_opts(db)}
    return templates.TemplateResponse("inventario/productos_form.html", ctx)

@router.post("/inventario/productos/nuevo")
def productos_create(
    request: Request,
    nombre: str = Form(...),
    sku: str | None = Form(None),
    categoria_id: int | None = Form(None),
    unidad_id: int | None = Form(None),
    stock_minimo: float = Form(0),
    stock_maximo: float | None = Form(None),
    track_lote: int = Form(0),
    track_serie: int = Form(0),
    activo: int = Form(1),
    descripcion: str | None = Form(None),
    db: Session = Depends(get_db),
):
    p = Producto(
        nombre=nombre.strip(),
        sku=sku or None,
        categoria_id=categoria_id or None,
        unidad_id=unidad_id or None,
        stock_minimo=stock_minimo or 0,
        stock_maximo=stock_maximo or None,
        track_lote=1 if track_lote else 0,
        track_serie=1 if track_serie else 0,
        activo=1 if activo else 0,
        descripcion=descripcion or None,
    )
    db.add(p)
    db.commit()
    return RedirectResponse(url="/inventario/productos?ok=1", status_code=303)

@router.get("/inventario/productos/{prod_id}/editar", response_class=HTMLResponse)
def productos_edit_form(prod_id: int, request: Request, db: Session = Depends(get_db)):
    p = db.get(Producto, prod_id)
    if not p:
        raise HTTPException(404)
    ctx = {"request": request, "prod": p, **_get_opts(db)}
    return templates.TemplateResponse("inventario/productos_form.html", ctx)

@router.post("/inventario/productos/{prod_id}/editar")
def productos_update(
    prod_id: int,
    nombre: str = Form(...),
    sku: str | None = Form(None),
    categoria_id: int | None = Form(None),
    unidad_id: int | None = Form(None),
    stock_minimo: float = Form(0),
    stock_maximo: float | None = Form(None),
    track_lote: int = Form(0),
    track_serie: int = Form(0),
    activo: int = Form(1),
    descripcion: str | None = Form(None),
    db: Session = Depends(get_db),
):
    p = db.get(Producto, prod_id)
    if not p:
        raise HTTPException(404)
    p.nombre = nombre.strip()
    p.sku = sku or None
    p.categoria_id = categoria_id or None
    p.unidad_id = unidad_id or None
    p.stock_minimo = stock_minimo or 0
    p.stock_maximo = stock_maximo or None
    p.track_lote = 1 if track_lote else 0
    p.track_serie = 1 if track_serie else 0
    p.activo = 1 if activo else 0
    p.descripcion = descripcion or None
    db.commit()
    return RedirectResponse(url="/inventario/productos?ok=1", status_code=303)

@router.post("/inventario/productos/{prod_id}/eliminar")
def productos_delete(prod_id: int, db: Session = Depends(get_db)):
    p = db.get(Producto, prod_id)
    if not p:
        raise HTTPException(404)
    try:
        db.delete(p)
        db.commit()
        return RedirectResponse(url="/inventario/productos?ok=1", status_code=303)
    except Exception:
        db.rollback()
        return RedirectResponse(url="/inventario/productos?error=No%20se%20puede%20eliminar%20(producto%20en%20uso)", status_code=303)