#!/usr/bin/env python3
"""
Script para criar um tenant e usuário de teste
"""
import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy.orm import Session
from basecore.db import Base, get_engine, get_sessionmaker
from basecore.security import get_password_hash
from app.models.tenant import Tenant
from app.models.user import User

def create_test_data():
    """Cria tenant e usuário de teste"""
    SessionLocal = get_sessionmaker()
    engine = get_engine()
    db = SessionLocal()
    
    try:
        # Verifica se já existe tenant de teste
        existing_tenant = db.query(Tenant).filter(
            Tenant.email == "loja@teste.com"
        ).first()
        
        if existing_tenant:
            print(f"Tenant de teste já existe: {existing_tenant.id}")
            tenant = existing_tenant
        else:
            # Cria tenant de teste
            tenant = Tenant(
                nome="Loja de Teste",
                cnpj="12.345.678/0001-90",
                email="loja@teste.com",
                telefone="(24) 99999-9999",
                endereco="Rua de Teste, 123 - Barra Mansa, RJ",
                ativo=True
            )
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
            print(f"✅ Tenant criado: {tenant.id}")
            print(f"   Nome: {tenant.nome}")
            print(f"   Email: {tenant.email}")
        
        # Verifica se já existe usuário de teste
        existing_user = db.query(User).filter(
            User.email == "admin@teste.com",
            User.tenant_id == tenant.id
        ).first()
        
        if existing_user:
            print(f"\nUsuário de teste já existe: {existing_user.id}")
            user = existing_user
        else:
            # Cria usuário admin de teste
            user = User(
                tenant_id=tenant.id,
                nome="Administrador",
                email="admin@teste.com",
                password_hash=get_password_hash("senha123"),
                role="admin",
                ativo=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"\n✅ Usuário criado: {user.id}")
            print(f"   Nome: {user.nome}")
            print(f"   Email: {user.email}")
            print(f"   Senha: senha123")
            print(f"   Role: {user.role}")
        
        print("\n" + "="*60)
        print("CREDENCIAIS DE TESTE")
        print("="*60)
        print(f"Email: {user.email}")
        print(f"Senha: senha123")
        print(f"Tenant ID: {tenant.id}")
        print("="*60)
        
        return tenant, user
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erro ao criar dados de teste: {e}")
        import traceback
        traceback.print_exc()
        return None, None
    finally:
        db.close()

if __name__ == "__main__":
    print("Criando dados de teste...")
    print("-" * 60)
    
    # Garante que as tabelas existem
    Base.metadata.create_all(bind=engine)
    
    create_test_data()

