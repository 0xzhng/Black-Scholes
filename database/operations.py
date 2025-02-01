from database.models import Ticker, VolatilitySnapshot, VolatilityDataPoint, get_session
import pandas as pd
import datetime

def get_or_create_ticker(symbol):
    """Get a ticker from the database or create it if it doesn't exist"""
    session = get_session()
    try:
        ticker = session.query(Ticker).filter_by(symbol=symbol).first()
        
        if not ticker:
            ticker = Ticker(symbol=symbol)
            session.add(ticker)
            session.commit()
            # Get the ID of the newly created ticker
            ticker_id = ticker.id
            session.close()
            # Create a new session and fetch the ticker to avoid detached instance errors
            session = get_session()
            ticker = session.query(Ticker).filter_by(id=ticker_id).first()
        
        return ticker
    finally:
        session.close()

def save_volatility_snapshot(ticker_symbol, spot_price, risk_free_rate, dividend_yield, options_df):
    """Save a volatility surface snapshot to the database"""
    session = get_session()
    try:
        # Get or create ticker
        ticker = get_or_create_ticker(ticker_symbol)
        
        # Create snapshot
        snapshot = VolatilitySnapshot(
            ticker_id=ticker.id,
            spot_price=spot_price,
            risk_free_rate=risk_free_rate,
            dividend_yield=dividend_yield
        )
        
        session.add(snapshot)
        session.flush()  # Get the ID without committing
        snapshot_id = snapshot.id
        
        # Add data points
        for _, row in options_df.iterrows():
            data_point = VolatilityDataPoint(
                snapshot_id=snapshot_id,
                strike=row['strike'],
                expiration_date=row['expirationDate'],
                days_to_expiration=row['daysToExpiration'],
                time_to_expiration=row['timeToExpiration'],
                implied_volatility=row['impliedVolatility']
            )
            session.add(data_point)
        
        session.commit()
        return snapshot_id
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def get_active_tickers():
    """Get all active tickers from the database"""
    session = get_session()
    try:
        tickers = session.query(Ticker).filter_by(is_active=1).all()
        result = [ticker.symbol for ticker in tickers]
        return result
    finally:
        session.close()

def set_ticker_active(symbol, active=True):
    """Set a ticker as active or inactive"""
    session = get_session()
    try:
        ticker = session.query(Ticker).filter_by(symbol=symbol).first()
        
        if ticker:
            ticker.is_active = 1 if active else 0
            session.commit()
            result = True
        else:
            result = False
        
        return result
    finally:
        session.close()

def get_snapshot_timerange(ticker_symbol):
    """Get the earliest and latest snapshot timestamps for a ticker"""
    session = get_session()
    try:
        ticker = session.query(Ticker).filter_by(symbol=ticker_symbol).first()
        
        if not ticker:
            return None, None
        
        earliest = session.query(VolatilitySnapshot.timestamp)\
            .filter_by(ticker_id=ticker.id)\
            .order_by(VolatilitySnapshot.timestamp.asc())\
            .first()
        
        latest = session.query(VolatilitySnapshot.timestamp)\
            .filter_by(ticker_id=ticker.id)\
            .order_by(VolatilitySnapshot.timestamp.desc())\
            .first()
        
        if earliest and latest:
            return earliest[0], latest[0]
        return None, None
    finally:
        session.close()

def get_snapshots_in_timerange(ticker_symbol, start_time, end_time):
    """Get all snapshots for a ticker within a time range"""
    session = get_session()
    try:
        ticker = session.query(Ticker).filter_by(symbol=ticker_symbol).first()
        
        if not ticker:
            return []
        
        snapshots = session.query(VolatilitySnapshot)\
            .filter_by(ticker_id=ticker.id)\
            .filter(VolatilitySnapshot.timestamp >= start_time)\
            .filter(VolatilitySnapshot.timestamp <= end_time)\
            .order_by(VolatilitySnapshot.timestamp.asc())\
            .all()
        
        result = []
        for snapshot in snapshots:
            data_points = session.query(VolatilityDataPoint)\
                .filter_by(snapshot_id=snapshot.id)\
                .all()
            
            # Convert to DataFrame format
            df_data = []
            for dp in data_points:
                df_data.append({
                    'strike': dp.strike,
                    'expirationDate': dp.expiration_date,
                    'daysToExpiration': dp.days_to_expiration,
                    'timeToExpiration': dp.time_to_expiration,
                    'impliedVolatility': dp.implied_volatility
                })
            
            options_df = pd.DataFrame(df_data)
            
            result.append({
                'id': snapshot.id,
                'timestamp': snapshot.timestamp,
                'spot_price': snapshot.spot_price,
                'risk_free_rate': snapshot.risk_free_rate,
                'dividend_yield': snapshot.dividend_yield,
                'options_df': options_df
            })
        
        return result
    finally:
        session.close() 
# Modified on 2024-11-29 00:00:00

# Modified on 2024-11-30 00:00:00

# Modified on 2024-12-05 00:00:00

# Modified on 2024-12-08 00:00:00

# Modified on 2024-12-16 00:00:00

# Modified on 2024-12-18 00:00:00

# Modified on 2025-01-15 00:00:00

# Modified on 2025-01-16 00:00:00

# Modified on 2025-01-25 00:00:00

# Modified on 2025-01-30 00:00:00

# Modified on 2025-02-01 00:00:00
