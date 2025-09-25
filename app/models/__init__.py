# Re-exporta tus modelos antiguos (finanzas) y Base
from app.models_finanzas import *   # noqa: F401,F403
from app.models_finanzas import Base

# (opcional pero recomendado) importa inventario para registrar sus tablas
# en Base.metadata cuando se importe app.models
from .inventario import *  # noqa: F401,F403