from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from sqlalchemy import func, or_
from app.db import get_db
from app.models_finanzas import BancoMovimiento, CajaMovimiento
from app.models import Categoria
from app.core.templates import templates
from app.utils.money import clp

router = APIRouter(prefix="/informes", tags=["Informes"])

@router.get("/anual", response_class=HTMLResponse)
def informe_detallado(
    request: Request, 
    db: Session = Depends(get_db),
    desde: date = Query(default=date.today().replace(day=1) - timedelta(days=180)),
    hasta: date = Query(default=date.today())
):
    # 1. Totales de fuentes (Liquidez Actual)
    def get_total(Model):
        ing = db.query(func.sum(Model.monto)).filter(Model.tipo == 'entrada').scalar() or 0
        egr = db.query(func.sum(Model.monto)).filter(Model.tipo == 'salida').scalar() or 0
        return float(ing - egr)

    # 2. Datos para Gráfico de Barras (Últimos 6 meses)
    grafico_mensual = []
    for i in range(5, -1, -1):
        fecha_temp = date.today() - timedelta(days=i*30)
        mes = fecha_temp.month
        anio = fecha_temp.year
        
        ing_mes = 0
        egr_mes = 0
        for Model in [BancoMovimiento, CajaMovimiento]:
            ing_mes += db.query(func.sum(Model.monto)).filter(func.extract('month', Model.fecha) == mes, func.extract('year', Model.fecha) == anio, Model.tipo == 'entrada').scalar() or 0
            egr_mes += db.query(func.sum(Model.monto)).filter(func.extract('month', Model.fecha) == mes, func.extract('year', Model.fecha) == anio, Model.tipo == 'salida').scalar() or 0
        
        grafico_mensual.append({
            "mes": fecha_temp.strftime("%b %Y"),
            "ingresos": float(ing_mes),
            "gastos": float(egr_mes)
        })

    # 3. Datos para Gráfico de Dona (Gastos por Categoría en el rango seleccionado)
    gastos_cat = []
    res_cat = db.query(Categoria.nombre, func.sum(BancoMovimiento.monto + CajaMovimiento.monto))\
        .select_from(Categoria)\
        .outerjoin(BancoMovimiento, BancoMovimiento.categoria_id == Categoria.id)\
        .outerjoin(CajaMovimiento, CajaMovimiento.categoria_id == Categoria.id)\
        .filter(or_(BancoMovimiento.fecha.between(desde, hasta), CajaMovimiento.fecha.between(desde, hasta)))\
        .group_by(Categoria.nombre).all()
    
    # Limpiamos y formateamos para Chart.js
    labels_dona = [r[0] for r in res_cat if r[1] is not None]
    data_dona = [float(r[1]) for r in res_cat if r[1] is not None]

    return templates.TemplateResponse("informes/detallado.html", {
        "request": request,
        "fuentes": {"banco": get_total(BancoMovimiento), "caja": get_total(CajaMovimiento)},
        "grafico_mensual": grafico_mensual,
        "dona": {"labels": labels_dona, "data": data_dona},
        "filtro": {"desde": desde, "hasta": hasta},
        "fecha_informe": date.today().strftime("%d/%m/%Y")
    })