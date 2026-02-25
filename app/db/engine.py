from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,        
    pool_size=5,
    max_overflow=10)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

class Base(DeclarativeBase):
    pass

def test_connection():
    with engine.connect() as conn:
        conn.execute(text("select 1"))

if __name__ == "__main__":
    test_connection()
    print("DB connection OK")