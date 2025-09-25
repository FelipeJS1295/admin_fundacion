from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.templates import templates
from app.db import get_db
from app.auth import get_current_user

router = APIRouter(tags=["inventario"])

@router.get("/inventario", response_class=HTMLResponse)
def inv_panel(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return templates.TemplateResponse("inventario/index.html", {"request": request})

@router.get("/inventario/productos", response_class=HTMLResponse)
def inv_productos(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return templates.TemplateResponse("inventario/productos_list.html", {"request": request})

@router.get("/inventario/movimientos", response_class=HTMLResponse)
def inv_movs(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return templates.TemplateResponse("inventario/movimientos_list.html", {"request": request})

@router.get("/inventario/bodegas", response_class=HTMLResponse)
def inv_bodegas(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return templates.TemplateResponse("inventario/bodegas_list.html", {"request": request})

@router.get("/inventario/categorias", response_class=HTMLResponse)
def inv_categorias(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return templates.TemplateResponse("inventario/categorias_list.html", {"request": request})
