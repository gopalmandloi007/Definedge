import streamlit as st
import requests
from integrate import ConnectToIntegrate

st.title("GTT OCO/Single Modify & Cancel")

def get_headers():
    session_key = st.secrets["integrate_api_session_key"]
    return {"Authorization": session_key}

BASE_URL = "https://integrate.definedgesecurities.com/dart/v1"

@st.cache_data
def fetch_gtt_orders():
    url = f"{BASE_URL}/gttorders"
    r = requests.get(url, headers=get_headers())
    r.raise_for_status()
    data = r.json()
    if "pendingGTTOrderBook" in data:
        return data["pendingGTTOrderBook"]
    for val in data.values():
        if isinstance(val, list):
            return val
    return []

orders = fetch_gtt_orders()
if not orders:
    st.info("No GTT orders found.")
else:
    df = st.dataframe(orders)
    idx = st.number_input("Select order number to modify/cancel (1-based)", min_value=1, max_value=len(orders))
    selected = orders[int(idx)-1]
    st.json(selected)
    action = st.selectbox("Action", options=["Modify", "Cancel"])
    if action == "Cancel":
        if st.button("Cancel Order"):
            alert_id = selected.get("alert_id")
            is_oco = any([selected.get(f) for f in ("stoploss_price", "stoploss_trigger", "target_price", "target_trigger")])
            if is_oco:
                url = f"{BASE_URL}/ococancel/{alert_id}"
            else:
                url = f"{BASE_URL}/gttcancel/{alert_id}"
            resp = requests.get(url, headers=get_headers())
            st.write(resp.json())
    if action == "Modify":
        if any([selected.get(f) for f in ("stoploss_price", "stoploss_trigger", "target_price", "target_trigger")]):
            # OCO order
            st.write("OCO Order Modification")
            new_target_trigger = st.text_input("Target Trigger", value=str(selected.get('target_trigger', '')))
            new_target_price = st.text_input("Target Price", value=str(selected.get('target_price', '')))
            new_stoploss_trigger = st.text_input("Stoploss Trigger", value=str(selected.get('stoploss_trigger', '')))
            new_stoploss_price = st.text_input("Stoploss Price", value=str(selected.get('stoploss_price', '')))
            new_target_qty = st.text_input("Target Qty", value=str(selected.get('target_quantity', '')))
            new_stoploss_qty = st.text_input("Stoploss Qty", value=str(selected.get('stoploss_quantity', '')))
            if st.button("Modify OCO"):
                data = {
                    "tradingsymbol": selected.get("tradingsymbol"),
                    "exchange": selected.get("exchange"),
                    "order_type": selected.get("order_type"),
                    "target_quantity": new_target_qty,
                    "stoploss_quantity": new_stoploss_qty,
                    "target_price": new_target_price,
                    "stoploss_price": new_stoploss_price,
                    "alert_id": selected.get("alert_id"),
                    "remarks": "modified by Streamlit",
                    "product_type": selected.get("product_type", "CNC"),
                }
                url = f"{BASE_URL}/ocomodify"
                resp = requests.post(url, headers={**get_headers(), "Content-Type": "application/json"}, json=data)
                st.write(resp.json())
        else:
            # Single GTT
            st.write("Single GTT Order Modification")
            new_trigger = st.text_input("Trigger Price", value=str(selected.get('trigger_price', '')))
            new_price = st.text_input("Order Price", value=str(selected.get('price', '')))
            new_qty = st.text_input("Quantity", value=str(selected.get('quantity', '')))
            if st.button("Modify GTT"):
                data = {
                    "exchange": selected.get("exchange"),
                    "alert_id": selected.get("alert_id"),
                    "tradingsymbol": selected.get("tradingsymbol"),
                    "condition": selected.get("condition"),
                    "order_type": selected.get("order_type"),
                    "alert_price": new_trigger,
                    "price": new_price,
                    "quantity": new_qty
                }
                url = f"{BASE_URL}/gttmodify"
                resp = requests.post(url, headers={**get_headers(), "Content-Type": "application/json"}, json=data)
                st.write(resp.json())
