from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.templates import templates
from app.db import get_db
from app.models.inventario import CategoriaInv, Producto

router = APIRouter(tags=["inventario:categorias"])


def _opts_padres(db: Session, excluir_id: int | None = None):
    q = select(CategoriaInv).where(CategoriaInv.activo == 1)
    if excluir_id:
        q = q.where(CategoriaInv.id != excluir_id)
    return db.execute(q.order_by(CategoriaInv.nombre)).scalars().all()


@router.get("/inventario/categorias", response_class=HTMLResponse)
def categorias_list(request: Request, q: str | None = None, db: Session = Depends(get_db)):
    # subconsultas de conteos
    sub_child = (
        select(CategoriaInv.parent_id.label("parent_id"), func.count().label("hijos"))
        .group_by(CategoriaInv.parent_id)
        .subquery()
    )
    sub_prod = (
        select(Producto.categoria_id.label("categoria_id"), func.count().label("productos"))
        .group_by(Producto.categoria_id)
        .subquery()
    )

    stmt = (
        select(
            CategoriaInv,
            func.coalesce(sub_child.c.hijos, 0),
            func.coalesce(sub_prod.c.productos, 0),
        )
        .outerjoin(sub_child, sub_child.c.parent_id == CategoriaInv.id)
        .outerjoin(sub_prod, sub_prod.c.categoria_id == CategoriaInv.id)
        .order_by(CategoriaInv.nombre)
    )

    if q:
        like = f"%{q}%"
        stmt = stmt.where(CategoriaInv.nombre.like(like))  # MySQL es case-insensitive por collation

    rows = db.execute(stmt).all()
    items = [{"cat": c, "hijos": h, "productos": p} for (c, h, p) in rows]

    return templates.TemplateResponse(
        "inventario/categorias_list.html",
        {"request": request, "items": items, "q": q or ""},
    )


@router.get("/inventario/categorias/nueva", response_class=HTMLResponse)
def categorias_new_form(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        "inventario/categorias_form.html",
        {"request": request, "cat": None, "padres": _opts_padres(db)},
    )


@router.post("/inventario/categorias/nueva")
def categorias_create(
    request: Request,
    nombre: str = Form(...),
    parent_id: int | None = Form(None),
    activa: int = Form(1),
    db: Session = Depends(get_db),
):
    c = CategoriaInv(nombre=nombre.strip(), parent_id=parent_id or None, activo=1 if activa else 0)
    db.add(c)
    db.commit()
    return RedirectResponse(url="/inventario/categorias?ok=1", status_code=303)


@router.get("/inventario/categorias/{cat_id}/editar", response_class=HTMLResponse)
def categorias_edit_form(cat_id: int, request: Request, db: Session = Depends(get_db)):
    c = db.get(CategoriaInv, cat_id)
    if not c:
        raise HTTPException(404)
    padres = _opts_padres(db, excluir_id=c.id)
    return templates.TemplateResponse(
        "inventario/categorias_form.html",
        {"request": request, "cat": c, "padres": padres},
    )


@router.post("/inventario/categorias/{cat_id}/editar")
def categorias_update(
    cat_id: int,
    nombre: str = Form(...),
    parent_id: int | None = Form(None),
    activa: int = Form(1),
    db: Session = Depends(get_db),
):
    c = db.get(CategoriaInv, cat_id)
    if not c:
        raise HTTPException(404)
    # evitar que sea padre de sí misma
    if parent_id and parent_id == c.id:
        return RedirectResponse(url="/inventario/categorias?error=Padre%20inv%C3%A1lido", status_code=303)

    c.nombre = nombre.strip()
    c.parent_id = parent_id or None
    c.activo = 1 if activa else 0
    db.commit()
    return RedirectResponse(url="/inventario/categorias?ok=1", status_code=303)


@router.post("/inventario/categorias/{cat_id}/eliminar")
def categorias_delete(cat_id: int, db: Session = Depends(get_db)):
    c = db.get(CategoriaInv, cat_id)
    if not c:
        raise HTTPException(404)

    # bloquea si tiene hijos o productos
    tiene_hijos = db.scalar(select(func.count()).select_from(CategoriaInv).where(CategoriaInv.parent_id == c.id)) or 0
    tiene_prod = db.scalar(select(func.count()).select_from(Producto).where(Producto.categoria_id == c.id)) or 0
    if tiene_hijos or tiene_prod:
        return RedirectResponse(
            url="/inventario/categorias?error=No%20se%20puede%20eliminar:%20tiene%20dependencias",
            status_code=303,
        )

    db.delete(c)
    db.commit()
    return RedirectResponse(url="/inventario/categorias?ok=1", status_code=303)
