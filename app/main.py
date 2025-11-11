from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import RedirectResponse
import os

# -------------------------------
# Base de datos y modelos
# -------------------------------
from app.db import engine, SessionLocal
from app.models import Base, User

# ⚙️ Importa todos los modelos que tengan tablas (para registrarlos en el mismo Base.metadata)
import app.models.finance         # contiene Categoria
import app.models_finanzas        # contiene BancoMovimiento y CajaMovimiento

# -------------------------------
# Routers
# -------------------------------
from app.routers.web import router as web_router
from app.routers.entradas import router as entradas_router
from app.routers.salidas import router as salidas_router
from app.routers.categorias import router as categorias_router
from app.routers.auth import router as auth_router, seed_admin_user
from app.routers.inventario_simple import router as inventario_simple_router
from app.routers.pacientes import router as pacientes_router
from app.routers.dashboard import router as dashboard_router
from app.routers.finanzas import router as finanzas_pages_router
from app.routers import usuarios as r_usuarios


# -------------------------------
# Configuración de la app
# -------------------------------
app = FastAPI(title="Contabilidad Fundación")
app.mount("/static", StaticFiles(directory="static"), name="static")

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")


# -------------------------------
# Inicialización
# -------------------------------
@app.on_event("startup")
def on_startup():
    # Asegura que todas las tablas de todos los modelos se registren en el mismo metadata
    Base.metadata.create_all(bind=engine)
    seed_admin_user()


# -------------------------------
# Middleware de autenticación
# -------------------------------
PUBLIC_PATH_PREFIXES = (
    "/static",
    "/login",
    "/openapi.json",
    "/docs",
    "/redoc",
    "/favicon.ico",
)

@app.middleware("http")
async def auth_required(request: Request, call_next):
    """Middleware que protege rutas y mantiene el usuario en request.state.user"""
    request.state.user = None
    path = request.url.path

    # Permitir rutas públicas sin sesión
    if path.startswith(PUBLIC_PATH_PREFIXES):
        return await call_next(request)

    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url=f"/login?next={path}", status_code=303)

    # Cargar usuario activo para esta request
    try:
        db = SessionLocal()
        request.state.user = db.get(User, user_id)
    finally:
        db.close()

    return await call_next(request)


# -------------------------------
# Middleware de sesión
# -------------------------------
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="cf_session",
    same_site="lax",
    https_only=False,       # cámbialo a True si sirves por HTTPS
    max_age=60 * 60 * 24 * 14,  # 14 días
)


# -------------------------------
# Rutas principales
# -------------------------------
app.include_router(auth_router)
app.include_router(web_router)
app.include_router(entradas_router)
app.include_router(salidas_router)
app.include_router(categorias_router)
app.include_router(inventario_simple_router)
app.include_router(pacientes_router)
app.include_router(dashboard_router)
app.include_router(r_usuarios.router_admin)
app.include_router(r_usuarios.router_account)
app.include_router(finanzas_pages_router)
