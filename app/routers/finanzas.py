from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional, Literal
from starlette.templating import Jinja2Templates
from sqlalchemy import select, or_

from app.db import SessionLocal
from app.models_finanzas import BancoMovimiento, CajaMovimiento
from app.models import Categoria  # exportado en app/models/__init__.py

router = APIRouter(prefix="/finanzas", tags=["Finanzas"])
templates = Jinja2Templates(directory="templates")

Tipo = Literal["entrada", "salida"]

# -------------------------- utils --------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def to_int_or_none(v: str | None):
    if not v:
        return None
    v = v.strip()
    if v == "" or v.lower() == "null":
        return None
    try:
        return int(v)
    except ValueError:
        return None

def model_for(scope: Literal["banco","caja"]):
    return BancoMovimiento if scope == "banco" else CajaMovimiento

def render_listado(request: Request, scope: Literal["banco","caja"], tipo: Tipo,
                   db: Session,
                   desde: Optional[date], hasta: Optional[date],
                   categoria_id: Optional[int], metodo: Optional[str], q: Optional[str]):
    Model = model_for(scope)
    qs = db.query(Model).filter(Model.tipo == tipo)
    if desde: qs = qs.filter(Model.fecha >= desde)
    if hasta: qs = qs.filter(Model.fecha <= hasta)
    if categoria_id: qs = qs.filter(Model.categoria_id == categoria_id)
    if scope == "banco" and metodo: qs = qs.filter(Model.metodo_pago == metodo)
    if q: qs = qs.filter(Model.concepto.ilike(f"%{q}%"))
    items = qs.order_by(Model.fecha.desc(), Model.id.desc()).all()
    total = float(sum(i.monto for i in items)) if items else 0.0

    # categorías para filtro (tipo del movimiento + mixta)
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
            "filtro": {
                "desde": desde,
                "hasta": hasta,
                "categoria_id": categoria_id,
                "metodo": metodo,
                "q": q,
            },
        },
    )

# -------------------------- listados (con filtros) --------------------------
@router.get("/banco/entradas", response_class=HTMLResponse)
def banco_entradas(request: Request, db: Session = Depends(get_db),
                   desde: Optional[date] = None, hasta: Optional[date] = None,
                   categoria_id: Optional[int] = None, metodo: Optional[str] = None, q: Optional[str] = None):
    return render_listado(request, "banco", "entrada", db, desde, hasta, categoria_id, metodo, q)

@router.get("/banco/salidas", response_class=HTMLResponse)
def banco_salidas(request: Request, db: Session = Depends(get_db),
                  desde: Optional[date] = None, hasta: Optional[date] = None,
                  categoria_id: Optional[int] = None, metodo: Optional[str] = None, q: Optional[str] = None):
    return render_listado(request, "banco", "salida", db, desde, hasta, categoria_id, metodo, q)

@router.get("/caja/entradas", response_class=HTMLResponse)
def caja_entradas(request: Request, db: Session = Depends(get_db),
                  desde: Optional[date] = None, hasta: Optional[date] = None,
                  categoria_id: Optional[int] = None, q: Optional[str] = None):
    return render_listado(request, "caja", "entrada", db, desde, hasta, categoria_id, None, q)

@router.get("/caja/salidas", response_class=HTMLResponse)
def caja_salidas(request: Request, db: Session = Depends(get_db),
                 desde: Optional[date] = None, hasta: Optional[date] = None,
                 categoria_id: Optional[int] = None, q: Optional[str] = None):
    return render_listado(request, "caja", "salida", db, desde, hasta, categoria_id, None, q)

# -------------------------- form: nuevo --------------------------
@router.get("/{scope}/{tipo}/nuevo", response_class=HTMLResponse)
def nuevo_movimiento(request: Request, scope: Literal["banco","caja"], tipo: Tipo, db: Session = Depends(get_db)):
    rows = db.execute(
        select(Categoria.id, Categoria.nombre)
        .where(or_(Categoria.tipo == tipo, Categoria.tipo == "mixta"))
        .order_by(Categoria.nombre)
    ).all()
    categorias = [{"id": r.id, "nombre": r.nombre} for r in rows]
    return templates.TemplateResponse(
        "finanzas/form_movimiento.html",
        {"request": request, "scope": scope, "tipo": tipo, "categorias": categorias},
    )

@router.post("/{scope}/{tipo}/nuevo")
def crear_movimiento(scope: Literal["banco","caja"], tipo: Tipo,
                     fecha: str = Form(...),
                     monto: float = Form(...),
                     concepto: str = Form(...),
                     categoria_id: str | None = Form(None),
                     metodo_pago: str | None = Form(None),
                     numero_documento: str | None = Form(None),
                     descripcion: str | None = Form(None),
                     db: Session = Depends(get_db)):
    Model = model_for(scope)
    obj = Model(
        fecha=fecha,
        tipo=tipo,
        monto=monto,
        concepto=concepto,
        categoria_id=to_int_or_none(categoria_id),
        numero_documento=numero_documento,
        descripcion=descripcion,
    )
    if scope == "banco":
        obj.metodo_pago = (metodo_pago or "otro")
    db.add(obj); db.commit()
    return RedirectResponse(
        url=f"/finanzas/{scope}/{'entradas' if tipo=='entrada' else 'salidas'}",
        status_code=303,
    )

# -------------------------- form: editar --------------------------
@router.get("/{scope}/{tipo}/{mid}/editar", response_class=HTMLResponse)
def editar_movimiento(request: Request, scope: Literal["banco","caja"], tipo: Tipo, mid: int, db: Session = Depends(get_db)):
    Model = model_for(scope)
    obj = db.get(Model, mid)
    if not obj:
        return RedirectResponse(url=f"/finanzas/{scope}/{'entradas' if tipo=='entrada' else 'salidas'}", status_code=303)

    rows = db.execute(
        select(Categoria.id, Categoria.nombre)
        .where(or_(Categoria.tipo == tipo, Categoria.tipo == "mixta"))
        .order_by(Categoria.nombre)
    ).all()
    categorias = [{"id": r.id, "nombre": r.nombre} for r in rows]

    return templates.TemplateResponse(
        "finanzas/form_movimiento.html",
        {"request": request, "scope": scope, "tipo": tipo, "categorias": categorias, "obj": obj},
    )

@router.post("/{scope}/{tipo}/{mid}/editar")
def actualizar_movimiento(scope: Literal["banco","caja"], tipo: Tipo, mid: int,
                          fecha: str = Form(...),
                          monto: float = Form(...),
                          concepto: str = Form(...),
                          categoria_id: str | None = Form(None),
                          metodo_pago: str | None = Form(None),
                          numero_documento: str | None = Form(None),
                          descripcion: str | None = Form(None),
                          db: Session = Depends(get_db)):
    Model = model_for(scope)
    obj = db.get(Model, mid)
    if not obj:
        return RedirectResponse(url=f"/finanzas/{scope}/{'entradas' if tipo=='entrada' else 'salidas'}", status_code=303)

    obj.fecha = fecha
    obj.monto = monto
    obj.concepto = concepto
    obj.categoria_id = to_int_or_none(categoria_id)
    obj.numero_documento = numero_documento
    obj.descripcion = descripcion
    if scope == "banco":
        obj.metodo_pago = (metodo_pago or obj.metodo_pago)

    db.commit()
    return RedirectResponse(url=f"/finanzas/{scope}/{'entradas' if tipo=='entrada' else 'salidas'}", status_code=303)

# -------------------------- eliminar --------------------------
@router.post("/{scope}/{tipo}/{mid}/eliminar")
def eliminar_movimiento(scope: Literal["banco","caja"], tipo: Tipo, mid: int, db: Session = Depends(get_db)):
    Model = model_for(scope)
    obj = db.get(Model, mid)
    if obj:
        db.delete(obj)
        db.commit()
    return RedirectResponse(url=f"/finanzas/{scope}/{'entradas' if tipo=='entrada' else 'salidas'}", status_code=303)

