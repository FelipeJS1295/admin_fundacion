from __future__ import annotations
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    String, Integer, Date, DateTime, ForeignKey, Numeric, Text, Boolean
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

# 👈 Usa SIEMPRE la Base única del proyecto
from app.models.base import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)  # puede ser email
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(10), default="User")  # "Admin" | "User"
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Categoria(Base):
    __tablename__ = "categorias"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    tipo: Mapped[str] = mapped_column(String(10))  # "entrada", "salida" o "mixta"
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    transacciones: Mapped[list["Transaccion"]] = relationship(back_populates="categoria")


class Transaccion(Base):
    __tablename__ = "transacciones"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    fecha: Mapped[datetime] = mapped_column(Date, nullable=False)       # si es solo fecha, Date está OK
    tipo: Mapped[str] = mapped_column(String(10))                       # "entrada" | "salida"
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    metodo_pago: Mapped[str] = mapped_column(String(30), default="efectivo")
    concepto: Mapped[str] = mapped_column(String(120), default="")
    numero_documento: Mapped[str] = mapped_column(String(50), default="")
    documento_path: Mapped[str] = mapped_column(String(255), default="")
    descripcion: Mapped[str] = mapped_column(Text, default="")
    categoria_id: Mapped[int | None] = mapped_column(ForeignKey("categorias.id"), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    categoria: Mapped["Categoria"] = relationship(back_populates="transacciones")