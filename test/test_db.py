from sqlalcchmy import staticpool , create_engine
from sqlalcchmy.orm import sessionmaker

from app.db.schema import Base



database_url = "sqlite:///:memory:"
engine = create_engine(
    database_url,
    connect_args={"check_same_thread": False},
    poolclass=staticpool.StaticPool,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)