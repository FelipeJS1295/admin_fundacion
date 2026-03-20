from datetime import date
from typing import Optional
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from app.db import get_db
from app.models_finanzas import BancoMovimiento, CajaMovimiento
from app.models import Categoria
from app.core.templates import templates

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/", response_class=HTMLResponse)
def dashboard_consolidado(
    request: Request,
    db: Session = Depends(get_db),
    desde: Optional[date] = Query(None),
    hasta: Optional[date] = Query(None),
    categoria_id: Optional[int] = Query(None),
    metodo: Optional[str] = Query(None),
    origen: Optional[str] = Query(None),
):
    # 1. Configuración de fuentes según filtro de origen
    fuentes_config = []
    if not origen or origen == "Banco":
        fuentes_config.append({"model": BancoMovimiento, "label": "Banco"})
    if not origen or origen == "Caja":
        fuentes_config.append({"model": CajaMovimiento, "label": "Caja"})

    movimientos_mezclados = []
    datos_por_dia = {}
    datos_cat_ent = {}
    datos_cat_sal = {}

    # 2. Consulta y procesamiento
    for fuente in fuentes_config:
        Model = fuente["model"]
        query = db.query(Model, Categoria.nombre.label("cat_nombre")).outerjoin(
            Categoria, Model.categoria_id == Categoria.id
        )

        if desde: query = query.filter(Model.fecha >= desde)
        if hasta: query = query.filter(Model.fecha <= hasta)
        if categoria_id: query = query.filter(Model.categoria_id == categoria_id)
        if fuente["label"] == "Banco" and metodo:
            query = query.filter(Model.metodo_pago == metodo)

        resultados = query.all()

        for obj, cat_nombre in resultados:
            monto = float(obj.monto)
            cat_name = cat_nombre or "Sin categoría"
            fecha_iso = obj.fecha.isoformat()

            # Datos para la tabla
            movimientos_mezclados.append({
                "fecha": obj.fecha,
                "tipo": obj.tipo,
                "monto": monto,
                "categoria": cat_name,
                "origen": fuente["label"],
                "concepto": obj.concepto
            })

            # Agregación para Gráfico de Línea
            if fecha_iso not in datos_por_dia:
                datos_por_dia[fecha_iso] = {"entradas": 0, "salidas": 0}
            
            if obj.tipo == "entrada":
                datos_por_dia[fecha_iso]["entradas"] += monto
                datos_cat_ent[cat_name] = datos_cat_ent.get(cat_name, 0) + monto
            else:
                datos_por_dia[fecha_iso]["salidas"] += monto
                datos_cat_sal[cat_name] = datos_cat_sal.get(cat_name, 0) + monto

    # 3. Ordenar y formatear para el frontend
    movimientos_mezclados.sort(key=lambda x: x["fecha"], reverse=True)
    
    serie_diaria = [
        {"fecha": k, "entradas": v["entradas"], "salidas": v["salidas"]} 
        for k, v in sorted(datos_por_dia.items())
    ]
    
    cat_ent_list = [{"categoria": k, "total": v} for k, v in sorted(datos_cat_ent.items(), key=lambda x: x[1], reverse=True)]
    cat_sal_list = [{"categoria": k, "total": v} for k, v in sorted(datos_cat_sal.items(), key=lambda x: x[1], reverse=True)]

    # 4. Respuesta
    return templates.TemplateResponse("dashboard/index.html", {
        "request": request,
        "items": movimientos_mezclados,
        "kpi": {
            "entradas": sum(d['total'] for d in cat_ent_list),
            "salidas": sum(d['total'] for d in cat_sal_list),
            "neto": sum(d['total'] for d in cat_ent_list) - sum(d['total'] for d in cat_sal_list)
        },
        "serie": serie_diaria,
        "cat_entradas": cat_ent_list[:8],
        "cat_salidas": cat_sal_list[:8],
        "categorias": db.query(Categoria).order_by(Categoria.nombre).all(),
        "filtro": {
            "desde": desde.isoformat() if desde else "",
            "hasta": hasta.isoformat() if hasta else "",
            "categoria_id": categoria_id,
            "metodo": metodo,
            "origen": origen
        }
    })