import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- Page Config ---
# 'layout="wide"' gives us the fluid design to utilize the whole screen
st.set_page_config(page_title="Shariah Stock Screener", layout="wide")
st.title("🕌 BSE/NSE Shariah & Technical Screener")
st.markdown("Automated AAOIFI financial ratios and Technical Analysis for Indian equities.")

# --- Search Interface ---
st.sidebar.header("Search Stock")
ticker_input = st.sidebar.text_input("Enter Ticker Symbol (e.g., RELIANCE, TCS, RISHABH):", "RELIANCE").upper()
exchange = st.sidebar.radio("Select Exchange:", ("NSE", "BSE"))

# Format ticker for Yahoo Finance
if exchange == "NSE":
    yf_ticker = f"{ticker_input}.NS"
else:
    yf_ticker = f"{ticker_input}.BO"

# --- Fetch Data Functions ---
@st.cache_data(ttl=3600) 
def fetch_financials(ticker_symbol):
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        bs = stock.balance_sheet
        financials = stock.financials
        return info, bs, financials
    except Exception as e:
        return None, None, None

@st.cache_data(ttl=3600)
def fetch_price_data(ticker_symbol):
    try:
        stock = yf.Ticker(ticker_symbol)
        # Fetch max daily data for ATH and long-term MAs
        hist_daily = stock.history(period="max")
        # Fetch 2 years of weekly data for 30 WEMA
        hist_weekly = stock.history(period="2y", interval="1wk")
        return hist_daily, hist_weekly
    except Exception as e:
        return None, None

if st.sidebar.button("Analyze Stock"):
    with st.spinner(f"Fetching data for {ticker_input}..."):
        info, bs, financials = fetch_financials(yf_ticker)
        hist_daily, hist_weekly = fetch_price_data(yf_ticker)
        
        # Check if info is valid and dataframes aren't empty
        if not isinstance(info, dict) or "symbol" not in info or bs.empty or financials.empty or hist_daily.empty:
            st.error("❌ Could not fetch complete data. Please check the ticker symbol or try a different exchange.")
        else:
            current_price = hist_daily['Close'].iloc[-1]
            st.subheader(f"{info.get('longName', ticker_input)} ({yf_ticker}) - Current Price: ₹{current_price:.2f}")
            st.write(f"**Sector:** {info.get('sector', 'N/A')} | **Industry:** {info.get('industry', 'N/A')}")
            
            # --- STEP 1: Sector Screening ---
            st.warning("**Step 1: Sector Screening (Manual Check Required)**\n\nEnsure this company does not derive its primary revenue from conventional banking, alcohol, gambling, or pork products.")
            
            # --- STEP 2: Financial Ratio Calculations ---
            st.markdown("### Step 2: Financial Ratios (AAOIFI Standards)")
            try:
                recent_bs = bs.iloc[:, 0] 
                recent_inc = financials.iloc[:, 0]
                
                total_assets = recent_bs.get("Total Assets", 0)
                total_debt = recent_bs.get("Total Debt", 0)
                cash_and_equiv = recent_bs.get("Cash And Cash Equivalents", 0)
                short_term_investments = recent_bs.get("Other Short Term Investments", 0)
                long_term_investments = recent_bs.get("Long Term Investments", 0)
                
                total_revenue = recent_inc.get("Total Revenue", 0)
                interest_income = recent_inc.get("Interest Income", 0)
                
                total_cash_investments = cash_and_equiv + short_term_investments
                interest_bearing_securities = short_term_investments + long_term_investments
                
                if total_assets > 0 and total_revenue > 0:
                    debt_to_assets = (total_debt / total_assets) * 100
                    cash_to_assets = (total_cash_investments / total_assets) * 100
                    securities_to_assets = (interest_bearing_securities / total_assets) * 100
                    interest_to_revenue = (interest_income / total_revenue) * 100
                    
                    f_col1, f_col2, f_col3, f_col4 = st.columns(4)
                    
                    with f_col1:
                        st.metric(label="Debt / Assets (< 33%)", value=f"{debt_to_assets:.2f}%")
                    with f_col2:
                        st.metric(label="Cash / Assets (< 33%)", value=f"{cash_to_assets:.2f}%")
                    with f_col3:
                        st.metric(label="Securities / Assets (< 33%)", value=f"{securities_to_assets:.2f}%")
                    with f_col4:
                        st.metric(label="Interest / Revenue (< 5%)", value=f"{interest_to_revenue:.2f}%")
                            
                    if debt_to_assets < 33 and cash_to_assets < 33 and securities_to_assets < 33 and interest_to_revenue < 5:
                        st.success("🟢 **Financial Ratios: COMPLIANT** (Passes all AAOIFI thresholds)")
                    else:
                        st.error("🔴 **Financial Ratios: NON-COMPLIANT** (Fails one or more thresholds)")
                else:
                    st.warning("Total Assets or Total Revenue data is missing. Cannot calculate Shariah ratios.")
            except Exception as e:
                st.error(f"⚠️ Incomplete financial data available. (Error: {e})")

            st.divider()

            # --- STEP 3: Technical Analysis & Performance ---
            st.markdown("### Step 3: Technical Analysis & Performance")
            
            try:
                # --- 1. Calculate Returns ---
                # Trading days approximations: 6M (~126 days), 12M (~252 days), 3Y (~756 days)
                ret_6m = ((current_price / hist_daily['Close'].iloc[-126]) - 1) * 100 if len(hist_daily) >= 126 else None
                ret_12m = ((current_price / hist_daily['Close'].iloc[-252]) - 1) * 100 if len(hist_daily) >= 252 else None
                ret_3y = ((current_price / hist_daily['Close'].iloc[-756]) - 1) * 100 if len(hist_daily) >= 756 else None

                # --- 2. Calculate Moving Averages (Crossover) ---
                hist_daily['SMA_50'] = hist_daily['Close'].rolling(window=50).mean()
                hist_daily['SMA_200'] = hist_daily['Close'].rolling(window=200).mean()
                sma_50 = hist_daily['SMA_50'].iloc[-1]
                sma_200 = hist_daily['SMA_200'].iloc[-1]
                
                if pd.isna(sma_200):
                    crossover_status = "Not enough data"
                elif sma_50 > sma_200:
                    crossover_status = "🟢 Bullish (50 > 200 DMA)"
                else:
                    crossover_status = "🔴 Bearish (50 < 200 DMA)"

                # --- 3. Calculate 30 WEMA ---
                hist_weekly['WEMA_30'] = hist_weekly['Close'].ewm(span=30, adjust=False).mean()
                wema_30 = hist_weekly['WEMA_30'].iloc[-1]
                wema_status = "🟢 Above 30 WEMA" if current_price > wema_30 else "🔴 Below 30 WEMA"

                # --- 4. Calculate Distance from Highs ---
                high_52w = hist_daily['Close'].tail(252).max()
                ath = hist_daily['Close'].max()
                
                dist_52w = ((current_price / high_52w) - 1) * 100
                dist_ath = ((current_price / ath) - 1) * 100

                # --- Render Technical Metrics in Columns ---
                st.markdown("**Historical Returns**")
                r_col1, r_col2, r_col3 = st.columns(3)
                with r_col1:
                    st.metric("6-Month Return", f"{ret_6m:.2f}%" if ret_6m else "N/A", delta=f"{ret_6m:.2f}%" if ret_6m else None)
                with r_col2:
                    st.metric("12-Month Return", f"{ret_12m:.2f}%" if ret_12m else "N/A", delta=f"{ret_12m:.2f}%" if ret_12m else None)
                with r_col3:
                    st.metric("3-Year Return", f"{ret_3y:.2f}%" if ret_3y else "N/A", delta=f"{ret_3y:.2f}%" if ret_3y else None)
                
                st.markdown("<br>**Technical Indicators**", unsafe_allow_html=True)
                t_col1, t_col2, t_col3, t_col4 = st.columns(4)
                with t_col1:
                    st.metric("Trend (50 vs 200 DMA)", crossover_status)
                with t_col2:
                    st.metric("Weekly Trend (30 WEMA)", wema_status)
                with t_col3:
                    st.metric("Distance from 52W High", f"{dist_52w:.2f}%")
                with t_col4:
                    st.metric("Distance from ATH", f"{dist_ath:.2f}%")

            except Exception as e:
                st.error(f"⚠️ Could not calculate all technical indicators. (Error details: {e})")