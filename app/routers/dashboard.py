# routers/dashboard.py
from datetime import date, datetime, timedelta
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

def _month_limits_for(dt: date) -> tuple[date, date]:
    """(inicio_mes, inicio_mes_siguiente)"""
    ini = dt.replace(day=1)
    if dt.month == 12:
        fin = date(dt.year + 1, 1, 1)
    else:
        fin = date(dt.year, dt.month + 1, 1)
    return ini, fin

def _month_limits_today() -> tuple[date, date]:
    return _month_limits_for(date.today())

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_view(
    request: Request,
    db: Session = Depends(get_db),
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    categoria_id: Optional[str] = Query(None),
    metodo_pago: Optional[str] = Query(None),
):
    # 1) Rango por defecto = mes actual
    d_default_start, d_default_end = _month_limits_today()

    d1 = _parse_date(desde) or d_default_start
    d2 = _parse_date(hasta)  or d_default_end

    # "Hasta" incluyente -> usamos < (d2 + 1 día) internamente
    d2_excl = d2 + timedelta(days=1)

    user_set_range = (desde is not None) or (hasta is not None)

    # 2) Filtros comunes
    filtros = [Transaccion.fecha >= d1, Transaccion.fecha < d2_excl]
    if categoria_id and categoria_id.isdigit():
        filtros.append(Transaccion.categoria_id == int(categoria_id))
    if metodo_pago:
        filtros.append(Transaccion.metodo_pago == metodo_pago)

    # 3) Si el usuario no eligió fechas y no hay datos en el mes actual,
    #    ajustamos el rango al último mes con movimientos (o a últimos 30 días como fallback).
    has_data = db.query(func.count(Transaccion.id)).filter(*filtros).scalar() or 0
    if not user_set_range and has_data == 0:
        # último día con movimientos
        last_date: Optional[date] = db.query(func.max(Transaccion.fecha)).scalar()
        if last_date:
            d1, d2 = _month_limits_for(last_date)
            d2_excl = d2  # ya es inicio del siguiente mes
        else:
            # fallback: últimos 30 días
            d2 = date.today()
            d1 = d2 - timedelta(days=30)
            d2_excl = d2 + timedelta(days=1)
        # recomponer filtros con el nuevo rango
        filtros = [Transaccion.fecha >= d1, Transaccion.fecha < d2_excl]
        if categoria_id and categoria_id.isdigit():
            filtros.append(Transaccion.categoria_id == int(categoria_id))
        if metodo_pago:
            filtros.append(Transaccion.metodo_pago == metodo_pago)

    # 4) KPIs
    total_entradas = (db.query(func.coalesce(func.sum(Transaccion.monto), 0))
                        .filter(*filtros, Transaccion.tipo == "entrada")
                        .scalar() or 0)
    total_salidas  = (db.query(func.coalesce(func.sum(Transaccion.monto), 0))
                        .filter(*filtros, Transaccion.tipo == "salida")
                        .scalar() or 0)
    neto = total_entradas - total_salidas

    # 5) Serie diaria: entradas vs salidas por día
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

    # 6) Top categorías (entradas y salidas)
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

    # 7) Métodos de pago (entradas/salidas)
    met_ent_rows = (
        db.query(Transaccion.metodo_pago, func.coalesce(func.sum(Transaccion.monto), 0))
        .filter(*filtros, Transaccion.tipo == "entrada")
        .group_by(Transaccion.metodo_pago)
        .order_by(func.sum(Transaccion.monto).desc())
        .all()
    )
    met_entradas = [{"metodo": (m or "otros"), "total": float(t)} for m, t in met_ent_rows]

    met_sal_rows = (
        db.query(Transaccion.metodo_pago, func.coalesce(func.sum(Transaccion.monto), 0))
        .filter(*filtros, Transaccion.tipo == "salida")
        .group_by(Transaccion.metodo_pago)
        .order_by(func.sum(Transaccion.monto).desc())
        .all()
    )
    met_salidas = [{"metodo": (m or "otros"), "total": float(t)} for m, t in met_sal_rows]

    # 8) Últimos movimientos
    ultimos = (
        db.query(Transaccion)
          .filter(*filtros)
          .order_by(Transaccion.fecha.desc(), Transaccion.id.desc())
          .limit(10).all()
    )

    # 9) Selects
    categorias = db.query(Categoria).order_by(Categoria.nombre).all()

    # 10) Devolvemos el rango que realmente se usó (para que el form lo muestre)
    return templates.TemplateResponse("dashboard/index.html", {
        "request": request,
        "desde": d1.isoformat(),
        "hasta": (d2_excl - timedelta(days=1)).isoformat(),  # mostramos el "hasta" incluyente
        "categoria_id": int(categoria_id) if (categoria_id and categoria_id.isdigit()) else "",
        "metodo_pago": metodo_pago or "",

        "kpi": {"entradas": float(total_entradas), "salidas": float(total_salidas), "neto": float(neto)},
        "serie": serie,
        "cat_entradas": cat_entradas,
        "cat_salidas": cat_salidas,
        "met_entradas": met_entradas,
        "met_salidas": met_salidas,
        "ultimos": ultimos,
        "categorias": categorias,
    })
