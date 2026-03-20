from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from typing import Optional, Literal  # <--- ESTO ES LO QUE FALTA
from sqlalchemy import func, or_

from app.db import get_db
from app.models_finanzas import BancoMovimiento, CajaMovimiento
from app.models import Categoria
from app.core.templates import templates
from app.utils.money import clp

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/", response_class=HTMLResponse)
def get_dashboard(
    request: Request, 
    db: Session = Depends(get_db),
    # FILTROS RECIBIDOS DESDE EL HTML
    desde: date = Query(default=date.today() - timedelta(days=365)), # Predeterminado: último año
    hasta: date = Query(default=date.today()),
    categoria_id: Optional[int] = None,
    origen: Optional[Literal["banco", "caja"]] = None, # Filtro de fuente
    metodo: Optional[str] = None
):
    # --- 1. CONFIGURACIÓN DE MODELOS SEGÚN EL FILTRO 'ORIGEN' ---
    # Si el usuario filtra por 'banco' o 'caja', solo usamos ese modelo.
    # Si no, usamos ambos para consolidar datos.
    modelos_a_usar = []
    if origen == "banco":
        modelos_a_usar = [BancoMovimiento]
    elif origen == "caja":
        modelos_a_usar = [CajaMovimiento]
    else:
        modelos_a_usar = [BancoMovimiento, CajaMovimiento]

    # --- 2. CONSULTA DE KPIs (Ingresos, Gastos, Balance) CON FILTROS ---
    totales_consolidado = {"ingresos": 0, "gastos": 0}
    
    for Model in modelos_a_usar:
        # Consulta base con filtro de fechas
        base_query = db.query(func.sum(Model.monto)).filter(Model.fecha.between(desde, hasta))
        
        # Aplicar filtros opcionales
        if categoria_id:
            base_query = base_query.filter(Model.categoria_id == categoria_id)
        if metodo and hasattr(Model, 'metodo_pago'): # Solo Banco tiene metodo_pago
            base_query = base_query.filter(Model.metodo_pago == metodo)
            
        ing = base_query.filter(Model.tipo == 'entrada').scalar() or 0
        gas = base_query.filter(Model.tipo == 'salida').scalar() or 0
        totales_consolidado["ingresos"] += float(ing)
        totales_consolidado["gastos"] += float(gas)

    kpi = {
        "entradas": totales_consolidado["ingresos"],
        "salidas": totales_consolidado["gastos"],
        "neto": totales_consolidado["ingresos"] - totales_consolidado["gastos"]
    }

    # --- 3. DATOS DINÁMICOS PARA GRÁFICO DE BARRAS (INGRESOS vs GASTOS) ---
    # Calculamos los meses entre 'desde' y 'hasta' para construir el gráfico barra por barra
    serie_mensual = []
    fecha_bucle = desde.replace(day=1) # Empezamos en el día 1 del mes 'desde'
    
    while fecha_bucle <= hasta:
        mes = fecha_bucle.month
        anio = fecha_bucle.year
        
        ing_mes = 0
        gas_mes = 0
        
        # Sumamos datos de todas las fuentes seleccionadas para este mes
        for Model in modelos_a_usar:
            # Consulta base para el mes/año del bucle
            mes_query = db.query(func.sum(Model.monto))\
                .filter(func.extract('month', Model.fecha) == mes)\
                .filter(func.extract('year', Model.fecha) == anio)
            
            # Aplicar filtros opcionales (Categoría, Método)
            if categoria_id:
                mes_query = mes_query.filter(Model.categoria_id == categoria_id)
            if metodo and hasattr(Model, 'metodo_pago'):
                mes_query = mes_query.filter(Model.metodo_pago == metodo)
                
            ing_mes += mes_query.filter(Model.tipo == 'entrada').scalar() or 0
            gas_mes += mes_query.filter(Model.tipo == 'salida').scalar() or 0
            
        serie_mensual.append({
            "label": fecha_bucle.strftime("%b %Y"), # Ej: "Jan 2025"
            "entradas": float(ing_mes),
            "salidas": float(gas_mes)
        })
        
        # Avanzar al siguiente mes
        # Sumamos 32 días y volvemos al día 1 para asegurar el cambio de mes
        fecha_bucle = (fecha_bucle + timedelta(days=32)).replace(day=1)

    # --- 4. DATOS PARA GRÁFICO DE DONA (GASTOS POR CATEGORÍA CON FILTROS) ---
    cat_salidas = []
    # Consultamos categorías y la suma de gastos asociados en ambas tablas
    res_cat = db.query(Categoria.nombre, func.sum(BancoMovimiento.monto + CajaMovimiento.monto))\
        .select_from(Categoria)\
        .outerjoin(BancoMovimiento, BancoMovimiento.categoria_id == Categoria.id)\
        .outerjoin(CajaMovimiento, CajaMovimiento.categoria_id == Categoria.id)\
        .filter(or_(\
            BancoMovimiento.fecha.between(desde, hasta),\
            CajaMovimiento.fecha.between(desde, hasta)\
        ))
    
    # Aplicar filtros opcionales (Metodo) - Categoría no aplica aquí por ser la base
    if metodo:
        # El metodo de pago solo aplica a Banco, filtramos esa parte
        res_cat = res_cat.filter(BancoMovimiento.metodo_pago == metodo)

    res_cat = res_cat.group_by(Categoria.nombre).all()
    
    # Formatear para Chart.js
    labels_dona = [r[0] for r in res_cat if r[1] is not None]
    data_dona = [float(r[1]) for r in res_cat if r[1] is not None]

    # --- 5. RENDERIZAR TEMPLATE CON DATOS FILTRADOS ---
    # Categorías para rellenar el select del filtro
    todas_categorias = db.query(Categoria).order_by(Categoria.nombre).all()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "kpi": kpi,
        "serie_mensual": serie_mensual,
        "dona": {"labels": labels_dona, "data": data_dona},
        "categorias": todas_categorias,
        # Devolvemos los filtros para que el HTML los muestre como seleccionados
        "filtro": {
            "desde": desde,
            "hasta": hasta,
            "categoria_id": categoria_id,
            "origen": origen,
            "metodo": metodo
        },
        "paleta_colores": ['#10b981', '#3b82f6', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4']
    })