from fastapi import APIRouter, Request, Depends, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select, func
from sqlalchemy.orm import Session, aliased

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
    # 1) Trae TODAS las categorías (aplica filtro si viene q)
    base_stmt = select(CategoriaInv).order_by(CategoriaInv.nombre)
    if q:
        like = f"%{q}%"
        base_stmt = base_stmt.where(CategoriaInv.nombre.like(like))  # MySQL collation -> case-insensitive
    cats = db.execute(base_stmt).scalars().all()

    if not cats:
        return templates.TemplateResponse(
            "inventario/categorias_list.html",
            {"request": request, "items": [], "q": q or ""},
        )

    # 2) Conteos por separado (diccionarios pid->#hijos / cid->#productos)
    child_counts = dict(
        db.execute(
            select(CategoriaInv.parent_id, func.count())
            .where(CategoriaInv.parent_id.is_not(None))
            .group_by(CategoriaInv.parent_id)
        ).all()
    )
    prod_counts = dict(
        db.execute(
            select(Producto.categoria_id, func.count())
            .where(Producto.categoria_id.is_not(None))
            .group_by(Producto.categoria_id)
        ).all()
    )

    # 3) Arma items para la vista
    items = [
        {"cat": c, "hijos": child_counts.get(c.id, 0), "productos": prod_counts.get(c.id, 0)}
        for c in cats
    ]

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
    parent_id: str | None = Form(None),   # << string
    activa: int = Form(1),
    db: Session = Depends(get_db),
):
    parent = int(parent_id) if parent_id and parent_id.isdigit() else None
    c = CategoriaInv(nombre=nombre.strip(), parent_id=parent, activo=1 if activa else 0)
    db.add(c); db.commit()
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
    parent_id: str | None = Form(None),   # << string
    activa: int = Form(1),
    db: Session = Depends(get_db),
):
    c = db.get(CategoriaInv, cat_id)
    if not c: raise HTTPException(404)
    parent = int(parent_id) if parent_id and parent_id.isdigit() else None
    if parent and parent == c.id:
        return RedirectResponse(url="/inventario/categorias?error=Padre%20inv%C3%A1lido", status_code=303)
    c.nombre = nombre.strip(); c.parent_id = parent; c.activo = 1 if activa else 0
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
