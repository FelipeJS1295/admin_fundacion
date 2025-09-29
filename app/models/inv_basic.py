from __future__ import annotations
from decimal import Decimal
from sqlalchemy import String, Integer, ForeignKey, DECIMAL, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Usa la Base de tu proyecto (ya existente)
from app.models import Base

class InvCategoria(Base):
    __tablename__ = "inv_categoria"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)

    items: Mapped[list["InventarioItem"]] = relationship(back_populates="categoria", cascade="all,delete")

class UnidadMedida(Base):
    __tablename__ = "inv_unidad_medida"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)

    items: Mapped[list["InventarioItem"]] = relationship(back_populates="unidad")

class InventarioItem(Base):
    __tablename__ = "inventario"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    categoria_id: Mapped[int] = mapped_column(ForeignKey("inv_categoria.id", ondelete="RESTRICT"))
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    unidad_id: Mapped[int] = mapped_column(ForeignKey("inv_unidad_medida.id", ondelete="RESTRICT"))
    stock_inicial: Mapped[Decimal] = mapped_column(DECIMAL(18, 3), default=0, nullable=False)
    created_at: Mapped[str] = mapped_column(DateTime, server_default=func.current_timestamp())

    categoria: Mapped["InvCategoria"] = relationship(back_populates="items")
    unidad: Mapped["UnidadMedida"] = relationship(back_populates="items")
