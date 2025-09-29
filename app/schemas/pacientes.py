# schemas/pacientes.py
from pydantic import BaseModel, EmailStr, field_validator
from datetime import date
from typing import List, Optional, Literal

Sexo = Literal["M", "F", "Otro"]
Movilidad = Literal["Autónomo", "Asistido", "Postrado"]
Dependencia = Literal["Leve", "Moderada", "Severa"]
Prevision = Literal["Fonasa", "Isapre", "Ninguna"]

def validar_rut_chileno(rut: str) -> bool:
    # Normaliza
    rut = rut.replace(".", "").replace(" ", "").upper()
    if "-" not in rut: 
        return False
    cuerpo, dv = rut.split("-")
    if not cuerpo.isdigit(): 
        return False
    # Cálculo DV
    reverso = map(int, reversed(cuerpo))
    factores = [2,3,4,5,6,7]
    suma, f_i = 0, 0
    for n in reverso:
        suma += n * factores[f_i]
        f_i = (f_i + 1) % len(factores)
    resto = 11 - (suma % 11)
    dv_calc = "0" if resto == 11 else "K" if resto == 10 else str(resto)
    return dv_calc == dv

class PacienteBase(BaseModel):
    nombres: str
    apellidos: str
    rut: str
    sexo: Sexo
    fecha_nacimiento: date
    direccion: str
    comuna_id: int

    telefono: Optional[str] = None
    email: Optional[EmailStr] = None

    prevision_salud: Optional[Prevision] = None
    movilidad: Optional[Movilidad] = None
    dependencia: Optional[Dependencia] = None

    cuidador_principal: Optional[str] = None
    cuidador_parentesco: Optional[str] = None
    vive_solo: bool = False
    red_apoyo: Optional[str] = None

    puntaje_vulnerabilidad: Optional[int] = None
    observaciones: Optional[str] = None

    enfermedades_ids: List[int] = []   # seleccionadas del catálogo
    enfermedades_otras: List[str] = [] # escritas manualmente
    activo: bool = True

    @field_validator("rut")
    @classmethod
    def check_rut(cls, v):
        if not validar_rut_chileno(v):
            raise ValueError("RUT inválido")
        return v

class PacienteCreate(PacienteBase):
    pass

class PacienteUpdate(PacienteBase):
    pass

class PacienteOut(BaseModel):
    id: int
    nombres: str
    apellidos: str
    rut: str
    sexo: Sexo
    fecha_nacimiento: date
    direccion: str
    comuna: str
    telefono: Optional[str]
    email: Optional[EmailStr]
    prevision_salud: Optional[Prevision]
    movilidad: Optional[Movilidad]
    dependencia: Optional[Dependencia]
    cuidador_principal: Optional[str]
    cuidador_parentesco: Optional[str]
    vive_solo: bool
    red_apoyo: Optional[str]
    puntaje_vulnerabilidad: Optional[int]
    observaciones: Optional[str]
    enfermedades: List[str]
    imagen_url: Optional[str]
    activo: bool
