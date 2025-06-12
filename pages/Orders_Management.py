import streamlit as st
import math
from integrate import ConnectToIntegrate, IntegrateOrders
import requests

# --- Session/Secrets ---
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

BASE_URL = "https://integrate.definedgesecurities.com/dart/v1"
HEADERS = {"Authorization": api_session_key}

st.set_page_config(page_title="Orders & GTT Management", layout="wide")
st.title("Orders & GTT: Place, Modify, Cancel, and GTT Management")

# --- Sidebar Navigation ---
menu = st.sidebar.radio("Choose Action", [
    "CNC Buy/Sell Order",
    "Modify Existing Order",
    "Place Single GTT Order",
    "Place OCO GTT Order",
    "GTT OCO/Single View-Modify-Cancel"
])

# --- 1. CNC BUY/SELL ORDER ---
if menu == "CNC Buy/Sell Order":
    st.header("Place New CNC Buy/Sell Order")
    with st.form("cnc_order_form"):
        tradingsymbol = st.text_input("Symbol (e.g. SBIN-EQ)", value="HPL-EQ")
        side = st.selectbox("Order Side", ["BUY", "SELL"])
        quantity = st.number_input("Quantity (set 0 if using amount)", min_value=0, value=0, step=1)
        amount = st.number_input("Total Amount (Rs)", min_value=0, value=55000)
        price = st.number_input("Limit Price (for Market, leave as 0)", min_value=0.0, value=588.0)
        price_type = st.selectbox("Price Type", ["LIMIT", "MARKET"])
        exchange = st.selectbox("Exchange", ["NSE", "BSE"])
        validity = st.selectbox("Validity", ["DAY", "IOC"])
        product_type = "CNC"

        submitted = st.form_submit_button("Place Order")
        if submitted:
            try:
                # If user uses amount, calculate qty
                use_amount = amount > 0
                use_price = price if price_type == "LIMIT" and price > 0 else None

                # LTP fetch (optional, only for market/amount orders)
                ltp = None
                if use_amount and (use_price is None or use_price == 0):
                    # Optional: Token mapping; adapt this logic for production
                    token_map = {"TEXRAIL-EQ": "5489", "SBIN-EQ": "3045"}
                    token = token_map.get(tradingsymbol)
                    if token:
                        url = f"{BASE_URL}/quotes/{exchange}/{token}"
                        res = requests.get(url, headers=HEADERS, timeout=10)
                        if res.status_code == 200:
                            ltp = float(res.json().get('ltp'))
                    if ltp:
                        use_price = ltp
                final_qty = int(quantity)
                if use_amount and use_price:
                    final_qty = math.floor(amount / use_price)
                if final_qty < 1:
                    st.error("Order quantity must be at least 1 after calculation.")
                else:
                    order_kwargs = dict(
                        tradingsymbol=tradingsymbol,
                        exchange=conn.EXCHANGE_TYPE_NSE if exchange == "NSE" else conn.EXCHANGE_TYPE_BSE,
                        order_type=conn.ORDER_TYPE_BUY if side == "BUY" else conn.ORDER_TYPE_SELL,
                        price=price,
                        price_type=conn.PRICE_TYPE_LIMIT if price_type == "LIMIT" else conn.PRICE_TYPE_MARKET,
                        product_type=conn.PRODUCT_TYPE_CNC,
                        quantity=final_qty
                    )
                    resp = io.place_order(**order_kwargs)
                    st.success(f"Order Placed! Response: {resp}")
            except Exception as e:
                st.error(f"Order Placement Failed: {e}")

# --- 2. MODIFY EXISTING ORDER ---
elif menu == "Modify Existing Order":
    st.header("Modify Existing Order")
    with st.form("modify_order_form"):
        order_id = st.text_input("Order ID")
        tradingsymbol = st.text_input("Symbol", value="BDL-EQ")
        price = st.number_input("New Price", value=0.0)
        quantity = st.number_input("New Quantity", value=0, step=1)
        price_type = st.selectbox("Price Type", ["LIMIT", "MARKET"])
        exchange = st.selectbox("Exchange", ["NSE", "BSE"])
        order_type = st.selectbox("Order Side", ["BUY", "SELL"])
        product_type = st.selectbox("Product Type", ["CNC", "MIS"])
        submitted = st.form_submit_button("Modify Order")
        if submitted:
            try:
                modify_kwargs = dict(
                    order_id=order_id,
                    price=price,
                    quantity=quantity,
                    price_type=conn.PRICE_TYPE_LIMIT if price_type == "LIMIT" else conn.PRICE_TYPE_MARKET,
                    exchange=conn.EXCHANGE_TYPE_NSE if exchange == "NSE" else conn.EXCHANGE_TYPE_BSE,
                    order_type=conn.ORDER_TYPE_BUY if order_type == "BUY" else conn.ORDER_TYPE_SELL,
                    product_type=conn.PRODUCT_TYPE_CNC if product_type == "CNC" else conn.PRODUCT_TYPE_MIS,
                    tradingsymbol=tradingsymbol,
                )
                resp = io.modify_order(**modify_kwargs)
                st.success(f"Order Modified! Response: {resp}")
            except Exception as e:
                st.error(f"Order modification failed: {e}")

# --- 3. PLACE SINGLE GTT ORDER ---
elif menu == "Place Single GTT Order":
    st.header("Place Single GTT Order")
    with st.form("single_gtt_form"):
        tradingsymbol = st.text_input("Symbol", value="BDL-EQ")
        exchange = st.selectbox("Exchange", ["NSE", "BSE"])
        order_type = st.selectbox("Order Type", ["BUY", "SELL"])
        quantity = st.number_input("Quantity", value=1, step=1)
        trigger_price = st.number_input("Trigger Price", value=1850.0)
        price = st.number_input("Order Price", value=1855.0)
        remarks = st.text_input("Remarks", value="Single GTT via API")
        submitted = st.form_submit_button("Place Single GTT")
        if submitted:
            try:
                order_kwargs = dict(
                    tradingsymbol=tradingsymbol,
                    exchange=conn.EXCHANGE_TYPE_NSE if exchange == "NSE" else conn.EXCHANGE_TYPE_BSE,
                    order_type=conn.ORDER_TYPE_SELL if order_type == "SELL" else conn.ORDER_TYPE_BUY,
                    quantity=str(quantity),
                    alert_price=str(trigger_price),
                    price=str(price),
                    condition="LTP_BELOW"  # Or as your API expects
                )
                resp = io.place_gtt_order(**order_kwargs)
                st.success(f"Single GTT Order Placed! Response: {resp}")
            except Exception as e:
                st.error(f"Single GTT placement failed: {e}")

# --- 4. PLACE OCO GTT ORDER ---
elif menu == "Place OCO GTT Order":
    st.header("Place OCO GTT Order")
    with st.form("oco_gtt_form"):
        tradingsymbol = st.text_input("Symbol", value="MRPL-EQ")
        exchange = st.selectbox("Exchange", ["NSE", "BSE"])
        order_type = st.selectbox("Order Type", ["BUY", "SELL"])
        target_quantity = st.number_input("Target Quantity", value=93, step=1)
        stoploss_quantity = st.number_input("Stoploss Quantity", value=371, step=1)
        target_price = st.number_input("Target Price", value=164.0)
        stoploss_price = st.number_input("Stoploss Price", value=144.0)
        remarks = st.text_input("Remarks", value="OCO GTT via API")
        submitted = st.form_submit_button("Place OCO GTT")
        if submitted:
            try:
                order_kwargs = dict(
                    tradingsymbol=tradingsymbol,
                    exchange=conn.EXCHANGE_TYPE_NSE if exchange == "NSE" else conn.EXCHANGE_TYPE_BSE,
                    order_type=conn.ORDER_TYPE_SELL if order_type == "SELL" else conn.ORDER_TYPE_BUY,
                    target_quantity=str(target_quantity),
                    stoploss_quantity=str(stoploss_quantity),
                    target_price=str(target_price),
                    stoploss_price=str(stoploss_price),
                    remarks=remarks
                )
                resp = io.place_oco_order(**order_kwargs)
                st.success(f"OCO GTT Order Placed! Response: {resp}")
            except Exception as e:
                st.error(f"OCO GTT placement failed: {e}")

# --- 5. GTT OCO/SINGLE VIEW-MODIFY-CANCEL ---
elif menu == "GTT OCO/Single View-Modify-Cancel":
    st.header("GTT OCO/Single: View, Modify, Cancel Orders")
    # 1. Fetch all GTT orders
    try:
        r = requests.get(f"{BASE_URL}/gttorders", headers=HEADERS)
        r.raise_for_status()
        data = r.json()
        orders = data.get("pendingGTTOrderBook") or next((v for v in data.values() if isinstance(v, list)), [])
        if not orders:
            st.info("No GTT orders found.")
        else:
            df = []
            for o in orders:
                df.append({k: o.get(k, "") for k in [
                    "alert_id", "tradingsymbol", "exchange", "order_type", "product_type", "quantity", "price", "trigger_price",
                    "target_price", "target_quantity", "stoploss_price", "stoploss_quantity", "remarks", "order_time"
                ]})
            st.dataframe(df)
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
                    resp = requests.get(url, headers=HEADERS)
                    st.write(resp.json())
            if action == "Modify":
                is_oco = any([selected.get(f) for f in ("stoploss_price", "stoploss_trigger", "target_price", "target_trigger")])
                if is_oco:
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
                        resp = requests.post(url, headers={**HEADERS, "Content-Type": "application/json"}, json=data)
                        st.write(resp.json())
                else:
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
                        resp = requests.post(url, headers={**HEADERS, "Content-Type": "application/json"}, json=data)
                        st.write(resp.json())
    except Exception as e:
        st.error(f"Failed to fetch GTT order book: {e}")
