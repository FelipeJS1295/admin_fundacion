# models/pacientes.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Date, DateTime, ForeignKey, Text, Boolean, Enum
from datetime import datetime
from app.models.base import Base
import enum

class Base(DeclarativeBase):
    pass

class SexoEnum(str, enum.Enum):
    M = "M"
    F = "F"
    Otro = "Otro"

class MovilidadEnum(str, enum.Enum):
    Autonomo = "Autónomo"
    Asistido = "Asistido"
    Postrado = "Postrado"

class DependenciaEnum(str, enum.Enum):
    Leve = "Leve"
    Moderada = "Moderada"
    Severa = "Severa"

class PrevisionEnum(str, enum.Enum):
    Fonasa = "Fonasa"
    Isapre = "Isapre"
    Ninguna = "Ninguna"

class Comuna(Base):
    __tablename__ = "comunas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), unique=True, index=True)

class Enfermedad(Base):
    __tablename__ = "enfermedades"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), unique=True, index=True)

class Paciente(Base):
    __tablename__ = "pacientes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombres: Mapped[str] = mapped_column(String(120), index=True)
    apellidos: Mapped[str] = mapped_column(String(120), index=True)
    rut: Mapped[str] = mapped_column(String(12), unique=True, index=True)  # 12 por seguridad: 99.999.999-9
    sexo: Mapped[SexoEnum] = mapped_column(Enum(SexoEnum))
    fecha_nacimiento: Mapped[Date] = mapped_column(Date)

    direccion: Mapped[str] = mapped_column(String(255))
    comuna_id: Mapped[int] = mapped_column(ForeignKey("comunas.id"))
    comuna: Mapped["Comuna"] = relationship()

    telefono: Mapped[str | None] = mapped_column(String(20), default=None)
    email: Mapped[str | None] = mapped_column(String(120), default=None)

    prevision_salud: Mapped[PrevisionEnum | None] = mapped_column(Enum(PrevisionEnum), default=None)
    movilidad: Mapped[MovilidadEnum | None] = mapped_column(Enum(MovilidadEnum), default=None)
    dependencia: Mapped[DependenciaEnum | None] = mapped_column(Enum(DependenciaEnum), default=None)

    cuidador_principal: Mapped[str | None] = mapped_column(String(120), default=None)
    cuidador_parentesco: Mapped[str | None] = mapped_column(String(60), default=None)
    vive_solo: Mapped[bool] = mapped_column(Boolean, default=False)
    red_apoyo: Mapped[str | None] = mapped_column(Text, default=None)

    puntaje_vulnerabilidad: Mapped[int | None] = mapped_column(Integer, default=None)
    observaciones: Mapped[str | None] = mapped_column(Text, default=None)

    imagen_path: Mapped[str | None] = mapped_column(String(255), default=None)  # ruta en disco o URL
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class PacienteEnfermedad(Base):
    __tablename__ = "paciente_enfermedad"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    paciente_id: Mapped[int] = mapped_column(ForeignKey("pacientes.id", ondelete="CASCADE"))
    enfermedad_id: Mapped[int] = mapped_column(ForeignKey("enfermedades.id"))
