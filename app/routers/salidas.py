from datetime import date, datetime
from pathlib import Path
import secrets

from fastapi import APIRouter, Request, Depends, Form, UploadFile, File, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db import get_db
from app.models import Transaccion, Categoria

router = APIRouter(tags=["salidas"])
templates = Jinja2Templates(directory="templates")

DOCS_DIR = Path("static") / "docs_salidas"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

def categorias_salida(db: Session):
    return db.query(Categoria)\
             .filter(or_(Categoria.tipo == "salida", Categoria.tipo == "mixta"))\
             .order_by(Categoria.nombre)\
             .all()

def guardar_archivo(upload: UploadFile | None) -> str:
    if not upload or not upload.filename:
        return ""
    allowed = {"image/jpeg", "image/png", "application/pdf"}
    if upload.content_type not in allowed:
        return ""
    ext = Path(upload.filename).suffix.lower()
    nombre = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}{ext}"
    destino = DOCS_DIR / nombre
    with destino.open("wb") as f:
        f.write(upload.file.read())
    return f"/static/docs_salidas/{nombre}"

def eliminar_archivo(path_url: str):
    try:
        if path_url and path_url.startswith("/static/docs_salidas/"):
            p = Path(path_url.lstrip("/"))
            if p.exists():
                p.unlink()
    except Exception:
        pass

# LISTADO
@router.get("/salidas", response_class=HTMLResponse)
def listar_salidas(
    request: Request,
    db: Session = Depends(get_db),
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    categoria_id: int | None = Query(None),
    metodo_pago: str | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
):
    query = db.query(Transaccion).filter(Transaccion.tipo == "salida")
    if desde:
        query = query.filter(Transaccion.fecha >= desde)
    if hasta:
        query = query.filter(Transaccion.fecha <= hasta)
    if categoria_id:
        query = query.filter(Transaccion.categoria_id == categoria_id)
    if metodo_pago:
        query = query.filter(Transaccion.metodo_pago == metodo_pago)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Transaccion.concepto.like(like)) |
            (Transaccion.descripcion.like(like)) |
            (Transaccion.numero_documento.like(like))
        )
    salidas = query.order_by(Transaccion.fecha.desc(), Transaccion.id.desc()).limit(limit).all()
    cats = categorias_salida(db)

    return templates.TemplateResponse("salidas_list.html", {
        "request": request,
        "salidas": salidas,
        "categorias": cats,
        "filtros": {"desde": desde, "hasta": hasta, "categoria_id": categoria_id,
                    "metodo_pago": metodo_pago, "q": q, "limit": limit}
    })

# CREAR
@router.get("/salidas/nueva", response_class=HTMLResponse)
def nueva_salida_form(request: Request, db: Session = Depends(get_db)):
    cats = categorias_salida(db)
    return templates.TemplateResponse("salidas_form.html", {
        "request": request,
        "categorias": cats,
        "today": date.today().isoformat()
    })

@router.post("/salidas")
def crear_salida(
    request: Request,
    fecha: str = Form(...),
    monto: float = Form(...),
    categoria_id: int | None = Form(None),
    metodo_pago: str = Form("efectivo"),
    concepto: str = Form(""),
    numero_documento: str = Form(""),
    descripcion: str = Form(""),
    documento: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    try:
        f = datetime.fromisoformat(fecha).date()
    except Exception:
        f = date.today()
    if monto <= 0:
        return RedirectResponse(url="/salidas/nueva?error=Monto%20inv%C3%A1lido", status_code=303)

    doc_path = guardar_archivo(documento)
    cat = db.get(Categoria, categoria_id) if categoria_id else None
    tx = Transaccion(
        fecha=f, tipo="salida", monto=monto, metodo_pago=metodo_pago,
        concepto=concepto.strip(), numero_documento=numero_documento.strip(),
        documento_path=doc_path, descripcion=descripcion.strip(), categoria=cat
    )
    db.add(tx)
    db.commit()
    return RedirectResponse(url="/salidas?ok=1", status_code=303)

# VER
@router.get("/salidas/{tx_id}", response_class=HTMLResponse)
def ver_salida(tx_id: int, request: Request, db: Session = Depends(get_db)):
    tx = db.get(Transaccion, tx_id)
    if not tx or tx.tipo != "salida":
        return RedirectResponse(url="/salidas?error=Salida%20no%20encontrada", status_code=303)
    return templates.TemplateResponse("salidas_show.html", {"request": request, "t": tx})

# EDITAR
@router.get("/salidas/{tx_id}/editar", response_class=HTMLResponse)
def editar_salida_form(tx_id: int, request: Request, db: Session = Depends(get_db)):
    tx = db.get(Transaccion, tx_id)
    if not tx or tx.tipo != "salida":
        return RedirectResponse(url="/salidas?error=Salida%20no%20encontrada", status_code=303)
    cats = categorias_salida(db)
    return templates.TemplateResponse("salidas_edit.html", {
        "request": request, "t": tx, "categorias": cats
    })

@router.post("/salidas/{tx_id}")
def actualizar_salida(
    tx_id: int,
    request: Request,
    fecha: str = Form(...),
    monto: float = Form(...),
    categoria_id: int | None = Form(None),
    metodo_pago: str = Form("efectivo"),
    concepto: str = Form(""),
    numero_documento: str = Form(""),
    descripcion: str = Form(""),
    eliminar_documento: str | None = Form(None),
    documento: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    tx = db.get(Transaccion, tx_id)
    if not tx or tx.tipo != "salida":
        return RedirectResponse(url="/salidas?error=Salida%20no%20encontrada", status_code=303)

    try:
        tx.fecha = datetime.fromisoformat(fecha).date()
    except Exception:
        tx.fecha = date.today()

    tx.monto = monto
    tx.metodo_pago = metodo_pago
    tx.concepto = concepto.strip()
    tx.numero_documento = numero_documento.strip()
    tx.descripcion = descripcion.strip()
    tx.categoria = db.get(Categoria, categoria_id) if categoria_id else None

    # Manejo de archivo
    if eliminar_documento == "1" and tx.documento_path:
        eliminar_archivo(tx.documento_path)
        tx.documento_path = ""

    if documento and documento.filename:
        # si ya tenía uno, bórralo
        if tx.documento_path:
            eliminar_archivo(tx.documento_path)
        tx.documento_path = guardar_archivo(documento)

    db.commit()
    return RedirectResponse(url=f"/salidas/{tx_id}?ok=1", status_code=303)

# ELIMINAR
@router.post("/salidas/{tx_id}/eliminar")
def eliminar_salida(tx_id: int, db: Session = Depends(get_db)):
    tx = db.get(Transaccion, tx_id)
    if tx and tx.tipo == "salida":
        if tx.documento_path:
            eliminar_archivo(tx.documento_path)
        db.delete(tx)
        db.commit()
    return RedirectResponse(url="/salidas?ok=1", status_code=303)
