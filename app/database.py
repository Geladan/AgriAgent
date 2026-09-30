"""Farmer profile storage.

Default: local SQLite (zero setup). Swap DATABASE_URL in .env to
PostgreSQL/Supabase later — the code stays the same.
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, String, Text, create_engine, inspect, text
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
    # Telegram chats have no phone number, so link them to the profile here.
    telegram_chat_id = Column(String, default="")


Base.metadata.create_all(engine)


def _add_missing_columns() -> None:
    """Add columns introduced after the database file was first created.

    create_all() never alters an existing table, so an old agri_ai.db would
    otherwise fail on the new telegram_chat_id column.
    """
    if not config.DATABASE_URL.startswith("sqlite"):
        return  # Postgres users should run a real migration
    inspector = inspect(engine)
    if "farmers" not in inspector.get_table_names():
        return
    existing = {c["name"] for c in inspector.get_columns("farmers")}
    for column in Farmer.__table__.columns:
        if column.name in existing or column.primary_key:
            continue
        ddl = (f'ALTER TABLE farmers ADD COLUMN "{column.name}" '
               f'{column.type.compile(engine.dialect)}')
        try:
            with engine.begin() as conn:
                conn.execute(text(ddl))
        except Exception:  # noqa: BLE001 — concurrent start-up, column landed anyway
            pass


_add_missing_columns()


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


def telegram_profile_key(chat_id) -> str:
    """Stable phone-shaped key for a chat that has no phone number."""
    return f"tg:{chat_id}"


def get_farmer_by_telegram(chat_id) -> dict | None:
    """Look up a profile by linked Telegram chat, falling back to the chat key."""
    cid = str(chat_id)
    db = SessionLocal()
    try:
        farmer = db.query(Farmer).filter(Farmer.telegram_chat_id == cid).first()
        if not farmer:
            farmer = db.query(Farmer).filter(
                Farmer.phone == telegram_profile_key(cid)).first()
        if not farmer:
            return None
        return {c.name: getattr(farmer, c.name) for c in Farmer.__table__.columns}
    finally:
        db.close()


def save_telegram_farmer(chat_id, data: dict) -> dict:
    """Create/update the profile for a Telegram chat and link the chat to it."""
    cid = str(chat_id)
    db = SessionLocal()
    try:
        farmer = db.query(Farmer).filter(Farmer.telegram_chat_id == cid).first()
        if not farmer:
            farmer = db.query(Farmer).filter(
                Farmer.phone == telegram_profile_key(cid)).first()
        if not farmer:
            farmer = Farmer(phone=telegram_profile_key(cid))
            db.add(farmer)
        for k, v in data.items():
            setattr(farmer, k, v)
        farmer.telegram_chat_id = cid
        db.commit()
        return {c.name: getattr(farmer, c.name) for c in Farmer.__table__.columns}
    finally:
        db.close()


def link_telegram_chat(chat_id, phone: str) -> bool:
    """Attach an existing phone-registered profile to a Telegram chat."""
    db = SessionLocal()
    try:
        farmer = db.query(Farmer).filter(Farmer.phone == phone).first()
        if not farmer:
            return False
        farmer.telegram_chat_id = str(chat_id)
        db.commit()
        return True
    finally:
        db.close()
