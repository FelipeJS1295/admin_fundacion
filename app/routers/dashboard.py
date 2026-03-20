from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from typing import Optional, Literal
from datetime import date

from app.db import get_db
from app.models_finanzas import BancoMovimiento, CajaMovimiento  # Tus nuevos modelos
from app.models import Categoria
from app.core.templates import templates # O Jinja2Templates si usas el otro

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/", response_class=HTMLResponse)
def dashboard_consolidado(
    request: Request,
    db: Session = Depends(get_db),
    desde: Optional[date] = Query(None),
    hasta: Optional[date] = Query(None),
    categoria_id: Optional[int] = Query(None),
    metodo: Optional[str] = Query(None),
):
    # --- 1. Definir fuentes de datos ---
    fuentes = [
        {"model": BancoMovimiento, "label": "Banco", "color": "blue"},
        {"model": CajaMovimiento, "label": "Caja", "color": "green"}
    ]
    
    movimientos_mezclados = []

    # --- 2. Consultar ambas tablas ---
    for fuente in fuentes:
        Model = fuente["model"]
        # Join con categorías para tener el nombre
        query = db.query(Model, Categoria.nombre.label("cat_nombre")).outerjoin(
            Categoria, Model.categoria_id == Categoria.id
        )

        # Aplicar filtros comunes
        if desde: query = query.filter(Model.fecha >= desde)
        if hasta: query = query.filter(Model.fecha <= hasta)
        if categoria_id: query = query.filter(Model.categoria_id == categoria_id)
        
        # Filtro específico de Banco (si el modelo lo tiene)
        if fuente["label"] == "Banco" and metodo:
            query = query.filter(Model.metodo_pago == metodo)

        resultados = query.all()

        for obj, cat_nombre in resultados:
            movimientos_mezclados.append({
                "id": obj.id,
                "fecha": obj.fecha,
                "tipo": obj.tipo,  # 'entrada' o 'salida'
                "monto": float(obj.monto),
                "concepto": obj.concepto,
                "categoria": cat_nombre or "Sin categoría",
                "origen": fuente["label"],
                "color": fuente["color"],
                "metodo_pago": getattr(obj, "metodo_pago", "Efectivo") # Caja suele ser efectivo
            })

    # --- 3. Ordenar por fecha (lo más nuevo arriba) ---
    movimientos_mezclados.sort(key=lambda x: x["fecha"], reverse=True)

    # --- 4. Calcular Totales (KPIs) ---
    total_entradas = sum(m["monto"] for m in movimientos_mezclados if m["tipo"] == "entrada")
    total_salidas = sum(m["monto"] for m in movimientos_mezclados if m["tipo"] == "salida")
    neto = total_entradas - total_salidas

    # --- 5. Datos para selectores ---
    categorias = db.query(Categoria).order_by(Categoria.nombre).all()

    return templates.TemplateResponse("dashboard/index.html", {
        "request": request,
        "items": movimientos_mezclados[:20], # Mostramos solo los últimos 20 en el dashboard
        "kpi": {
            "entradas": total_entradas,
            "salidas": total_salidas,
            "neto": neto
        },
        "categorias": categorias,
        "filtro": {
            "desde": desde,
            "hasta": hasta,
            "categoria_id": categoria_id,
            "metodo": metodo
        }
    })