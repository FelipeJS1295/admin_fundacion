from datetime import date
from typing import Optional

from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from datetime import datetime
from sqlalchemy import or_, func

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
def transacciones_list(
    request: Request,
    db: Session = Depends(get_db),
    # ⚠️ como strings para tolerar "" desde el formulario
    desde: str | None = Query(None),
    hasta: str | None = Query(None),
    categoria_id: str | None = Query(None),
    metodo_pago: str | None = Query(None),
    tipo: str | None = Query(None),        # "entrada" | "salida" | None
    q: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    # ---- helpers seguros ----
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

    # ---- filtros comunes para lista y totales ----
    filtros = []
    if d1: filtros.append(Transaccion.fecha >= d1)
    if d2: filtros.append(Transaccion.fecha <= d2)
    if cat_id: filtros.append(Transaccion.categoria_id == cat_id)
    if metodo_pago: filtros.append(Transaccion.metodo_pago == metodo_pago)
    if tipo in ("entrada", "salida"): filtros.append(Transaccion.tipo == tipo)
    if q:
        like = f"%{q}%"
        filtros.append(or_(
            Transaccion.descripcion.like(like),
            Transaccion.concepto.like(like),
            Transaccion.numero_documento.like(like),
        ))

    base_q = db.query(Transaccion).filter(*filtros)

    # ---- totales usando los MISMOS filtros ----
    total_entradas = (
        db.query(func.coalesce(func.sum(Transaccion.monto), 0))
          .filter(*filtros, Transaccion.tipo == "entrada")
          .scalar()
        or 0
    )
    total_salidas = (
        db.query(func.coalesce(func.sum(Transaccion.monto), 0))
          .filter(*filtros, Transaccion.tipo == "salida")
          .scalar()
        or 0
    )
    neto = total_entradas - total_salidas

    # ---- listado ----
    transacciones = (
        base_q.order_by(Transaccion.fecha.desc(), Transaccion.id.desc())
              .limit(limit).all()
    )

    categorias = db.query(Categoria).order_by(Categoria.nombre).all()

    return templates.TemplateResponse("transacciones.html", {
        "request": request,
        "transacciones": transacciones,
        "categorias": categorias,
        "tot": {
            "entradas": float(total_entradas),
            "salidas": float(total_salidas),
            "neto": float(neto),
        },
        "filtros": {
            "desde": d1.isoformat() if d1 else "",
            "hasta": d2.isoformat() if d2 else "",
            "categoria_id": cat_id,
            "metodo_pago": metodo_pago or "",
            "tipo": tipo or "",
            "q": q or "",
            "limit": limit,
        }
    })