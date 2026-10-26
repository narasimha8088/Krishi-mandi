"""Table definitions (works on SQLite and PostgreSQL)."""
from sqlalchemy import (MetaData, Table, Column, Integer, String, Float, Date, DateTime,
                        ForeignKey, UniqueConstraint, Index, func)
from app.db import engine

metadata = MetaData()

markets = Table(
    "markets", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String, nullable=False),
    Column("district", String),
    Column("state", String, nullable=False),
    Column("lat", Float, nullable=False),
    Column("lon", Float, nullable=False),
    UniqueConstraint("name", "state"),
)

mandi_prices = Table(
    "mandi_prices", metadata,
    Column("market_id", Integer, ForeignKey("markets.id"), primary_key=True),
    Column("commodity", String, primary_key=True),
    Column("arrival_date", Date, primary_key=True),
    Column("variety", String),
    Column("min_price", Float),
    Column("max_price", Float),
    Column("modal_price", Float, nullable=False),   # Rs per quintal
    Index("idx_prices_crop_date", "commodity", "arrival_date"),
)

forecasts = Table(
    "forecasts", metadata,
    Column("market_id", Integer, ForeignKey("markets.id"), primary_key=True),
    Column("commodity", String, primary_key=True),
    Column("target_date", Date, primary_key=True),
    Column("yhat", Float), Column("lower", Float), Column("upper", Float),
    Column("model", String),
    Column("mape", Float),                          # 15-day backtest error, %
    Column("created_at", DateTime, server_default=func.now()),
)


def init_db():
    metadata.create_all(engine)
