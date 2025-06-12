import streamlit as st
import os
from integrate import ConnectToIntegrate, IntegrateOrders
import pandas as pd

def get_credentials():
    secrets = st.secrets
    return (
        secrets["integrate_api_token"],
        secrets["integrate_api_secret"],
        secrets["integrate_uid"],
        secrets["integrate_actid"],
        secrets["integrate_api_session_key"],
        secrets["integrate_ws_session_key"],
    )

def get_io():
    api_token, api_secret, uid, actid, api_session_key, ws_session_key = get_credentials()
    conn = ConnectToIntegrate()
    conn.login(api_token, api_secret)
    conn.set_session_keys(uid, actid, api_session_key, ws_session_key)
    return IntegrateOrders(conn)

def show_order_book(io):
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

def show_gtt_order_book(io):
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

def show_trade_book(io):
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
            return
        trades = resp.get("trades") or resp.get("data", [])
        if not trades:
            st.info("No trades found.")
        else:
            st.dataframe(pd.DataFrame(trades))
    except Exception as e:
        st.error(f"Failed to get trade book: {e}")

st.title("Order Book & Trade Book")
io = get_io()
show_order_book(io)
show_gtt_order_book(io)
show_trade_book(io)
