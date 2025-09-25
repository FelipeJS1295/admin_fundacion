from sqlalchemy.orm import Session
from app.models import Categoria

CATS_ENTRADA = [
    "Aportes de socios",
    "Donaciones",
    "Subvenciones",
    "Recaudaciones / Eventos",
    "Ventas / Servicios",
    "Intereses / Rendimientos",
    "Otros ingresos",
]

CATS_SALIDA = [
    "Arriendo",
    "Servicios básicos",
    "Insumos",
    "Sueldos",
    "Honorarios",
    "Transporte",
    "Publicidad / Marketing",
    "Impuestos / Tasas",
    "Comisiones bancarias",
    "Otros egresos",
]

def seed_categorias(db: Session):
    existentes = {c.nombre for c in db.query(Categoria).all()}
    for nombre in CATS_ENTRADA + CATS_SALIDA:
        if nombre not in existentes:
            # decide el tipo por lista de origen
            tipo = "entrada" if nombre in CATS_ENTRADA else "salida"
            db.add(Categoria(nombre=nombre, tipo=tipo))
    db.commit()