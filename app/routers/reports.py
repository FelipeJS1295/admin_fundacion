from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import Optional, Literal
from sqlalchemy import func, or_, extract

from app.db import get_db
from app.models_finanzas import BancoMovimiento, CajaMovimiento
from app.models import Categoria
from app.core.templates import templates
from app.utils.money import clp

router = APIRouter(prefix="/informes", tags=["Informes"])

@router.get("/anual", response_class=HTMLResponse)
def informe_ejecutivo(
    request: Request, 
    db: Session = Depends(get_db),
    desde: date = Query(default=date.today().replace(month=1, day=1)),
    hasta: date = Query(default=date.today()),
    origen: Optional[Literal["banco", "caja"]] = None,
    categoria_id: Optional[int] = None
):
    # 1. Definir qué tablas consultar según el filtro de origen
    modelos = []
    if origen == "banco": modelos = [BancoMovimiento]
    elif origen == "caja": modelos = [CajaMovimiento]
    else: modelos = [BancoMovimiento, CajaMovimiento]

    # 2. Generar Serie Temporal (Barras) - Dinámica por el rango seleccionado
    serie_data = []
    curr = desde.replace(day=1)
    while curr <= hasta:
        m, a = curr.month, curr.year
        ing, gas = 0, 0
        for M in modelos:
            q = db.query(func.sum(M.monto)).filter(extract('month', M.fecha)==m, extract('year', M.fecha)==a)
            if categoria_id: q = q.filter(M.categoria_id == categoria_id)
            
            ing += q.filter(M.tipo == 'entrada').scalar() or 0
            gas += q.filter(M.tipo == 'salida').scalar() or 0
            
        serie_data.append({
            "label": curr.strftime("%b %Y"),
            "ingresos": float(ing),
            "gastos": float(gas)
        })
        curr = (curr + timedelta(days=32)).replace(day=1)

    # 3. Distribución por Categorías (Dona) - Reactiva a TODO
    labels_pie, data_pie = [], []
    # Consultamos la suma de gastos por categoría en el rango
    for cat in db.query(Categoria).all():
        total_cat = 0
        for M in modelos:
            res = db.query(func.sum(M.monto)).filter(
                M.categoria_id == cat.id,
                M.tipo == 'salida',
                M.fecha.between(desde, hasta)
            ).scalar() or 0
            total_cat += float(res)
        
        if total_cat > 0:
            labels_pie.append(cat.nombre)
            data_pie.append(total_cat)

    # 4. Métricas de Comparación (KPIs)
    total_ing = sum(d['ingresos'] for d in serie_data)
    total_gas = sum(d['gastos'] for d in serie_data)

    categorias = db.query(Categoria).order_by(Categoria.nombre).all()

    return templates.TemplateResponse("informes/detallado.html", {
        "request": request,
        "serie": serie_data,
        "pie": {"labels": labels_pie, "data": data_pie},
        "kpi": {"ingresos": total_ing, "gastos": total_gas, "neto": total_ing - total_gas},
        "categorias": categorias,
        "filtro": {"desde": desde, "hasta": hasta, "origen": origen, "categoria_id": categoria_id}
    })