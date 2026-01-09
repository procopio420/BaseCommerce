from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import Token, UserLogin
from basecore.db import get_db
from basecore.security import create_access_token, verify_password
from basecore.settings import get_settings

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(user_login: UserLogin, db: Session = Depends(get_db)):
    """
    Login de usuário.
    Se tenant_id não for fornecido, busca primeiro usuário ativo.
    """
    settings = get_settings()
    # Se tenant_id fornecido, busca por tenant específico
    if user_login.tenant_id:
        tenant = (
            db.query(Tenant).filter(Tenant.id == user_login.tenant_id, Tenant.ativo is True).first()
        )
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Tenant não encontrado ou inativo"
            )

    # Busca usuário
    user = db.query(User).filter(User.email == user_login.email, User.ativo is True)

    if user_login.tenant_id:
        user = user.filter(User.tenant_id == user_login.tenant_id)

    user = user.first()

    if not user or not verify_password(user_login.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Cria token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "tenant_id": str(user.tenant_id), "email": user.email},
        expires_delta=access_token_expires,
    )

    return {"access_token": access_token, "token_type": "bearer"}
