"""Database connection. Defaults to a local SQLite file so the project runs with zero setup.
Set DATABASE_URL to use PostgreSQL, e.g. postgresql+psycopg2://mandi:mandi@localhost:5432/krishimandi"""
import os
from pathlib import Path
from sqlalchemy import create_engine

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DATA_DIR.mkdir(exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{(DATA_DIR / 'krishimandi.db').as_posix()}")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
