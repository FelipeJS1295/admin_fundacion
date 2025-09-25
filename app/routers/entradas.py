from datetime import date, datetime
from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db import get_db
from app.models import Transaccion, Categoria

router = APIRouter(tags=["entradas"])
templates = Jinja2Templates(directory="templates")

def categorias_entrada(db: Session):
    return db.query(Categoria)\
             .filter(or_(Categoria.tipo == "entrada", Categoria.tipo == "mixta"))\
             .order_by(Categoria.nombre)\
             .all()

# LISTADO
@router.get("/entradas", response_class=HTMLResponse)
def listar_entradas(
    request: Request,
    db: Session = Depends(get_db),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    categoria_id: int | None = Query(None),
    metodo_pago: str | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
):
    query = db.query(Transaccion).filter(Transaccion.tipo == "entrada")
    if desde:
        query = query.filter(Transaccion.fecha >= desde)
    if hasta:
        query = query.filter(Transaccion.fecha <= hasta)
    if categoria_id:
        query = query.filter(Transaccion.categoria_id == categoria_id)
    if metodo_pago:
        query = query.filter(Transaccion.metodo_pago == metodo_pago)
    if q:
        query = query.filter(Transaccion.descripcion.like(f"%{q}%"))

    entradas = query.order_by(Transaccion.fecha.desc(), Transaccion.id.desc()).limit(limit).all()
    cats = categorias_entrada(db)

    return templates.TemplateResponse("entradas_list.html", {
        "request": request,
        "entradas": entradas,
        "categorias": cats,
        "filtros": {"desde": desde, "hasta": hasta, "categoria_id": categoria_id,
                    "metodo_pago": metodo_pago, "q": q, "limit": limit}
    })

# CREAR
@router.get("/entradas/nueva", response_class=HTMLResponse)
def nueva_entrada_form(request: Request, db: Session = Depends(get_db)):
    cats = categorias_entrada(db)
    return templates.TemplateResponse("entradas_form.html", {
        "request": request,
        "categorias": cats,
        "today": date.today().isoformat()
    })

@router.post("/entradas")
def crear_entrada(
    request: Request,
    fecha: str = Form(...),
    monto: float = Form(...),
    categoria_id: int | None = Form(None),
    metodo_pago: str = Form("efectivo"),
    descripcion: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        f = datetime.fromisoformat(fecha).date()
    except Exception:
        f = date.today()
    if monto <= 0:
        return RedirectResponse(url="/entradas/nueva?error=Monto%20inv%C3%A1lido", status_code=303)
    cat = db.get(Categoria, categoria_id) if categoria_id else None
    tx = Transaccion(
        fecha=f, tipo="entrada", monto=monto,
        metodo_pago=metodo_pago, descripcion=descripcion.strip(), categoria=cat
    )
    db.add(tx)
    db.commit()
    return RedirectResponse(url="/entradas?ok=1", status_code=303)

# VER
@router.get("/entradas/{tx_id}", response_class=HTMLResponse)
def ver_entrada(tx_id: int, request: Request, db: Session = Depends(get_db)):
    tx = db.get(Transaccion, tx_id)
    if not tx or tx.tipo != "entrada":
        return RedirectResponse(url="/entradas?error=Entrada%20no%20encontrada", status_code=303)
    return templates.TemplateResponse("entradas_show.html", {
        "request": request, "t": tx
    })

# EDITAR
@router.get("/entradas/{tx_id}/editar", response_class=HTMLResponse)
def editar_entrada_form(tx_id: int, request: Request, db: Session = Depends(get_db)):
    tx = db.get(Transaccion, tx_id)
    if not tx or tx.tipo != "entrada":
        return RedirectResponse(url="/entradas?error=Entrada%20no%20encontrada", status_code=303)
    cats = categorias_entrada(db)
    return templates.TemplateResponse("entradas_edit.html", {
        "request": request, "t": tx, "categorias": cats
    })

@router.post("/entradas/{tx_id}")
def actualizar_entrada(
    tx_id: int,
    request: Request,
    fecha: str = Form(...),
    monto: float = Form(...),
    categoria_id: int | None = Form(None),
    metodo_pago: str = Form("efectivo"),
    descripcion: str = Form(""),
    db: Session = Depends(get_db),
):
    tx = db.get(Transaccion, tx_id)
    if not tx or tx.tipo != "entrada":
        return RedirectResponse(url="/entradas?error=Entrada%20no%20encontrada", status_code=303)
    try:
        tx.fecha = datetime.fromisoformat(fecha).date()
    except Exception:
        tx.fecha = date.today()
    tx.monto = monto
    tx.metodo_pago = metodo_pago
    tx.descripcion = descripcion.strip()
    tx.categoria = db.get(Categoria, categoria_id) if categoria_id else None
    db.commit()
    return RedirectResponse(url=f"/entradas/{tx_id}?ok=1", status_code=303)

# ELIMINAR
@router.post("/entradas/{tx_id}/eliminar")
def eliminar_entrada(tx_id: int, db: Session = Depends(get_db)):
    tx = db.get(Transaccion, tx_id)
    if tx and tx.tipo == "entrada":
        db.delete(tx)
        db.commit()
    return RedirectResponse(url="/entradas?ok=1", status_code=303)
