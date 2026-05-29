import yfinance as yf
from agents import function_tool

@function_tool
def fetch_5day_history(ticker: str) -> str:
    """
    Fetches the raw 5-day pricing matrix for a given stock ticker asset symbol.
    Input should be a simple ticker string (e.g., 'AAPL', 'NVDA').
    """
    clean_ticker = ticker.upper().strip()
    try:
        stock = yf.Ticker(clean_ticker)
        df = stock.history(period="5d")
        if df.empty:
            return f"Error: No data found for ticker '{clean_ticker}'."
        
        optimized_df = df[['Open', 'High', 'Low', 'Close', 'Volume']].round(2)
        return optimized_df.to_string()
    except Exception as e:
        return f"Data extraction failed: {str(e)}"