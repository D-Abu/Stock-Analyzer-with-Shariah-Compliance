import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- Page Config ---
st.set_page_config(page_title="Shariah Stock Screener", layout="wide")
st.title("🕌 BSE/NSE Shariah & Technical Screener")
st.markdown("Automated AAOIFI financial ratios and Technical Analysis for Indian equities.")

# --- MAIN PAGE SEARCH INTERFACE ---
st.markdown("### Search Stock")

# Use columns to lay out the search bar nicely
search_col1, search_col2 = st.columns([3, 1])

with search_col1:
    ticker_input = st.text_input("Enter Ticker Symbol (e.g., RELIANCE, TCS, RISHABH):", "RELIANCE").upper()

with search_col2:
    # Adding horizontal=True makes the radio buttons sit nicely side-by-side
    exchange = st.radio("Select Exchange:", ("NSE", "BSE"), horizontal=True)

# Format ticker for Yahoo Finance
if exchange == "NSE":
    yf_ticker = f"{ticker_input}.NS"
else:
    yf_ticker = f"{ticker_input}.BO"

# Make the button wide and styled as the primary call-to-action
analyze_button = st.button("🔍 Analyze Stock", use_container_width=True, type="primary")

st.divider()

# --- Fetch Data Functions ---
@st.cache_data(ttl=3600) 
def fetch_financials(ticker_symbol):
    stock = yf.Ticker(ticker_symbol)
    
    # Try to get info, but don't panic if it fails
    try:
        info = stock.info
    except Exception:
        info = {}
        
    # Try to get balance sheet
    try:
        bs = stock.balance_sheet
    except Exception:
        bs = pd.DataFrame()
        
    # Try to get income statement
    try:
        financials = stock.financials
    except Exception:
        financials = pd.DataFrame()
        
    return info, bs, financials

@st.cache_data(ttl=3600)
def fetch_price_data(ticker_symbol):
    try:
        stock = yf.Ticker(ticker_symbol)
        hist_daily = stock.history(period="max")
        hist_weekly = stock.history(period="2y", interval="1wk")
        return hist_daily, hist_weekly
    except Exception:
        return None, None


# --- Application Logic ---
if analyze_button:
    with st.spinner(f"Fetching data for {ticker_input}..."):
        info, bs, financials = fetch_financials(yf_ticker)
        hist_daily, hist_weekly = fetch_price_data(yf_ticker)
        
        # --- Diagnostic Error Handling ---
        if bs is None or bs.empty:
            st.error(f"❌ Could not fetch the Balance Sheet for {yf_ticker}. Yahoo Finance might be blocking the request or missing data.")
        elif financials is None or financials.empty:
            st.error(f"❌ Could not fetch the Income Statement (Financials) for {yf_ticker}.")
        elif hist_daily is None or hist_daily.empty:
            st.error(f"❌ Could not fetch Historical Price data for {yf_ticker}.")
        else:
            # Everything required for math fetched successfully!
            current_price = hist_daily['Close'].iloc[-1]
            
            # Safely get the name, or default to the
