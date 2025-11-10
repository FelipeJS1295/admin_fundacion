# app/models_finanzas.py
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import (
    BigInteger, Integer, Date, String, Numeric, Text, ForeignKey,
    TIMESTAMP, func
)

# Usa el Base global de tu app (¡clave!)
from app.models import Base

# ---------------- BANCO ----------------
class BancoMovimiento(Base):
    __tablename__ = "banco_movimientos"

    id: Mapped[int]               = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    fecha: Mapped[Date]           = mapped_column(Date, nullable=False)
    tipo: Mapped[str]             = mapped_column(String(10), nullable=False)  # 'entrada' | 'salida'
    monto: Mapped[float]          = mapped_column(Numeric(14, 2), nullable=False)
    metodo_pago: Mapped[str]      = mapped_column(String(20), nullable=False)  # debito|credito|transferencia|caja_vecina|otro
    concepto: Mapped[str]         = mapped_column(String(180), nullable=False)
    numero_documento: Mapped[str] = mapped_column(String(80), default="")
    descripcion: Mapped[str]      = mapped_column(Text, default="")
    # categorias.id es INT (según tu SHOW CREATE TABLE)
    categoria_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("categorias.id", ondelete="SET NULL", onupdate="CASCADE"))
    created_at = mapped_column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = mapped_column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False)

# ---------------- CAJA CHICA ----------------
class CajaMovimiento(Base):
    __tablename__ = "caja_movimientos"

    id: Mapped[int]               = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    fecha: Mapped[Date]           = mapped_column(Date, nullable=False)
    tipo: Mapped[str]             = mapped_column(String(10), nullable=False)  # 'entrada' | 'salida'
    monto: Mapped[float]          = mapped_column(Numeric(14, 2), nullable=False)
    concepto: Mapped[str]         = mapped_column(String(180), nullable=False)
    numero_documento: Mapped[str] = mapped_column(String(80), default="")
    descripcion: Mapped[str]      = mapped_column(Text, default="")
    categoria_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("categorias.id", ondelete="SET NULL", onupdate="CASCADE"))
    created_at = mapped_column(TIMESTAMP, server_default=func.current_timestamp(), nullable=False)
    updated_at = mapped_column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False)
