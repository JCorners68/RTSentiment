import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime
from typing import Generator
from contextlib import contextmanager

# Database connection
DB_USER = os.getenv("POSTGRES_USER", "pgadmin")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "localdev")
DB_HOST = os.getenv("POSTGRES_HOST", "postgres")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "sentimentdb")

SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

@contextmanager
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Database models
class SentimentEvent(Base):
    __tablename__ = "sentiment_events"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(100), nullable=False)
    priority = Column(String(50), nullable=False)
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    model = Column(String(100), nullable=True)
    sentiment_score = Column(Float, nullable=True)
    sentiment_label = Column(String(50), nullable=True)
    processing_time = Column(Float, nullable=True)  # in seconds
    event_id = Column(String(100), unique=True, index=True)
    ticker_sentiments = relationship("TickerSentiment", back_populates="event")

class TickerSentiment(Base):
    __tablename__ = "ticker_sentiments"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("sentiment_events.id"), nullable=False)
    ticker = Column(String(20), nullable=False)
    sentiment_score = Column(Float, nullable=False)
    sentiment_label = Column(String(50), nullable=False)
    event = relationship("SentimentEvent", back_populates="ticker_sentiments")

# Create tables
def init_db():
    Base.metadata.create_all(bind=engine)