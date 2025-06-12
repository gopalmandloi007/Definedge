import streamlit as st
import pandas as pd
from integrate import ConnectToIntegrate, IntegrateOrders

# --- LOGIN BLOCK ---
api_token = st.secrets["integrate_api_token"]
api_secret = st.secrets["integrate_api_secret"]
uid = st.secrets["integrate_uid"]
actid = st.secrets["integrate_actid"]
api_session_key = st.secrets["integrate_api_session_key"]
ws_session_key = st.secrets["integrate_ws_session_key"]

conn = ConnectToIntegrate()
conn.login(api_token, api_secret)
conn.set_session_keys(uid, actid, api_session_key, ws_session_key)
io = IntegrateOrders(conn)

st.title("Order Book & Trade Book")

st.subheader("Regular Order Book")
try:
    resp = io.orders()
    orders = resp.get("orders") or resp.get("data", [])
    if not orders:
        st.info("No regular orders found.")
    else:
        st.dataframe(pd.DataFrame(orders))
except Exception as e:
    st.error(f"Failed to get regular order book: {e}")

st.subheader("GTT & OCO GTT Order Book")
try:
    resp = io.gtt_orders() if hasattr(io, "gtt_orders") else {}
    orders = (
        resp.get("pendingGTTOrderBook")
        or resp.get("gtt_orders")
        or resp.get("data", [])
    )
    if not orders:
        st.info("No GTT orders found.")
    else:
        st.dataframe(pd.DataFrame(orders))
except Exception as e:
    st.error(f"Failed to get GTT order book: {e}")

st.subheader("Trade Book")
try:
    if hasattr(io, "trade_book"):
        resp = io.trade_book()
    elif hasattr(io, "trades"):
        resp = io.trades()
    elif hasattr(io, "tradebook"):
        resp = io.tradebook()
    else:
        st.warning("No trade book method found in IntegrateOrders. Please check method name.")
        resp = {}
    trades = resp.get("trades") or resp.get("data", [])
    if not trades:
        st.info("No trades found.")
    else:
        st.dataframe(pd.DataFrame(trades))
except Exception as e:
    st.error(f"Failed to get trade book: {e}")
