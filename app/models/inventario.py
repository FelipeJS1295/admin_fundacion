from __future__ import annotations
import enum
from typing import List, Optional

from sqlalchemy import (
    String, Text, Integer, BigInteger, Enum, DateTime, Date, DECIMAL,
    ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

# 👇 toma Base del paquete actual (app.models)
from . import Base


# ---------- Tablas maestras ----------
class Unidad(Base):
    __tablename__ = "inv_unidad"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(50), nullable=False)
    activo: Mapped[int] = mapped_column(Integer, default=1)


class CategoriaInv(Base):
    __tablename__ = "inv_categoria"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("inv_categoria.id"))
    activo: Mapped[int] = mapped_column(Integer, default=1)

    parent = relationship("CategoriaInv", remote_side=[id], backref="children")


class Bodega(Base):
    __tablename__ = "inv_bodega"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    codigo: Mapped[Optional[str]] = mapped_column(String(30), unique=True)
    ubicacion: Mapped[Optional[str]] = mapped_column(String(150))
    activa: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[Optional[DateTime]] = mapped_column(DateTime)


class Producto(Base):
    __tablename__ = "inv_producto"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sku: Mapped[Optional[str]] = mapped_column(String(64), unique=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)

    categoria_id: Mapped[Optional[int]] = mapped_column(ForeignKey("inv_categoria.id"))
    unidad_id: Mapped[Optional[int]] = mapped_column(ForeignKey("inv_unidad.id"))

    activo: Mapped[int] = mapped_column(Integer, default=1)
    track_lote: Mapped[int] = mapped_column(Integer, default=0)
    track_serie: Mapped[int] = mapped_column(Integer, default=0)
    stock_minimo: Mapped[float] = mapped_column(DECIMAL(18, 3), default=0)
    stock_maximo: Mapped[Optional[float]] = mapped_column(DECIMAL(18, 3))
    costo_promedio: Mapped[float] = mapped_column(DECIMAL(18, 4), default=0)

    categoria = relationship("CategoriaInv")
    unidad = relationship("Unidad")


class Lote(Base):
    __tablename__ = "inv_lote"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    producto_id: Mapped[int] = mapped_column(ForeignKey("inv_producto.id"), nullable=False)
    codigo: Mapped[Optional[str]] = mapped_column(String(80))
    fecha_venc: Mapped[Optional[Date]] = mapped_column(Date)

    producto = relationship("Producto")
    __table_args__ = (UniqueConstraint("producto_id", "codigo", name="uq_lote_prod_codigo"),)


# ---------- Movimientos ----------
class TipoMov(str, enum.Enum):
    IN = "IN"
    OUT = "OUT"
    AJUSTE_IN = "AJUSTE_IN"
    AJUSTE_OUT = "AJUSTE_OUT"
    TRANSFER = "TRANSFER"


class DocTipo(str, enum.Enum):
    NINGUNO = "NINGUNO"
    BOLETA = "BOLETA"
    FACTURA = "FACTURA"
    GUIA = "GUIA"
    DONACION = "DONACION"
    OTRO = "OTRO"


class Movimiento(Base):
    __tablename__ = "inv_movimiento"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tipo: Mapped[TipoMov] = mapped_column(Enum(TipoMov), nullable=False)
    fecha: Mapped[DateTime] = mapped_column(DateTime)
    bodega_origen_id: Mapped[Optional[int]] = mapped_column(ForeignKey("inv_bodega.id"))
    bodega_destino_id: Mapped[Optional[int]] = mapped_column(ForeignKey("inv_bodega.id"))

    referencia: Mapped[Optional[str]] = mapped_column(String(120))
    doc_tipo: Mapped[DocTipo] = mapped_column(Enum(DocTipo), default=DocTipo.NINGUNO)
    doc_numero: Mapped[Optional[str]] = mapped_column(String(60))
    observacion: Mapped[Optional[str]] = mapped_column(Text)
    total_items: Mapped[int] = mapped_column(Integer, default=0)

    bodega_origen = relationship("Bodega", foreign_keys=[bodega_origen_id])
    bodega_destino = relationship("Bodega", foreign_keys=[bodega_destino_id])

    items: Mapped[List["MovimientoItem"]] = relationship(
        "MovimientoItem", back_populates="movimiento", cascade="all, delete-orphan"
    )


class MovimientoItem(Base):
    __tablename__ = "inv_movimiento_item"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    movimiento_id: Mapped[int] = mapped_column(ForeignKey("inv_movimiento.id"), nullable=False)
    producto_id: Mapped[int] = mapped_column(ForeignKey("inv_producto.id"), nullable=False)
    cantidad: Mapped[float] = mapped_column(DECIMAL(18, 3), nullable=False)
    unidad_id: Mapped[int] = mapped_column(ForeignKey("inv_unidad.id"), nullable=False)
    costo_unitario: Mapped[float] = mapped_column(DECIMAL(18, 4), default=0)
    lote_id: Mapped[Optional[int]] = mapped_column(ForeignKey("inv_lote.id"))
    serie: Mapped[Optional[str]] = mapped_column(String(120))

    movimiento = relationship("Movimiento", back_populates="items")
    producto = relationship("Producto")
    unidad = relationship("Unidad")
    lote = relationship("Lote")