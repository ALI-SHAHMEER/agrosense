from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,       # auto-reconnect on stale connections
    pool_size=10,
    max_overflow=20,
    echo=settings.DEBUG,      # log SQL in dev
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# Dependency — used in every route: `db: Session = Depends(get_db)`
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
