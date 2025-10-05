# routers/dashboard.py
from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from app.db import get_db
from app.models import Transaccion, Categoria
from app.core.templates import templates

router = APIRouter(tags=["dashboard"])

def _parse_date(s: Optional[str]) -> Optional[date]:
    if not s: return None
    try:
        return datetime.fromisoformat(s).date()
    except Exception:
        return None

def _month_limits_today() -> tuple[date, date]:
    hoy = date.today()
    inicio = hoy.replace(day=1)
    if hoy.month == 12:
        fin = date(hoy.year + 1, 1, 1)
    else:
        fin = date(hoy.year, hoy.month + 1, 1)
    return inicio, fin

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_view(
    request: Request,
    db: Session = Depends(get_db),
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    categoria_id: Optional[str] = Query(None),
    metodo_pago: Optional[str] = Query(None),
):
    # Rango por defecto = mes actual
    d_default_start, d_default_end = _month_limits_today()
    d1 = _parse_date(desde) or d_default_start
    d2 = _parse_date(hasta)  or d_default_end

    # Filtros comunes
    filtros = [Transaccion.fecha >= d1, Transaccion.fecha < d2]
    if categoria_id and categoria_id.isdigit():
        filtros.append(Transaccion.categoria_id == int(categoria_id))
    if metodo_pago:
        filtros.append(Transaccion.metodo_pago == metodo_pago)

    # KPIs
    total_entradas = (db.query(func.coalesce(func.sum(Transaccion.monto), 0))
                        .filter(*filtros, Transaccion.tipo == "entrada")
                        .scalar() or 0)
    total_salidas  = (db.query(func.coalesce(func.sum(Transaccion.monto), 0))
                        .filter(*filtros, Transaccion.tipo == "salida")
                        .scalar() or 0)
    neto = total_entradas - total_salidas

    # Serie diaria: entradas vs salidas por día
    # group by fecha dentro del rango
    entradas_case = case((Transaccion.tipo == "entrada", Transaccion.monto), else_=0)
    salidas_case  = case((Transaccion.tipo == "salida",  Transaccion.monto), else_=0)

    serie_rows = (
        db.query(
            Transaccion.fecha.label("fecha"),
            func.coalesce(func.sum(entradas_case), 0).label("entradas"),
            func.coalesce(func.sum(salidas_case),  0).label("salidas"),
        )
        .filter(*filtros)
        .group_by(Transaccion.fecha)
        .order_by(Transaccion.fecha.asc())
        .all()
    )
    serie = [
        {"fecha": r.fecha.isoformat(), "entradas": float(r.entradas), "salidas": float(r.salidas)}
        for r in serie_rows
    ]

    # Top categorías (entradas)
    cat_ent_rows = (
        db.query(Categoria.nombre, func.coalesce(func.sum(Transaccion.monto), 0))
        .join(Categoria, Categoria.id == Transaccion.categoria_id, isouter=True)
        .filter(*filtros, Transaccion.tipo == "entrada")
        .group_by(Categoria.nombre)
        .order_by(func.sum(Transaccion.monto).desc())
        .limit(8)
        .all()
    )
    cat_entradas = [{"categoria": (n or "Sin categoría"), "total": float(t)} for n, t in cat_ent_rows]

    # Top categorías (salidas)
    cat_sal_rows = (
        db.query(Categoria.nombre, func.coalesce(func.sum(Transaccion.monto), 0))
        .join(Categoria, Categoria.id == Transaccion.categoria_id, isouter=True)
        .filter(*filtros, Transaccion.tipo == "salida")
        .group_by(Categoria.nombre)
        .order_by(func.sum(Transaccion.monto).desc())
        .limit(8)
        .all()
    )
    cat_salidas = [{"categoria": (n or "Sin categoría"), "total": float(t)} for n, t in cat_sal_rows]

    # Métodos de pago (pie) — entradas
    met_ent_rows = (
        db.query(Transaccion.metodo_pago, func.coalesce(func.sum(Transaccion.monto), 0))
        .filter(*filtros, Transaccion.tipo == "entrada")
        .group_by(Transaccion.metodo_pago)
        .order_by(func.sum(Transaccion.monto).desc())
        .all()
    )
    met_entradas = [{"metodo": (m or "otros"), "total": float(t)} for m, t in met_ent_rows]

    # Métodos de pago (pie) — salidas
    met_sal_rows = (
        db.query(Transaccion.metodo_pago, func.coalesce(func.sum(Transaccion.monto), 0))
        .filter(*filtros, Transaccion.tipo == "salida")
        .group_by(Transaccion.metodo_pago)
        .order_by(func.sum(Transaccion.monto).desc())
        .all()
    )
    met_salidas = [{"metodo": (m or "otros"), "total": float(t)} for m, t in met_sal_rows]

    # Últimos movimientos (para tabla compacta)
    ultimos = (db.query(Transaccion)
                 .filter(*filtros)
                 .order_by(Transaccion.fecha.desc(), Transaccion.id.desc())
                 .limit(10).all())

    # Para selects
    categorias = db.query(Categoria).order_by(Categoria.nombre).all()

    return templates.TemplateResponse("dashboard/index.html", {
        "request": request,
        "desde": d1.isoformat(),
        "hasta": d2.isoformat(),
        "categoria_id": int(categoria_id) if (categoria_id and categoria_id.isdigit()) else "",
        "metodo_pago": metodo_pago or "",

        "kpi": {
            "entradas": float(total_entradas),
            "salidas": float(total_salidas),
            "neto": float(neto),
        },
        "serie": serie,
        "cat_entradas": cat_entradas,
        "cat_salidas": cat_salidas,
        "met_entradas": met_entradas,
        "met_salidas": met_salidas,
        "ultimos": ultimos,
        "categorias": categorias,
    })
