import functools

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from basecore.settings import get_settings

Base = declarative_base()


@functools.lru_cache()
def get_engine():
    """
    Get SQLAlchemy engine (cached).
    
    This function lazily initializes the engine to avoid import-time side effects.
    The engine is created using DATABASE_URL from settings.
    """
    settings = get_settings()
    return create_engine(settings.DATABASE_URL, pool_pre_ping=True, echo=False)


@functools.lru_cache()
def get_sessionmaker():
    """
    Get SQLAlchemy sessionmaker (cached).
    
    This function lazily initializes the sessionmaker to avoid import-time side effects.
    """
    engine = get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Dependency generator for FastAPI to get database session.
    
    Yields a database session and ensures it's closed after use.
    """
    SessionLocal = get_sessionmaker()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

