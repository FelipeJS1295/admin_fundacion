# routers/pacientes.py
from fastapi import APIRouter, Request, Depends, Form, UploadFile, File, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime
import os, shutil
from pathlib import Path

from app.db import get_db
from app.models.pacientes import Paciente, Enfermedad, PacienteEnfermedad, Comuna, SexoEnum, PrevisionEnum, MovilidadEnum, DependenciaEnum

router = APIRouter(prefix="/pacientes", tags=["Pacientes"])
templates = Jinja2Templates(directory="templates")  # asegúrate de apuntar a tu carpeta templates

BASE_DIR = Path(__file__).resolve().parents[2]
IMAGES_DIR = BASE_DIR / "static" / "pacientes"
IMAGES_DIR.mkdir(parents=True, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

# --- util RUT ---
def validar_rut_chileno(rut: str) -> bool:
    rut = rut.replace(".", "").replace(" ", "").upper()
    if "-" not in rut:
        return False
    cuerpo, dv = rut.split("-")
    if not cuerpo.isdigit():
        return False
    factores = [2,3,4,5,6,7]
    suma, f_i = 0, 0
    for n in map(int, reversed(cuerpo)):
        suma += n * factores[f_i]
        f_i = (f_i + 1) % len(factores)
    resto = 11 - (suma % 11)
    dv_calc = "0" if resto == 11 else "K" if resto == 10 else str(resto)
    return dv_calc == dv

# --- listado ---
@router.get("/")
def pacientes_index(request: Request, db: Session = Depends(get_db), q: str | None = None, activo: str | None = None):
    query = db.query(Paciente).join(Comuna)
    if q:
        like = f"%{q}%"
        query = query.filter(
            (Paciente.nombres.ilike(like)) |
            (Paciente.apellidos.ilike(like)) |
            (Paciente.rut.ilike(like))
        )
    if activo in ("1","0"):
        query = query.filter(Paciente.activo == (activo == "1"))
    pacientes = query.order_by(Paciente.creado_en.desc()).all()
    return templates.TemplateResponse("pacientes/index.html", {
        "request": request,
        "pacientes": pacientes
    })

# --- formulario crear ---
@router.get("/crear")
def pacientes_crear(request: Request, db: Session = Depends(get_db)):
    comunas = db.query(Comuna).order_by(Comuna.nombre).all()
    enfermedades = db.query(Enfermedad).order_by(Enfermedad.nombre).all()
    return templates.TemplateResponse("pacientes/create.html", {
        "request": request,
        "comunas": comunas,
        "enfermedades": enfermedades,
        "sexo_opts": [e.value for e in SexoEnum],
        "prevision_opts": [e.value for e in PrevisionEnum],
        "movilidad_opts": [e.value for e in MovilidadEnum],
        "dependencia_opts": [e.value for e in DependenciaEnum],
    })

# --- guardar ---
@router.post("/crear")
async def pacientes_store(
    request: Request,
    db: Session = Depends(get_db),
    # datos básicos
    nombres: str = Form(...),
    apellidos: str = Form(...),
    rut: str = Form(...),
    sexo: str = Form(...),
    fecha_nacimiento: str = Form(...),  # "YYYY-MM-DD"
    direccion: str = Form(...),
    comuna_id: int = Form(...),
    telefono: str | None = Form(None),
    email: str | None = Form(None),
    prevision_salud: str | None = Form(None),
    movilidad: str | None = Form(None),
    dependencia: str | None = Form(None),
    cuidador_principal: str | None = Form(None),
    cuidador_parentesco: str | None = Form(None),
    vive_solo: str | None = Form(None),  # "on" si marcado
    red_apoyo: str | None = Form(None),
    puntaje_vulnerabilidad: int | None = Form(None),
    observaciones: str | None = Form(None),
    activo: str | None = Form("on"),
    # enfermedades múltiples
    enfermedades_ids: list[int] = Form([]),
    enfermedades_otras: list[str] = Form([]),
    # imagen
    imagen: UploadFile | None = File(None),
):
    # validar RUT
    if not validar_rut_chileno(rut):
        raise HTTPException(400, detail="RUT inválido")

    p = Paciente(
        nombres=nombres.strip(),
        apellidos=apellidos.strip(),
        rut=rut.strip().upper(),
        sexo=SexoEnum(sexo),
        fecha_nacimiento=datetime.strptime(fecha_nacimiento, "%Y-%m-%d").date(),
        direccion=direccion.strip(),
        comuna_id=int(comuna_id),
        telefono=telefono or None,
        email=email or None,
        prevision_salud=PrevisionEnum(prevision_salud) if prevision_salud else None,
        movilidad=MovilidadEnum(movilidad) if movilidad else None,
        dependencia=DependenciaEnum(dependencia) if dependencia else None,
        cuidador_principal=cuidador_principal or None,
        cuidador_parentesco=cuidador_parentesco or None,
        vive_solo=(vive_solo == "on"),
        red_apoyo=red_apoyo or None,
        puntaje_vulnerabilidad=puntaje_vulnerabilidad,
        observaciones=observaciones or None,
        activo=(activo == "on"),
    )
    db.add(p); db.flush()

    # Enfermedades de catálogo
    if enfermedades_ids:
        for enf_id in enfermedades_ids:
            db.add(PacienteEnfermedad(paciente_id=p.id, enfermedad_id=int(enf_id)))

    # Otras enfermedades: crear si no existen (case-insensitive)
    for nombre in (enfermedades_otras or []):
        nombre = (nombre or "").strip()
        if not nombre:
            continue
        existente = db.query(Enfermedad).filter(Enfermedad.nombre.ilike(nombre)).first()
        enf = existente or Enfermedad(nombre=nombre)
        if not existente:
            db.add(enf); db.flush()
        db.add(PacienteEnfermedad(paciente_id=p.id, enfermedad_id=enf.id))

    # Imagen
    if imagen and imagen.filename:
        ext = os.path.splitext(imagen.filename)[1].lower()
        if ext not in [".jpg", ".jpeg", ".png", ".webp"]:
            raise HTTPException(400, detail="Formato de imagen no soportado")
        filename = f"pac_{p.id}{ext}"
        dest = IMAGES_DIR / filename
        with open(dest, "wb") as f:
            shutil.copyfileobj(imagen.file, f)
        p.imagen_path = f"static/pacientes/{filename}"

    db.commit()
    return RedirectResponse(url=f"/pacientes/{p.id}", status_code=303)

# --- detalle ---
@router.get("/{paciente_id}")
def pacientes_show(paciente_id: int, request: Request, db: Session = Depends(get_db)):
    p = db.get(Paciente, paciente_id)
    if not p:
        raise HTTPException(404, "Paciente no encontrado")
    rels = db.query(PacienteEnfermedad).filter_by(paciente_id=p.id).all()
    enf = []
    for r in rels:
        e = db.get(Enfermedad, r.enfermedad_id)
        if e: enf.append(e.nombre)
    return templates.TemplateResponse("pacientes/show.html", {
        "request": request,
        "p": p,
        "enfermedades": enf
    })
