from datetime import date, datetime
from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.db import get_db
from app.models import Transaccion, Categoria

router = APIRouter(tags=["entradas"])
from app.core.templates import templates

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
    desde: str | None = Query(None),
    hasta: str | None = Query(None),
    categoria_id: str | None = Query(None),   # 👈 string
    metodo_pago: str | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
):
    # parseos seguros
    def _parse_date(s: str | None):
        if not s: return None
        try:
            return datetime.fromisoformat(s).date()
        except Exception:
            return None

    def _parse_int(s: str | None):
        return int(s) if s and s.isdigit() else None

    d1 = _parse_date(desde)
    d2 = _parse_date(hasta)
    cat_id = _parse_int(categoria_id)

    # filtros comunes
    filtros = [Transaccion.tipo == "entrada"]
    if d1: filtros.append(Transaccion.fecha >= d1)
    if d2: filtros.append(Transaccion.fecha <= d2)
    if cat_id: filtros.append(Transaccion.categoria_id == cat_id)
    if metodo_pago: filtros.append(Transaccion.metodo_pago == metodo_pago)
    if q:
        like = f"%{q}%"
        filtros.append(or_(
            Transaccion.descripcion.like(like),
            Transaccion.concepto.like(like),
            Transaccion.numero_documento.like(like),
        ))

    base_q = db.query(Transaccion).filter(*filtros)

    total = base_q.with_entities(func.coalesce(func.sum(Transaccion.monto), 0)).scalar() or 0
    entradas = (base_q
                .order_by(Transaccion.fecha.desc(), Transaccion.id.desc())
                .limit(limit).all())

    cats = categorias_entrada(db)

    return templates.TemplateResponse("entradas/list.html", {
        "request": request,
        "entradas": entradas,
        "categorias": cats,
        "total": total,
        "filtros": {
            "desde": d1.isoformat() if d1 else "",
            "hasta": d2.isoformat() if d2 else "",
            "categoria_id": cat_id,                 # 👈 devolvemos int ya parseado
            "metodo_pago": metodo_pago or "",
            "q": q or "",
            "limit": limit
        }
    })

# CREAR
@router.get("/entradas/nueva", response_class=HTMLResponse)
def nueva_entrada_form(request: Request, db: Session = Depends(get_db)):
    cats = categorias_entrada(db)
    return templates.TemplateResponse("entradas/form.html", {
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
    return templates.TemplateResponse("entradas/show.html", {
        "request": request, "t": tx
    })

# EDITAR
@router.get("/entradas/{tx_id}/editar", response_class=HTMLResponse)
def editar_entrada_form(tx_id: int, request: Request, db: Session = Depends(get_db)):
    tx = db.get(Transaccion, tx_id)
    if not tx or tx.tipo != "entrada":
        return RedirectResponse(url="/entradas?error=Entrada%20no%20encontrada", status_code=303)
    cats = categorias_entrada(db)
    return templates.TemplateResponse("entradas/edit.html", {
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
