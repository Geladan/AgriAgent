"""Farmer profile storage.

Default: local SQLite (zero setup). Swap DATABASE_URL in .env to
PostgreSQL/Supabase later — the code stays the same.
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app import config

_connect_args = {"check_same_thread": False} if config.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(config.DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()


class Farmer(Base):
    __tablename__ = "farmers"

    phone = Column(String, primary_key=True)
    name = Column(String, default="")
    location = Column(String, default="")
    language = Column(String, default="English")
    primary_crop = Column(String, default="")
    farm_size = Column(Float, nullable=True)
    planting_date = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, default="")


Base.metadata.create_all(engine)


def get_farmer(phone: str) -> dict | None:
    """Return the farmer profile as a dict, or None if not registered."""
    db = SessionLocal()
    try:
        farmer = db.query(Farmer).filter(Farmer.phone == phone).first()
        if not farmer:
            return None
        return {c.name: getattr(farmer, c.name) for c in Farmer.__table__.columns}
    finally:
        db.close()


def save_farmer(phone: str, data: dict):
    """Create or update a farmer profile."""
    db = SessionLocal()
    try:
        farmer = db.query(Farmer).filter(Farmer.phone == phone).first()
        if farmer:
            for k, v in data.items():
                setattr(farmer, k, v)
        else:
            db.add(Farmer(phone=phone, **data))
        db.commit()
    finally:
        db.close()