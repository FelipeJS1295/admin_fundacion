from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import date, timedelta
from typing import Optional, Literal
from sqlalchemy import func, or_, extract

from app.db import SessionLocal
from app.models_finanzas import BancoMovimiento, CajaMovimiento
from app.models import Categoria
from app.core.templates import templates
from app.utils.money import clp

router = APIRouter(prefix="/informes", tags=["Informes"])

# -------------------------- UTILS --------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def obtener_datos_informe(db: Session, desde: date, hasta: date, origen: Optional[str]):
    """
    Función centralizada para procesar la lógica de negocio 
    compartida entre la vista web y la de impresión.
    """
    # 1. Definir qué tablas consultar según el filtro de origen
    modelos = []
    if origen == "banco":
        modelos = [BancoMovimiento]
    elif origen == "caja":
        modelos = [CajaMovimiento]
    else:
        modelos = [BancoMovimiento, CajaMovimiento]

    # 2. Generar Serie Temporal (Gráfico de Barras)
    serie_data = []
    # Empezamos desde el primer día del mes 'desde'
    curr = desde.replace(day=1)
    
    while curr <= hasta:
        m, a = curr.month, curr.year
        ing, gas = 0, 0
        for M in modelos:
            # Ingresos del mes
            ing += db.query(func.sum(M.monto)).filter(
                extract('month', M.fecha) == m, 
                extract('year', M.fecha) == a,
                M.tipo == 'entrada'
            ).scalar() or 0
            
            # Gastos del mes
            gas += db.query(func.sum(M.monto)).filter(
                extract('month', M.fecha) == m, 
                extract('year', M.fecha) == a,
                M.tipo == 'salida'
            ).scalar() or 0
            
        serie_data.append({
            "label": curr.strftime("%b %Y"),
            "ingresos": float(ing),
            "gastos": float(gas)
        })
        # Avanzar al siguiente mes
        curr = (curr + timedelta(days=32)).replace(day=1)

    # 3. Distribución por Categorías (Gráfico de Dona/Torta)
    labels_pie, data_pie = [], []
    todas_categorias = db.query(Categoria).all()
    
    for cat in todas_categorias:
        total_cat = 0
        for M in modelos:
            res = db.query(func.sum(M.monto)).filter(
                M.categoria_id == cat.id,
                M.tipo == 'salida', # Normalmente los informes se enfocan en distribución de GASTOS
                M.fecha.between(desde, hasta)
            ).scalar() or 0
            total_cat += float(res)
        
        if total_cat > 0:
            labels_pie.append(cat.nombre)
            data_pie.append(total_cat)

    # 4. Cálculo de KPIs Totales
    total_ing = sum(d['ingresos'] for d in serie_data)
    total_gas = sum(d['gastos'] for d in serie_data)

    return {
        "serie": serie_data,
        "pie": {"labels": labels_pie, "data": data_pie},
        "kpi": {
            "ingresos": total_ing, 
            "gastos": total_gas, 
            "neto": total_ing - total_gas
        }
    }

# -------------------------- RUTAS --------------------------

@router.get("/anual", response_class=HTMLResponse)
def informe_ejecutivo(
    request: Request, 
    db: Session = Depends(get_db),
    desde: date = Query(default=date.today().replace(month=1, day=1)),
    hasta: date = Query(default=date.today()),
    origen: Optional[Literal["banco", "caja"]] = None
):
    """ Vista estándar con Sidebar y estilos del sistema """
    datos = obtener_datos_informe(db, desde, hasta, origen)
    categorias = db.query(Categoria).order_by(Categoria.nombre).all()

    return templates.TemplateResponse("informes/detallado.html", {
        "request": request,
        "serie": datos["serie"],
        "pie": datos["pie"],
        "kpi": datos["kpi"],
        "categorias": categorias,
        "filtro": {"desde": desde, "hasta": hasta, "origen": origen},
        "fecha_informe": date.today().strftime("%d/%m/%Y")
    })

@router.get("/imprimir", response_class=HTMLResponse)
def imprimir_reporte_limpio(
    request: Request, 
    db: Session = Depends(get_db),
    desde: date = Query(...),
    hasta: date = Query(...),
    origen: Optional[str] = None
):
    """ Vista de impresión pura (Sin Layout, fondo blanco, auto-print) """
    datos = obtener_datos_informe(db, desde, hasta, origen)

    return templates.TemplateResponse("informes/imprimir_pdf.html", {
        "request": request,
        "serie": datos["serie"],
        "pie": datos["pie"],
        "kpi": datos["kpi"],
        "filtro": {"desde": desde, "hasta": hasta, "origen": origen},
        "fecha_informe": date.today().strftime("%d/%m/%Y")
    })