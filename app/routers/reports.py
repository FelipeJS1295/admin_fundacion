from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from sqlalchemy import func, extract
from app.db import get_db
from app.models_finanzas import BancoMovimiento, CajaMovimiento
from app.models import Categoria
from app.core.templates import templates
from app.utils.money import clp

router = APIRouter(prefix="/informes", tags=["Informes"])

@router.get("/anual", response_class=HTMLResponse)
def informe_detallado(request: Request, db: Session = Depends(get_db)):
    hoy = date.today()
    primer_dia_mes = hoy.replace(day=1)
    ultimo_dia_mes_pasado = primer_dia_mes - timedelta(days=1)
    primer_dia_mes_pasado = ultimo_dia_mes_pasado.replace(day=1)

    # 1. Función para obtener métricas de un periodo
    def get_period_metrics(start_date: date, end_date: date):
        metrics = {"ingresos": 0, "gastos": 0}
        for Model in [BancoMovimiento, CajaMovimiento]:
            ing = db.query(func.sum(Model.monto)).filter(Model.tipo == 'entrada', Model.fecha.between(start_date, end_date)).scalar() or 0
            gas = db.query(func.sum(Model.monto)).filter(Model.tipo == 'salida', Model.fecha.between(start_date, end_date)).scalar() or 0
            metrics["ingresos"] += float(ing)
            metrics["gastos"] += float(gas)
        return metrics

    actual = get_period_metrics(primer_dia_mes, hoy)
    pasado = get_period_metrics(primer_dia_mes_pasado, ultimo_dia_mes_pasado)

    # 2. Cálculos de variación (Crecimiento %)
    def calcular_variacion(actual, anterior):
        if anterior == 0: return 100 if actual > 0 else 0
        return ((actual - anterior) / anterior) * 100

    variacion_ingresos = calcular_variacion(actual["ingresos"], pasado["ingresos"])
    variacion_gastos = calcular_variacion(actual["gastos"], pasado["gastos"])

    # 3. Totales por Categoría (Top 5 Gastos)
    def get_top_categories(tipo='salida'):
        res = []
        # Combinamos ambas tablas en una query de categorías
        for Model in [BancoMovimiento, CajaMovimiento]:
            query = db.query(Categoria.nombre, func.sum(Model.monto).label('total'))\
                .join(Model, Model.categoria_id == Categoria.id)\
                .filter(Model.tipo == tipo)\
                .group_by(Categoria.nombre).all()
            res.extend(query)
        
        # Agrupar repetidos si existen en ambas fuentes
        final = {}
        for nombre, total in res:
            final[nombre] = final.get(nombre, 0) + float(total)
        return sorted(final.items(), key=lambda x: x[1], reverse=True)[:5]

    # 4. Salud por Fuente (Saldo actual Banco vs Caja)
    saldo_banco_ing = db.query(func.sum(BancoMovimiento.monto)).filter(BancoMovimiento.tipo == 'entrada').scalar() or 0
    saldo_banco_gas = db.query(func.sum(BancoMovimiento.monto)).filter(BancoMovimiento.tipo == 'salida').scalar() or 0
    saldo_caja_ing = db.query(func.sum(CajaMovimiento.monto)).filter(CajaMovimiento.tipo == 'entrada').scalar() or 0
    saldo_caja_gas = db.query(func.sum(CajaMovimiento.monto)).filter(CajaMovimiento.tipo == 'salida').scalar() or 0

    return templates.TemplateResponse("informes/detallado.html", {
        "request": request,
        "mes_actual": actual,
        "variaciones": {"ing": variacion_ingresos, "gas": variacion_gastos},
        "top_gastos": get_top_categories('salida'),
        "top_ingresos": get_top_categories('entrada'),
        "fuentes": {
            "banco": float(saldo_banco_ing - saldo_banco_gas),
            "caja": float(saldo_caja_ing - saldo_caja_gas)
        },
        "fecha_informe": hoy.strftime("%d/%m/%Y")
    })