from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import yfinance as yf
import pandas as pd
from datetime import timedelta
import logging
import time
import os
from database.operations import get_active_tickers, save_volatility_snapshot
from database.models import init_db
from utils.volatility import calculate_implied_volatility

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('volatility_scheduler')

def fetch_volatility_data(ticker_symbol, risk_free_rate, dividend_yield, min_strike_pct=80.0, max_strike_pct=120.0):
    """Fetch volatility data for a ticker"""
    logger.info(f"Fetching volatility data for {ticker_symbol}")
    
    try:
        ticker = yf.Ticker(ticker_symbol)
        today = pd.Timestamp('today').normalize()
        
        # Get expirations
        expirations = ticker.options
        exp_dates = [pd.Timestamp(exp) for exp in expirations if pd.Timestamp(exp) > today + timedelta(days=7)]
        
        if not exp_dates:
            logger.warning(f"No available option expiration dates for {ticker_symbol}")
            return None, None, None
        
        # Get spot price
        spot_history = ticker.history(period='5d')
        if spot_history.empty:
            logger.warning(f"Failed to retrieve spot price data for {ticker_symbol}")
            return None, None, None
        
        spot_price = spot_history['Close'].iloc[-1]
        
        # Get option data
        option_data = []
        for exp_date in exp_dates:
            try:
                opt_chain = ticker.option_chain(exp_date.strftime('%Y-%m-%d'))
                calls = opt_chain.calls
                
                calls = calls[(calls['bid'] > 0) & (calls['ask'] > 0)]
                
                for index, row in calls.iterrows():
                    strike = row['strike']
                    bid = row['bid']
                    ask = row['ask']
                    mid_price = (bid + ask) / 2
                    
                    option_data.append({
                        'expirationDate': exp_date,
                        'strike': strike,
                        'bid': bid,
                        'ask': ask,
                        'mid': mid_price
                    })
            except Exception as e:
                logger.warning(f"Failed to fetch option chain for {exp_date.date()}: {e}")
                continue
        
        if not option_data:
            logger.warning(f"No option data available after filtering for {ticker_symbol}")
            return None, None, None
        
        # Create DataFrame
        options_df = pd.DataFrame(option_data)
        
        # Calculate days to expiration
        options_df['daysToExpiration'] = (options_df['expirationDate'] - today).dt.days
        options_df['timeToExpiration'] = options_df['daysToExpiration'] / 365
        
        # Filter by strike price
        options_df = options_df[
            (options_df['strike'] >= spot_price * (min_strike_pct / 100)) &
            (options_df['strike'] <= spot_price * (max_strike_pct / 100))
        ]
        
        options_df.reset_index(drop=True, inplace=True)
        
        # Calculate implied volatility
        options_df = calculate_implied_volatility(
            options_df, 
            spot_price, 
            risk_free_rate, 
            dividend_yield
        )
        
        options_df.dropna(subset=['impliedVolatility'], inplace=True)
        
        if options_df.empty:
            logger.warning(f"No valid implied volatility data for {ticker_symbol}")
            return None, None, None
        
        return spot_price, options_df, None
    
    except Exception as e:
        logger.error(f"Error fetching volatility data for {ticker_symbol}: {e}")
        return None, None, str(e)

def snapshot_job():
    """Job to take snapshots of volatility surfaces for all active tickers"""
    logger.info("Starting volatility surface snapshot job")
    
    # Get active tickers
    tickers = get_active_tickers()
    
    if not tickers:
        logger.warning("No active tickers found")
        return
    
    # Default parameters
    risk_free_rate = float(os.getenv('RISK_FREE_RATE', '0.015'))
    dividend_yield = float(os.getenv('DIVIDEND_YIELD', '0.013'))
    min_strike_pct = float(os.getenv('MIN_STRIKE_PCT', '80.0'))
    max_strike_pct = float(os.getenv('MAX_STRIKE_PCT', '120.0'))
    
    # Take snapshots
    for ticker_symbol in tickers:
        spot_price, options_df, error = fetch_volatility_data(
            ticker_symbol, 
            risk_free_rate, 
            dividend_yield,
            min_strike_pct,
            max_strike_pct
        )
        
        if error:
            logger.error(f"Error fetching data for {ticker_symbol}: {error}")
            continue
        
        if spot_price is None or options_df is None or options_df.empty:
            logger.warning(f"No valid data for {ticker_symbol}")
            continue
        
        # Save to database
        try:
            snapshot_id = save_volatility_snapshot(
                ticker_symbol,
                spot_price,
                risk_free_rate,
                dividend_yield,
                options_df
            )
            logger.info(f"Saved snapshot {snapshot_id} for {ticker_symbol}")
        except Exception as e:
            logger.error(f"Error saving snapshot for {ticker_symbol}: {e}")

def start_scheduler():
    """Start the scheduler"""
    # Initialize database
    init_db()
    
    # Create scheduler
    scheduler = BackgroundScheduler()
    
    # Get interval from environment or default to 1 hour
    interval_minutes = int(os.getenv('SNAPSHOT_INTERVAL_MINUTES', '60'))
    
    # Add job
    scheduler.add_job(
        snapshot_job,
        IntervalTrigger(minutes=interval_minutes),
        id='volatility_snapshot_job',
        replace_existing=True
    )
    
    # Start scheduler
    scheduler.start()
    logger.info(f"Scheduler started with interval of {interval_minutes} minutes")
    
    return scheduler

if __name__ == "__main__":
    scheduler = start_scheduler()
    
    try:
        # Keep the script running
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown() 
# Modified on 2024-11-26 00:00:00

# Modified on 2024-12-08 00:00:00

# Modified on 2024-12-13 00:00:00

# Modified on 2024-12-16 00:00:00

# Modified on 2024-12-17 00:00:00

# Modified on 2024-12-18 00:00:00

# Modified on 2024-12-20 00:00:00

# Modified on 2024-12-28 00:00:00

# Modified on 2024-12-29 00:00:00

# Modified on 2025-01-03 00:00:00

# Modified on 2025-01-10 00:00:00

# Modified on 2025-01-13 00:00:00

# Modified on 2025-01-22 00:00:00
