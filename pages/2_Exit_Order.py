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
    try:
        json_resp = response.json()
    except Exception:
        json_resp = None
    return {
        "status_code": response.status_code,
        "raw_text": response.text,
        "json": json_resp
    }

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

tab = st.radio("Choose source for SELL order:", ["Holdings (NSE only)", "Positions"])

if tab == "Holdings (NSE only)":
    try:
        holdings_resp = fetch_holdings()
        raw_holdings = holdings_resp.get("data", []) if isinstance(holdings_resp, dict) else []
        holdings = flatten_holdings(raw_holdings)
    except Exception as e:
        st.error(f"Failed to fetch holdings: {e}")
        holdings = []
    df = pd.DataFrame(holdings)
    if len(df) == 0:
        st.warning("No holdings available.")
        st.stop()
    st.dataframe(df)
    for i, row in df.iterrows():
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(
                f"**{row['tradingsymbol']}** | Qty: {row['dp_qty']} | Avg Price: {row['avg_buy_price']}"
            )
        with col2:
            if st.button(f"Exit ({row['tradingsymbol']})", key=f"exit_h_{i}"):
                with st.form(f"form_exit_h_{i}", clear_on_submit=True):
                    ltp = fetch_ltp(row["exchange"], row["token"])
                    qty = st.number_input("Enter quantity to SELL", min_value=1, max_value=int(float(row["dp_qty"])), value=int(float(row["dp_qty"])), key=f"qty_h_{i}")
                    order_type = st.selectbox("Order type", ["LIMIT", "MARKET"], key=f"ordertype_h_{i}")
                    price = "0"
                    if order_type == "LIMIT":
                        st.info(f"LTP (Last Traded Price): {ltp}")
                        price = st.text_input("Enter LIMIT price", value=str(ltp), key=f"price_h_{i}")
                    remarks = st.text_input("Remarks (optional)", key=f"remarks_h_{i}")
                    submitted = st.form_submit_button("Place this SELL order")
                    if submitted:
                        order = {
                            "tradingsymbol": str(row["tradingsymbol"]),
                            "exchange": str(row["exchange"]),
                            "order_type": "SELL",
                            "quantity": str(qty),
                            "product_type": "CNC",
                            "price_type": order_type.upper(),
                            "validity": "DAY",
                            "disclosed_quantity": "0",
                            "price": str(price) if order_type == "LIMIT" else "0",
                            "remarks": remarks,
                        }
                        st.info("Outgoing Order Payload:")
                        st.json(order)
                        try:
                            result = place_sell_order(order)
                            st.success("Order API response below:")
                            st.json(result)
                            if not (isinstance(result.get("json"), dict) and ("order_id" in result.get("json", {}) or "status" in result.get("json", {}))):
                                st.warning("Order may not have been placed successfully. Please check order book for status or errors.")
                        except Exception as e:
                            st.error(f"Failed to place order: {e}")

elif tab == "Positions":
    try:
        positions_resp = fetch_positions()
        raw_positions = positions_resp.get("positions", []) if isinstance(positions_resp, dict) else []
        positions = flatten_positions(raw_positions)
    except Exception as e:
        st.error(f"Failed to fetch positions: {e}")
        positions = []
    df = pd.DataFrame(positions)
    if len(df) == 0:
        st.warning("No positions available.")
        st.stop()
    st.dataframe(df)
    for i, row in df.iterrows():
        col1, col2 = st.columns([4, 1])
        with col1:
            st.write(
                f"**{row['tradingsymbol']}** | Qty: {row['net_quantity']} | Avg Price: {row['net_averageprice']}"
            )
        with col2:
            if st.button(f"Exit ({row['tradingsymbol']})", key=f"exit_p_{i}"):
                with st.form(f"form_exit_p_{i}", clear_on_submit=True):
                    ltp = fetch_ltp(row["exchange"], row["token"])
                    max_qty = abs(int(float(row["net_quantity"])))
                    prd = row["product_type"]
                    qty = st.number_input("Enter quantity to SELL", min_value=1, max_value=max_qty, value=max_qty, key=f"qty_p_{i}")
                    order_type = st.selectbox("Order type", ["LIMIT", "MARKET"], key=f"ordertype_p_{i}")
                    price = "0"
                    if order_type == "LIMIT":
                        st.info(f"LTP (Last Traded Price): {ltp}")
                        price = st.text_input("Enter LIMIT price", value=str(ltp), key=f"price_p_{i}")
                    remarks = st.text_input("Remarks (optional)", key=f"remarks_p_{i}")
                    submitted = st.form_submit_button("Place this SELL order")
                    if submitted:
                        order = {
                            "tradingsymbol": str(row["tradingsymbol"]),
                            "exchange": str(row["exchange"]),
                            "order_type": "SELL",
                            "quantity": str(qty),
                            "product_type": prd,
                            "price_type": order_type.upper(),
                            "validity": "DAY",
                            "disclosed_quantity": "0",
                            "price": str(price) if order_type == "LIMIT" else "0",
                            "remarks": remarks,
                        }
                        st.info("Outgoing Order Payload:")
                        st.json(order)
                        try:
                            result = place_sell_order(order)
                            st.success("Order API response below:")
                            st.json(result)
                            if not (isinstance(result.get("json"), dict) and ("order_id" in result.get("json", {}) or "status" in result.get("json", {}))):
                                st.warning("Order may not have been placed successfully. Please check order book for status or errors.")
                        except Exception as e:
                            st.error(f"Failed to place order: {e}")
