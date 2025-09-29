# app/models/__init__.py
from .base import Base

# Re-export para compatibilidad con: from app.models import Transaccion, Categoria, User
from .finance import Transaccion, Categoria, User
from .pacientes import *

# NO importes inv_basic aquí para evitar ciclos; impórtalo donde lo uses:
# from app.models.inv_basic import InvCategoria, UnidadMedida, InventarioItem
