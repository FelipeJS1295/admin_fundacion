from datetime import date
from typing import Optional

from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Transaccion, Categoria

router = APIRouter()
from app.core.templates import templates


def limites_mes_actual() -> tuple[date, date]:
    """Devuelve (inicio_mes, inicio_mes_siguiente)."""
    hoy = date.today()
    inicio = hoy.replace(day=1)
    if hoy.month == 12:
        fin = date(hoy.year + 1, 1, 1)
    else:
        fin = date(hoy.year, hoy.month + 1, 1)
    return inicio, fin


@router.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    """Resumen del mes + últimos movimientos."""
    inicio, fin = limites_mes_actual()

    total_entradas = db.query(func.coalesce(func.sum(Transaccion.monto), 0)) \
        .filter(
            Transaccion.tipo == "entrada",
            Transaccion.fecha >= inicio,
            Transaccion.fecha < fin
        ).scalar()

    total_salidas = db.query(func.coalesce(func.sum(Transaccion.monto), 0)) \
        .filter(
            Transaccion.tipo == "salida",
            Transaccion.fecha >= inicio,
            Transaccion.fecha < fin
        ).scalar()

    balance = (total_entradas or 0) - (total_salidas or 0)

    ultimos = db.query(Transaccion) \
        .order_by(Transaccion.fecha.desc(), Transaccion.id.desc()) \
        .limit(10).all()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "total_entradas_mes": float(total_entradas or 0),
        "total_salidas_mes": float(total_salidas or 0),
        "balance_mes": float(balance or 0),
        "ultimos": ultimos
    })


@router.get("/transacciones", response_class=HTMLResponse)
def listar_transacciones(
    request: Request,
    db: Session = Depends(get_db),
    tipo: Optional[str] = Query(None, description="entrada|salida"),
    categoria_id: Optional[int] = Query(None),
    metodo_pago: Optional[str] = Query(None),
    desde: Optional[date] = Query(None),
    hasta: Optional[date] = Query(None),
    q: Optional[str] = Query(None, description="buscar en descripción"),
    limit: int = Query(100, ge=1, le=1000),
):
    """
    Lista de transacciones (últimas N). Soporta filtros por querystring:
    /transacciones?tipo=entrada&categoria_id=1&desde=2025-01-01&hasta=2025-12-31&q=aporte
    """
    query = db.query(Transaccion)

    if tipo in {"entrada", "salida"}:
        query = query.filter(Transaccion.tipo == tipo)
    if categoria_id:
        query = query.filter(Transaccion.categoria_id == categoria_id)
    if metodo_pago:
        query = query.filter(Transaccion.metodo_pago == metodo_pago)
    if desde:
        query = query.filter(Transaccion.fecha >= desde)
    if hasta:
        query = query.filter(Transaccion.fecha <= hasta)
    if q:
        # MySQL es case-insensitive por collation; LIKE alcanza.
        query = query.filter(Transaccion.descripcion.like(f"%{q}%"))

    transacciones = query.order_by(
        Transaccion.fecha.desc(), Transaccion.id.desc()
    ).limit(limit).all()

    categorias = db.query(Categoria).order_by(Categoria.nombre).all()

    return templates.TemplateResponse("transacciones.html", {
        "request": request,
        "transacciones": transacciones,
        "categorias": categorias,
        "filtros": {
            "tipo": tipo, "categoria_id": categoria_id, "metodo_pago": metodo_pago,
            "desde": desde, "hasta": hasta, "q": q, "limit": limit
        }
    })
