from sqlalchemy import text
from app.db.engine import engine
from app.db.schema import Base  
from app.db.trigger import TRIGGERS_AND_INDEXES_SQL  


def init_db():
    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
        conn.execute(text(TRIGGERS_AND_INDEXES_SQL))

