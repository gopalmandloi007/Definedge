import streamlit as st
import requests
import pandas as pd

BASE_URL = "https://integrate.definedgesecurities.com/dart/v1"
api_session_key = st.secrets["integrate_api_session_key"]

def get_headers():
    return {"Authorization": api_session_key}

def fetch_order_book():
    url = f"{BASE_URL}/orders"
    response = requests.get(url, headers=get_headers())
    response.raise_for_status()
    return response.json()

def fetch_ltp(exchange, token):
    url = f"{BASE_URL}/quotes/{exchange}/{token}"
    try:
        response = requests.get(url, headers=get_headers())
        response.raise_for_status()
        data = response.json()
        return data.get("ltp", "-")
    except Exception:
        return "-"

def cancel_order(order_id):
    url = f"{BASE_URL}/cancel/{order_id}"
    response = requests.get(url, headers=get_headers())
    response.raise_for_status()
    return response.json()

def modify_order(order, new_price, new_qty, new_trigger_price=None):
    url = f"{BASE_URL}/modify"
    payload = {
        "exchange": order.get("exchange"),
        "order_id": order.get("order_id"),
        "tradingsymbol": order.get("tradingsymbol"),
        "quantity": str(new_qty),
        "price": str(new_price),
        "product_type": order.get("product_type"),
        "order_type": order.get("order_type"),
        "price_type": order.get("price_type"),
        "validity": order.get("validity"),
        "disclosed_quantity": order.get("disclosed_quantity") or "0",
        "remarks": order.get("remarks") or "",
    }
    if new_trigger_price is not None:
        payload["trigger_price"] = str(new_trigger_price)
    response = requests.post(
        url, headers={**get_headers(), "Content-Type": "application/json"}, json=payload
    )
    response.raise_for_status()
    return response.json()

def filter_pending_orders(order_book):
    pending_status = {"NEW", "OPEN", "REPLACED"}
    filtered = [
        o for o in order_book
        if o.get("order_status") in pending_status and int(float(o.get("pending_qty", 0))) > 0
    ]
    return filtered

st.set_page_config(page_title="Modify/Cancel Order", layout="wide")
st.title("Order Book: Modify / Cancel Pending Orders")

# Fetch order book
try:
    order_book_resp = fetch_order_book()
    orders = order_book_resp.get("orders", [])
    pending_orders = filter_pending_orders(orders)
except Exception as e:
    st.error(f"Failed to fetch order book: {e}")
    pending_orders = []

if not pending_orders:
    st.info("No pending orders found.")
    st.stop()

df = pd.DataFrame(pending_orders)
show_cols = [
    "order_id", "tradingsymbol", "exchange", "order_type", "price_type", "product_type",
    "quantity", "pending_qty", "filled_qty", "price", "order_status", "order_entry_time"
]
st.dataframe(df[show_cols])

st.write("**Modify / Cancel individual pending orders below:**")

for i, order in enumerate(pending_orders):
    with st.expander(f"Order: {order.get('tradingsymbol')} | {order.get('order_id')} | {order.get('order_status')}"):
        col1, col2, col3 = st.columns([3,1,1])
        with col1:
            st.json(order)
        with col2:
            if st.button("Modify", key=f"modify_{i}"):
                st.session_state[f"modify_{i}_active"] = True
        with col3:
            if st.button("Cancel", key=f"cancel_{i}"):
                try:
                    result = cancel_order(order.get("order_id"))
                    st.success(f"Order cancelled: {result}")
                except Exception as e:
                    st.error(f"Failed to cancel order: {e}")

        # Show modify form if Modify pressed
        if st.session_state.get(f"modify_{i}_active", False):
            st.info("Modify Order Details:")
            ltp = fetch_ltp(order.get("exchange"), order.get("token"))
            new_price = st.text_input("New Price", value=str(order.get("price")), key=f"price_{i}")
            new_qty = st.text_input("New Quantity", value=str(order.get("quantity")), key=f"qty_{i}")
            # Show trigger price only for SL orders
            if order.get("price_type") in ("SL-LIMIT", "SL-MARKET"):
                new_trigger_price = st.text_input("New Trigger Price", value=str(order.get("trigger_price", "0")), key=f"trig_{i}")
            else:
                new_trigger_price = None
            if st.button("Submit Modification", key=f"submitmod_{i}"):
                try:
                    result = modify_order(order, new_price, new_qty, new_trigger_price)
                    st.success(f"Order modified: {result}")
                    # Close the modify form after success
                    st.session_state[f"modify_{i}_active"] = False
                except Exception as e:
                    st.error(f"Failed to modify order: {e}")

        # To reset the form after cancellation or modification
        if st.button("Close", key=f"close_{i}"):
            st.session_state[f"modify_{i}_active"] = False
