from decimal import Decimal, InvalidOperation
from types import SimpleNamespace
from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.templates import templates
from app.db import get_db
from app.models.inv_basic import InvCategoria, UnidadMedida, InventarioItem

router = APIRouter(prefix="/inventario", tags=["inventario"])

# ---------- utilidades ----------
def _to_int(v: str | None) -> int | None:
    return int(v) if v and v.isdigit() else None

def _to_decimal(v: str | None) -> Decimal:
    if not v or v.strip() == "":
        return Decimal("0")
    try:
        return Decimal(v.replace(",", "."))
    except InvalidOperation:
        return Decimal("0")

# ========== CATEGORÍAS ==========
@router.get("/categorias", response_class=HTMLResponse)
def cat_list(request: Request, q: str | None = None, db: Session = Depends(get_db)):
    stmt = select(InvCategoria).order_by(InvCategoria.nombre)
    if q:
        stmt = stmt.where(InvCategoria.nombre.like(f"%{q}%"))
    cats = db.execute(stmt).scalars().all()

    # conteo de items por categoría
    counts = dict(
        db.execute(
            select(InventarioItem.categoria_id, func.count())
            .group_by(InventarioItem.categoria_id)
        ).all()
    )

    items = [{"cat": c, "productos": counts.get(c.id, 0)} for c in cats]
    return templates.TemplateResponse("inventario/categorias_list.html",
                                      {"request": request, "items": items, "q": q or ""})

@router.get("/categorias/nueva", response_class=HTMLResponse)
def cat_new_form(request: Request):
    return templates.TemplateResponse("inventario/categorias_form.html",
                                      {"request": request, "cat": None})

@router.post("/categorias/nueva")
def cat_create(nombre: str = Form(...), db: Session = Depends(get_db)):
    c = InvCategoria(nombre=nombre.strip())
    db.add(c); db.commit()
    return RedirectResponse("/inventario/categorias?ok=1", status_code=303)

@router.get("/categorias/{cat_id}/editar", response_class=HTMLResponse)
def cat_edit_form(cat_id: int, request: Request, db: Session = Depends(get_db)):
    c = db.get(InvCategoria, cat_id)
    if not c: raise HTTPException(404)
    return templates.TemplateResponse("inventario/categorias_form.html",
                                      {"request": request, "cat": c})

@router.post("/categorias/{cat_id}/editar")
def cat_update(cat_id: int, nombre: str = Form(...), db: Session = Depends(get_db)):
    c = db.get(InvCategoria, cat_id)
    if not c: raise HTTPException(404)
    c.nombre = nombre.strip()
    db.commit()
    return RedirectResponse("/inventario/categorias?ok=1", status_code=303)

@router.post("/categorias/{cat_id}/eliminar")
def cat_delete(cat_id: int, db: Session = Depends(get_db)):
    c = db.get(InvCategoria, cat_id)
    if not c: raise HTTPException(404)
    # bloqueo si está usada por items
    usados = db.scalar(select(func.count()).select_from(InventarioItem).where(InventarioItem.categoria_id == c.id)) or 0
    if usados:
        return RedirectResponse("/inventario/categorias?error=No%20se%20puede%20eliminar:%20tiene%20items", status_code=303)
    db.delete(c); db.commit()
    return RedirectResponse("/inventario/categorias?ok=1", status_code=303)

# ========== ITEMS ==========
@router.get("/items", response_class=HTMLResponse)
def items_list(request: Request, q: str | None = None, db: Session = Depends(get_db)):
    stmt = select(InventarioItem).order_by(InventarioItem.nombre)
    if q:
        stmt = stmt.where(InventarioItem.nombre.like(f"%{q}%"))
    rows = db.execute(stmt).scalars().all()
    return templates.TemplateResponse("inventario/items_list.html",
        {"request": request, "rows": rows, "q": q or ""})

@router.get("/items/nuevo", response_class=HTMLResponse)
def items_new_form(request: Request, db: Session = Depends(get_db)):
    cats = db.execute(select(InvCategoria).order_by(InvCategoria.nombre)).scalars().all()
    unidades = db.execute(select(UnidadMedida).order_by(UnidadMedida.nombre)).scalars().all()
    return templates.TemplateResponse("inventario/items_form.html",
        {"request": request, "item": None, "cats": cats, "unidades": unidades})

@router.post("/items/nuevo")
def items_create(
    nombre: str = Form(...),
    categoria_id: str | None = Form(None),
    unidad_id: str | None = Form(None),
    stock_inicial: str | None = Form("0"),
    db: Session = Depends(get_db),
):
    cat = _to_int(categoria_id)
    uni = _to_int(unidad_id)
    if not cat or not uni:
        return RedirectResponse("/inventario/items/nuevo?error=Categoria%20y%20unidad%20requeridas", status_code=303)
    item = InventarioItem(
        nombre=nombre.strip(),
        categoria_id=cat,
        unidad_id=uni,
        stock_inicial=_to_decimal(stock_inicial),
    )
    db.add(item); db.commit()
    return RedirectResponse("/inventario/items?ok=1", status_code=303)

@router.get("/items/{item_id}/editar", response_class=HTMLResponse)
def items_edit_form(item_id: int, request: Request, db: Session = Depends(get_db)):
    it = db.get(InventarioItem, item_id)
    if not it: raise HTTPException(404)
    cats = db.execute(select(InvCategoria).order_by(InvCategoria.nombre)).scalars().all()
    unidades = db.execute(select(UnidadMedida).order_by(UnidadMedida.nombre)).scalars().all()
    return templates.TemplateResponse("inventario/items_form.html",
        {"request": request, "item": it, "cats": cats, "unidades": unidades})

@router.post("/items/{item_id}/editar")
def items_update(
    item_id: int,
    nombre: str = Form(...),
    categoria_id: str | None = Form(None),
    unidad_id: str | None = Form(None),
    stock_inicial: str | None = Form("0"),
    db: Session = Depends(get_db),
):
    it = db.get(InventarioItem, item_id)
    if not it: raise HTTPException(404)
    it.nombre = nombre.strip()
    it.categoria_id = _to_int(categoria_id) or it.categoria_id
    it.unidad_id = _to_int(unidad_id) or it.unidad_id
    it.stock_inicial = _to_decimal(stock_inicial)
    db.commit()
    return RedirectResponse("/inventario/items?ok=1", status_code=303)

@router.post("/items/{item_id}/eliminar")
def items_delete(item_id: int, db: Session = Depends(get_db)):
    it = db.get(InventarioItem, item_id)
    if not it: raise HTTPException(404)
    db.delete(it); db.commit()
    return RedirectResponse("/inventario/items?ok=1", status_code=303)
