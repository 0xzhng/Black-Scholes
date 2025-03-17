# Black-Scholes Implied Volatility Surface 
A Streamlit application that enables users to visualize the Implied Volatility Surfaces of put and call options for an underlying security, based on the Black-Scholes-Merton model.

![NVIDIA Volatility Surface](img/NVDA.png)

![Broadcom Volatility Surface](img/AVGO.png)

## Call Option Price:
$$ C = S_0 N(d_1) - X e^{-rT} N(d_2) $$

## Put Option Price:
$$ P = X e^{-rT} N(-d_2) - S_0 N(-d_1) $$

## Definitions of Variables:

- **C** = Price of a call option  
- **P** = Price of a put option  
- **S₀** = **Current price** of the underlying asset  
- **X** = **Strike price** (exercise price of the option)  
- **T** = **Time to expiration** (in years)  
- **r** = **Risk-free interest rate** (continuously compounded)  
- **σ** = **Volatility** (standard deviation of the underlying asset’s returns)  
- **N(d)** = **Cumulative standard normal distribution function**  

### \( d_1 \) and \( d_2 \) are calculated as:

$$
d_1 = \frac{\ln(S_0 / X) + (r + \sigma^2 / 2)T}{\sigma \sqrt{T}}
$$

$$
d_2 = d_1 - \sigma \sqrt{T}
$$

### Video Explaining Black-Scholes:
[![Black-Scholes Explanation](https://img.youtube.com/vi/pr-u4LCFYEY/0.jpg)](https://www.youtube.com/watch?v=pr-u4LCFYEY)

## Features

- **Live Volatility Surface View**: View the current implied volatility surface for any ticker
- **Historical Data Collection**: Automatically collect and store volatility surface data at configurable intervals
- **Historical Replay**: View how volatility surfaces have evolved over time with animation capabilities
- **Ticker Management**: Configure which tickers to track and manage data collection settings


### Installation

#### Option 1: Local Installation (don't be a fool and use a venv)

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Create a `.env` file based on `.env.example`:
   ```
   cp .env.example .env
   ```

#### Option 2: Docker Installation

1. Clone this repository
2. Build and run with Docker Compose:
   ```
   docker-compose up -d
   ```

## Running the Application

### Option 1: Using the run.py script 

The easiest way to run the application is to use the `run.py` script, which will start both the data collection server and the Streamlit UI:

# Run the application
python run.py
```

You can also run only the server or only the UI:

```bash
# Run only the data collection server
python run.py --server-only

# Run only the Streamlit UI
python run.py --ui-only
```

### Option 2: Running components separately

If you prefer to run the components separately, you can do so:

1. Start the data collection server:
```bash
source venv/bin/activate
python -m utils.server
```

2. In a separate terminal, start the Streamlit UI:
```bash
source venv/bin/activate
streamlit run main.py
```

### Option 3: Using Docker

If you're using Docker, both the web interface and data collection server will start automatically. Access the web interface at:

```
http://localhost:8501
```

## Configuration

Edit the `.env` file (or environment variables in docker-compose.yml) to configure:

- `DATABASE_URL`: Database connection string (SQLite)
- `SNAPSHOT_INTERVAL_MINUTES`: How often to collect data (default: 60 minutes)
- `RISK_FREE_RATE`: Default risk-free rate for Black-Scholes model
- `DIVIDEND_YIELD`: Default dividend yield for Black-Scholes model
- `MIN_STRIKE_PCT`: Default minimum strike price as percentage of spot price
- `MAX_STRIKE_PCT`: Default maximum strike price as percentage of spot price


## Deployment

For production deployment, consider:

1. Setting up the data collection server as a systemd service or using Docker
2. Deploying the web interface behind a reverse proxy

### Docker Deployment

The included Docker configuration provides a simple way to deploy the application:

1. Adjust environment variables in `docker-compose.yml`
2. Deploy to your server:
   ```
   docker-compose up -d
   ```
3. For persistence, the SQLite database is mounted as a volume

## License

MIT

