from datetime import date, datetime
from pathlib import Path
import secrets

from fastapi import APIRouter, Request, Depends, Form, UploadFile, File, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.db import get_db
from app.models import Transaccion, Categoria

router = APIRouter(tags=["salidas"])
from app.core.templates import templates

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
    # 👇 recibir como string para tolerar "" y convertir nosotros
    desde: str | None = Query(None),
    hasta: str | None = Query(None),
    categoria_id: str | None = Query(None),
    metodo_pago: str | None = Query(None),
    q: str | None = Query(None),
    limit: int = Query(200, ge=1, le=1000),
):
    # Parseos seguros
    def _parse_date(s: str | None):
        if not s: return None
        try:
            return datetime.fromisoformat(s).date()
        except Exception:
            return None

    def _parse_int(s: str | None):
        return int(s) if s and s.isdigit() else None

    d1 = _parse_date(desde)
    d2 = _parse_date(hasta)
    cat_id = _parse_int(categoria_id)

    # Filtros comunes
    filtros = [Transaccion.tipo == "salida"]
    if d1: filtros.append(Transaccion.fecha >= d1)
    if d2: filtros.append(Transaccion.fecha <= d2)
    if cat_id: filtros.append(Transaccion.categoria_id == cat_id)
    if metodo_pago: filtros.append(Transaccion.metodo_pago == metodo_pago)
    if q:
        like = f"%{q}%"
        filtros.append(
            or_(
                Transaccion.concepto.like(like),
                Transaccion.descripcion.like(like),
                Transaccion.numero_documento.like(like),
            )
        )

    base_q = db.query(Transaccion).filter(*filtros)

    # Total filtrado (sin limit/orden)
    total = base_q.with_entities(func.coalesce(func.sum(Transaccion.monto), 0)).scalar() or 0

    # Lista limitada
    salidas = (
        base_q.order_by(Transaccion.fecha.desc(), Transaccion.id.desc())
              .limit(limit).all()
    )

    cats = categorias_salida(db)

    return templates.TemplateResponse("salidas/list.html", {
        "request": request,
        "salidas": salidas,
        "categorias": cats,
        "total": total,
        "filtros": {
            "desde": d1.isoformat() if d1 else "",
            "hasta": d2.isoformat() if d2 else "",
            "categoria_id": cat_id,
            "metodo_pago": metodo_pago or "",
            "q": q or "",
            "limit": limit
        }
    })

# CREAR
@router.get("/salidas/nueva", response_class=HTMLResponse)
def nueva_salida_form(request: Request, db: Session = Depends(get_db)):
    cats = categorias_salida(db)
    return templates.TemplateResponse("salidas/form.html", {
        "request": request,
        "categorias": cats,
        "today": date.today().isoformat()
    })

@router.post("/salidas")
def crear_salida(
    request: Request,
    fecha: str = Form(...),
    monto: float = Form(...),
    categoria_id: str | None = Form(None),   # 👈 string
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

    cat_id = int(categoria_id) if categoria_id and categoria_id.isdigit() else None
    cat = db.get(Categoria, cat_id) if cat_id else None

    doc_path = guardar_archivo(documento)
    tx = Transaccion(
        fecha=f, tipo="salida", monto=monto, metodo_pago=metodo_pago,
        concepto=concepto.strip(), numero_documento=numero_documento.strip(),
        documento_path=doc_path, descripcion=descripcion.strip(), categoria=cat
    )
    db.add(tx); db.commit()
    return RedirectResponse(url="/salidas?ok=1", status_code=303)

# VER
@router.get("/salidas/{tx_id}", response_class=HTMLResponse)
def ver_salida(tx_id: int, request: Request, db: Session = Depends(get_db)):
    tx = db.get(Transaccion, tx_id)
    if not tx or tx.tipo != "salida":
        return RedirectResponse(url="/salidas?error=Salida%20no%20encontrada", status_code=303)
    return templates.TemplateResponse("salidas/show.html", {"request": request, "t": tx})

# EDITAR
@router.get("/salidas/{tx_id}/editar", response_class=HTMLResponse)
def editar_salida_form(tx_id: int, request: Request, db: Session = Depends(get_db)):
    tx = db.get(Transaccion, tx_id)
    if not tx or tx.tipo != "salida":
        return RedirectResponse(url="/salidas?error=Salida%20no%20encontrada", status_code=303)
    cats = categorias_salida(db)
    return templates.TemplateResponse("salidas/edit.html", {
        "request": request, "t": tx, "categorias": cats
    })

@router.post("/salidas/{tx_id}")
def actualizar_salida(
    tx_id: int,
    request: Request,
    fecha: str = Form(...),
    monto: float = Form(...),
    categoria_id: str | None = Form(None),   # 👈 string
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

    cat_id = int(categoria_id) if categoria_id and categoria_id.isdigit() else None
    tx.categoria = db.get(Categoria, cat_id) if cat_id else None

    if eliminar_documento == "1" and tx.documento_path:
        eliminar_archivo(tx.documento_path)
        tx.documento_path = ""

    if documento and documento.filename:
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
