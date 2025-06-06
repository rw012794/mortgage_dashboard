import pandas as pd
import plotly.express as px
import streamlit as st
import requests
from bs4 import BeautifulSoup

import yfinance as yf

@st.cache_data(ttl=3600)  # Refresh every hour
def get_live_rates():
    try:
        # 10-Year Treasury Yield (Yahoo: ^TNX is in basis points, divide by 100)
        tnx = yf.Ticker("^TNX")
        treasury_yield = tnx.history(period="1d")["Close"].iloc[-1]

    except Exception as e:
        st.warning(f"⚠️ Error fetching live data: {e}")
        return None, None

def get_30yr_mortgage_rate():
    url = "https://www.nerdwallet.com/mortgages/mortgage-rates"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        page = requests.get(url, headers=headers)
        soup = BeautifulSoup(page.content, "html.parser")

        # Find the element (you may need to update this selector over time)
        rate_span = soup.find("span", string="30-year fixed").find_next("span")
        rate_text = rate_span.text.strip().replace("%", "")
        return float(rate_text)
    except Exception as e:
        print(f"Error fetching mortgage rate: {e}")
        return None
        
        # 30-Year Mortgage Rate — placeholder / static fallback
        # Replace with an actual API or static scrape later
        #mortgage_rate = 6.92  # You can update this manually or automate with another source

        return round(treasury_yield, 2), get_30yr_mortgage_rate


# Load the data
@st.cache_data
def load_data():
    df = pd.read_csv("Mortgage_Rate_Indicators_Forecast.csv", parse_dates=['Date'])
    return df

data = load_data()

st.title("Mortgage Rate Indicators Dashboard")

# Date filter
date_range = st.slider(
    "Select date range:",
    min_value=data['Date'].min().to_pydatetime(),
    max_value=data['Date'].max().to_pydatetime(),
    value=(data['Date'].min().to_pydatetime(), data['Date'].max().to_pydatetime())
)

filtered_data = data[
    (data['Date'] >= pd.to_datetime(date_range[0])) & 
    (data['Date'] <= pd.to_datetime(date_range[1]))
]

# Indicator selection
indicator = st.selectbox("Select indicator to visualize:", data.columns.drop("Date"))

# Plot
fig = px.line(filtered_data, x="Date", y=indicator, title=f"{indicator} Over Time")
st.plotly_chart(fig)

# Correlation heatmap
if st.checkbox("Show Correlation Heatmap"):
    heatmap_data = data.drop(columns=["Date"]).corr()
    st.dataframe(heatmap_data.style.background_gradient(cmap='RdYlGn', axis=None))

import io

# --- Chart Download as PNG ---
try:
    import kaleido
    fig_bytes = io.BytesIO()
    fig.write_image(fig_bytes, format="png")

    st.download_button(
        label="📥 Download Chart as PNG",
        data=fig_bytes.getvalue(),
        file_name=f"{indicator}_chart.png",
        mime="image/png"
    )
except Exception as e:
    st.warning("⚠️ Install 'kaleido' to enable chart download: pip install kaleido")

# --- Excel Export of Filtered Data ---
csv_data = filtered_data.to_csv(index=False).encode('utf-8')

st.download_button(
    label="📊 Download Filtered Data (CSV)",
    data=csv_data,
    file_name="filtered_mortgage_data.csv",
    mime="text/csv"
)

# --- Forecast Alert Message ---
try:
    last_yield = data[data['Date'] == data['Date'].max()]['10Y_Treasury_Yield'].values[0]
    if last_yield > 5.0:
        st.warning("⚠️ 10Y Yield is projected above 5%. Mortgage rates may rise — refinancing could become less favorable.")
    elif last_yield < 3.5:
        st.success("✅ 10Y Yield is projected below 3.5%. Mortgage rates may drop — consider locking in refinancing.")
    else:
        st.info("ℹ️ Mortgage rates are expected to remain stable in the near term.")
except:
    st.info("ℹ️ Forecast alerts will appear here once 10Y Treasury Yield is loaded.")

try:
    forecast_window = filtered_data.copy()
    forecasted_yield = forecast_window['10Y_Treasury_Yield'].iloc[-1]

    # Real-world current rates (can later pull dynamically)
    actual_10Y_yield, actual_mortgage_rate = get_live_rates()
    current_spread = round(actual_mortgage_rate - actual_10Y_yield, 2)

    st.subheader("📌 Investment Guidance")

    # Yield-based guidance
    if forecasted_yield > 5.0:
        st.error("📉 Forecasted 10Y Yield is above 5%.")
        st.write("Mortgage rates may increase. Consider delaying unless urgent.")
    elif forecasted_yield > 4.0:
        st.warning("📊 Forecasted 10Y Yield is between 4% and 5%.")
        st.write("Rates are stable. Lock only if timing matters.")
    else:
        st.success("✅ Forecasted 10Y Yield is below 4%.")
        st.write("Consider locking or refinancing now to capture lower rates.")

    # Spread-based risk analysis
    st.markdown("---")
    st.markdown(f"**📉 Current 10Y Treasury Yield**: {actual_10Y_yield:.2f}%  \n"
                f"**🏦 Current 30Y Mortgage Rate**: {actual_mortgage_rate:.2f}%  \n"
                f"**📊 Current Spread**: {current_spread:.2f}%")

    if current_spread > 2.0:
        st.warning("⚠️ Mortgage rates are elevated due to a higher-than-normal spread.\n\n"
                   "This suggests lenders are pricing in risk premiums — rates may come down even if Treasury yields stay flat.")
    else:
        st.success("✔️ Spread is within normal range. Mortgage pricing aligns with historical expectations.")

    st.caption(f"(Forecasted 10Y Yield: {forecasted_yield:.2f}%)")

except Exception as e:
    st.warning("⚠️ Could not generate investment guidance.")
    st.caption(str(e))
    
