import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import timedelta, datetime
from scipy.stats import norm
from scipy.optimize import brentq
from scipy.interpolate import griddata
import plotly.graph_objects as go
import os
import argparse
import sys
from dotenv import load_dotenv
from database.models import init_db
from database.operations import (
    get_active_tickers, set_ticker_active, get_or_create_ticker,
    save_volatility_snapshot, get_snapshot_timerange, get_snapshots_in_timerange
)
from utils.volatility import calculate_implied_volatility
from utils.server import start_server, stop_server

# Load dat db and env variables
load_dotenv()
init_db()

# Start the server if not in streamlit mode
server_components = None
if not os.environ.get('STREAMLIT_SCRIPT_PATH'):
    # Running directly, not through run.py, so start server in background
    server_components = start_server()
    st.session_state.server_components = server_components

# config for streamlit app 
st.set_page_config(
    page_title="Black-Scholes Model",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "Implied Volatility Surface | Created by rynn"
    }
)

# Register a cleanup handler for when Streamlit exits
def cleanup():
    if 'server_components' in st.session_state and st.session_state.server_components:
        scheduler, stop_event, _ = st.session_state.server_components
        stop_server(scheduler, stop_event)

# Register the cleanup function to run when the script exits
import atexit
atexit.register(cleanup)

st.title('Implied Volatility Surface')

# Create tabs for different views
tab1, tab2, tab3, tab4 = st.tabs(["Live View", "Historical View", "Ticker Management", "Playback"])

with tab1:
    st.header("Black-Scholes Implied Volatility Surface")
    
    def bs_call_price(S, K, T, r, sigma, q=0):
        d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        call_price = S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        return call_price

    def implied_volatility(price, S, K, T, r, q=0):
        if T <= 0 or price <= 0:
            return np.nan

        def objective_function(sigma):
            return bs_call_price(S, K, T, r, sigma, q) - price

        try:
            implied_vol = brentq(objective_function, 1e-6, 5)
        except (ValueError, RuntimeError):
            implied_vol = np.nan

        return implied_vol

    st.sidebar.header('Model Parameters')
    st.sidebar.write('Adjust the parameters for the Black-Scholes model.')

    # Convert percentage to decimal for risk-free rate
    risk_free_pct = st.sidebar.number_input(
        'Risk-Free Rate (%)',
        min_value=0.0,
        max_value=20.0,
        value=float(os.getenv('RISK_FREE_RATE', '0.0431')) * 100,
        format="%.2f"
    )
    risk_free_rate = risk_free_pct / 100.0

    # Convert percentage to decimal for dividend yield
    dividend_pct = st.sidebar.number_input(
        'Dividend Yield (%)',
        min_value=0.0,
        max_value=20.0,
        value=float(os.getenv('DIVIDEND_YIELD', '0.0127')) * 100,
        format="%.2f"
    )
    dividend_yield = dividend_pct / 100.0

    st.sidebar.header('Visualization Parameters')
    y_axis_option = st.sidebar.selectbox(
        'Select Y-axis:',
        ('Strike Price ($)', 'Moneyness')
    )

    st.sidebar.header('Ticker Symbol')
    
    # Get active tickers for dropdown
    active_tickers = get_active_tickers()
    default_ticker = 'SPY'
    
    # If we have active tickers, use the first one as default
    if active_tickers:
        default_ticker = active_tickers[0]
    
    ticker_symbol = st.sidebar.text_input(
        'Enter Ticker Symbol',
        value=default_ticker,
        max_chars=10
    ).upper()

    st.sidebar.header('Strike Price Filter Parameters')

    min_strike_pct = st.sidebar.number_input(
        'Minimum Strike Price (% of Spot Price)',
        min_value=0.01,
        max_value=199.0,
        value=float(os.getenv('MIN_STRIKE_PCT', '0.01')),
        step=1.0,
        format="%.2f"
    )

    max_strike_pct = st.sidebar.number_input(
        'Maximum Strike Price (% of Spot Price)',
        min_value=0.02,
        max_value=12000.0,
        value=float(os.getenv('MAX_STRIKE_PCT', '12000.0')),
        step=1.0,
        format="%.2f"
    )

    # Add option to save current view to database
    save_snapshot = st.sidebar.button("Save Current View to Database")

    if min_strike_pct >= max_strike_pct:
        st.sidebar.error('Minimum percentage must be less than maximum percentage.')
        st.stop()

    ticker = yf.Ticker(ticker_symbol)

    today = pd.Timestamp('today').normalize()

    try:
        expirations = ticker.options
    except Exception as e:
        st.error(f'Error fetching options for {ticker_symbol}: {e}')
        st.stop()

    exp_dates = [pd.Timestamp(exp) for exp in expirations if pd.Timestamp(exp) > today + timedelta(days=7)]

    if not exp_dates:
        st.error(f'No available option expiration dates for {ticker_symbol}.')
    else:
        option_data = []

        for exp_date in exp_dates:
            try:
                opt_chain = ticker.option_chain(exp_date.strftime('%Y-%m-%d'))
                calls = opt_chain.calls
            except Exception as e:
                st.warning(f'Failed to fetch option chain for {exp_date.date()}: {e}')
                continue

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

        if not option_data:
            st.error('No option data available after filtering.')
        else:
            options_df = pd.DataFrame(option_data)

            try:
                spot_history = ticker.history(period='5d')
                if spot_history.empty:
                    st.error(f'Failed to retrieve spot price data for {ticker_symbol}.')
                    st.stop()
                else:
                    spot_price = spot_history['Close'].iloc[-1]
            except Exception as e:
                st.error(f'An error occurred while fetching spot price data: {e}')
                st.stop()

            options_df['daysToExpiration'] = (options_df['expirationDate'] - today).dt.days
            options_df['timeToExpiration'] = options_df['daysToExpiration'] / 365

            options_df = options_df[
                (options_df['strike'] >= spot_price * (min_strike_pct / 100)) &
                (options_df['strike'] <= spot_price * (max_strike_pct / 100))
            ]

            options_df.reset_index(drop=True, inplace=True)

            with st.spinner('Calculating implied volatility...'):
                options_df['impliedVolatility'] = options_df.apply(
                    lambda row: implied_volatility(
                        price=row['mid'],
                        S=spot_price,
                        K=row['strike'],
                        T=row['timeToExpiration'],
                        r=risk_free_rate,
                        q=dividend_yield
                    ), axis=1
                )

            options_df.dropna(subset=['impliedVolatility'], inplace=True)

            options_df['impliedVolatility'] *= 100

            options_df.sort_values('strike', inplace=True)

            options_df['moneyness'] = options_df['strike'] / spot_price

            if y_axis_option == 'Strike Price ($)':
                Y = options_df['strike'].values
                y_label = 'Strike Price ($)'
            else:
                Y = options_df['moneyness'].values
                y_label = 'Moneyness (Strike / Spot)'

            X = options_df['timeToExpiration'].values
            Z = options_df['impliedVolatility'].values

            ti = np.linspace(X.min(), X.max(), 50)
            ki = np.linspace(Y.min(), Y.max(), 50)
            T, K = np.meshgrid(ti, ki)

            Zi = griddata((X, Y), Z, (T, K), method='linear')

            Zi = np.ma.array(Zi, mask=np.isnan(Zi))

            fig = go.Figure(data=[go.Surface(
                x=T, y=K, z=Zi,
                colorscale='Inferno',
                colorbar_title='Implied Volatility (%)'
            )])

            fig.update_layout(
                title=f'Implied Volatility Surface for {ticker_symbol} Options',
                scene=dict(
                    xaxis_title='Time to Expiration (years)',
                    yaxis_title=y_label,
                    zaxis_title='Implied Volatility (%)'
                ),
                autosize=False,
                width=900,
                height=800,
                margin=dict(l=65, r=50, b=65, t=90)
            )

            st.plotly_chart(fig)
            
            # Save snapshot if requested
            if save_snapshot:
                try:
                    snapshot_id = save_volatility_snapshot(
                        ticker_symbol,
                        spot_price,
                        risk_free_rate,
                        dividend_yield,
                        options_df
                    )
                    st.success(f"Snapshot saved successfully (ID: {snapshot_id})")
                    
                    # Add ticker to active tickers if not already there
                    if ticker_symbol not in active_tickers:
                        get_or_create_ticker(ticker_symbol)
                        st.info(f"Added {ticker_symbol} to active tickers")
                except Exception as e:
                    st.error(f"Error saving snapshot: {e}")

with tab2:
    st.header("Historical Volatility Surface View")
    
    # Get active tickers for dropdown
    hist_active_tickers = get_active_tickers()
    
    if not hist_active_tickers:
        st.warning("No active tickers found in the database. Please add tickers in the Ticker Management tab.")
    else:
        # Select ticker
        hist_ticker = st.selectbox(
            "Select Ticker",
            options=hist_active_tickers,
            index=0
        )
        
        # Get time range for selected ticker
        start_time, end_time = get_snapshot_timerange(hist_ticker)
        
        if start_time is None or end_time is None:
            st.warning(f"No historical data available for {hist_ticker}. Try saving some snapshots first.")
        else:
            # Format dates for display
            start_date_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
            end_date_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
            
            st.info(f"Available data range: {start_date_str} to {end_date_str}")
            
            # Select time range
            col1, col2 = st.columns(2)
            
            with col1:
                selected_start = st.date_input(
                    "Start Date",
                    value=start_time.date(),
                    min_value=start_time.date(),
                    max_value=end_time.date()
                )
                
                selected_start_time = st.time_input(
                    "Start Time",
                    value=datetime.min.time()
                )
            
            with col2:
                selected_end = st.date_input(
                    "End Date",
                    value=end_time.date(),
                    min_value=start_time.date(),
                    max_value=end_time.date()
                )
                
                selected_end_time = st.time_input(
                    "End Time",
                    value=datetime.max.time()
                )
            
            # Combine date and time
            selected_start_dt = datetime.combine(selected_start, selected_start_time)
            selected_end_dt = datetime.combine(selected_end, selected_end_time)
            
            # Visualization parameters
            hist_y_axis = st.selectbox(
                'Select Y-axis:',
                ('Strike Price ($)', 'Moneyness'),
                key="hist_y_axis"
            )
            
            # Get snapshots
            snapshots = get_snapshots_in_timerange(hist_ticker, selected_start_dt, selected_end_dt)
            
            if not snapshots:
                st.warning(f"No snapshots found for {hist_ticker} in the selected time range.")
            else:
                st.success(f"Found {len(snapshots)} snapshots in the selected time range.")
                
                # Create a slider for selecting snapshots - handle case with only one snapshot
                if len(snapshots) == 1:
                    # If there's only one snapshot, don't use a slider
                    snapshot_index = 0
                    st.info("Only one snapshot available in the selected time range.")
                else:
                    # Create slider for multiple snapshots
                    snapshot_index = st.slider(
                        "Select Snapshot",
                        min_value=0,
                        max_value=len(snapshots) - 1,
                        value=0
                    )
                
                # Display selected snapshot timestamp
                selected_snapshot = snapshots[snapshot_index]
                st.write(f"Viewing snapshot from: {selected_snapshot['timestamp']}")
                st.write(f"Spot Price: ${selected_snapshot['spot_price']:.2f}")
                
                # Get data for selected snapshot
                options_df = selected_snapshot['options_df']
                
                if hist_y_axis == 'Strike Price ($)':
                    Y = options_df['strike'].values
                    y_label = 'Strike Price ($)'
                else:
                    Y = options_df['moneyness'].values
                    y_label = 'Moneyness (Strike / Spot)'

                X = options_df['timeToExpiration'].values
                Z = options_df['impliedVolatility'].values

                # Create surface plot
                if len(X) > 0 and len(Y) > 0 and len(Z) > 0:
                    ti = np.linspace(X.min(), X.max(), 50)
                    ki = np.linspace(Y.min(), Y.max(), 50)
                    T, K = np.meshgrid(ti, ki)

                    Zi = griddata((X, Y), Z, (T, K), method='linear')
                    Zi = np.ma.array(Zi, mask=np.isnan(Zi))

                    fig = go.Figure(data=[go.Surface(
                        x=T, y=K, z=Zi,
                        colorscale='Inferno',
                        colorbar_title='Implied Volatility (%)'
                    )])

                    fig.update_layout(
                        title=f'Historical Implied Volatility Surface for {hist_ticker}',
                        scene=dict(
                            xaxis_title='Time to Expiration (years)',
                            yaxis_title=y_label,
                            zaxis_title='Implied Volatility (%)'
                        ),
                        autosize=False,
                        width=900,
                        height=800,
                        margin=dict(l=65, r=50, b=65, t=90)
                    )

                    st.plotly_chart(fig)
                else:
                    st.error("Not enough data points to create a surface plot.")
                
                # Add animation controls - only show if there are multiple snapshots
                if len(snapshots) > 1:
                    st.subheader("Animation Controls")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        play_animation = st.button("Play Animation", key="hist_play_animation")
                    
                    with col2:
                        animation_speed = st.slider(
                            "Animation Speed (seconds per frame)",
                            min_value=0.5,
                            max_value=5.0,
                            value=2.0,
                            step=0.5,
                            key="hist_animation_speed"
                        )
                    
                    if play_animation:
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        animation_placeholder = st.empty()
                        
                        for i, snapshot in enumerate(snapshots):
                            # Update progress
                            progress = int(100 * i / (len(snapshots) - 1))
                            progress_bar.progress(progress)
                            
                            # Display timestamp
                            status_text.write(f"Viewing snapshot from: {snapshot['timestamp']}")
                            
                            # Get data for current snapshot
                            options_df = snapshot['options_df']
                            
                            if hist_y_axis == 'Strike Price ($)':
                                Y = options_df['strike'].values
                                y_label = 'Strike Price ($)'
                            else:
                                Y = options_df['moneyness'].values
                                y_label = 'Moneyness (Strike / Spot)'

                            X = options_df['timeToExpiration'].values
                            Z = options_df['impliedVolatility'].values

                            # Create surface plot
                            if len(X) > 0 and len(Y) > 0 and len(Z) > 0:
                                ti = np.linspace(X.min(), X.max(), 50)
                                ki = np.linspace(Y.min(), Y.max(), 50)
                                T, K = np.meshgrid(ti, ki)

                                Zi = griddata((X, Y), Z, (T, K), method='linear')
                                Zi = np.ma.array(Zi, mask=np.isnan(Zi))

                                fig = go.Figure(data=[go.Surface(
                                    x=T, y=K, z=Zi,
                                    colorscale='Inferno',
                                    colorbar_title='Implied Volatility (%)'
                                )])

                                fig.update_layout(
                                    title=f'Historical Implied Volatility Surface for {hist_ticker}',
                                    scene=dict(
                                        xaxis_title='Time to Expiration (years)',
                                        yaxis_title=y_label,
                                        zaxis_title='Implied Volatility (%)',
                                        camera=dict(
                                            eye=dict(x=1.5, y=1.5, z=1.2)
                                        )
                                    ),
                                    autosize=False,
                                    width=900,
                                    height=800,
                                    margin=dict(l=65, r=50, b=65, t=90)
                                )

                                animation_placeholder.plotly_chart(fig, key=f"hist_anim_frame_{i}")
                                
                                # Wait for animation speed
                                import time
                                time.sleep(animation_speed)
                        
                        # Complete progress bar
                        progress_bar.progress(100)

                        # Display animation
                        st.plotly_chart(fig, key="playback_animation")

with tab3:
    st.header("Ticker Management")
    
    st.subheader("Add New Ticker")
    
    new_ticker = st.text_input(
        "Enter Ticker Symbol",
        max_chars=10
    ).upper()
    
    add_ticker = st.button("Add Ticker")
    
    if add_ticker and new_ticker:
        try:
            # Validate ticker by fetching data
            ticker = yf.Ticker(new_ticker)
            info = ticker.info
            
            if 'symbol' in info:
                # Add to database
                get_or_create_ticker(new_ticker)
                st.success(f"Added {new_ticker} to active tickers")
            else:
                st.error(f"Invalid ticker symbol: {new_ticker}")
        except Exception as e:
            st.error(f"Error adding ticker: {e}")
    
    st.subheader("Manage Active Tickers")
    
    # Get all tickers
    active_tickers = get_active_tickers()
    
    if not active_tickers:
        st.info("No active tickers found. Add some tickers above.")
    else:
        st.write("Select tickers to deactivate:")
        
        for ticker in active_tickers:
            if st.checkbox(ticker, value=True, key=f"active_{ticker}"):
                # Keep ticker active
                pass
            else:
                # Deactivate ticker
                set_ticker_active(ticker, False)
                st.success(f"Deactivated {ticker}")
    
    st.subheader("Snapshot Schedule Configuration")
    
    current_interval = int(os.getenv('SNAPSHOT_INTERVAL_MINUTES', '60'))
    
    new_interval = st.number_input(
        "Snapshot Interval (minutes)",
        min_value=5,
        max_value=1440,
        value=current_interval,
        step=5
    )
    
    if new_interval != current_interval:
        st.info(f"To change the snapshot interval to {new_interval} minutes, update the SNAPSHOT_INTERVAL_MINUTES value in your .env file and restart the server.")

with tab4:
    st.header("IV Surface Playback")
    
    # Get active tickers for dropdown
    anim_active_tickers = get_active_tickers()
    
    if not anim_active_tickers:
        st.warning("No active tickers found in the database. Please add tickers in the Ticker Management tab.")
    else:
        # Select ticker
        anim_ticker = st.selectbox(
            "Select Ticker",
            options=anim_active_tickers,
            index=0,
            key="anim_ticker"
        )
        
        # Get time range for selected ticker
        start_time, end_time = get_snapshot_timerange(anim_ticker)
        
        if start_time is None or end_time is None:
            st.warning(f"No historical data available for {anim_ticker}. Try saving some snapshots first.")
        else:
            # Format dates for display
            start_date_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
            end_date_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
            
            st.info(f"Available data range: {start_date_str} to {end_date_str}")
            
            # Select time range
            col1, col2 = st.columns(2)
            
            with col1:
                anim_start = st.date_input(
                    "Start Date",
                    value=start_time.date(),
                    min_value=start_time.date(),
                    max_value=end_time.date(),
                    key="anim_start_date"
                )
                
                anim_start_time = st.time_input(
                    "Start Time",
                    value=datetime.min.time(),
                    key="anim_start_time"
                )
            
            with col2:
                anim_end = st.date_input(
                    "End Date",
                    value=end_time.date(),
                    min_value=start_time.date(),
                    max_value=end_time.date(),
                    key="anim_end_date"
                )
                
                anim_end_time = st.time_input(
                    "End Time",
                    value=datetime.max.time(),
                    key="anim_end_time"
                )
            
            # Combine date and time
            anim_start_dt = datetime.combine(anim_start, anim_start_time)
            anim_end_dt = datetime.combine(anim_end, anim_end_time)
            
            # Animation settings
            st.subheader("Playback Settings")
            
            col1, col2 = st.columns(2)
            
            with col1:
                anim_y_axis = st.selectbox(
                    'Select Y-axis:',
                    ('Strike Price ($)', 'Moneyness'),
                    key="anim_y_axis"
                )
                
                frame_duration = st.slider(
                    "Frame Duration (ms)",
                    min_value=100,
                    max_value=2000,
                    value=500,
                    step=100,
                    key="frame_duration"
                )
            
            with col2:
                transition_duration = st.slider(
                    "Transition Duration (ms)",
                    min_value=0,
                    max_value=1000,
                    value=300,
                    step=50,
                    key="transition_duration"
                )
                
                colorscale = st.selectbox(
                    "Color Scale",
                    options=["Viridis", "Plasma", "Inferno", "Magma", "Cividis", "Turbo"],
                    index=2,
                    key="colorscale"
                )
            
            # Get snapshots
            snapshots = get_snapshots_in_timerange(anim_ticker, anim_start_dt, anim_end_dt)
            
            if not snapshots:
                st.warning(f"No snapshots found for {anim_ticker} in the selected time range.")
            elif len(snapshots) < 2:
                st.warning(f"At least 2 snapshots are needed for playback. Found only {len(snapshots)}.")
            else:
                st.success(f"Found {len(snapshots)} snapshots for playback.")
                
                # Create animation
                create_animation = st.button("Generate Playback", key="create_animation")
                
                if create_animation:
                    # Prepare data for animation
                    frames = []
                    
                    # Progress bar for data preparation
                    prep_progress = st.progress(0)
                    prep_status = st.empty()
                    
                    for i, snapshot in enumerate(snapshots):
                        # Update progress
                        progress = int(100 * i / (len(snapshots) - 1))
                        prep_progress.progress(progress)
                        prep_status.write(f"Preparing frame {i+1}/{len(snapshots)}...")
                        
                        # Get data for current snapshot
                        options_df = snapshot['options_df']
                        
                        if anim_y_axis == 'Strike Price ($)':
                            Y = options_df['strike'].values
                            y_label = 'Strike Price ($)'
                        else:
                            Y = options_df['moneyness'].values
                            y_label = 'Moneyness (Strike / Spot)'

                        X = options_df['timeToExpiration'].values
                        Z = options_df['impliedVolatility'].values
                        
                        # Create surface for this frame
                        if len(X) > 0 and len(Y) > 0 and len(Z) > 0:
                            ti = np.linspace(X.min(), X.max(), 50)
                            ki = np.linspace(Y.min(), Y.max(), 50)
                            T, K = np.meshgrid(ti, ki)
                            
                            Zi = griddata((X, Y), Z, (T, K), method='linear')
                            Zi = np.ma.array(Zi, mask=np.isnan(Zi))
                            
                            # Create frame
                            frame = go.Frame(
                                data=[go.Surface(
                                    x=T, y=K, z=Zi,
                                    colorscale=colorscale.lower(),
                                    colorbar_title='Implied Volatility (%)',
                                    showscale=(i == 0)  # Only show colorbar on first frame
                                )],
                                name=f"frame_{i}",
                                traces=[0]
                            )
                            
                            frames.append(frame)
                    
                    # Complete progress
                    prep_progress.progress(100)
                    prep_status.write("Playback preparation complete!")
                    
                    if len(frames) > 0:
                        # Create base figure with first frame data
                        base_snapshot = snapshots[0]
                        options_df = base_snapshot['options_df']
                        
                        if anim_y_axis == 'Strike Price ($)':
                            Y = options_df['strike'].values
                            y_label = 'Strike Price ($)'
                        else:
                            Y = options_df['moneyness'].values
                            y_label = 'Moneyness (Strike / Spot)'

                        X = options_df['timeToExpiration'].values
                        Z = options_df['impliedVolatility'].values
                        
                        ti = np.linspace(X.min(), X.max(), 50)
                        ki = np.linspace(Y.min(), Y.max(), 50)
                        T, K = np.meshgrid(ti, ki)
                        
                        Zi = griddata((X, Y), Z, (T, K), method='linear')
                        Zi = np.ma.array(Zi, mask=np.isnan(Zi))
                        
                        # Create figure
                        fig = go.Figure(
                            data=[go.Surface(
                                x=T, y=K, z=Zi,
                                colorscale=colorscale.lower(),
                                colorbar_title='Implied Volatility (%)'
                            )],
                            frames=frames
                        )
                        
                        # Format timestamps 
                        slider_labels = [s["timestamp"].strftime("%H:%M:%S") for s in snapshots]
                        
                        # animation controls
                        fig.update_layout(
                            title=f'IV Surface Evolution for {anim_ticker}',
                            scene=dict(
                                xaxis_title='Time to Expiration (years)',
                                yaxis_title=y_label,
                                zaxis_title='Implied Volatility (%)',
                                camera=dict(
                                    eye=dict(x=1.5, y=1.5, z=1.2)
                                )
                            ),
                            updatemenus=[
                                {
                                    "type": "buttons",
                                    "buttons": [
                                        {
                                            "label": "Play",
                                            "method": "animate",
                                            "args": [
                                                None, 
                                                {
                                                    "frame": {"duration": frame_duration, "redraw": True},
                                                    "fromcurrent": True,
                                                    "transition": {"duration": transition_duration, "easing": "cubic-in-out"}
                                                }
                                            ]
                                        },
                                        {
                                            "label": "Pause",
                                            "method": "animate",
                                            "args": [
                                                [None], 
                                                {
                                                    "frame": {"duration": 0, "redraw": False},
                                                    "mode": "immediate",
                                                    "transition": {"duration": 0}
                                                }
                                            ]
                                        }
                                    ],
                                    "direction": "left",
                                    "pad": {"r": 10, "t": 10},
                                    "showactive": True,
                                    "type": "buttons",
                                    "x": 0.1,
                                    "y": 0,
                                    "xanchor": "right",
                                    "yanchor": "top"
                                }
                            ],
                            sliders=[
                                {
                                    "active": 0,
                                    "yanchor": "top",
                                    "xanchor": "left",
                                    "currentvalue": {
                                        "font": {"size": 12},
                                        "prefix": "Timestamp: ",
                                        "visible": True,
                                        "xanchor": "right"
                                    },
                                    "transition": {"duration": transition_duration, "easing": "cubic-in-out"},
                                    "pad": {"b": 10, "t": 50},
                                    "len": 0.9,
                                    "x": 0.1,
                                    "y": 0,
                                    "steps": [
                                        {
                                            "args": [
                                                [f"frame_{i}"],
                                                {
                                                    "frame": {"duration": frame_duration, "redraw": True},
                                                    "mode": "immediate",
                                                    "transition": {"duration": transition_duration}
                                                }
                                            ],
                                            "label": slider_labels[i],
                                            "method": "animate"
                                        }
                                        for i in range(len(frames))
                                    ]
                                }
                            ],
                            autosize=False,
                            width=900,
                            height=800,
                            margin=dict(l=65, r=50, b=65, t=90)
                        )
                        
                        
                        animation_container = st.container()
                        with animation_container:
                            st.plotly_chart(fig, key="playback_animation")
                        
                        
                        st.subheader("Snapshot Information")
                        
                
                        timestamp_data = {
                            "Timestamp": [s["timestamp"].strftime("%Y-%m-%d %H:%M:%S") for s in snapshots],
                            "Spot Price": [f"${s['spot_price']:.2f}" for s in snapshots],
                            "Risk-Free Rate": [f"{s['risk_free_rate']:.2%}" for s in snapshots],
                            "Dividend Yield": [f"{s['dividend_yield']:.2%}" for s in snapshots]
                        }
                        
                        timestamp_df = pd.DataFrame(timestamp_data)
                        st.dataframe(timestamp_df, use_container_width=True)
                        
                        # download link for them haters
                        st.download_button(
                            label="Download Playback HTML",
                            data=fig.to_html(),
                            file_name=f"{anim_ticker}_iv_surface_playback.html",
                            mime="text/html"
                        )
                    else:
                        st.error("Failed to create playback frames. Please try a different time range.")

st.write("---")
st.markdown(
    "Created by rynn  | zhng.dev | rynn@zhng.dev"
)
# Modified on 2024-11-21 00:00:00

# Modified on 2024-12-03 00:00:00

# Modified on 2024-12-13 00:00:00

# Modified on 2024-12-22 00:00:00

# Modified on 2025-01-04 00:00:00

# Modified on 2025-01-07 00:00:00

# Modified on 2025-01-13 00:00:00

# Modified on 2025-01-15 00:00:00

# Modified on 2025-01-22 00:00:00

# Modified on 2025-01-25 00:00:00
