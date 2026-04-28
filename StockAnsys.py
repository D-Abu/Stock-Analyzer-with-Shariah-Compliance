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

search_col1, search_col2 = st.columns([3, 1])

with search_col1:
    ticker_input = st.text_input("Enter Ticker Symbol (e.g., RELIANCE, TCS, M&M):", "TCS").upper().strip()

with search_col2:
    exchange = st.radio("Select Exchange:", ("NSE", "BSE"), horizontal=True)

# Ticker Cleaning
base_symbol = ticker_input.split('.')[0]

if exchange == "NSE":
    yf_ticker = f"{base_symbol}.NS"
else:
    yf_ticker = f"{base_symbol}.BO"

analyze_button = st.button("🔍 Analyze Stock", use_container_width=True, type="primary")

st.divider()

# --- Fetch Data Functions ---
# We have removed the custom session here. Yfinance handles it natively now!
@st.cache_data(ttl=3600) 
def fetch_financials(ticker_symbol):
    stock = yf.Ticker(ticker_symbol)
    
    try:
        info = stock.info
    except Exception:
        info = {}
        
    try:
        bs = stock.balance_sheet
    except Exception:
        bs = pd.DataFrame()
        
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
    with st.spinner(f"Fetching data for {yf_ticker}..."):
        info, bs, financials = fetch_financials(yf_ticker)
        hist_daily, hist_weekly = fetch_price_data(yf_ticker)
        
        # --- Error Handling ---
        if bs is None or bs.empty:
            st.error(f"❌ Could not fetch the Balance Sheet for {yf_ticker}. Please ensure the ticker is correct for the selected exchange.")
        elif financials is None or financials.empty:
            st.error(f"❌ Could not fetch the Income Statement (Financials) for {yf_ticker}.")
        elif hist_daily is None or hist_daily.empty:
            st.error(f"❌ Could not fetch Historical Price data for {yf_ticker}.")
        else:
            # Data fetched successfully!
            current_price = hist_daily['Close'].iloc[-1]
            
            company_name = info.get('longName', ticker_input) if isinstance(info, dict) else ticker_input
            sector = info.get('sector', 'Unknown') if isinstance(info, dict) else 'Unknown'
            industry = info.get('industry', 'Unknown') if isinstance(info, dict) else 'Unknown'
            
            st.subheader(f"{company_name} ({yf_ticker}) - Current Price: ₹{current_price:.2f}")
            st.write(f"**Sector:** {sector} | **Industry:** {industry}")
            
            # --- STEP 1: Sector Screening ---
            st.warning("**Step 1: Sector Screening (Manual Check Required)**\n\nEnsure this company does not derive its primary revenue from non-compliant sources like conventional banking, alcohol, or gambling.")
            
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
                        st.success("🟢 **Financial Ratios: COMPLIANT**")
                    else:
                        st.error("🔴 **Financial Ratios: NON-COMPLIANT**")
                else:
                    st.warning("Financial data (Assets/Revenue) is zero or missing for this ticker.")
                    
            except Exception as e:
                st.error(f"⚠️ Error calculating ratios: {e}")

            st.divider()

            # --- STEP 3: Technical Analysis & Performance ---
            st.markdown("### Step 3: Technical Analysis & Performance")
            
            try:
                ret_6m = ((current_price / hist_daily['Close'].iloc[-126]) - 1) * 100 if len(hist_daily) >= 126 else None
                ret_12m = ((current_price / hist_daily['Close'].iloc[-252]) - 1) * 100 if len(hist_daily) >= 252 else None
                ret_3y = ((current_price / hist_daily['Close'].iloc[-756]) - 1) * 100 if len(hist_daily) >= 756 else None

                hist_daily['SMA_50'] = hist_daily['Close'].rolling(window=50).mean()
                hist_daily['SMA_200'] = hist_daily['Close'].rolling(window=200).mean()
                sma_50 = hist_daily['SMA_50'].iloc[-1]
                sma_200 = hist_daily['SMA_200'].iloc[-1]
                
                crossover = "🟢 Bullish" if sma_50 > sma_200 else "🔴 Bearish"

                hist_weekly['WEMA_30'] = hist_weekly['Close'].ewm(span=30, adjust=False).mean()
                wema_30 = hist_weekly['WEMA_30'].iloc[-1]
                wema_status = "🟢 Above 30 WEMA" if current_price > wema_30 else "🔴 Below 30 WEMA"

                high_52w = hist_daily['Close'].tail(252).max()
                ath = hist_daily['Close'].max()
                dist_52w = ((current_price / high_52w) - 1) * 100
                dist_ath = ((current_price / ath) - 1) * 100

                st.markdown("**Returns**")
                r_col1, r_col2, r_col3 = st.columns(3)
                r_col1.metric("6M Return", f"{ret_6m:.2f}%" if ret_6m else "N/A")
                r_col2.metric("12M Return", f"{ret_12m:.2f}%" if ret_12m else "N/A")
                r_col3.metric("3Y Return", f"{ret_3y:.2f}%" if ret_3y else "N/A")
                
                st.markdown("**Technical Indicators**")
                t_col1, t_col2, t_col3, t_col4 = st.columns(4)
                t_col1.metric("DMA Crossover", crossover)
                t_col2.metric("Weekly Trend", wema_status)
                t_col3.metric("vs 52W High", f"{dist_52w:.2f}%")
                t_col4.metric("vs ATH", f"{dist_ath:.2f}%")

            except Exception as e:
                st.error(f"⚠️ Technical analysis error: {e}")
