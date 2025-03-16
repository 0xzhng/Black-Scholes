from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import datetime
import os
from dotenv import load_dotenv

load_dotenv()

Base = declarative_base()

class Ticker(Base):
    __tablename__ = 'tickers'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String, unique=True, nullable=False)
    is_active = Column(Integer, default=1)
    snapshots = relationship("VolatilitySnapshot", back_populates="ticker", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Ticker(symbol='{self.symbol}', is_active={self.is_active})>"

class VolatilitySnapshot(Base):
    __tablename__ = 'volatility_snapshots'
    
    id = Column(Integer, primary_key=True)
    ticker_id = Column(Integer, ForeignKey('tickers.id'), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    spot_price = Column(Float, nullable=False)
    risk_free_rate = Column(Float, nullable=False)
    dividend_yield = Column(Float, nullable=False)
    
    ticker = relationship("Ticker", back_populates="snapshots")
    data_points = relationship("VolatilityDataPoint", back_populates="snapshot", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<VolatilitySnapshot(ticker='{self.ticker.symbol}', timestamp='{self.timestamp}')>"

class VolatilityDataPoint(Base):
    __tablename__ = 'volatility_data_points'
    
    id = Column(Integer, primary_key=True)
    snapshot_id = Column(Integer, ForeignKey('volatility_snapshots.id'), nullable=False)
    strike = Column(Float, nullable=False)
    expiration_date = Column(DateTime, nullable=False)
    days_to_expiration = Column(Integer, nullable=False)
    time_to_expiration = Column(Float, nullable=False)
    implied_volatility = Column(Float, nullable=False)
    
    snapshot = relationship("VolatilitySnapshot", back_populates="data_points")
    
    def __repr__(self):
        return f"<VolatilityDataPoint(strike={self.strike}, expiration='{self.expiration_date}', iv={self.implied_volatility})>"

def get_engine():
    """Get database engine based on environment configuration."""
    db_url = os.getenv('DATABASE_URL', 'sqlite:///volatility_surface.db')
    return create_engine(db_url)

def get_session():
    """Get a new database session"""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()

def init_db():
    """Initialize the database, creating tables if they don't exist"""
    engine = get_engine()
    Base.metadata.create_all(engine) 
# Modified on 2024-11-21 00:00:00

# Modified on 2024-11-27 00:00:00

# Modified on 2024-11-28 00:00:00

# Modified on 2024-11-30 00:00:00

# Modified on 2024-12-17 00:00:00

# Modified on 2024-12-19 00:00:00

# Modified on 2024-12-20 00:00:00

# Modified on 2024-12-24 00:00:00

# Modified on 2024-12-30 00:00:00

# Modified on 2025-01-13 00:00:00

# Modified on 2025-01-17 00:00:00

# Modified on 2025-01-18 00:00:00

# Modified on 2025-01-23 00:00:00

# Modified on 2025-01-29 00:00:00

# Modified on 2025-02-01 00:00:00

# Modified on 2025-02-09 00:00:00

# Modified on 2025-02-19 00:00:00

# Modified on 2025-02-24 00:00:00

# Modified on 2025-02-25 00:00:00

# Modified on 2025-03-01 00:00:00

# Modified on 2025-03-02 00:00:00

# Modified on 2025-03-13 00:00:00

# Modified on 2025-03-16 00:00:00

# Modified on 2025-03-16 00:00:00
