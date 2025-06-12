import streamlit as st
import requests
import pandas as pd

BASE_URL = "https://integrate.definedgesecurities.com/dart/v1"
api_session_key = st.secrets["integrate_api_session_key"]

def get_headers():
    return {"Authorization": api_session_key}

def fetch_holdings():
    url = f"{BASE_URL}/holdings"
    response = requests.get(url, headers=get_headers())
    response.raise_for_status()
    return response.json()

def fetch_positions():
    url = f"{BASE_URL}/positions"
    response = requests.get(url, headers=get_headers())
    response.raise_for_status()
    return response.json()

def fetch_ltp(exchange, token):
    url = f"{BASE_URL}/quotes/{exchange}/{token}"
    try:
        response = requests.get(url, headers=get_headers())
        response.raise_for_status()
        data = response.json()
        ltp = data.get("ltp", "-")
        return ltp
    except Exception:
        return "-"

def place_sell_order(data):
    url = f"{BASE_URL}/placeorder"
    response = requests.post(
        url,
        headers={**get_headers(), "Content-Type": "application/json"},
        json=data
    )
    response.raise_for_status()
    return response.json()

def flatten_holdings(raw_holdings):
    flat = []
    for h in raw_holdings:
        ts_list = h.get("tradingsymbol", [])
        for ts in ts_list:
            if ts.get("exchange") == "NSE":
                flat.append({
                    "tradingsymbol": ts.get("tradingsymbol"),
                    "exchange": ts.get("exchange"),
                    "isin": ts.get("isin"),
                    "dp_qty": h.get("dp_qty"),
                    "avg_buy_price": h.get("avg_buy_price"),
                    "haircut": h.get("haircut"),
                    "t1_qty": h.get("t1_qty"),
                    "holding_used": h.get("holding_used"),
                    "token": ts.get("token", "-"),
                })
    return flat

def flatten_positions(raw_positions):
    flat = []
    for p in raw_positions:
        flat.append({
            "tradingsymbol": p.get("tradingsymbol"),
            "exchange": p.get("exchange"),
            "product_type": p.get("product_type"),
            "net_quantity": p.get("net_quantity"),
            "net_averageprice": p.get("net_averageprice"),
            "realized_pnl": p.get("realized_pnl"),
            "unrealized_pnl": p.get("unrealized_pnl"),
            "token": p.get("token", "-"),
        })
    return flat

st.set_page_config(page_title="Exit Order", layout="wide")
st.title("Exit Direct from Holding / Position")

# Fetch data
try:
    holdings_resp = fetch_holdings()
    raw_holdings = holdings_resp.get("data", []) if isinstance(holdings_resp, dict) else []
    holdings = flatten_holdings(raw_holdings)
except Exception as e:
    st.error(f"Failed to fetch holdings: {e}")
    holdings = []

try:
    positions_resp = fetch_positions()
    raw_positions = positions_resp.get("positions", []) if isinstance(positions_resp, dict) else []
    positions = flatten_positions(raw_positions)
except Exception as e:
    st.error(f"Failed to fetch positions: {e}")
    positions = []

tab = st.radio("Choose source for SELL order:", ["Holdings (NSE only)", "Positions"])

if tab == "Holdings (NSE only)":
    df = pd.DataFrame(holdings)
    st.dataframe(df)
    if len(df) > 0:
        idx = st.selectbox("Select holding to SELL", range(len(df)), format_func=lambda i: f"{df.iloc[i]['tradingsymbol']} ({df.iloc[i]['dp_qty']})")
        selected = df.iloc[idx]
        max_qty = int(float(selected["dp_qty"]))
        ltp = fetch_ltp(selected["exchange"], selected["token"])
        prd = "CNC"
    else:
        st.warning("No holdings available.")
        st.stop()
else:
    df = pd.DataFrame(positions)
    st.dataframe(df)
    if len(df) > 0:
        idx = st.selectbox("Select position to SELL", range(len(df)), format_func=lambda i: f"{df.iloc[i]['tradingsymbol']} ({df.iloc[i]['net_quantity']})")
        selected = df.iloc[idx]
        max_qty = abs(int(float(selected["net_quantity"])))
        ltp = fetch_ltp(selected["exchange"], selected["token"])
        prd = selected["product_type"]
    else:
        st.warning("No positions available.")
        st.stop()

qty = st.number_input("Enter quantity to SELL", min_value=1, max_value=max_qty, value=max_qty)
order_type = st.selectbox("Order type", ["LIMIT", "MARKET"])
price = "0"
if order_type == "LIMIT":
    st.info(f"LTP (Last Traded Price): {ltp}")
    price = st.text_input("Enter LIMIT price", value=str(ltp))
remarks = st.text_input("Remarks (optional)")

order = {
    "tradingsymbol": str(selected["tradingsymbol"]),
    "exchange": str(selected["exchange"]),
    "order_type": "SELL",
    "quantity": str(qty),
    "product_type": prd,
    "price_type": order_type,
    "validity": "DAY",
    "disclosed_quantity": "0",
    "price": str(price) if order_type == "LIMIT" else "0",
    "remarks": remarks,
}

if order_type in ("SL-LIMIT", "SL-MARKET"):
    trigger_price = st.text_input("Enter Trigger Price for Stoploss order")
    order["trigger_price"] = str(trigger_price)

st.subheader("Order details (payload to API):")
st.json(order)

if st.button("Place this SELL order"):
    try:
        result = place_sell_order(order)
        st.success(f"Order placement result: {result}")
    except Exception as e:
        st.error(f"Failed to place order: {e}")
