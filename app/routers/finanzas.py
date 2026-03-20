from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional, Literal
from sqlalchemy import select, or_, func

from app.db import SessionLocal
from app.models_finanzas import BancoMovimiento, CajaMovimiento
from app.models import Categoria
from app.core.templates import templates  # Importación central
from app.utils.money import clp, clp_signed # Importación de filtros

# REGISTRO DE FILTROS (Esto es lo que falta)
templates.env.filters["clp"] = clp
templates.env.filters["clp_signed"] = clp_signed

router = APIRouter(prefix="/finanzas", tags=["Finanzas"])

Tipo = Literal["entrada", "salida"]
Scope = Literal["banco", "caja"]

# -------------------------- utils --------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def to_int_or_none(v: str | None):
    if not v or v.strip() == "" or v.lower() == "null":
        return None
    try:
        return int(v)
    except ValueError:
        return None

def model_for(scope: Scope):
    return BancoMovimiento if scope == "banco" else CajaMovimiento

# -------------------------- Listados --------------------------

def render_listado(request: Request, scope: Scope, tipo: Tipo, db: Session, **filtros):
    Model = model_for(scope)
    qs = db.query(Model).filter(Model.tipo == tipo)
    
    if filtros.get('desde'): qs = qs.filter(Model.fecha >= filtros['desde'])
    if filtros.get('hasta'): qs = qs.filter(Model.fecha <= filtros['hasta'])
    if filtros.get('categoria_id'): qs = qs.filter(Model.categoria_id == filtros['categoria_id'])
    if scope == "banco" and filtros.get('metodo'): qs = qs.filter(Model.metodo_pago == filtros['metodo'])
    if filtros.get('q'): qs = qs.filter(Model.concepto.ilike(f"%{filtros['q']}%"))
    
    items = qs.order_by(Model.fecha.desc(), Model.id.desc()).all()
    total = float(sum(i.monto for i in items)) if items else 0.0

    # categorías para filtro
    rows = db.execute(
        select(Categoria.id, Categoria.nombre)
        .where(or_(Categoria.tipo == tipo, Categoria.tipo == "mixta"))
        .order_by(Categoria.nombre)
    ).all()
    categorias = [{"id": r.id, "nombre": r.nombre} for r in rows]

    return templates.TemplateResponse(
        "finanzas/listado.html",
        {
            "request": request,
            "scope": scope,
            "tipo": tipo,
            "items": items,
            "total": total,
            "categorias": categorias,
            "filtro": filtros,
        },
    )

@router.get("/banco/entradas")
def banco_entradas(request: Request, db: Session = Depends(get_db), desde: Optional[date] = None, hasta: Optional[date] = None, categoria_id: Optional[int] = None, metodo: Optional[str] = None, q: Optional[str] = None):
    return render_listado(request, "banco", "entrada", db, desde=desde, hasta=hasta, categoria_id=categoria_id, metodo=metodo, q=q)

@router.get("/banco/salidas")
def banco_salidas(request: Request, db: Session = Depends(get_db), desde: Optional[date] = None, hasta: Optional[date] = None, categoria_id: Optional[int] = None, metodo: Optional[str] = None, q: Optional[str] = None):
    return render_listado(request, "banco", "salida", db, desde=desde, hasta=hasta, categoria_id=categoria_id, metodo=metodo, q=q)

@router.get("/caja/entradas")
def caja_entradas(request: Request, db: Session = Depends(get_db), desde: Optional[date] = None, hasta: Optional[date] = None, categoria_id: Optional[int] = None, q: Optional[str] = None):
    return render_listado(request, "caja", "entrada", db, desde=desde, hasta=hasta, categoria_id=categoria_id, q=q)

@router.get("/caja/salidas")
def caja_salidas(request: Request, db: Session = Depends(get_db), desde: Optional[date] = None, hasta: Optional[date] = None, categoria_id: Optional[int] = None, q: Optional[str] = None):
    return render_listado(request, "caja", "salida", db, desde=desde, hasta=hasta, categoria_id=categoria_id, q=q)

# -------------------------- Crear / Editar --------------------------

@router.get("/{scope}/{tipo}/nuevo")
def nuevo_movimiento(request: Request, scope: Scope, tipo: Tipo, db: Session = Depends(get_db)):
    categorias = db.query(Categoria).filter(or_(Categoria.tipo == tipo, Categoria.tipo == "mixta")).order_by(Categoria.nombre).all()
    return templates.TemplateResponse("finanzas/form_movimiento.html", {
        "request": request, "scope": scope, "tipo": tipo, "categorias": categorias, "obj": None
    })

@router.get("/{scope}/{tipo}/{mid}/editar")
def editar_movimiento(request: Request, scope: Scope, tipo: Tipo, mid: int, db: Session = Depends(get_db)):
    Model = model_for(scope)
    obj = db.get(Model, mid)
    if not obj:
        return RedirectResponse(url=f"/finanzas/{scope}/movimientos", status_code=303)

    categorias = db.query(Categoria).filter(or_(Categoria.tipo == tipo, Categoria.tipo == "mixta")).order_by(Categoria.nombre).all()
    
    return templates.TemplateResponse("finanzas/form_movimiento.html", {
        "request": request, "scope": scope, "tipo": tipo, "categorias": categorias, "obj": obj
    })

@router.post("/{scope}/{tipo}/nuevo")
@router.post("/{scope}/{tipo}/{mid}/editar")
def guardar_movimiento(
    scope: Scope, tipo: Tipo, mid: Optional[int] = None,
    fecha: date = Form(...), monto: float = Form(...), concepto: str = Form(...),
    categoria_id: Optional[str] = Form(None), metodo_pago: Optional[str] = Form(None),
    numero_documento: Optional[str] = Form(None), descripcion: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    Model = model_for(scope)
    
    if mid: # EDITAR
        obj = db.get(Model, mid)
        if not obj: return RedirectResponse(url=f"/finanzas/{scope}/movimientos", status_code=303)
    else: # CREAR
        obj = Model()
        db.add(obj)

    obj.fecha = fecha
    obj.tipo = tipo
    obj.monto = monto
    obj.concepto = concepto
    obj.categoria_id = to_int_or_none(categoria_id)
    obj.numero_documento = numero_documento
    obj.descripcion = descripcion
    
    if scope == "banco":
        obj.metodo_pago = metodo_pago or "otro"

    db.commit()
    redirect_to = "entradas" if tipo == "entrada" else "salidas"
    return RedirectResponse(url=f"/finanzas/{scope}/{redirect_to}", status_code=303)

# -------------------------- Eliminar --------------------------

@router.post("/{scope}/{tipo}/{mid}/eliminar")
def eliminar_movimiento(scope: Scope, tipo: Tipo, mid: int, db: Session = Depends(get_db)):
    Model = model_for(scope)
    obj = db.get(Model, mid)
    if obj:
        db.delete(obj)
        db.commit()
    redirect_to = "entradas" if tipo == "entrada" else "salidas"
    return RedirectResponse(url=f"/finanzas/{scope}/{redirect_to}", status_code=303)

# -------------------------- Vista General Movimientos --------------------------

@router.get("/{scope}/movimientos")
def movimientos(
    request: Request,
    scope: Scope,
    db: Session = Depends(get_db),
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
    categoria_id: Optional[int] = None,
    metodo: Optional[str] = None,
    q: Optional[str] = None,
):
    Model = model_for(scope)
    base = db.query(Model, Categoria.nombre.label("categoria_nombre")).outerjoin(Categoria, Model.categoria_id == Categoria.id)

    if desde: base = base.filter(Model.fecha >= desde)
    if hasta: base = base.filter(Model.fecha <= hasta)
    if categoria_id: base = base.filter(Model.categoria_id == categoria_id)
    if scope == "banco" and metodo: base = base.filter(Model.metodo_pago == metodo)
    if q: base = base.filter(Model.concepto.ilike(f"%{q}%"))

    rows = base.order_by(Model.fecha.asc(), Model.id.asc()).all()
    items = []
    for obj, cat_nombre in rows:
        items.append({
            "id": obj.id,
            "fecha": obj.fecha,
            "tipo": obj.tipo,
            "monto": float(obj.monto),
            "concepto": obj.concepto,
            "numero_documento": obj.numero_documento,
            "metodo_pago": getattr(obj, "metodo_pago", None),
            "categoria_nombre": cat_nombre,
        })

    totales = {"entradas": sum(i['monto'] for i in items if i['tipo'] == 'entrada'), "salidas": sum(i['monto'] for i in items if i['tipo'] == 'salida')}
    
    # Saldo inicial
    saldo_inicial = 0.0
    if desde:
        prev = db.query(Model.tipo, Model.monto).filter(Model.fecha < desde).all()
        for t, m in prev:
            saldo_inicial += float(m) if t == "entrada" else -float(m)

    categorias = db.query(Categoria.id, Categoria.nombre).order_by(Categoria.nombre).all()

    return templates.TemplateResponse(
        "finanzas/movimientos.html",
        {
            "request": request,
            "scope": scope,
            "items": items,
            "totales": totales,
            "saldo_inicial": saldo_inicial,
            "categorias": categorias,
            "filtro": {"desde": desde, "hasta": hasta, "categoria_id": categoria_id, "metodo": metodo if scope == "banco" else None, "q": q},
        },
    )