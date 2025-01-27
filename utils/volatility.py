import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq


# jesus fucking christ, probs the most complex function i ever wrote 
def bs_call_price(S, K, T, r, sigma, q=0):
    """Calculate Black-Scholes call option price"""
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    call_price = S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    return call_price

def implied_volatility(price, S, K, T, r, q=0):
    """Calculate implied volatility using the Black-Scholes model"""
    if T <= 0 or price <= 0:
        return np.nan

    def objective_function(sigma):
        return bs_call_price(S, K, T, r, sigma, q) - price

    try:
        implied_vol = brentq(objective_function, 1e-6, 5)
    except (ValueError, RuntimeError):
        implied_vol = np.nan

    return implied_vol

def calculate_implied_volatility(options_df, spot_price, risk_free_rate, dividend_yield):
    """Calculate implied volatility for a DataFrame of options"""
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
    
    # Convert to percentage
    options_df['impliedVolatility'] *= 100
    

    options_df['moneyness'] = options_df['strike'] / spot_price
    
    return options_df 
# Modified on 2024-12-12 00:00:00

# Modified on 2024-12-18 00:00:00

# Modified on 2024-12-25 00:00:00

# Modified on 2024-12-28 00:00:00

# Modified on 2025-01-03 00:00:00

# Modified on 2025-01-04 00:00:00

# Modified on 2025-01-10 00:00:00

# Modified on 2025-01-13 00:00:00

# Modified on 2025-01-25 00:00:00

# Modified on 2025-01-27 00:00:00

# Modified on 2025-01-27 00:00:00
