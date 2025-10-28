from fastapi import Depends, HTTPException, status
from app.auth import get_current_user, is_admin

def require_admin(user = Depends(get_current_user)):
    if not user or not is_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")
    return user