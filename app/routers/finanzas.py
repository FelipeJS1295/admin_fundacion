from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import date
from typing import Optional, Literal
from app.db import SessionLocal
from starlette.templating import Jinja2Templates
from app.models_finanzas import BancoMovimiento, CajaMovimiento

router = APIRouter(prefix="/finanzas", tags=["Finanzas"])
templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

Tipo = Literal["entrada","salida"]

# ---------- LISTADOS CON TOTALES ----------
@router.get("/banco/entradas", response_class=HTMLResponse)
def banco_entradas(request: Request, db: Session = Depends(get_db),
                   desde: Optional[date] = None, hasta: Optional[date] = None, categoria_id: Optional[int] = None):
    q = db.query(BancoMovimiento).filter(BancoMovimiento.tipo=="entrada")
    if desde: q = q.filter(BancoMovimiento.fecha >= desde)
    if hasta: q = q.filter(BancoMovimiento.fecha <= hasta)
    if categoria_id: q = q.filter(BancoMovimiento.categoria_id == categoria_id)
    items = q.order_by(BancoMovimiento.fecha.desc(), BancoMovimiento.id.desc()).all()
    total = sum([float(i.monto) for i in items]) if items else 0.0
    return templates.TemplateResponse("finanzas/listado.html", {"request":request, "scope":"banco", "tipo":"entrada", "items":items, "total":total})

@router.get("/banco/salidas", response_class=HTMLResponse)
def banco_salidas(request: Request, db: Session = Depends(get_db),
                  desde: Optional[date] = None, hasta: Optional[date] = None, categoria_id: Optional[int] = None):
    q = db.query(BancoMovimiento).filter(BancoMovimiento.tipo=="salida")
    if desde: q = q.filter(BancoMovimiento.fecha >= desde)
    if hasta: q = q.filter(BancoMovimiento.fecha <= hasta)
    if categoria_id: q = q.filter(BancoMovimiento.categoria_id == categoria_id)
    items = q.order_by(BancoMovimiento.fecha.desc(), BancoMovimiento.id.desc()).all()
    total = sum([float(i.monto) for i in items]) if items else 0.0
    return templates.TemplateResponse("finanzas/listado.html", {"request":request, "scope":"banco", "tipo":"salida", "items":items, "total":total})

@router.get("/caja/entradas", response_class=HTMLResponse)
def caja_entradas(request: Request, db: Session = Depends(get_db),
                  desde: Optional[date] = None, hasta: Optional[date] = None, categoria_id: Optional[int] = None):
    q = db.query(CajaMovimiento).filter(CajaMovimiento.tipo=="entrada")
    if desde: q = q.filter(CajaMovimiento.fecha >= desde)
    if hasta: q = q.filter(CajaMovimiento.fecha <= hasta)
    if categoria_id: q = q.filter(CajaMovimiento.categoria_id == categoria_id)
    items = q.order_by(CajaMovimiento.fecha.desc(), CajaMovimiento.id.desc()).all()
    total = sum([float(i.monto) for i in items]) if items else 0.0
    return templates.TemplateResponse("finanzas/listado.html", {"request":request, "scope":"caja", "tipo":"entrada", "items":items, "total":total})

@router.get("/caja/salidas", response_class=HTMLResponse)
def caja_salidas(request: Request, db: Session = Depends(get_db),
                 desde: Optional[date] = None, hasta: Optional[date] = None, categoria_id: Optional[int] = None):
    q = db.query(CajaMovimiento).filter(CajaMovimiento.tipo=="salida")
    if desde: q = q.filter(CajaMovimiento.fecha >= desde)
    if hasta: q = q.filter(CajaMovimiento.fecha <= hasta)
    if categoria_id: q = q.filter(CajaMovimiento.categoria_id == categoria_id)
    items = q.order_by(CajaMovimiento.fecha.desc(), CajaMovimiento.id.desc()).all()
    total = sum([float(i.monto) for i in items]) if items else 0.0
    return templates.TemplateResponse("finanzas/listado.html", {"request":request, "scope":"caja", "tipo":"salida", "items":items, "total":total})

# ---------- FORM NUEVO ----------
@router.get("/{scope}/{tipo}/nuevo", response_class=HTMLResponse)
def nuevo_movimiento(request: Request, scope: Literal["banco","caja"], tipo: Tipo):
    return templates.TemplateResponse("finanzas/form_movimiento.html", {"request": request, "scope": scope, "tipo": tipo})

@router.post("/{scope}/{tipo}/nuevo")
def crear_movimiento(scope: Literal["banco","caja"], tipo: Tipo,
                     fecha: str = Form(...),
                     monto: float = Form(...),
                     concepto: str = Form(...),
                     categoria_id: Optional[int] = Form(None),
                     metodo_pago: Optional[str] = Form(None),
                     numero_documento: Optional[str] = Form(None),
                     descripcion: Optional[str] = Form(None),
                     db: Session = Depends(get_db)):
    if scope == "banco":
        obj = BancoMovimiento(fecha=fecha, tipo=tipo, monto=monto, concepto=concepto,
                              categoria_id=categoria_id, metodo_pago=metodo_pago or "otro",
                              numero_documento=numero_documento, descripcion=descripcion)
        db.add(obj)
        db.commit()
        return RedirectResponse(url=f"/finanzas/banco/{'entradas' if tipo=='entrada' else 'salidas'}", status_code=303)
    else:
        obj = CajaMovimiento(fecha=fecha, tipo=tipo, monto=monto, concepto=concepto,
                             categoria_id=categoria_id, numero_documento=numero_documento, descripcion=descripcion)
        db.add(obj)
        db.commit()
        return RedirectResponse(url=f"/finanzas/caja/{'entradas' if tipo=='entrada' else 'salidas'}", status_code=303)
