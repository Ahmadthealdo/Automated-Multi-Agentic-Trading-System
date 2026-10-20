import yfinance as yf
import pandas as pd
from agents import function_tool

@function_tool
def fetch_market_data(ticker: str, period: str, interval: str) -> str:
    """
    Fetches the pricing history for a given ticker asset symbol with a specified lookback period and interval.
    Calculates key technical indicators (EMA, SMA, RSI, MACD) to optimize context usage and token footprint.
    
    Parameters:
    - ticker: Ticker symbol (e.g. 'AAPL', 'BTC-USD')
    - period: Lookback period (e.g. '7d', '30d', '60d', '180d')
    - interval: Data interval (e.g. '15m', '1h', '4h', '1d')
    """
    clean_ticker = ticker.upper().strip()
    try:
        stock = yf.Ticker(clean_ticker)
        df = stock.history(period=period, interval=interval)
        if df.empty:
            return f"Error: No data found for ticker '{clean_ticker}' with period='{period}' and interval='{interval}'."
        
        # Calculate RSI (14)
        delta = df['Close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=13, adjust=False).mean()
        avg_loss = loss.ewm(com=13, adjust=False).mean()
        rs = avg_gain / avg_loss
        df['RSI_14'] = (100 - (100 / (1 + rs))).round(2)
        
        # Calculate EMA (9 & 21)
        df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean().round(2)
        df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean().round(2)
        
        # Calculate SMA (50 & 200)
        df['SMA_50'] = df['Close'].rolling(window=min(50, len(df))).mean().round(2)
        df['SMA_200'] = df['Close'].rolling(window=min(200, len(df))).mean().round(2)
        
        # Calculate MACD
        ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = (ema_12 - ema_26).round(2)
        df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean().round(2)
        df['MACD_Hist'] = (df['MACD'] - df['MACD_Signal']).round(2)
        
        # Calculate ATR (14) for volatility metrics
        high_low = df['High'] - df['Low']
        high_close = (df['High'] - df['Close'].shift()).abs()
        low_close = (df['Low'] - df['Close'].shift()).abs()
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['ATR_14'] = true_range.ewm(span=14, adjust=False).mean().round(2)
        
        # Identify Support & Demand Zones (Swing Highs and Lows)
        window_size = 5
        if len(df) < 50:
            window_size = 3
        if len(df) < 20:
            window_size = 2
            
        high_mask = pd.Series(True, index=df.index)
        for i in range(-window_size, window_size + 1):
            if i != 0:
                high_mask &= (df['High'] >= df['High'].shift(i))
                
        low_mask = pd.Series(True, index=df.index)
        for i in range(-window_size, window_size + 1):
            if i != 0:
                low_mask &= (df['Low'] <= df['Low'].shift(i))
                
        raw_highs = df[high_mask]['High'].dropna().tolist()
        raw_lows = df[low_mask]['Low'].dropna().tolist()
        
        def consolidate_levels(levels, tolerance=0.005):
            if not levels:
                return []
            sorted_levels = sorted(levels)
            consolidated = [sorted_levels[0]]
            for lvl in sorted_levels[1:]:
                if (lvl - consolidated[-1]) / consolidated[-1] >= tolerance:
                    consolidated.append(lvl)
            return consolidated
            
        swing_highs = consolidate_levels(raw_highs)
        swing_lows = consolidate_levels(raw_lows)
        
        current_price = float(df['Close'].iloc[-1])
        supply_above = [sh for sh in swing_highs if sh > current_price]
        demand_below = [sl for sl in swing_lows if sl < current_price]
        
        nearest_supply = min(supply_above) if supply_above else None
        nearest_demand = max(demand_below) if demand_below else None
        
        # Format a token-conserved return representation
        latest = df.iloc[-1]
        summary = []
        summary.append(f"=== Live Quantitative Report for {clean_ticker} ===")
        summary.append(f"Lookback Period: {period} | Interval: {interval}")
        summary.append(f"Latest Close Price: ${latest['Close']:.2f}")
        summary.append(f"Latest Open: ${latest['Open']:.2f} | High: ${latest['High']:.2f} | Low: ${latest['Low']:.2f} | Volume: {int(latest['Volume'])}")
        
        summary.append("\n--- Latest Technical Indicator Values ---")
        summary.append(f"RSI (14): {latest['RSI_14']}")
        summary.append(f"EMA(9): {latest['EMA_9']} | EMA(21): {latest['EMA_21']} | Crossover Signal: {'Bullish (9-EMA > 21-EMA)' if latest['EMA_9'] > latest['EMA_21'] else 'Bearish (9-EMA < 21-EMA)'}")
        
        if len(df) >= 50:
            summary.append(f"SMA(50): {latest['SMA_50']}")
        if len(df) >= 200:
            summary.append(f"SMA(200): {latest['SMA_200']}")
            
        summary.append(f"MACD Line: {latest['MACD']} | Signal Line: {latest['MACD_Signal']} | Histogram: {latest['MACD_Hist']}")
        summary.append(f"ATR (14): ${latest['ATR_14']:.2f}")
        
        summary.append("\n--- Identified Supply & Demand Zones ---")
        summary.append(f"Nearest Supply Zone (Resistance): ${nearest_supply:.2f}" if nearest_supply else "Nearest Supply Zone (Resistance): None (Asset is at multi-period highs)")
        summary.append(f"Nearest Demand Zone (Support): ${nearest_demand:.2f}" if nearest_demand else "Nearest Demand Zone (Support): None (Asset is at multi-period lows)")
        summary.append(f"All Active Supply Zones (Highs): {', '.join([f'${x:.2f}' for x in sorted(supply_above)[:3]]) if supply_above else 'None'}")
        summary.append(f"All Active Demand Zones (Lows): {', '.join([f'${x:.2f}' for x in sorted(demand_below, reverse=True)[:3]]) if demand_below else 'None'}")
        
        summary.append("\n--- Last 5 Pricing & Indicator Intervals ---")
        recent_df = df[['Open', 'High', 'Low', 'Close', 'Volume', 'RSI_14', 'EMA_9', 'EMA_21']].tail(5)
        summary.append(recent_df.round(2).to_string())
        
        return "\n".join(summary)
    except Exception as e:
        return f"Data extraction failed: {str(e)}"