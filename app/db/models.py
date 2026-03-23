from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/digicloset")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Shop(Base):
    __tablename__ = "shops"

    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String, unique=True, index=True)
    access_token = Column(String)
    installed_at = Column(DateTime, default=datetime.utcnow)
    uninstalled_at = Column(DateTime, nullable=True)

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id"))
    plan_name = Column(String)  # starter, growth, scale
    status = Column(String)  # inactive, pending, active, cancelled
    charge_id = Column(String, nullable=True)
    trial_ends_at = Column(DateTime, nullable=True)
    activated_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    shop = relationship("Shop")

class UsageEvent(Base):
    __tablename__ = "usage_events"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id"))
    event_type = Column(String)  # ai_credit, subscription, etc.
    amount = Column(Float)
    description = Column(Text, nullable=True)
    feature = Column(String, nullable=True)
    time_saved_minutes = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    shop = relationship("Shop")

class CreditBalance(Base):
    __tablename__ = "credit_balances"

    id = Column(Integer, primary_key=True, index=True)
    shop_id = Column(Integer, ForeignKey("shops.id"))
    credits = Column(Float, default=0.0)
    monthly_limit = Column(Float, nullable=True)  # for plans with limits
    reset_date = Column(DateTime)  # when credits reset
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    shop = relationship("Shop")

# Create tables
Base.metadata.create_all(bind=engine)
