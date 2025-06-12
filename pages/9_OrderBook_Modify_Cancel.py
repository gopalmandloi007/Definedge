import streamlit as st
import requests

# --- LOGIN BLOCK ---
from integrate import ConnectToIntegrate, IntegrateOrders

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

st.title("Modify / Cancel Order from Order Book")

BASE_URL = "https://integrate.definedgesecurities.com/dart/v1"

def get_headers():
    return {"Authorization": api_session_key}

def fetch_order_book():
    url = f"{BASE_URL}/orders"
    r = requests.get(url, headers=get_headers())
    r.raise_for_status()
    return r.json()

@st.cache_data
def get_pending_orders():
    order_book = fetch_order_book()
    orders = order_book.get("orders", [])
    pending_status = {"NEW", "OPEN", "REPLACED"}
    filtered = [
        o for o in orders if o.get("order_status") in pending_status and int(float(o.get("pending_qty", 0))) > 0
    ]
    return filtered

orders = get_pending_orders()
if not orders:
    st.info("No pending orders found.")
else:
    st.dataframe(orders)
    idx = st.number_input("Select order to modify/cancel (1-based)", min_value=1, max_value=len(orders))
    selected = orders[int(idx)-1]
    st.json(selected)
    action = st.selectbox("Action", options=["Modify", "Cancel"])
    if action == "Cancel":
        if st.button("Cancel Order"):
            url = f"{BASE_URL}/cancel/{selected.get('order_id')}"
            resp = requests.get(url, headers=get_headers())
            st.write(resp.json())
    if action == "Modify":
        st.write(f"Current price: {selected.get('price')}, quantity: {selected.get('quantity')}")
        new_price = st.text_input("New Price", value=str(selected.get("price", "")))
        new_qty = st.text_input("New Quantity", value=str(selected.get("quantity", "")))
        trigger_price = st.text_input("Trigger Price (if SL)", value=str(selected.get("trigger_price", "0"))) if selected.get("price_type") in ("SL-LIMIT", "SL-MARKET") else None
        if st.button("Modify Order"):
            payload = {
                "exchange": selected.get("exchange"),
                "order_id": selected.get("order_id"),
                "tradingsymbol": selected.get("tradingsymbol"),
                "quantity": str(new_qty),
                "price": str(new_price),
                "product_type": selected.get("product_type"),
                "order_type": selected.get("order_type"),
                "price_type": selected.get("price_type"),
                "validity": selected.get("validity"),
                "disclosed_quantity": selected.get("disclosed_quantity") or "0",
                "remarks": selected.get("remarks") or "",
            }
            if trigger_price is not None:
                payload["trigger_price"] = str(trigger_price)
            url = f"{BASE_URL}/modify"
            resp = requests.post(url, headers={**get_headers(), "Content-Type": "application/json"}, json=payload)
            st.write(resp.json())
